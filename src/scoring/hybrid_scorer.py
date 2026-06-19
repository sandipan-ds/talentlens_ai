"""Hybrid (keyword + semantic) scoring engine.

Combines the deterministic keyword scorer with the semantic cosine scorer.
The blend is governed by ``alpha`` (weight on the keyword score):

    final_score = alpha * keyword_score + (1 - alpha) * semantic_score

Default ``alpha = 0.5`` (equal blend) per design discussion. Recruiters can
override via the CLI (``--alpha``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .keyword_scorer import CandidateScore, evaluate_candidate, load_weight_config
from .semantic_scorer import SemanticScore


@dataclass
class HybridScore:
    """Combined score for one candidate across both strategies."""

    candidate_id: str
    role_bucket: str
    keyword_score: float
    semantic_score: float
    final_score: float
    alpha: float
    keyword_components: List[Dict[str, Any]] = field(default_factory=list)
    semantic_components: List[Dict[str, Any]] = field(default_factory=list)
    source_file: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "role_bucket": self.role_bucket,
            "source_file": self.source_file,
            "keyword_score": round(self.keyword_score, 4),
            "semantic_score": round(self.semantic_score, 4),
            "final_score": round(self.final_score, 4),
            "alpha": self.alpha,
            "keyword_components": self.keyword_components,
            "semantic_components": self.semantic_components,
        }


def blend(keyword_norm: float, semantic_norm: float, alpha: float) -> float:
    """Linearly blend two 0-100 scores with ``alpha`` weight on keyword."""
    if not 0.0 <= alpha <= 1.0:
        raise ValueError(f"alpha must be in [0, 1], got {alpha}")
    return alpha * keyword_norm + (1.0 - alpha) * semantic_norm


def build_hybrid_score(
    keyword: CandidateScore,
    semantic: SemanticScore,
    alpha: float = 0.5,
) -> HybridScore:
    """Blend one keyword score and one semantic score into a hybrid score."""
    final = blend(keyword.normalized_score, semantic.normalized_score, alpha)
    return HybridScore(
        candidate_id=keyword.candidate_id,
        role_bucket=keyword.role_bucket or semantic.role_bucket,
        keyword_score=keyword.normalized_score,
        semantic_score=semantic.normalized_score,
        final_score=final,
        alpha=alpha,
        keyword_components=[c.to_dict() for c in keyword.components],
        semantic_components=[c.to_dict() for c in semantic.components],
        source_file=keyword.source_file or semantic.source_file,
    )


def rank_hybrid(scores: List[HybridScore]) -> List[HybridScore]:
    """Rank by final_score desc, ties broken by keyword_score desc."""
    return sorted(
        scores,
        key=lambda s: (s.final_score, s.keyword_score),
        reverse=True,
    )


def evaluate_role_hybrid(
    role_bucket: str,
    jd_path: Path,
    weight_config_path: Path,
    alpha: float = 0.5,
    output_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """End-to-end: load profiles, run both scorers, blend, rank, optionally write.

    Args:
        role_bucket: e.g. ``"BusinessAnalyst"``.
        jd_path: Path to the JD markdown (used for semantic scoring).
        weight_config_path: Path to the recruiter weight config (keyword scoring).
        alpha: Blend weight on keyword score (default 0.5).
        output_path: Optional ranked-output JSON path.
    """
    from .keyword_scorer import load_profiles_for_role
    from .semantic_scorer import evaluate_role_semantic

    profiles = load_profiles_for_role(role_bucket)
    weight_config = load_weight_config(weight_config_path)

    # ---- keyword pass ----
    keyword_scores: Dict[str, CandidateScore] = {}
    for profile in profiles:
        cand_id = profile.get("candidate_id") or ""
        ks = evaluate_candidate(
            profile, weight_config, role_bucket=role_bucket, chunks_by_id={}
        )
        keyword_scores[cand_id] = ks

    # ---- semantic pass (one embedding query per JD bullet per candidate) ----
    semantic_results = evaluate_role_semantic(
        role_bucket=role_bucket,
        jd_path=jd_path,
        output_path=None,
        profile_loader=lambda rb: profiles,
    )
    semantic_scores: Dict[str, SemanticScore] = {}
    for s in semantic_results:
        cand_id = s["candidate_id"]
        # Re-hydrate SemanticScore from dict so we can call build_hybrid_score.
        from .semantic_scorer import SemanticComponent

        semantic_scores[cand_id] = SemanticScore(
            candidate_id=cand_id,
            role_bucket=s["role_bucket"],
            raw_score=s["raw_score"],
            max_score=s["max_score"],
            normalized_score=s["normalized_score"],
            scale_factor=s["scale_factor"],
            components=[SemanticComponent(**c) for c in s["components"]],
            source_file=s.get("source_file"),
        )

    # ---- blend ----
    hybrids: List[HybridScore] = []
    for cand_id, ks in keyword_scores.items():
        ss = semantic_scores.get(cand_id)
        if ss is None:
            ss = SemanticScore(
                candidate_id=cand_id,
                role_bucket=role_bucket,
                raw_score=0.0,
                normalized_score=0.0,
            )
        hybrids.append(build_hybrid_score(ks, ss, alpha=alpha))

    ranked = rank_hybrid(hybrids)
    results = [h.to_dict() for h in ranked]
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as fh:
            json.dump(results, fh, ensure_ascii=False, indent=2)
    return results
