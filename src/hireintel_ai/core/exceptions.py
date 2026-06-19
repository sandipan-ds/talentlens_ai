"""Shared exception types for HireIntel AI."""


class HireIntelError(Exception):
    """Base exception for domain-specific application failures."""


class ValidationError(HireIntelError):
    """Raised when trusted application validation fails."""


class EvidenceNotFoundError(HireIntelError):
    """Raised when required resume evidence is unavailable."""

