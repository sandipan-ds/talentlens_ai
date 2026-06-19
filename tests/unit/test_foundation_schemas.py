"""Tests for foundational schemas and deterministic helpers."""

from hireintel_ai.evaluation.parsing_metrics import calculate_f1_score
from hireintel_ai.ranking.ranker import rank_candidates
from hireintel_ai.schemas import EvaluationResult, ScoringPolicy


def test_scoring_policy_keeps_recruiter_weights() -> None:
    """Scoring policies should preserve recruiter-defined weights."""
    policy = ScoringPolicy(
        policy_id="policy-1",
        job_id="job-1",
        weights={"Python": 40.0, "SQL": 30.0, "experience": 30.0},
    )

    assert policy.weights["Python"] == 40.0
    assert sum(policy.weights.values()) == 100.0


def test_rank_candidates_sorts_by_total_score_descending() -> None:
    """Candidate ranking should be deterministic by score."""
    evaluations = [
        EvaluationResult(candidate_id="candidate-b", job_id="job-1", total_score=72),
        EvaluationResult(candidate_id="candidate-a", job_id="job-1", total_score=91),
    ]

    ranked = rank_candidates(evaluations)

    assert [result.candidate_id for result in ranked] == [
        "candidate-a",
        "candidate-b",
    ]


def test_calculate_f1_score_handles_zero_values() -> None:
    """F1 calculation should avoid division by zero."""
    assert calculate_f1_score(0.0, 0.0) == 0.0
    assert round(calculate_f1_score(0.5, 1.0), 4) == 0.6667

