"""Evidence aggregation and explanation helpers for scored candidates.

Used by the recruiter UI / Phase 5 ranking view to answer:

* "Why did this candidate receive this score?"
* "Which resume chunks support the score?"
* "Which components are missing?"
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .evaluate import CandidateScore, ScoreComponent


@dataclass
class EvidenceCard:
    """One recruiter-facing explanation card per score component."""

    category: str
    item_name: str
    description: str
    importance: int
    matched: bool
    matched_weight: float
    chunk_id: Optional[str]
    snippet: Optional[str]
    source_file: Optional[str]
    notes: str

    @classmethod
    def from_component(cls, c: ScoreComponent) -> "EvidenceCard":
        return cls(
            category=c.category,
            item_name=c.item_name,
            description=c.description,
            importance=c.importance,
            matched=c.matched,
            matched_weight=c.matched_weight,
            chunk_id=c.chunk_id,
            snippet=c.snippet,
            source_file=c.source_file,
            notes=c.notes,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "item_name": self.item_name,
            "description": self.description,
            "importance": self.importance,
            "matched": self.matched,
            "matched_weight": round(self.matched_weight, 4),
            "chunk_id": self.chunk_id,
            "snippet": self.snippet,
            "source_file": self.source_file,
            "notes": self.notes,
        }


def build_evidence(score: CandidateScore) -> Dict[str, Any]:
    """Build the recruiter-facing evidence view for one scored candidate."""
    matched = [EvidenceCard.from_component(c) for c in score.components if c.matched]
    missing = [EvidenceCard.from_component(c) for c in score.components if not c.matched]
    grouped_matched: Dict[str, List[EvidenceCard]] = {}
    for card in matched:
        grouped_matched.setdefault(card.category, []).append(card)
    grouped_missing: Dict[str, List[EvidenceCard]] = {}
    for card in missing:
        grouped_missing.setdefault(card.category, []).append(card)

    return {
        "candidate_id": score.candidate_id,
        "role_bucket": score.role_bucket,
        "raw_score": round(score.raw_score, 4),
        "normalized_score": round(score.normalized_score, 4),
        "max_score": round(score.max_score, 4),
        "scale_factor": round(score.scale_factor, 4),
        "matched_components": len(matched),
        "total_components": len(score.components),
        "matched_by_category": {k: [c.to_dict() for c in v] for k, v in grouped_matched.items()},
        "missing_by_category": {k: [c.to_dict() for c in v] for k, v in grouped_missing.items()},
    }


def explain_candidate(score: CandidateScore) -> str:
    """Return a human-readable summary of why this candidate received this score.

    Used as a fallback when an LLM is not yet integrated for explanation
    generation. The output is stable, deterministic, and useful for tests.
    """
    lines: List[str] = []
    lines.append(
        f"Candidate {score.candidate_id} ({score.role_bucket}) scored "
        f"{score.normalized_score:.1f}/100 "
        f"(raw {score.raw_score:.1f} / {score.max_score:.1f}, scale {score.scale_factor:.3f})."
    )
    matched = [c for c in score.components if c.matched]
    missing = [c for c in score.components if not c.matched]
    lines.append(
        f"Matched {len(matched)} of {len(score.components)} weighted items."
    )
    if matched:
        lines.append("Top matched items:")
        for c in sorted(matched, key=lambda x: x.importance, reverse=True)[:5]:
            line = f"  - [{c.category}] {c.item_name} (+{c.importance}) — {c.notes}"
            if c.chunk_id:
                line += f" [chunk: {c.chunk_id}]"
            lines.append(line)
    if missing:
        lines.append("Top gaps (high-importance items not matched):")
        for c in sorted(missing, key=lambda x: x.importance, reverse=True)[:5]:
            lines.append(f"  - [{c.category}] {c.item_name} (worth {c.importance}) — {c.notes}")
    return "\n".join(lines)

