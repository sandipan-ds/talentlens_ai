"""Backward-compatible re-export of the keyword scorer.

The deterministic keyword-based scoring engine was renamed to
:mod:`src.scoring.keyword_scorer`. This module is kept so any code that
imports from ``src.scoring.evaluate`` continues to work.
"""

from .keyword_scorer import (  # noqa: F401
    CandidateScore,
    ScoreComponent,
    _find_evidence_chunk,
    _has_bachelor,
    _keyword_match,
    _profile_text,
    _total_years_experience,
    compute_scale_factor,
    evaluate_batch,
    evaluate_candidate,
    evaluate_role,
    load_profiles_for_role,
    load_weight_config,
    rank_candidates,
    score_item,
)


__all__ = [
    "CandidateScore",
    "ScoreComponent",
    "compute_scale_factor",
    "evaluate_batch",
    "evaluate_candidate",
    "evaluate_role",
    "load_profiles_for_role",
    "load_weight_config",
    "rank_candidates",
]
