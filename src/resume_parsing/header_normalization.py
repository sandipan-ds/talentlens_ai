"""Header Normalization — maps heterogeneous resume section headers to canonical labels.

Resumes do not use consistent section names: "Skills" vs "Technical Skills" vs
"Core Competencies"; "Experience" vs "Employment History" vs "Career History".
Routing a JD requirement to "the Education section" only works if every resume's
education-like header reliably maps to the same canonical label.

This module implements the two-layer approach defined in ``WORKING_LOGIC.md``
("Header Normalization"):

Layer 1 — Synonym Lookup (free, deterministic):
    A maintained table catches the large majority of headers with no model call.

Layer 2 — Fallback Classification (one model call, only for unmatched headers):
    If a header doesn't match the table — or a resume has no headers at all and
    uses free-flowing paragraphs — one LLM classification call per resume
    assigns it to a canonical section. This is a discrete classification into a
    fixed set of 7 buckets, not a similarity score, so it is deterministic-enough
    and auditable: the system logs which header (or absence of one) produced
    which label and with what confidence.

The 7 canonical sections (per ``WORKING_LOGIC.md``):

    Personal_Info | Education | Experience | Projects
    | Skills | Certifications | Languages
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Canonical sections — the only valid output labels.
# ---------------------------------------------------------------------------

CANONICAL_SECTIONS: Tuple[str, ...] = (
    "Personal_Info",
    "Education",
    "Experience",
    "Projects",
    "Skills",
    "Certifications",
    "Languages",
)

# ---------------------------------------------------------------------------
# Layer 1 — Synonym lookup table.
#
# Every key is lower-cased and stripped before matching. The values MUST be one
# of ``CANONICAL_SECTIONS``. This table is maintained by humans and is the
# primary, free, deterministic normalization path.
#
# The entries match the table in WORKING_LOGIC.md "Header Normalization" plus
# common additional synonyms encountered in real resumes.
# ---------------------------------------------------------------------------

_SYNONYM_TABLE: Dict[str, str] = {}

# Helper to register a group of synonyms → one canonical section.
def _register(synonyms: Sequence[str], canonical: str) -> None:
    for s in synonyms:
        _SYNONYM_TABLE[s.lower().strip()] = canonical

# Personal_Info
_register(
    [
        "personal information", "personal details", "personal",
        "contact", "contact information", "contact details",
        "about me", "profile", "objective", "career objective",
        "summary", "professional summary", "executive summary",
        "headline", "title", "details",
    ],
    "Personal_Info",
)

# Education
_register(
    [
        "education", "academic background", "academic qualifications",
        "academic", "academics", "educational background",
        "educational qualifications", "qualifications",
        "schooling", "university", "college",
    ],
    "Education",
)

# Experience
_register(
    [
        "work experience", "employment history", "professional experience",
        "job experience", "career history", "experience",
        "work history", "employment", "professional background",
        "career", "work", "internship", "internships",
        "professional experience & training",
    ],
    "Experience",
)

# Projects
_register(
    [
        "projects", "selected projects", "project experience",
        "key projects", "academic projects", "personal projects",
        "notable projects", "project portfolio", "project work",
    ],
    "Projects",
)

# Skills
_register(
    [
        "skills", "technical skills", "core competencies",
        "technical proficiencies", "competencies", "key skills",
        "top skills", "core skills", "areas of expertise",
        "expertise", "technical expertise", "skill set",
        "technologies", "tech stack", "tools & technologies",
        "tools and technologies", "programming languages",
        "languages & technologies", "technical skills & tools",
    ],
    "Skills",
)

# Certifications
_register(
    [
        "certifications", "licenses", "credentials",
        "licenses & certifications", "certificates",
        "professional certifications", "certification",
        "licenses and certifications", "training & certifications",
    ],
    "Certifications",
)

# Languages
_register(
    [
        "languages", "language skills", "language proficiency",
        "language", "languages known", "spoken languages",
    ],
    "Languages",
)


# ---------------------------------------------------------------------------
# Public dataclass for the result of a single header normalization.
# ---------------------------------------------------------------------------

@dataclass
class HeaderClassification:
    """The result of classifying a single resume header line.

    Attributes:
        canonical_section: One of ``CANONICAL_SECTIONS``.
        original_header: The raw header text as found in the resume.
        method: How the label was determined — "synonym_lookup" or
            "fallback_classification".
        confidence: 1.0 for synonym lookup (exact match); for fallback
            classification this is the LLM's reported confidence (0.0–1.0).
        multi_tag_sections: Additional canonical sections this chunk's content
            spans (empty unless multi-tag detection is enabled during fallback).
    """

    canonical_section: str
    original_header: str
    method: str
    confidence: float = 1.0
    multi_tag_sections: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Layer 1 — Synonym lookup (deterministic, free, no model call).
# ---------------------------------------------------------------------------

def _clean_header(line: str) -> str:
    """Strip decorations and normalize a header line for matching.

    Args:
        line: Raw header text from a resume.

    Returns:
        Cleaned, lower-cased string suitable for synonym table lookup.
    """
    # Remove common decorations: colons, dashes, equals, bullets, leading/trailing whitespace.
    cleaned = line.strip().strip(" :*-=#•·|").strip()
    # Collapse internal whitespace.
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.lower()


def synonym_lookup(header: str) -> Optional[str]:
    """Look up a header in the synonym table.

    This is Layer 1 — free, deterministic, no model call.

    Args:
        header: Raw header text from a resume.

    Returns:
        Canonical section name if found, ``None`` otherwise.
    """
    cleaned = _clean_header(header)
    if not cleaned:
        return None
    # Exact match.
    if cleaned in _SYNONYM_TABLE:
        return _SYNONYM_TABLE[cleaned]
    # Prefix match: "Skills & Tools" → "skills" → Skills.
    for synonym, canonical in _SYNONYM_TABLE.items():
        if cleaned.startswith(synonym + " ") or cleaned.startswith(synonym + "&"):
            return canonical
    return None


# ---------------------------------------------------------------------------
# Layer 2 — Fallback LLM classification (only for unmatched headers).
# ---------------------------------------------------------------------------

_FALLBACK_PROMPT_TEMPLATE = """You are a resume section classifier.

Classify the following resume header into exactly one of these 7 canonical sections:
- Personal_Info (name, contact, summary, profile, objective)
- Education (degree, university, academic)
- Experience (work history, employment, career)
- Projects (project work, portfolio)
- Skills (technical skills, competencies, tools)
- Certifications (certificates, licenses, credentials)
- Languages (language skills)

Resume header: "{header}"

Respond with ONLY a JSON object, no other text:
{{"section": "<one of the 7 canonical sections>", "confidence": <0.0 to 1.0>}}"""


def _fallback_classify_single(header: str, llm_caller) -> Tuple[str, float]:
    """Classify a single unmatched header via one LLM call.

    Args:
        header: Raw header text that did not match the synonym table.
        llm_caller: Callable that takes a prompt string and returns the LLM
            text response. If ``None``, returns ("Personal_Info", 0.0) as a
            safe default.

    Returns:
        Tuple of (canonical_section, confidence).
    """
    if llm_caller is None:
        logger.warning(
            "No LLM caller provided for fallback classification; "
            "defaulting unmatched header '%s' to Personal_Info", header
        )
        return "Personal_Info", 0.0

    prompt = _FALLBACK_PROMPT_TEMPLATE.format(header=header)
    try:
        response = llm_caller(prompt).strip()
        # Extract JSON from the response (handles markdown code fences).
        json_match = re.search(r"\{[^}]+\}", response)
        if json_match:
            data = json.loads(json_match.group())
            section = data.get("section", "Personal_Info")
            confidence = float(data.get("confidence", 0.0))
            # Validate section is one of the canonical 7.
            if section not in CANONICAL_SECTIONS:
                logger.warning(
                    "LLM returned invalid section '%s'; defaulting to Personal_Info", section
                )
                return "Personal_Info", confidence
            return section, confidence
        logger.warning("LLM response did not contain valid JSON: %s", response[:200])
        return "Personal_Info", 0.0
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning("Fallback classification failed for '%s': %s", header, exc)
        return "Personal_Info", 0.0


# ---------------------------------------------------------------------------
# Public API — normalize a list of headers.
# ---------------------------------------------------------------------------

def normalize_headers(
    headers: List[str],
    llm_caller=None,
) -> List[HeaderClassification]:
    """Normalize a list of resume headers into canonical section labels.

    This is the main entry point. It tries Layer 1 (synonym lookup) first,
    and only falls back to Layer 2 (LLM classification) for headers that
    don't match the table.

    Args:
        headers: List of raw header strings found in the resume.
        llm_caller: Optional callable for Layer 2 fallback. Takes a prompt
            string, returns the LLM text response. If ``None``, unmatched
            headers default to ``Personal_Info`` with confidence 0.0.

    Returns:
        List of ``HeaderClassification`` — one per input header, in order.
    """
    results: List[HeaderClassification] = []
    for header in headers:
        canonical = synonym_lookup(header)
        if canonical is not None:
            results.append(HeaderClassification(
                canonical_section=canonical,
                original_header=header,
                method="synonym_lookup",
                confidence=1.0,
            ))
        else:
            section, conf = _fallback_classify_single(header, llm_caller)
            results.append(HeaderClassification(
                canonical_section=section,
                original_header=header,
                method="fallback_classification",
                confidence=conf,
            ))
    return results


def normalize_single_header(header: str, llm_caller=None) -> HeaderClassification:
    """Normalize a single resume header.

    Args:
        header: Raw header text from a resume.
        llm_caller: Optional callable for Layer 2 fallback.

    Returns:
        ``HeaderClassification`` for the given header.
    """
    results = normalize_headers([header], llm_caller)
    return results[0]


def get_synonym_table() -> Dict[str, str]:
    """Return a copy of the synonym lookup table (for inspection/debugging).

    Returns:
        Dict mapping lower-cased synonym → canonical section name.
    """
    return dict(_SYNONYM_TABLE)
