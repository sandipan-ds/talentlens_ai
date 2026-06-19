"""Document-Aware chunker for parsed resume profiles.

Each parsed profile (see ``src.resume_parsing.parser.parse_resume``) is split
into a list of ``ChunkRecord`` objects. The chunker treats *resume sections*
as the natural semantic units:

* one chunk per experience entry
* one chunk per education entry
* one chunk per project
* one chunk per free-text section (summary, skills, certifications,
  languages, "other")

Very large chunks (> ``MAX_CHUNK_CHARS``) are sub-split on paragraph breaks
with a small overlap so the embedding model never receives text larger than
its context window.

The output of :func:`chunk_profile` is a list of dictionaries matching the
schema documented in ``docs/AI_ARCHITECTURE.md`` § Document-Aware Chunking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------

# Soft upper bound for a single chunk. We split when a section is larger
# than this so embedding models with small context windows are happy.
MAX_CHUNK_CHARS: int = 1200

# Overlap applied when sub-splitting an oversized chunk. Kept small because
# sub-splits only happen on big free-text sections; we want each resulting
# chunk to remain a coherent unit.
SPLIT_OVERLAP_CHARS: int = 120


@dataclass
class ChunkRecord:
    """One chunk of a resume, ready for embedding + retrieval."""

    chunk_id: str
    candidate_id: str
    role_bucket: str
    source_file: str
    section: str
    chunk_index: int
    text: str
    char_span: Tuple[int, int]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "candidate_id": self.candidate_id,
            "role_bucket": self.role_bucket,
            "source_file": self.source_file,
            "section": self.section,
            "chunk_index": self.chunk_index,
            "text": self.text,
            "char_span": list(self.char_span),
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def chunk_profile(profile: Dict[str, Any], role_bucket: str = "") -> List[ChunkRecord]:
    """Convert one parsed profile into a list of chunk records.

    Args:
        profile:
            A parsed resume dict as produced by
            ``src.resume_parsing.parser.parse_resume``.
        role_bucket:
            The role folder the resume was filed under
            (``"BusinessAnalyst"``, ``"DataScience"`` ...). Used as a
            metadata field so the vector store can be filtered by role.

    Returns:
        List of :class:`ChunkRecord`. Order is deterministic: summary,
        experience entries, education entries, projects, skills,
        certifications, languages, other free-text sections.
    """
    candidate_id = profile.get("candidate_id") or "cand_unknown"
    source_file = profile.get("source_file", "")

    chunks: List[ChunkRecord] = []

    # ---- 1) Summary ---------------------------------------------------
    summary = profile.get("summary") or {}
    summary_text = (summary.get("value") or "").strip()
    if summary_text:
        chunks.extend(
            _emit_section_chunks(
                profile=profile,
                candidate_id=candidate_id,
                role_bucket=role_bucket,
                source_file=source_file,
                section_name="summary",
                text=summary_text,
                char_span=None,
                metadata={},
            )
        )

    # ---- 2) Experience (one chunk per entry) --------------------------
    experience = profile.get("experience") or {}
    experience_records = experience.get("entries") or []
    for i, entry in enumerate(experience_records):
        text = _entry_to_text(entry)
        if not text:
            continue
        chunks.append(
            ChunkRecord(
                chunk_id=f"{candidate_id}__experience__{i}",
                candidate_id=candidate_id,
                role_bucket=role_bucket,
                source_file=source_file,
                section="experience",
                chunk_index=i,
                text=text,
                char_span=(0, len(text)),
                metadata={
                    "title": entry.get("title"),
                    "company": entry.get("company"),
                    "dates": entry.get("dates"),
                    "location": entry.get("location"),
                    "bullet_count": len(entry.get("details") or []),
                },
            )
        )

    # ---- 3) Education (one chunk per entry) ---------------------------
    education = profile.get("education") or {}
    education_records = education.get("entries") or []
    for i, entry in enumerate(education_records):
        text = (entry.get("description") or "").strip()
        if not text:
            continue
        chunks.append(
            ChunkRecord(
                chunk_id=f"{candidate_id}__education__{i}",
                candidate_id=candidate_id,
                role_bucket=role_bucket,
                source_file=source_file,
                section="education",
                chunk_index=i,
                text=text,
                char_span=(0, len(text)),
                metadata={"description": text},
            )
        )

    # ---- 4) Projects --------------------------------------------------
    projects = profile.get("projects") or []
    for i, project_text in enumerate(projects):
        text = (project_text or "").strip()
        if not text:
            continue
        chunks.append(
            ChunkRecord(
                chunk_id=f"{candidate_id}__projects__{i}",
                candidate_id=candidate_id,
                role_bucket=role_bucket,
                source_file=source_file,
                section="projects",
                chunk_index=i,
                text=text,
                char_span=(0, len(text)),
                metadata={},
            )
        )

    # ---- 5) Skills, certifications, languages (single chunk each) -----
    list_fields = {
        "skills": profile.get("skills") or [],
        "certifications": profile.get("certifications") or [],
        "languages": profile.get("languages") or [],
    }
    for field_name, items in list_fields.items():
        items_clean = [str(x).strip() for x in items if str(x).strip()]
        if not items_clean:
            continue
        text = ", ".join(items_clean)
        chunks.append(
            ChunkRecord(
                chunk_id=f"{candidate_id}__{field_name}__0",
                candidate_id=candidate_id,
                role_bucket=role_bucket,
                source_file=source_file,
                section=field_name,
                chunk_index=0,
                text=text,
                char_span=(0, len(text)),
                metadata={"items": items_clean, "count": len(items_clean)},
            )
        )

    # ---- 6) Any free-text section not yet covered ---------------------
    sections = profile.get("sections") or {}
    emitted_section_names = {
        "summary",
        "experience",
        "education",
        "projects",
        "skills",
        "certifications",
        "languages",
    }
    for section_name, record in sections.items():
        if section_name in emitted_section_names:
            continue
        section_text = (record.get("text") or "").strip()
        if not section_text:
            continue
        start = int(record.get("start", 0))
        end = int(record.get("end", start + len(section_text)))
        chunks.extend(
            _emit_section_chunks(
                profile=profile,
                candidate_id=candidate_id,
                role_bucket=role_bucket,
                source_file=source_file,
                section_name=section_name,
                text=section_text,
                char_span=(start, end),
                metadata={},
            )
        )

    return chunks


def chunks_to_jsonl(chunks: Iterable[ChunkRecord]) -> str:
    """Serialize chunks to a JSONL string (one JSON object per line)."""
    import json

    return "\n".join(json.dumps(c.to_dict(), ensure_ascii=False) for c in chunks)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _entry_to_text(entry: Dict[str, Any]) -> str:
    """Render an experience/education entry as a single human-readable block."""
    parts: List[str] = []
    title = (entry.get("title") or "").strip()
    company = (entry.get("company") or "").strip()
    if title and company:
        parts.append(f"{title} @ {company}")
    elif title:
        parts.append(title)
    elif company:
        parts.append(company)
    dates = (entry.get("dates") or "").strip()
    location = (entry.get("location") or "").strip()
    if dates or location:
        meta = " | ".join(x for x in (dates, location) if x)
        parts.append(meta)
    details = [d.strip() for d in (entry.get("details") or []) if d and d.strip()]
    for bullet in details:
        parts.append(f"- {bullet}")
    return "\n".join(parts).strip()


def _emit_section_chunks(
    *,
    profile: Dict[str, Any],
    candidate_id: str,
    role_bucket: str,
    source_file: str,
    section_name: str,
    text: str,
    char_span: Optional[Tuple[int, int]],
    metadata: Dict[str, Any],
) -> List[ChunkRecord]:
    """Emit one or more chunk records for a free-text section.

    Sections shorter than ``MAX_CHUNK_CHARS`` produce a single chunk. Larger
    sections are split on paragraph breaks with a small overlap so we never
    emit a chunk larger than the embedding model's comfortable context.
    """
    text = text.strip()
    if not text:
        return []

    if len(text) <= MAX_CHUNK_CHARS:
        return [
            ChunkRecord(
                chunk_id=f"{candidate_id}__{section_name}__0",
                candidate_id=candidate_id,
                role_bucket=role_bucket,
                source_file=source_file,
                section=section_name,
                chunk_index=0,
                text=text,
                char_span=char_span or (0, len(text)),
                metadata=dict(metadata),
            )
        ]

    # Sub-split: walk through paragraph breaks and accumulate up to the
    # soft cap, leaving ``SPLIT_OVERLAP_CHARS`` overlap between consecutive
    # chunks for retrieval continuity.
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    pieces: List[str] = []
    current = ""
    for para in paragraphs:
        candidate = (current + "\n\n" + para).strip() if current else para
        if len(candidate) <= MAX_CHUNK_CHARS:
            current = candidate
            continue
        if current:
            pieces.append(current)
            # Start next piece with overlap from the previous tail.
            tail = current[-SPLIT_OVERLAP_CHARS:] if len(current) > SPLIT_OVERLAP_CHARS else current
            current = (tail + "\n\n" + para).strip()
        else:
            # Single paragraph is itself too long — hard-split on sentences.
            current = para[:MAX_CHUNK_CHARS]
            pieces.append(current)
            current = para[MAX_CHUNK_CHARS - SPLIT_OVERLAP_CHARS :]
    if current:
        pieces.append(current)

    out: List[ChunkRecord] = []
    cursor = 0
    for i, piece in enumerate(pieces):
        # Locate piece within char_span (best-effort; offsets are advisory).
        if char_span:
            absolute_start = char_span[0] + text.find(piece, cursor)
            if absolute_start == char_span[0] - 1:
                absolute_start = char_span[0]
            absolute_end = absolute_start + len(piece)
        else:
            absolute_start = 0
            absolute_end = len(piece)
        cursor += len(piece)
        out.append(
            ChunkRecord(
                chunk_id=f"{candidate_id}__{section_name}__{i}",
                candidate_id=candidate_id,
                role_bucket=role_bucket,
                source_file=source_file,
                section=section_name,
                chunk_index=i,
                text=piece,
                char_span=(absolute_start, absolute_end),
                metadata=dict(metadata),
            )
        )
    return out
