"""LLM service placeholder for extraction and explanation workflows."""


class LlmService:
    """Coordinate LLM-backed tasks without owning deterministic scoring."""

    def is_configured(self) -> bool:
        """Return whether an LLM provider is configured.

        Returns:
            False until provider configuration is implemented.
        """
        return False

