"""Job description requirement extraction interface."""

from hireintel_ai.schemas import JobDescription


class JobDescriptionExtractor:
    """Extract structured hiring requirements from job description text."""

    def extract(self, job_id: str, title: str, raw_text: str) -> JobDescription:
        """Create a structured job description from raw text.

        Args:
            job_id: Stable job identifier.
            title: Role title.
            raw_text: Extracted job description text.

        Returns:
            Structured job description. Requirement extraction will be expanded
            in the JD intelligence milestone.
        """
        return JobDescription(job_id=job_id, title=title, raw_text=raw_text)

