"""Tests for the canonical deterministic scorer (docs/WORKING_LOGIC.md)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from scoring.graded_scorer import (
    _aliases_for,
    _detect_years_in_text,
    _expected_years_for,
    _is_experience_item,
    _make_reason,
    _search_profile,
    evaluate_candidate,
    render_report,
    CandidateEvaluation,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _profile(**overrides):
    """A minimal but realistic BA profile."""
    base = {
        "candidate_id": "cand_test",
        "name": {"value": "Test Candidate"},
        "summary": {
            "value": (
                "7+ years of experience as a Business Analyst supporting e-commerce "
                "retailers. Skilled in Power BI, SQL, Excel, and Agile delivery."
            )
        },
        "experience": {
            "entries": [
                {
                    "title": "Business Analyst",
                    "company": "Acme",
                    "dates": "2019 - Present",
                    "details": [
                        "Gather business requirements and translate them into user stories.",
                        "Build Power BI dashboards for executive reporting.",
                        "Write complex SQL queries against the data warehouse.",
                        "Run daily standups in an Agile/Scrum environment.",
                    ],
                },
                {
                    "title": "Junior Analyst",
                    "company": "Initech",
                    "dates": "2014 - 2019",
                    "details": [
                        "Documented as-is and to-be business processes.",
                        "Analyzed data and produced trend-analysis reports in Excel.",
                    ],
                },
            ]
        },
        "skills": [
            "Power BI",
            "SQL",
            "Excel",
            "Agile software development",
            "Stakeholder management",
        ],
        "education": {
            "entries": [
                {"description": "Bachelor of Engineering in Computer Science, 2014."}
            ]
        },
        "certifications": ["Microsoft Power BI Data Analyst Associate"],
        "projects": [],
        "languages": [],
    }
    base.update(overrides)
    return base


def _weights():
    return {
        "role": "Business Analyst",
        "max_score": 50,
        "scale_factor": 2.0,         # 100 / 50
        "categories": [
            {
                "name": "Core Skills",
                "items": [
                    {"name": "Requirements Gathering", "importance": 8,
                     "normalized_importance": 4.0},
                    {"name": "Power BI", "importance": 7,
                     "normalized_importance": 3.5},
                    {"name": "SQL", "importance": 5,
                     "normalized_importance": 2.5},
                ],
            },
            {
                "name": "Education",
                "items": [
                    {"name": "BE/BTech or equivalent", "importance": 5,
                     "normalized_importance": 2.5},
                ],
            },
        ],
    }


# ---------------------------------------------------------------------------
# Alias & matcher tests
# ---------------------------------------------------------------------------

class TestAliases:
    def test_aliases_for_known_item_returns_compiled_patterns(self):
        patterns = _aliases_for("Power BI")
        assert patterns, "expected at least one pattern"
        text = "Built Power BI dashboards."
        assert any(p.search(text) for p in patterns)

    def test_aliases_word_boundary_does_not_match_embedded(self):
        # "be" must NOT match "between" or "become".
        patterns = _aliases_for("BE/BTech or equivalent")
        assert not any(p.search("between us") for p in patterns)
        assert not any(p.search("become better") for p in patterns)
        # But it SHOULD match the actual credential.
        assert any(p.search("Bachelor of Engineering") for p in patterns)

    def test_aliases_agile_tools_catches_synonyms(self):
        patterns = _aliases_for("Agile Tools")
        assert any(p.search("Agile software development") for p in patterns)
        assert any(p.search("scrum") for p in patterns)
        assert any(p.search("jira") for p in patterns)


class TestYearsDetection:
    def test_detect_years_near_alias(self):
        text = "I have 6 years of Power BI experience."
        years = _detect_years_in_text(text, _aliases_for("Power BI"))
        assert years == pytest.approx(6.0)

    def test_detect_years_fallback_to_text_max(self):
        # "7+ years" anywhere in the text should still count.
        text = "7+ years of experience. I build Power BI dashboards."
        years = _detect_years_in_text(text, _aliases_for("Power BI"))
        assert years == pytest.approx(7.0)

    def test_detect_years_handles_plus_suffix(self):
        text = "5+ years of SQL experience."
        years = _detect_years_in_text(text, _aliases_for("SQL"))
        assert years == pytest.approx(5.0)


class TestSearchProfile:
    def test_search_finds_skill_in_experience(self):
        result = _search_profile(_profile(), _aliases_for("Power BI"))
        matched, section, snippet, years = result
        assert matched
        assert section == "experience"
        assert "Power BI" in snippet
        assert years == pytest.approx(7.0)

    def test_search_finds_education_credential(self):
        result = _search_profile(
            _profile(), _aliases_for("BE/BTech or equivalent")
        )
        matched, section, snippet, _ = result
        assert matched
        assert section == "education"
        assert "Bachelor of Engineering" in snippet

    def test_search_finds_certification(self):
        result = _search_profile(_profile(), _aliases_for("CBAP / PMI-PBA"))
        assert result[0] is False


# ---------------------------------------------------------------------------
# Scoring tests
# ---------------------------------------------------------------------------

class TestScoring:
    def test_proportional_years_score(self):
        # Power BI: 7 years vs 10 expected → ratio 0.7 × importance 7 = 4.9
        ev = evaluate_candidate(_profile(), _weights())
        item = ev.categories[0].items[1]   # Power BI
        assert item.matched
        assert item.years_detected == pytest.approx(7.0)
        assert item.raw_score == pytest.approx(4.9, abs=0.05)
        assert item.score > 0

    def test_missing_evidence_zero_score(self):
        weights = _weights()
        weights["categories"][0]["items"].append(
            {"name": "Tableau", "importance": 5, "normalized_importance": 2.5}
        )
        ev = evaluate_candidate(_profile(), weights)
        tableau = ev.categories[0].items[-1]
        assert tableau.matched is False
        assert tableau.score == 0.0
        assert "No evidence" in tableau.reason

    def test_total_normalized_to_100(self):
        ev = evaluate_candidate(_profile(), _weights())
        assert 0 <= ev.total <= 100

    def test_experience_items_allow_summary_years_fallback(self):
        # Stakeholder management is not in the profile's experience text
        # directly, but the summary says "7+ years … as a Business Analyst"
        # → summary-years fallback should kick in.
        weights = _weights()
        weights["categories"][0]["items"].append(
            {"name": "Stakeholder Management", "importance": 9,
             "normalized_importance": 4.5}
        )
        ev = evaluate_candidate(_profile(), weights)
        item = ev.categories[0].items[-1]
        assert item.matched
        assert item.years_detected == pytest.approx(7.0)

    def test_education_items_do_not_use_summary_years_fallback(self):
        # BE/BTech matched via education section; summary years must not leak.
        ev = evaluate_candidate(_profile(), _weights())
        edu = ev.categories[1].items[0]
        assert edu.matched
        assert edu.years_detected == 0.0
        assert "no years of experience" in edu.reason.lower()

    def test_evaluation_is_deterministic(self):
        ev1 = evaluate_candidate(_profile(), _weights())
        ev2 = evaluate_candidate(_profile(), _weights())
        assert ev1.to_dict() == ev2.to_dict()


# ---------------------------------------------------------------------------
# Reason & report tests
# ---------------------------------------------------------------------------

class TestReasonAndReport:
    def test_reason_does_not_stutter_experience_word(self):
        reason = _make_reason(
            "Industry/domain experience", True, 7.0, 10.0, 9.0, "summary"
        )
        assert "experience experience" not in reason

    def test_reason_does_not_stutter_for_clause_item(self):
        reason = _make_reason(
            "6+ years in business analysis", True, 7.0, 10.0, 8.0, "experience"
        )
        # No "of 6+ years in business analysis experience" double-stutter.
        assert "analysis experience identified" not in reason

    def test_reason_when_no_evidence(self):
        reason = _make_reason("Power BI", False, 0.0, 10.0, 7.0, "")
        assert "No evidence" in reason

    def test_report_has_total_and_per_item_sections(self):
        ev = evaluate_candidate(_profile(), _weights())
        report = render_report(ev)
        assert "### Total Score:" in report
        assert "Requirements Gathering" in report
        assert "Power BI" in report
        assert "Reason:" in report
        assert "Evidence:" in report
        assert "Section : experience" in report or "Section : summary" in report \
            or "Section : skills" in report or "Section : education" in report


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

class TestConfigHelpers:
    def test_expected_years_falls_back_to_default(self):
        assert _expected_years_for({}, default=10) == 10.0

    def test_expected_years_uses_explicit_value(self):
        assert _expected_years_for({"expected_years": 5}, default=10) == 5.0

    def test_is_experience_item_recognises_skill_categories(self):
        assert _is_experience_item({"name": "Power BI"}, "Technology & Tools")
        assert _is_experience_item({"name": "BA"}, "Core Skills")

    def test_is_experience_item_rejects_credential_categories(self):
        assert not _is_experience_item({"name": "BE/BTech"}, "Education")
        assert not _is_experience_item({"name": "CBAP"}, "Certifications")
