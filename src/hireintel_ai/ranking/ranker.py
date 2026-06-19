"""Candidate ranking helpers."""

from hireintel_ai.schemas import EvaluationResult


def rank_candidates(evaluations: list[EvaluationResult]) -> list[EvaluationResult]:
    """Sort candidates by deterministic score.

    Args:
        evaluations: Candidate evaluation results for the same job.

    Returns:
        Evaluations sorted from highest to lowest score.
    """
    return sorted(evaluations, key=lambda result: result.total_score, reverse=True)

