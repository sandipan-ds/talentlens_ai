"""Semantic (cosine-similarity) candidate evaluation engine.

This is the second of two scoring strategies shipped in HireIntel AI:

* :mod:`src.scoring.keyword_scorer` — deterministic keyword + heuristic
  matching against recruiter-defined weight items (binary, exact-match).
* :mod:`src.scoring.semantic_scorer` — **this module.** Each JD bullet is
  embedded; the candidate's own chunks are queried; the best-matching chunk
  per bullet becomes the candidate's "answer" to that requirement.

Scoring formula (per design discussion, ``docs/AI_DESIGN_RATIONALE.md``):

* For each JD bullet ``b_i``:
  - embed ``b_i`` (MiniLM-L6, 384-dim, unit-norm).
  - take ``sim_i = max cosine(b_i, candidate.chunks)``.
  - record the supporting chunk (id, snippet, source file).
* ``semantic_score = mean(sim_i for all i) * 100``.

Output schema is identical to the keyword scorer's :class:`CandidateScore`
so downstream consumers (Phase 5 ranking, recruiter UI) do not care which
strategy produced the score.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src.rag.embeddings import embed_texts
from src.rag.index import CHUNKS_DIR


# ---------------------------------------------------------------------------
# Score component (re-uses keyword scorer's shape so downstream code is
# strategy-agnostic).
# ---------------------------------------------------------------------------


@dataclass
class SemanticComponent:
    """One JD bullet scored against the candidate's chunks."""

    category: str  # JD section heading, e.g. "Key Responsibilities"
    item_name: str  # the JD bullet text itself
    importance: float = 1.0  # bullets are equally weighted by default
    matched: bool = True  # bullets always produce a score (cosine is continuous)
    matched_weight: float = 0.0  # raw cosine value
    chunk_id: Optional[str] = None
    snippet: Optional[str] = None
    source_file: Optional[str] = None
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "item_name": self.item_name,
            "importance": self.importance,
            "matched": self.matched,
            "matched_weight": round(self.matched_weight, 4),
            "chunk_id": self.chunk_id,
            "snippet": self.snippet,
            "source_file": self.source_file,
            "notes": self.notes,
        }


@dataclass
class SemanticScore:
    """Aggregate semantic score for one candidate against a JD's bullets."""

    candidate_id: str
    role_bucket: str
    raw_score: float  # mean cosine
    max_score: float = 100.0
    normalized_score: float = 0.0  # raw * 100
    scale_factor: float = 100.0
    components: List[SemanticComponent] = field(default_factory=list)
    source_file: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "role_bucket": self.role_bucket,
            "source_file": self.source_file,
            "raw_score": round(self.raw_score, 4),
            "max_score": round(self.max_score, 4),
            "normalized_score": round(self.normalized_score, 4),
            "scale_factor": round(self.scale_factor, 4),
            "components": [c.to_dict() for c in self.components],
            "matched_components": len(self.components),
            "total_components": len(self.components),
        }


# ---------------------------------------------------------------------------
# JD bullet extraction
# ---------------------------------------------------------------------------


def _load_jd_bullets(jd_path: Path) -> List[Tuple[str, str]]:
    """Read a JD markdown file and return ``[(section, bullet_text), ...]``.

    Each H2 heading starts a new section. Bulleted lines (``-``, ``*``,
    numbered ``1.``) become individual bullets. Long descriptive paragraphs
    under section titles like "Role Overview" also become a single bullet so
    they aren't dropped from the scoring loop.
    """
    import re

    text = jd_path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    current_section = "Role Overview"
    bullets: List[Tuple[str, str]] = []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            current_section = line.lstrip("#").strip() or current_section
            continue
        bullet_match = re.match(r"^[-*•]\s+(.*)$", line) or re.match(
            r"^\d+\.\s+(.*)$", line
        )
        if bullet_match:
            content = bullet_match.group(1).strip()
            if content:
                bullets.append((current_section, content))
            continue
        # Long descriptive paragraph in 'Role Overview' / 'Key Responsibilities'
        # etc. → keep as one bullet so it gets a chance to match.
        if len(line.split()) > 6 and current_section.lower() in {
            "role overview",
            "key responsibilities",
            "responsibilities",
        }:
            bullets.append((current_section, line))
    return bullets


# ---------------------------------------------------------------------------
# Chunk loading
# ---------------------------------------------------------------------------


def _load_candidate_chunks(role_bucket: str, candidate_id: str) -> List[Dict[str, Any]]:
    """Load the JSONL chunks belonging to a single candidate."""
    chunk_path = CHUNKS_DIR / role_bucket / f"{candidate_id}.jsonl"
    chunks: List[Dict[str, Any]] = []
    if not chunk_path.exists():
        return chunks
    with chunk_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            chunks.append(json.loads(line))
    return chunks


# ---------------------------------------------------------------------------
# Per-candidate semantic scoring
# ---------------------------------------------------------------------------


def score_candidate_semantic(
    candidate_id: str,
    role_bucket: str,
    jd_bullets: List[Tuple[str, str]],
    source_file: Optional[str] = None,
) -> SemanticScore:
    """Score one candidate against a list of (section, bullet) tuples.

    For each bullet:
      * embed the bullet text
      * cosine against every chunk of this candidate
      * record the best match (chunk_id, similarity, snippet)

    The candidate's semantic score is the mean similarity across all bullets,
    expressed on a 0-100 scale.

    If the candidate has no chunks on disk, returns a score of 0 with a
    single "no chunks" component so the row still appears in the ranking.
    """
    chunks = _load_candidate_chunks(role_bucket, candidate_id)
    components: List[SemanticComponent] = []

    if not chunks:
        components.append(
            SemanticComponent(
                category="(no chunks)",
                item_name="(no chunks indexed for this candidate)",
                matched_weight=0.0,
                notes="No chunks found in data/chunks/<role>/<candidate>.jsonl",
            )
        )
        return SemanticScore(
            candidate_id=candidate_id,
            role_bucket=role_bucket,
            raw_score=0.0,
            normalized_score=0.0,
            components=components,
            source_file=source_file,
        )

    # Pre-compute candidate chunk embeddings once (small per-candidate set).
    chunk_texts = [(c.get("text") or "").strip() or " " for c in chunks]
    chunk_vectors = embed_texts(chunk_texts)
    # Pre-normalize defensively (embed_texts already returns unit-norm).
    norms = np.linalg.norm(chunk_vectors, axis=1, keepdims=True)
    norms = np.clip(norms, 1e-12, None)
    chunk_vectors = chunk_vectors / norms

    similarities: List[float] = []
    for section, bullet in jd_bullets:
        query_vec = embed_texts([bullet])[0]
        q_norm = np.linalg.norm(query_vec)
        if q_norm > 1e-12:
            q = query_vec / q_norm
        else:
            q = query_vec
        sims = chunk_vectors @ q  # shape: (n_chunks,)
        best_idx = int(np.argmax(sims))
        best_sim = float(sims[best_idx])
        best_chunk = chunks[best_idx]
        similarities.append(best_sim)
        components.append(
            SemanticComponent(
                category=section,
                item_name=bullet,
                matched_weight=best_sim,
                chunk_id=best_chunk.get("chunk_id"),
                snippet=(best_chunk.get("text") or "")[:240],
                source_file=best_chunk.get("source_file"),
                notes=f"cosine={best_sim:.3f} against chunk section='{best_chunk.get('section','')}'",
            )
        )

    mean_sim = float(np.mean(similarities)) if similarities else 0.0
    return SemanticScore(
        candidate_id=candidate_id,
        role_bucket=role_bucket,
        raw_score=mean_sim,
        normalized_score=mean_sim * 100.0,
        components=components,
        source_file=source_file,
    )


def rank_semantic(scores: List[SemanticScore]) -> List[SemanticScore]:
    """Rank candidates by normalized semantic score (desc)."""
    return sorted(scores, key=lambda s: s.normalized_score, reverse=True)


# ---------------------------------------------------------------------------
# Batch semantic scoring for one role
# ---------------------------------------------------------------------------


def evaluate_role_semantic(
    role_bucket: str,
    jd_path: Path,
    output_path: Optional[Path] = None,
    profile_loader=None,
) -> List[Dict[str, Any]]:
    """Score every profile in ``data/processed/<role>/`` against the JD's bullets.

    Args:
        role_bucket: e.g. ``"BusinessAnalyst"``.
        jd_path: Path to the JD markdown file.
        output_path: Optional path to write ranked JSON.
        profile_loader: Optional callable ``(role_bucket) -> List[profile]``.
            Defaults to :func:`keyword_scorer.load_profiles_for_role`.

    Returns:
        Ranked list of score dicts.
    """
    if profile_loader is None:
        from .keyword_scorer import load_profiles_for_role as profile_loader

    profiles = profile_loader(role_bucket)
    jd_bullets = _load_jd_bullets(jd_path)

    scores: List[SemanticScore] = []
    for profile in profiles:
        cand_id = profile.get("candidate_id") or ""
        scores.append(
            score_candidate_semantic(
                candidate_id=cand_id,
                role_bucket=role_bucket,
                jd_bullets=jd_bullets,
                source_file=profile.get("source_file"),
            )
        )
    ranked = rank_semantic(scores)
    results = [s.to_dict() for s in ranked]
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as fh:
            json.dump(results, fh, ensure_ascii=False, indent=2)
    return results
