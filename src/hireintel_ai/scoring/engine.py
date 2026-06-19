"""Deterministic scoring engine for recruiter-defined policies."""

from hireintel_ai.schemas import CandidateProfile, EvaluationResult, ScoringPolicy


class ScoringEngine:
    """Apply recruiter-defined scoring policies to candidate profiles."""

    def evaluate(
        self,
        candidate: CandidateProfile,
        policy: ScoringPolicy,
    ) -> EvaluationResult:
        """Evaluate a candidate against a scoring policy.

        Args:
            candidate: Structured candidate profile.
            policy: Recruiter-defined scoring policy.

        Returns:
            Deterministic evaluation result. Scoring formulas will be expanded
            during the scoring engine milestone.
        """
        return EvaluationResult(
            candidate_id=candidate.candidate_id,
            job_id=policy.job_id,
            total_score=0.0,
        )

