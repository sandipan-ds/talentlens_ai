"""JD ↔ resume chunk matching.

A Job Description is parsed into a list of *requirements* (one per
section / bullet). For each requirement we retrieve the top-K most similar
chunks from the vector index, then aggregate per candidate:

* ``best_score`` — highest similarity across any chunk for that candidate
* ``avg_score``  — mean similarity across the top-N chunks
* ``evidence``   — list of cited chunk metadata + a snippet of text

The final output is a ranked candidate list per JD, with evidence. The
deterministic recruiter-weighted score (Phase 4) is computed separately;
this module provides the *retrieval* half of the pipeline.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .retriever import retrieve


ROOT = Path(__file__).resolve().parents[2]
JD_DIR = ROOT / "data" / "Job descriptions"

# Common JD section headings that signal a *requirement* block. We split
# the JD text on these so each requirement is its own query.
_REQUIREMENT_SECTION_TITLES = {
    "required skills",
    "preferred skills",
    "requirements",
    "required qualifications",
    "preferred qualifications",
    "qualifications",
    "experience",
    "education",
    "must have",
    "nice to have",
    "key responsibilities",
    "responsibilities",
    "role overview",
    "what you'll do",
    "what you'll need",
    "skills",
}


@dataclass
class Requirement:
    """One requirement extracted from a JD."""

    text: str
    section: str  # e.g. "Required Skills"
    required: bool = True  # True for required, False for preferred


@dataclass
class CandidateMatch:
    """Aggregated match information for one candidate against a JD."""

    candidate_id: str
    role_bucket: str
    best_score: float = 0.0
    avg_score: float = 0.0
    requirements_matched: int = 0
    requirements_total: int = 0
    evidence: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "role_bucket": self.role_bucket,
            "best_score": round(self.best_score, 4),
            "avg_score": round(self.avg_score, 4),
            "requirements_matched": self.requirements_matched,
            "requirements_total": self.requirements_total,
            "evidence": self.evidence,
        }


# ---------------------------------------------------------------------------
# JD parsing
# ---------------------------------------------------------------------------


def load_jd_text(jd_path: Path) -> str:
    """Read a JD file as text. Supports .md / .txt."""
    return jd_path.read_text(encoding="utf-8", errors="ignore")


def split_jd_into_requirements(jd_text: str) -> List[Requirement]:
    """Naive splitter: split JD on H2 headings + bullets.

    Returns one :class:`Requirement` per bullet point, tagged with the
    section it came from. ``required`` is False for "preferred" sections.
    """
    lines = jd_text.splitlines()
    current_section = "Role Overview"
    requirements: List[Requirement] = []
    # Detect H2 headings ("## ...").
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            heading = line.lstrip("#").strip()
            current_section = heading or current_section
            continue
        # Bullets become individual requirements.
        bullet_match = re.match(r"^[-*•\d.\)]\s+(.*)$", line)
        if bullet_match:
            text = bullet_match.group(1).strip()
            if not text:
                continue
            required = not any(
                tag in current_section.lower()
                for tag in ("preferred", "nice to have", "optional")
            )
            requirements.append(Requirement(text=text, section=current_section, required=required))
            continue
        # Long descriptive lines in the Role Overview become a single
        # requirement so the vector index sees them as queries too.
        if len(line.split()) > 6 and current_section.lower() in {
            "role overview",
            "key responsibilities",
            "responsibilities",
        }:
            required = not any(
                tag in current_section.lower()
                for tag in ("preferred", "nice to have", "optional")
            )
            requirements.append(Requirement(text=line, section=current_section, required=required))
    return requirements


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------


def match_requirements_to_candidates(
    requirements: List[Requirement],
    top_k_per_requirement: int = 5,
    score_threshold: float = 0.30,
    role_bucket: Optional[str] = None,
) -> Dict[str, CandidateMatch]:
    """For each requirement, retrieve top-K chunks and aggregate per candidate."""
    by_candidate: Dict[str, CandidateMatch] = {}
    for req in requirements:
        hits = retrieve(req.text, top_k=top_k_per_requirement, role_bucket=role_bucket)
        # Bucket hits per candidate.
        per_candidate_hits: Dict[str, List[Dict[str, Any]]] = {}
        for hit in hits:
            per_candidate_hits.setdefault(hit["candidate_id"], []).append(hit)

        for cand_id, cand_hits in per_candidate_hits.items():
            match = by_candidate.setdefault(
                cand_id,
                CandidateMatch(
                    candidate_id=cand_id,
                    role_bucket=cand_hits[0]["role_bucket"],
                ),
            )
            match.requirements_total += 1
            best = max(h["score"] for h in cand_hits)
            if best >= score_threshold:
                match.requirements_matched += 1
            for h in cand_hits:
                if h["score"] > match.best_score:
                    match.best_score = h["score"]
                # Keep evidence sorted by score desc, capped to top 8.
                match.evidence.append(
                    {
                        "chunk_id": h["chunk_id"],
                        "section": h["section"],
                        "score": round(h["score"], 4),
                        "requirement": req.text,
                        "requirement_section": req.section,
                        "required": req.required,
                        "snippet": h["text"][:240],
                    }
                )
            match.evidence.sort(key=lambda e: e["score"], reverse=True)
            match.evidence = match.evidence[:8]

    # Compute avg_score per candidate.
    for match in by_candidate.values():
        scores = [e["score"] for e in match.evidence]
        match.avg_score = sum(scores) / len(scores) if scores else 0.0
    return by_candidate


def rank_candidates(matches: Dict[str, CandidateMatch]) -> List[CandidateMatch]:
    """Rank candidates by a blended score: 0.6*best + 0.4*avg, tie-break by matched count."""
    def key(m: CandidateMatch):
        return (
            0.6 * m.best_score + 0.4 * m.avg_score,
            m.requirements_matched,
        )

    return sorted(matches.values(), key=key, reverse=True)


def match_jd(jd_path: Path, role_bucket: Optional[str] = None, top_k: int = 5) -> Dict[str, Any]:
    """End-to-end: parse JD, match, rank.

    Returns a JSON-serializable dict::

        {
          "jd_file": "...",
          "requirements": [...],
          "matches": [CandidateMatch.to_dict(), ...]   # ranked desc
        }
    """
    jd_text = load_jd_text(jd_path)
    requirements = split_jd_into_requirements(jd_text)
    matches = match_requirements_to_candidates(requirements, role_bucket=role_bucket)
    ranked = rank_candidates(matches)
    return {
        "jd_file": str(jd_path.name),
        "requirement_count": len(requirements),
        "candidates_considered": len(ranked),
        "matches": [m.to_dict() for m in ranked[:top_k]],
    }
