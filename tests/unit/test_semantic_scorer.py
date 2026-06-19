"""Unit tests for the semantic (cosine) scorer."""

import json
from pathlib import Path

import pytest

from src.scoring.semantic_scorer import (
    SemanticComponent,
    SemanticScore,
    _load_jd_bullets,
    rank_semantic,
    score_candidate_semantic,
)
from src.scoring.hybrid_scorer import blend


@pytest.fixture
def jd_path(tmp_path: Path) -> Path:
    """Write a small JD markdown file and return its path."""
    p = tmp_path / "jd.md"
    p.write_text(
        """# Senior Data Scientist

## Role Overview
We are looking for a senior data scientist with strong Python and PyTorch experience.

## Key Responsibilities
- Build production ML pipelines in Python.
- Train and evaluate deep learning models using PyTorch.
- Collaborate with engineering teams to deploy models at scale.

## Required Skills
- 5+ years of Python programming.
- Hands-on experience with PyTorch or TensorFlow.
- Experience deploying ML models in production.
""",
        encoding="utf-8",
    )
    return p


def test_load_jd_bullets_parses_sections_and_bullets(jd_path):
    bullets = _load_jd_bullets(jd_path)
    sections = [s for s, _ in bullets]
    assert "Role Overview" in sections
    assert "Key Responsibilities" in sections
    assert "Required Skills" in sections
    # 3 bullets under Key Responsibilities + 3 under Required Skills + 1 long
    # paragraph under Role Overview = 7.
    assert len(bullets) >= 6


def test_score_candidate_semantic_returns_zero_when_no_chunks(tmp_path):
    score = score_candidate_semantic(
        candidate_id="cand_nope",
        role_bucket="BusinessAnalyst",
        jd_bullets=[("Required Skills", "Python")],
    )
    assert score.normalized_score == 0.0
    assert score.components[0].notes.startswith("No chunks")


def test_blend_function_is_linear():
    assert blend(80.0, 40.0, 0.5) == 60.0
    assert blend(80.0, 40.0, 1.0) == 80.0  # pure keyword
    assert blend(80.0, 40.0, 0.0) == 40.0  # pure semantic


def test_blend_rejects_invalid_alpha():
    with pytest.raises(ValueError):
        blend(50.0, 50.0, 1.5)
    with pytest.raises(ValueError):
        blend(50.0, 50.0, -0.1)


def test_rank_semantic_orders_by_score():
    a = SemanticScore(candidate_id="a", role_bucket="X", raw_score=0.3, normalized_score=30.0)
    b = SemanticScore(candidate_id="b", role_bucket="X", raw_score=0.7, normalized_score=70.0)
    c = SemanticScore(candidate_id="c", role_bucket="X", raw_score=0.5, normalized_score=50.0)
    ranked = rank_semantic([a, c, b])
    assert [r.candidate_id for r in ranked] == ["b", "c", "a"]


def test_semantic_component_to_dict_round_trip():
    c = SemanticComponent(
        category="Required Skills",
        item_name="Python",
        matched_weight=0.42,
        chunk_id="cand_x__skills__0",
        snippet="Python, PyTorch, ...",
        source_file="/tmp/x.pdf",
        notes="cosine=0.42",
    )
    d = c.to_dict()
    assert d["category"] == "Required Skills"
    assert d["matched_weight"] == 0.42
    assert d["chunk_id"] == "cand_x__skills__0"
    # JSON-serializable.
    json.dumps(d)


def test_score_candidate_semantic_uses_real_chunks(tmp_path):
    """End-to-end: write a chunk JSONL, score a candidate against a JD bullet."""
    role = "BusinessAnalyst"
    cand_id = "cand_test_001"
    chunk_dir = tmp_path / "data" / "chunks" / role
    chunk_dir.mkdir(parents=True)
    chunk_path = chunk_dir / f"{cand_id}.jsonl"
    chunk_path.write_text(
        json.dumps(
            {
                "chunk_id": f"{cand_id}__experience__0",
                "candidate_id": cand_id,
                "role_bucket": role,
                "section": "experience",
                "chunk_index": 0,
                "text": "Senior Data Scientist at Acme. Built production ML pipelines in Python using PyTorch.",
                "char_span": [0, 100],
                "metadata": {},
                "source_file": "/tmp/test.pdf",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    # Monkey-patch CHUNKS_DIR to point at our tmp dir.
    import src.scoring.semantic_scorer as sem_mod
    original = sem_mod.CHUNKS_DIR
    sem_mod.CHUNKS_DIR = tmp_path / "data" / "chunks"
    try:
        score = score_candidate_semantic(
            candidate_id=cand_id,
            role_bucket=role,
            jd_bullets=[("Required Skills", "Python programming")],
        )
        assert score.normalized_score > 0
        assert score.components[0].chunk_id == f"{cand_id}__experience__0"
        assert "PyTorch" in (score.components[0].snippet or "")
    finally:
        sem_mod.CHUNKS_DIR = original