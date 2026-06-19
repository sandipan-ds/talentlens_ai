"""Unit tests for the deterministic scoring engine."""

import pytest

from src.scoring.evaluate import (
    CandidateScore,
    ScoreComponent,
    compute_scale_factor,
    evaluate_candidate,
    rank_candidates,
    score_item,
)


@pytest.fixture
def weight_config() -> dict:
    """A minimal but realistic weight config."""
    return {
        "role": "Business Analyst Lead",
        "categories": [
            {
                "name": "Core Skills",
                "items": [
                    {"name": "Requirements Gathering", "importance": 8},
                    {"name": "Stakeholder Management", "importance": 9},
                ],
            },
            {
                "name": "Technology & Tools",
                "items": [
                    {"name": "Power BI", "importance": 7},
                    {"name": "SQL", "importance": 6},
                ],
            },
            {
                "name": "Experience",
                "items": [{"name": "6+ years in business analysis", "importance": 8}],
            },
            {
                "name": "Education",
                "items": [{"name": "BE/BTech or equivalent", "importance": 5}],
            },
            {
                "name": "Certifications",
                "items": [{"name": "CBAP / PMI-PBA", "importance": 5}],
            },
        ],
    }


@pytest.fixture
def strong_profile() -> dict:
    """A profile that should score highly on every item."""
    return {
        "candidate_id": "cand_strong01",
        "source_file": "/tmp/strong.pdf",
        "summary": {"value": "Senior business analyst with proven stakeholder management and process mapping skills."},
        "skills": ["Power BI", "SQL", "Excel", "Jira"],
        "certifications": ["CBAP"],
        "experience": {
            "entries": [
                {
                    "title": "Senior Business Analyst",
                    "company": "Acme",
                    "dates": "2018 - Present",
                    "location": "Remote",
                    "details": [
                        "Led requirement gathering workshops",
                        "Built dashboards in Power BI",
                        "Wrote complex SQL queries",
                    ],
                },
                {
                    "title": "Business Analyst",
                    "company": "Beta",
                    "dates": "2014 - 2018",
                    "location": "NY",
                    "details": ["Stakeholder management, process mapping"],
                },
            ]
        },
        "education": {
            "entries": [{"description": "BS Computer Science, MIT, 2014"}]
        },
    }


@pytest.fixture
def weak_profile() -> dict:
    """A profile that matches nothing."""
    return {
        "candidate_id": "cand_weak0001",
        "source_file": "/tmp/weak.pdf",
        "summary": {"value": "Entry level."},
        "skills": ["Microsoft Word"],
        "certifications": [],
        "experience": {
            "entries": [
                {
                    "title": "Intern",
                    "company": "Coffee Shop",
                    "dates": "2024 - 2025",
                    "location": "Local",
                    "details": ["Made coffee"],
                }
            ]
        },
        "education": {"entries": [{"description": "High School Diploma, 2023"}]},
    }


def test_scale_factor_calculation(weight_config):
    max_score, scale = compute_scale_factor(weight_config)
    assert max_score == 8 + 9 + 7 + 6 + 8 + 5 + 5  # 48
    assert scale == pytest.approx(100.0 / 48.0)


def test_strong_profile_scores_high(strong_profile, weight_config):
    score = evaluate_candidate(strong_profile, weight_config, role_bucket="BusinessAnalyst")
    # All 6 items should match.
    assert score.normalized_score == pytest.approx(100.0, rel=0.01)
    matched = [c for c in score.components if c.matched]
    assert len(matched) == len(score.components)


def test_weak_profile_scores_zero(weak_profile, weight_config):
    score = evaluate_candidate(weak_profile, weight_config, role_bucket="BusinessAnalyst")
    assert score.normalized_score == 0.0
    matched = [c for c in score.components if c.matched]
    assert matched == []


def test_evidence_chunk_attached(strong_profile, weight_config):
    chunks = {
        "cand_strong01__experience__0": {
            "candidate_id": "cand_strong01",
            "chunk_id": "cand_strong01__experience__0",
            "section": "experience",
            "text": "Senior Business Analyst @ Acme. Led requirement gathering workshops.",
            "source_file": "/tmp/strong.pdf",
        }
    }
    score = evaluate_candidate(
        strong_profile, weight_config, role_bucket="BusinessAnalyst", chunks_by_id=chunks
    )
    req_comp = next(c for c in score.components if c.item_name == "Requirements Gathering")
    assert req_comp.matched is True
    assert req_comp.chunk_id == "cand_strong01__experience__0"


def test_rank_candidates_orders_by_score(strong_profile, weak_profile, weight_config):
    a = evaluate_candidate(strong_profile, weight_config, role_bucket="BusinessAnalyst")
    b = evaluate_candidate(weak_profile, weight_config, role_bucket="BusinessAnalyst")
    ranked = rank_candidates([b, a])
    assert ranked[0].candidate_id == "cand_strong01"
    assert ranked[1].candidate_id == "cand_weak0001"


def test_education_six_years_uses_year_parser(weight_config):
    profile = {
        "candidate_id": "cand_yrs",
        "experience": {
            "entries": [
                {
                    "title": "BA",
                    "company": "X",
                    "dates": "2010 - 2012",
                    "details": [],
                    "location": None,
                },
                {
                    "title": "BA",
                    "company": "Y",
                    "dates": "2013 - 2020",
                    "details": [],
                    "location": None,
                },
            ]
        },
        "summary": {"value": ""},
        "skills": [],
        "certifications": [],
        "education": {"entries": []},
    }
    score = evaluate_candidate(profile, weight_config, role_bucket="X")
    comp = next(c for c in score.components if c.item_name == "6+ years in business analysis")
    # 2010-2012 + 2013-2020 = 2 + 7 = 9 years >= 6.
    assert comp.matched is True


def test_bachelor_match_accepts_bba_and_bs(weight_config):
    profile = {
        "candidate_id": "cand_edu",
        "experience": {"entries": []},
        "summary": {"value": ""},
        "skills": [],
        "certifications": [],
        "education": {"entries": [{"description": "BBA Finance, 2020"}]},
    }
    score = evaluate_candidate(profile, weight_config, role_bucket="X")
    comp = next(c for c in score.components if c.item_name == "BE/BTech or equivalent")
    assert comp.matched is True
