"""Integration tests for JD matching.

These exercise the *full* path:

* Parse a JD into requirements.
* Build (or load) the vector index from ``data/chunks/``.
* Retrieve + aggregate hits per candidate.
* Rank and return top-K.

Run only if the index has been built. If not, the test is skipped.
"""

from pathlib import Path

import pytest

from src.rag.index import INDEX_PATH
from src.rag.jd_match import (
    CandidateMatch,
    Requirement,
    match_jd,
    rank_candidates,
    split_jd_into_requirements,
)


JD_PATH = Path("data/Job descriptions/BusinessAnalyst/BusinessAnalyst_Lead_JD.md")


@pytest.fixture(scope="module")
def jd_requirements() -> list:
    return split_jd_into_requirements(JD_PATH.read_text(encoding="utf-8"))


def test_jd_split_produces_requirements(jd_requirements):
    assert len(jd_requirements) > 5
    sections = {r.section for r in jd_requirements}
    assert "Required Skills" in sections
    assert "Preferred Skills" in sections


def test_preferred_requirements_are_tagged(jd_requirements):
    preferred = [r for r in jd_requirements if not r.required]
    assert preferred, "Expected at least one preferred requirement"
    assert all("preferred" in r.section.lower() for r in preferred)


@pytest.mark.skipif(not INDEX_PATH.exists(), reason="Vector index not built")
def test_match_returns_top_candidates():
    result = match_jd(JD_PATH, role_bucket="BusinessAnalyst", top_k=5)
    assert result["requirement_count"] > 0
    assert len(result["matches"]) > 0
    top = result["matches"][0]
    assert top["best_score"] > 0
    assert top["role_bucket"] == "BusinessAnalyst"
    # Evidence should be non-empty for the top candidate.
    assert len(top["evidence"]) > 0
    # Each evidence item should reference a real chunk.
    for ev in top["evidence"]:
        assert "chunk_id" in ev
        assert "score" in ev
        assert "snippet" in ev


@pytest.mark.skipif(not INDEX_PATH.exists(), reason="Vector index not built")
def test_rank_is_deterministic():
    a = match_jd(JD_PATH, role_bucket="BusinessAnalyst", top_k=5)
    b = match_jd(JD_PATH, role_bucket="BusinessAnalyst", top_k=5)
    assert [m["candidate_id"] for m in a["matches"]] == [
        m["candidate_id"] for m in b["matches"]
    ]


def test_rank_candidates_sorting():
    m1 = CandidateMatch(candidate_id="a", role_bucket="BusinessAnalyst", best_score=0.5, avg_score=0.4, requirements_matched=2, requirements_total=5)
    m2 = CandidateMatch(candidate_id="b", role_bucket="BusinessAnalyst", best_score=0.7, avg_score=0.3, requirements_matched=3, requirements_total=5)
    m3 = CandidateMatch(candidate_id="c", role_bucket="BusinessAnalyst", best_score=0.6, avg_score=0.6, requirements_matched=4, requirements_total=5)
    ranked = rank_candidates({"a": m1, "b": m2, "c": m3})
    # m3 has 0.6*0.6 + 0.4*0.6 = 0.60 -> highest; m2 0.6*0.7+0.4*0.3=0.54; m1 0.6*0.5+0.4*0.4=0.46.
    assert [m.candidate_id for m in ranked] == ["c", "b", "a"]
