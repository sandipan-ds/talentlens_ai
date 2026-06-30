"""Canonical deterministic candidate scorer.

This module is the single scoring engine described in
``docs/WORKING_LOGIC.md``. It supersedes the earlier
``keyword_scorer`` / ``semantic_scorer`` / ``hybrid_scorer`` split —
those produced multiple, non-comparable scores; the spec calls for
**one** deterministic scorer (see "AI Design Rationale").

Pipeline (per WORKING_LOGIC.md):

    1. The recruiter-weighted config declares, per item:
         * ``name``           – the criterion
         * ``importance``     – recruiter weight 0..10
         * ``expected_years`` – target years of experience (with a
           configurable default when the JD did not state it).
    2. For each candidate:
         a. Search the *structured* profile sections (``skills``,
            ``experience.entries[*].details``, ``education.entries``,
            ``certifications``) — never raw-text regex.
         b. Count how many years of relevant experience the profile
            shows for that criterion.
         c. Per-item raw score =
                min(importance, candidate_years / expected_years * importance)
            A presence-without-years finding still earns a small partial
            credit (``importance * 0.3``) so recruiters can distinguish
            "mentioned" from "demonstrated".
    3. Use ``normalized_importance`` (provided in the config) to roll
       the per-item score up to 100 deterministically — see
       ``docs/PROJECT_OVERVIEW.md`` Step 6.
    4. Evidence: for every score we record the **profile section**
       and the **exact snippet** that produced the match. No
       black-box scoring.

Public API:
    * :func:`evaluate_candidate` – score one profile.
    * :func:`evaluate_role`      – score every profile in a role.
    * :func:`render_report`      – human-readable report (matches the
      example in ``docs/PROJECT_OVERVIEW.md`` Phase 4).
    * :func:`load_weights`       – load the recruiter weight config.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

#: Default ``expected_years`` when neither the JD nor the recruiter
#: specify one for an item. Configurable per the spec (Step 5).
DEFAULT_EXPECTED_YEARS: int = 10

#: Minimum text length (chars) to bother searching.
_MIN_SECTION_LEN: int = 3


# ---------------------------------------------------------------------------
# Synonyms for skill matching.
# Keys are lower-cased canonical names; values are lower-cased aliases.
# ---------------------------------------------------------------------------
_SYNONYMS: Dict[str, List[str]] = {
    "power bi": ["powerbi", "pbi", "dax", "power query"],
    "sql": ["mysql", "postgresql", "postgres", "t-sql", "tsql", "pl/sql", "bigquery", "sql server"],
    "excel": ["vlookup", "pivot table", "pivottables", "spreadsheet", "microsoft excel"],
    "agile tools": ["jira", "azure devops", "ado", "confluence", "trello", "asana", "scrum", "kanban", "sprint"],
    "requirements gathering": [
        "requirement gathering", "requirement elicitation", "elicit requirement",
        "gather requirement", "user story", "user stories", "acceptance criteria",
        "functional spec", "functional specification", "business requirement",
    ],
    "stakeholder management": [
        "stakeholder", "stakeholders", "cross-functional", "cross functional",
        "liaison", "business partner", "client engagement",
    ],
    "process mapping": [
        "process map", "process mapping", "process improvement", "business process",
        "process re-engineering", "process redesign", "process optimization",
        "process analysis", "as-is", "to-be", "processes",
    ],
    "data analysis": [
        "data analysis", "data analytics", "data driven", "data-driven",
        "analyze data", "analyse data", "analyzed data", "analysed data",
        "analyze", "analyse", "analyzed", "analysed",
        "analysis", "analytical",
        "insight", "kpi", "metrics", "trend analysis",
        "reporting", "dashboard", "business data",
    ],
    "communication": [
        "communication", "communicate", "presented", "presentation",
        "stakeholder communication", "status update", "executive summary",
        "documentation", "report",
    ],
    "cbap / pmi-pba": ["cbap", "pmi-pba", "pmi pba", "certified business analysis professional"],
    "bi / analytics certification": [
        "power bi certification", "tableau certification", "analytics certification",
        "bi certification",
    ],
    "be/btech or equivalent": [
        r"\bb\.?\s?tech\b", r"\bbtech\b",
        r"\bbachelor of engineering\b", r"\bbachelor of technology\b",
        r"\bbachelor in engineering\b", r"\bundergraduate degree\b",
        r"\bbachelor of arts\b", r"\bbsc\b", r"\bb\.?sc\b",
    ],
    "6+ years in business analysis": [
        r"\bbusiness analyst\b", r"\bbusiness analysis\b",
        r"\bba role\b", r"\bba\b",
    ],
    "industry/domain experience": [
        "e-commerce", "ecommerce", "retail", "fintech", "banking",
        "healthcare", "saas", "manufacturing",
    ],
    "agile": [
        "agile software development", "agile methodology", "agile environment",
        "scrum master", "scrum team", "sprint planning", "agile delivery",
        "wrike", "attask", "monday.com", "smartsheet",
    ],
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ItemEvaluation:
    """Per-item evaluation result with evidence."""

    category: str
    item_name: str
    description: str
    importance: float          # recruiter weight 0..10
    expected_years: float      # target years for this item
    matched: bool
    years_detected: float      # 0 if no years value found
    raw_score: float           # 0..importance (pre-normalization)
    score: float               # raw_score * normalized_importance / importance
    section: str = ""          # profile section the evidence came from
    snippet: str = ""          # exact text snippet that earned the score
    reason: str = ""           # human-readable explanation

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CategoryEvaluation:
    name: str
    items: List[ItemEvaluation] = field(default_factory=list)

    @property
    def raw_score(self) -> float:
        return sum(i.raw_score for i in self.items)

    @property
    def max_score(self) -> float:
        return sum(i.importance for i in self.items)

    @property
    def score(self) -> float:
        return sum(i.score for i in self.items)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "raw_score": round(self.raw_score, 2),
            "max_score": round(self.max_score, 2),
            "score": round(self.score, 2),
            "items": [i.to_dict() for i in self.items],
        }


@dataclass
class CandidateEvaluation:
    candidate_id: str
    role: str
    total_raw: float           # sum of item.raw_score
    total_max: float           # sum of item.importance (= config max_score)
    total: float               # 0..100 normalized
    categories: List[CategoryEvaluation] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "role": self.role,
            "total_raw": round(self.total_raw, 2),
            "total_max": round(self.total_max, 2),
            "total": round(self.total, 2),
            "categories": [c.to_dict() for c in self.categories],
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    """Lower-case + collapse whitespace for matching."""
    return re.sub(r"\s+", " ", text.lower()).strip()


def _aliases_for(item_name: str) -> List[re.Pattern[str]]:
    """Return compiled regex patterns we should search for to match ``item_name``.

    The returned patterns honor word boundaries for short tokens
    (so ``"be"`` does not match "between") and case-insensitive matching
    for everything.
    """
    name = _normalize(item_name)
    raw: List[str] = [name]
    for key, vals in _SYNONYMS.items():
        if key in name or name in key:
            raw.extend(vals)
    # Dedupe, preserve order.
    seen: set[str] = set()
    out: List[re.Pattern[str]] = []
    for a in raw:
        a = a.strip()
        if not a or a in seen:
            continue
        seen.add(a)
        # If the alias already looks like a regex (contains \b), use as-is.
        # Otherwise wrap with word boundaries and escape the rest.
        if r"\b" in a:
            pattern = a
        else:
            pattern = r"\b" + re.escape(a) + r"\b"
        try:
            out.append(re.compile(pattern, re.IGNORECASE))
        except re.error:
            # Fallback: plain escaped literal.
            out.append(re.compile(re.escape(a), re.IGNORECASE))
    return out


_YEARS_RE = re.compile(
    r"(?P<num>\d+(?:\.\d+)?)\s*\+?\s*(?:year|yr)s?",
    re.IGNORECASE,
)


def _detect_years_in_text(text: str, patterns: List[re.Pattern[str]]) -> float:
    """Look for ``<n> year(s)`` phrases near any alias pattern match.

    Returns the **highest** years value found near an alias match.
    Falls back to the highest years value in the whole text if no
    alias is near any years phrase, so candidates that say
    "7+ years of experience as a Business Analyst" still receive
    years credit even when the years phrase sits in a different line.
    """
    norm = _normalize(text)
    if not norm:
        return 0.0

    best_near = 0.0
    best_any = 0.0

    for m in _YEARS_RE.finditer(norm):
        try:
            years = float(m.group("num"))
        except (ValueError, IndexError):
            continue
        best_any = max(best_any, years)
        window = norm[max(0, m.start() - 80): m.end() + 80]
        if any(p.search(window) for p in patterns):
            best_near = max(best_near, years)

    return best_near or best_any


def _snippet_for(text: str, patterns: List[re.Pattern[str]], max_len: int = 220) -> str:
    """Return the first plausible snippet of ``text`` that matches an alias pattern."""
    for pattern in patterns:
        m = pattern.search(text)
        if not m:
            continue
        start = max(0, m.start() - 60)
        end = min(len(text), m.end() + max_len)
        snippet = " ".join(text[start:end].split())
        return snippet[:max_len]
    return ""


def _text_matches(text: str, patterns: List[re.Pattern[str]]) -> bool:
    return any(p.search(text) for p in patterns)


def _summary_text(profile: Dict[str, Any]) -> str:
    summary = profile.get("summary", {})
    if isinstance(summary, dict):
        return summary.get("value", "") or ""
    if isinstance(summary, str):
        return summary
    return ""


def _search_profile(
    profile: Dict[str, Any],
    patterns: List[re.Pattern[str]],
    allow_summary_years: bool = True,
) -> Tuple[bool, str, str, float]:
    """Search the structured profile for evidence matching ``patterns``.

    Returns (matched, section_name, snippet, years_detected).
    Sections are searched in this priority order:
        experience.entries[*].details → skills → education.entries
        → certifications → projects → summary text.

    Years detection operates over the **whole matched section's text**
    (not just the matching line) so a single-line mention like
    "Business Analyst" still surfaces the "7+ years" stated elsewhere
    in the same section. For experience-style items
    (``allow_summary_years=True``) we additionally fall back to the
    summary's "X+ years" line, which is where candidates
    self-describe their total tenure.
    """
    summary = _summary_text(profile)

    # ----- 1. experience entries (details) -----
    for entry in profile.get("experience", {}).get("entries", []) or []:
        details = entry.get("details") or []
        section_text = " | ".join(str(d) for d in details if d)
        for line in details:
            if not isinstance(line, str) or len(line) < _MIN_SECTION_LEN:
                continue
            if _text_matches(line, patterns):
                years = _detect_years_in_text(section_text or line, patterns)
                if years <= 0 and allow_summary_years and summary:
                    years = _detect_years_in_text(summary, patterns)
                snippet = _snippet_for(line, patterns)
                return True, "experience", snippet, years

    # ----- 2. skills section (one big bag) -----
    skills = profile.get("skills") or []
    if isinstance(skills, list):
        skills_text = " | ".join(str(s) for s in skills)
    else:
        skills_text = str(skills)
    if skills_text and _text_matches(skills_text, patterns):
        years = _detect_years_in_text(skills_text, patterns)
        if years <= 0 and allow_summary_years and summary:
            years = _detect_years_in_text(summary, patterns)
        snippet = _snippet_for(skills_text, patterns)
        return True, "skills", snippet, years

    # ----- 3. education entries -----
    for entry in profile.get("education", {}).get("entries", []) or []:
        desc = entry.get("description") or ""
        if desc and _text_matches(desc, patterns):
            years = _detect_years_in_text(desc, patterns)
            if years <= 0 and allow_summary_years and summary:
                years = _detect_years_in_text(summary, patterns)
            snippet = _snippet_for(desc, patterns)
            return True, "education", snippet, years

    # ----- 4. certifications -----
    for cert in profile.get("certifications") or []:
        text = cert if isinstance(cert, str) else json.dumps(cert)
        if _text_matches(text, patterns):
            return True, "certifications", _snippet_for(text, patterns), 0.0

    # ----- 5. projects -----
    for proj in profile.get("projects") or []:
        text = proj if isinstance(proj, str) else json.dumps(proj)
        if _text_matches(text, patterns):
            return True, "projects", _snippet_for(text, patterns), 0.0

    # ----- 6. summary (lowest priority; covers self-described experience) -----
    if summary and _text_matches(summary, patterns):
        years = _detect_years_in_text(summary, patterns) if allow_summary_years else 0.0
        snippet = _snippet_for(summary, patterns)
        return True, "summary", snippet, years

    return False, "", "", 0.0


def _normalize_importance(item: Dict[str, Any]) -> float:
    """Pull the recruiter-normalized importance from the config item.

    Falls back to ``importance`` itself if the config didn't pre-normalize.
    """
    if "normalized_importance" in item and item["normalized_importance"] is not None:
        return float(item["normalized_importance"])
    return float(item.get("importance", 10))


def _expected_years_for(item: Dict[str, Any], default: int) -> float:
    """Resolve ``expected_years`` for a config item.

    Order: explicit on the item → category-level → global default.
    """
    if item.get("expected_years") is not None:
        try:
            return float(item["expected_years"])
        except (TypeError, ValueError):
            pass
    return float(default)


def _is_experience_item(item: Dict[str, Any], category_name: str) -> bool:
    """Heuristic: does this item measure years of experience?

    The summary's "7+ years of experience" line describes *total
    tenure*, so we can use it as a fallback for these items — but
    not for credentials like "BE/BTech" or single-shot items like
    "CBAP / PMI-PBA" where the summary years are unrelated.

    Categories like "Core Skills", "Technology & Tools", and
    "Experience" all measure how long the candidate has *done* the
    thing, so they get the summary-years fallback. "Education" and
    "Certifications" measure the existence of a credential, not tenure.
    """
    cat = category_name.lower()
    if any(kw in cat for kw in ("education", "certification")):
        return False
    return True


def _make_reason(
    item_name: str,
    matched: bool,
    years: float,
    expected: float,
    importance: float,
    section: str,
) -> str:
    """Build a human-readable reason in the spec's tone."""
    if not matched:
        return f"No evidence of {item_name} found in the candidate's profile."
    # Avoid the "X experience experience" stutter when the item name
    # already mentions experience, years, or a complete clause
    # (e.g. "6+ years in business analysis", "BE/BTech or equivalent").
    blob = item_name.lower()
    if (
        blob.endswith("experience")
        or "years" in blob
        or " or " in blob
        or "equivalent" in blob
        or blob.startswith("be/")
        or blob.startswith("bi ")
    ):
        noun = item_name
    else:
        noun = f"{item_name} experience"
    if years <= 0:
        return (
            f"{item_name} mentioned in the {section} section, but no years of "
            f"experience could be measured. Recruiter target: {expected:g} year(s)."
        )
    if years >= expected:
        return (
            f"{years:g} year(s) of {noun} identified in the {section} section — "
            f"meets or exceeds the recruiter target of {expected:g} year(s)."
        )
    return (
        f"{years:g} year(s) of {noun} identified in the {section} section — "
        f"below the recruiter target of {expected:g} year(s)."
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_weights(role: str, base_dir: str | Path = "data/Job descriptions") -> Dict[str, Any]:
    """Load the filled weights config for a role.

    Args:
        role: Role bucket name (e.g., ``"BusinessAnalyst"``).
        base_dir: Parent of the per-role directory.

    Returns:
        Parsed weights config dict.

    Raises:
        FileNotFoundError: if the file does not exist.
    """
    weights_path = Path(base_dir) / role / f"{role}_WeightConfig_filled.json"
    if not weights_path.exists():
        raise FileNotFoundError(f"Weights config not found: {weights_path}")
    with open(weights_path, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_candidate(
    profile: Dict[str, Any],
    weights: Dict[str, Any],
    default_expected_years: int = DEFAULT_EXPECTED_YEARS,
) -> CandidateEvaluation:
    """Score a single candidate against the recruiter's weight policy.

    Args:
        profile: Structured candidate profile dict (the JSON produced by
            the resume parser under ``data/processed/<role>/<id>.json``).
        weights: Recruiter weight config (categories → items).
        default_expected_years: Used when neither the config nor the
            JD supplied an explicit years target for an item.

    Returns:
        A :class:`CandidateEvaluation` with per-item evidence and a
        deterministic 0-100 total.
    """
    candidate_id = (
        profile.get("candidate_id")
        or profile.get("id")
        or Path(profile.get("source_file", "")).stem
        or "unknown"
    )
    role = weights.get("role", "")

    # Normalization factor — recruiter assigned total is mapped to 100
    # (see WORKING_LOGIC Step 6). ``scale_factor`` is pre-computed in
    # the config (``100 / max_score``).
    total_max_cfg = float(weights.get("max_score") or 0)
    scale = float(
        weights.get("scale_factor")
        or (100.0 / total_max_cfg if total_max_cfg else 0.0)
    )

    total_raw = 0.0
    total_max = 0.0
    categories: List[CategoryEvaluation] = []

    for category in weights.get("categories", []):
        cat_eval = CategoryEvaluation(name=category.get("name", "Unknown"))
        cat_name = category.get("name", "Unknown")
        for item in category.get("items", []):
            item_name = item.get("name", "Unknown")
            importance = float(item.get("importance", 10)) or 10.0
            norm_imp = _normalize_importance(item)
            expected = _expected_years_for(item, default_expected_years)
            patterns = _aliases_for(item_name)
            is_exp_item = _is_experience_item(item, cat_name)

            matched, section, snippet, years = _search_profile(
                profile, patterns, allow_summary_years=is_exp_item
            )

            # Per-item raw score (0..importance), per WORKING_LOGIC Step 5.
            if not matched:
                raw = 0.0
            elif years <= 0:
                raw = round(importance * 0.3, 2)            # mentioned, not measured
            else:
                ratio = min(1.0, years / max(expected, 1e-9))
                raw = round(importance * ratio, 2)

            # Normalize to 100-point scale using the recruiter's contribution.
            score = round(raw * (norm_imp / importance), 2) if importance else 0.0

            reason = _make_reason(
                item_name, matched, years, expected, importance, section or "profile"
            )

            cat_eval.items.append(
                ItemEvaluation(
                    category=cat_eval.name,
                    item_name=item_name,
                    description=item.get("description", ""),
                    importance=importance,
                    expected_years=expected,
                    matched=matched,
                    years_detected=years,
                    raw_score=raw,
                    score=score,
                    section=section,
                    snippet=snippet,
                    reason=reason,
                )
            )
            total_raw += raw
            total_max += importance

        categories.append(cat_eval)

    total = round(total_raw * scale, 2) if total_max else 0.0

    return CandidateEvaluation(
        candidate_id=candidate_id,
        role=role,
        total_raw=total_raw,
        total_max=total_max,
        total=total,
        categories=categories,
    )


def evaluate_role(
    role: str,
    profile_dir: str | Path,
    weights_path: str | Path | None = None,
    default_expected_years: int = DEFAULT_EXPECTED_YEARS,
) -> List[CandidateEvaluation]:
    """Evaluate every profile in a role bucket."""
    profile_dir = Path(profile_dir)
    if weights_path is None:
        weights = load_weights(role)
    else:
        weights = json.loads(Path(weights_path).read_text(encoding="utf-8"))
    out: List[CandidateEvaluation] = []
    for path in sorted(profile_dir.glob("*.json")):
        profile = json.loads(path.read_text(encoding="utf-8"))
        out.append(evaluate_candidate(profile, weights, default_expected_years))
    return out


def render_report(evaluation: CandidateEvaluation) -> str:
    """Render the evaluation in the format from ``docs/PROJECT_OVERVIEW.md`` Phase 4.

    Per-item score / max are on the recruiter's 0-10 ``importance`` scale.
    The total at the top is normalized to 0-100 per WORKING_LOGIC Step 6.
    """
    lines: List[str] = []
    lines.append("=" * 70)
    lines.append("CANDIDATE EVALUATION REPORT")
    lines.append("=" * 70)
    lines.append(f"Candidate: {evaluation.candidate_id}")
    lines.append(f"Role: {evaluation.role}")
    lines.append("")
    lines.append(f"### Total Score: {evaluation.total:.1f} / 100")
    lines.append("")

    for cat in evaluation.categories:
        lines.append(f"### {cat.name}")
        lines.append("")
        for item in cat.items:
            lines.append(f"{item.item_name}")
            lines.append("")
            lines.append(f"Score: {item.raw_score:.1f} / {item.importance:.1f}")
            lines.append("")
            lines.append("Reason:")
            lines.append(item.reason)
            lines.append("")
            if item.snippet:
                lines.append("Evidence:")
                lines.append(f"  Section : {item.section}")
                lines.append(f'  "{item.snippet}"')
                lines.append("")

    lines.append("=" * 70)
    return "\n".join(lines)
