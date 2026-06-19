"""Unit tests for the hybrid (keyword + semantic) scorer."""

import pytest

from src.scoring.hybrid_scorer import (
    HybridScore,
    blend,
    build_hybrid_score,
    rank_hybrid,
)
from src.scoring.keyword_scorer import CandidateScore, ScoreComponent
from src.scoring.semantic_scorer import SemanticComponent, SemanticScore


def _kw(candidate_id: str, score: float) -> CandidateScore:
    return CandidateScore(
        candidate_id=candidate_id,
        role_bucket="BusinessAnalyst",
        raw_score=score,
        max_score=100.0,
        normalized_score=score,
        scale_factor=1.0,
        components=[
            ScoreComponent(
                category="Core Skills",
                item_name="Requirements Gathering",
                description="",
                importance=8,
                matched=True,
                matched_weight=8.0,
            )
        ],
    )


def _sem(candidate_id: str, score: float) -> SemanticScore:
    return SemanticScore(
        candidate_id=candidate_id,
        role_bucket="BusinessAnalyst",
        raw_score=score / 100.0,
        normalized_score=score,
        components=[
            SemanticComponent(
                category="Required Skills",
                item_name="Python",
                matched_weight=score / 100.0,
            )
        ],
    )


def test_blend_default_alpha_is_half():
    assert blend(80.0, 40.0, 0.5) == 60.0


def test_build_hybrid_score_combines_both():
    kw = _kw("cand_a", 80.0)
    sem = _sem("cand_a", 40.0)
    h = build_hybrid_score(kw, sem, alpha=0.5)
    assert h.candidate_id == "cand_a"
    assert h.keyword_score == 80.0
    assert h.semantic_score == 40.0
    assert h.final_score == 60.0
    assert h.alpha == 0.5
    assert len(h.keyword_components) == 1
    assert len(h.semantic_components) == 1


def test_build_hybrid_score_alpha_one_is_pure_keyword():
    h = build_hybrid_score(_kw("cand_a", 80.0), _sem("cand_a", 40.0), alpha=1.0)
    assert h.final_score == 80.0


def test_build_hybrid_score_alpha_zero_is_pure_semantic():
    h = build_hybrid_score(_kw("cand_a", 80.0), _sem("cand_a", 40.0), alpha=0.0)
    assert h.final_score == 40.0


def test_rank_hybrid_orders_by_final_score():
    a = build_hybrid_score(_kw("a", 50.0), _sem("a", 50.0), alpha=0.5)
    b = build_hybrid_score(_kw("b", 80.0), _sem("b", 40.0), alpha=0.5)
    c = build_hybrid_score(_kw("c", 70.0), _sem("c", 70.0), alpha=0.5)
    ranked = rank_hybrid([a, b, c])
    # b: 0.5*80+0.5*40=60; c: 0.5*70+0.5*70=70; a: 50
    assert [r.candidate_id for r in ranked] == ["c", "b", "a"]


def test_hybrid_score_to_dict_round_trip():
    h = build_hybrid_score(_kw("a", 80.0), _sem("a", 40.0), alpha=0.5)
    d = h.to_dict()
    assert d["candidate_id"] == "a"
    assert d["final_score"] == 60.0
    assert d["alpha"] == 0.5
    import json
    json.dumps(d)