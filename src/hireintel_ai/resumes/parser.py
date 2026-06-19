"""Resume parsing interface for structured candidate profile extraction."""

from hireintel_ai.schemas import CandidateProfile


class ResumeParser:
    """Parse resume text into a structured candidate profile."""

    def parse(self, candidate_id: str, resume_id: str, text: str) -> CandidateProfile:
        """Create a structured candidate profile from resume text.

        Args:
            candidate_id: Stable candidate identifier.
            resume_id: Source resume identifier.
            text: Extracted resume text.

        Returns:
            Candidate profile. Field extraction will be expanded in the resume
            parsing milestone.
        """
        return CandidateProfile(candidate_id=candidate_id, resume_id=resume_id)

