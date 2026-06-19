"""Deterministic candidate evaluation engine.

This module turns a structured profile + a recruiter-weighted configuration
into an explainable, evidence-backed score.

Design contract (per ``AGENTS.md`` and ``docs/AI_DESIGN_RATIONALE.md``):

* Scoring is **deterministic** — same inputs always produce the same outputs.
* The LLM is **never** used to compute or rank candidates. It only supports
  extraction (parsing) and recruiter-facing chat.
* Every score component is **explainable** — we record the snippet and chunk
  id that earned (or failed to earn) the points.
* Per-item scoring is **binary**: the candidate either has the item or not,
  earning the full ``importance`` weight or 0. The ``ScoringGuide.md``
  defines this convention.

Public API:

* :func:`evaluate_candidate` — score a single profile against a weight config.
* :func:`evaluate_batch` — score every profile in a role bucket.
* :func:`evaluate_role` — load all profiles in ``data/processed/<role>`` and
  rank them against a weight config.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Keyword dictionaries per item name
#
# These keyword sets drive the binary match logic. They are intentionally
# generous (synonyms + abbreviations) because recruiters want to recognize
# real-world variants. Each list is AND-of-OR semantics: a chunk matches the
# item if ANY keyword in the list appears in the chunk text.
# ---------------------------------------------------------------------------

_KEYWORDS: Dict[str, List[str]] = {
    # Core Skills
    "requirements gathering": [
        "requirement gathering", "requirements gathering", "requirement elicitation",
        "elicit requirement", "gather requirement", "user story", "user stories",
        "acceptance criteria", "functional spec", "functional specification",
        "business requirement",
    ],
    "stakeholder management": [
        "stakeholder", "stakeholders", "stakeholder management",
        "cross-functional", "cross functional", "collaborate with",
        "liaison", "partners with", "business partner", "client engagement",
    ],
    "process mapping": [
        "process map", "process mapping", "process improvement",
        "business process", "process re-engineering", "process redesign",
        "process optimization", "process analysis",
        "as-is", "to-be",
    ],
    "data analysis": [
        "data analysis", "data analytics", "data driven", "data-driven",
        "analyze data", "analysed data", "insight", "kpi", "metrics",
        "trend analysis", "reporting", "dashboard",
    ],
    "communication": [
        "communication", "communicate", "presented", "presentation",
        "report", "reporting", "stakeholder communication",
        "status update", "executive summary", "documentation",
    ],
    # Technology & Tools
    "power bi": ["power bi", "powerbi", "pbi", "dax", "power query"],
    "sql": ["sql", "mysql", "postgresql", "postgres", "t-sql", "tsql", "pl/sql", "bigquery"],
    "excel": ["excel", "vlookup", "pivot table", "pivottables", "spreadsheet"],
    "agile tools": ["jira", "azure devops", "ado", "confluence", "trello", "asana", "agile", "scrum", "kanban", "sprint"],
    # Experience
    "6+ years in business analysis": [
        # Years are handled separately via the dates parser — we still keep
        # this for textual evidence, e.g. "6 years experience".
        "business analyst", "business analysis", "product analyst", "systems analyst",
    ],
    "industry/domain experience": [
        "industry", "domain", "vertical", "sector", "manufacturing", "retail",
        "healthcare", "finance", "fintech", "banking", "insurance", "logistics",
        "pharma", "telecom", "media", "ecommerce",
    ],
    # Education
    "be/btech or equivalent": [
        "b.e", "be ", "btech", "b.tech", "bachelor of engineering",
        "bachelor's in engineering", "bachelor of technology",
        "b.s.", "bs ", "b.sc", "bsc", "bachelor of science",
        "bachelor's", "undergraduate", "bba", "b.com", "bcom",
    ],
    # Certifications
    "cbap / pmi-pba": ["cbap", "pmi-pba", "pmi pba", "ccba"],
    "bi / analytics certification": [
        "power bi certified", "tableau certified", "google data analytics",
        "ibm data science", "microsoft certified: data analyst", "bi certification",
        "analytics certification",
    ],
}


# Common alternative phrasings for "BE/BTech or equivalent" — caught because
# recruiters want US/UK bachelor's holders to also earn the points.
_BACHELOR_KEYWORDS = ["bachelor", "undergraduate", "bs ", "b.s.", "bba"]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ScoreComponent:
    """One weighted item and the candidate's outcome on it."""

    category: str
    item_name: str
    description: str
    importance: int
    matched: bool
    matched_weight: float
    chunk_id: Optional[str] = None
    snippet: Optional[str] = None
    source_file: Optional[str] = None
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "item_name": self.item_name,
            "description": self.description,
            "importance": self.importance,
            "matched": self.matched,
            "matched_weight": round(self.matched_weight, 4),
            "chunk_id": self.chunk_id,
            "snippet": self.snippet,
            "source_file": self.source_file,
            "notes": self.notes,
        }


@dataclass
class CandidateScore:
    """Aggregate score for one candidate against a weight config."""

    candidate_id: str
    role_bucket: str
    raw_score: float
    max_score: float
    normalized_score: float
    scale_factor: float
    components: List[ScoreComponent] = field(default_factory=list)
    source_file: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "role_bucket": self.role_bucket,
            "source_file": self.source_file,
            "raw_score": round(self.raw_score, 4),
            "max_score": round(self.max_score, 4),
            "normalized_score": round(self.normalized_score, 4),
            "scale_factor": round(self.scale_factor, 4),
            "components": [c.to_dict() for c in self.components],
            "matched_components": sum(1 for c in self.components if c.matched),
            "total_components": len(self.components),
        }


# ---------------------------------------------------------------------------
# Profile helpers
# ---------------------------------------------------------------------------


def _profile_text(profile: Dict[str, Any]) -> str:
    """Flatten a profile's free-text fields into one searchable string."""
    parts: List[str] = []
    summary = (profile.get("summary") or {}).get("value") or ""
    if summary:
        parts.append(summary)
    parts.extend(profile.get("skills") or [])
    parts.extend(profile.get("certifications") or [])
    parts.extend(profile.get("languages") or [])
    parts.extend(profile.get("projects") or [])
    for entry in (profile.get("experience") or {}).get("entries") or []:
        for k in ("title", "company", "location", "dates"):
            if entry.get(k):
                parts.append(str(entry[k]))
        for bullet in entry.get("details") or []:
            if bullet:
                parts.append(str(bullet))
    for entry in (profile.get("education") or {}).get("entries") or []:
        desc = entry.get("description") or ""
        if desc:
            parts.append(desc)
    return "\n".join(parts)


def _total_years_experience(profile: Dict[str, Any]) -> float:
    """Best-effort estimate of years of experience from experience entries."""
    spans: List[Tuple[int, int]] = []
    current_year = 2026  # Deterministic anchor; replace with datetime.now().year for prod.
    for entry in (profile.get("experience") or {}).get("entries") or []:
        dates = entry.get("dates") or ""
        years = [int(y) for y in re.findall(r"(?:19|20)\d{2}", dates)]
        if not years:
            continue
        if "present" in dates.lower() or "current" in dates.lower():
            end = current_year
        else:
            end = years[-1] if len(years) >= 2 else years[0]
        start = years[0]
        if end >= start:
            spans.append((start, end))
    if not spans:
        return 0.0
    spans.sort()
    merged: List[List[int]] = [list(spans[0])]
    for s, e in spans[1:]:
        if s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return float(sum(e - s for s, e in merged))


# ---------------------------------------------------------------------------
# Matchers
# ---------------------------------------------------------------------------


def _keyword_match(text: str, keywords: List[str]) -> Optional[str]:
    """Return the first keyword that appears in ``text`` (case-insensitive)."""
    lower = text.lower()
    for kw in keywords:
        if kw.lower() in lower:
            return kw
    return None


def _has_bachelor(profile: Dict[str, Any]) -> bool:
    """Detect a bachelor's degree from the education entries."""
    for entry in (profile.get("education") or {}).get("entries") or []:
        desc = (entry.get("description") or "").lower()
        if any(k in desc for k in _BACHELOR_KEYWORDS):
            return True
    return False


# ---------------------------------------------------------------------------
# Weight-config loading
# ---------------------------------------------------------------------------


def load_weight_config(path: Path) -> Dict[str, Any]:
    """Load a recruiter-filled weight config (JSON)."""
    with Path(path).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def compute_scale_factor(weight_config: Dict[str, Any]) -> Tuple[float, float]:
    """Return ``(max_score, scale_factor)`` where ``scale = 100 / max`` if max > 0."""
    max_score = 0
    for category in weight_config.get("categories", []):
        for item in category.get("items", []):
            max_score += int(item.get("importance") or 0)
    scale = (100.0 / max_score) if max_score > 0 else 0.0
    return float(max_score), float(scale)


# ---------------------------------------------------------------------------
# Item-level scoring
# ---------------------------------------------------------------------------


def _find_evidence_chunk(
    profile: Dict[str, Any],
    chunks_by_id: Dict[str, Dict[str, Any]],
    keywords: List[str],
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Pick the best-matching chunk for a matched item.

    Returns ``(chunk_id, snippet, source_file)`` or ``(None, None, None)``
    if no chunk matches.
    """
    candidate_id = profile.get("candidate_id")
    if not candidate_id:
        return None, None, None
    candidates = [
        c for c in chunks_by_id.values() if c.get("candidate_id") == candidate_id
    ]
    for chunk in candidates:
        text = (chunk.get("text") or "").lower()
        for kw in keywords:
            if kw.lower() in text:
                snippet = (chunk.get("text") or "")[:240]
                return chunk.get("chunk_id"), snippet, chunk.get("source_file")
    return None, None, None


def score_item(
    category: str,
    item: Dict[str, Any],
    profile: Dict[str, Any],
    profile_text: str,
    chunks_by_id: Dict[str, Dict[str, Any]],
) -> ScoreComponent:
    """Score a single weight item against a profile.

    Per the scoring guide, the match is binary: either the candidate has the
    item (earns the full ``importance``) or does not (earns 0). Notes record
    *why* a match did or did not occur.
    """
    name = item.get("name", "").strip()
    importance = int(item.get("importance") or 0)
    description = item.get("description", "")
    keywords = _KEYWORDS.get(name.lower(), [name.lower()])

    matched = False
    notes = ""

    # ----- Special-case logic for items that need richer signals -----
    if name.lower() == "6+ years in business analysis":
        years = _total_years_experience(profile)
        matched = years >= 6.0
        notes = f"Estimated total experience: {years:.1f} years"
        matched_weight = importance if matched else 0.0
    elif name.lower() == "be/btech or equivalent":
        matched = _has_bachelor(profile)
        notes = "Bachelor's degree detected in education entries" if matched else "No bachelor's degree detected"
        matched_weight = importance if matched else 0.0
    else:
        kw = _keyword_match(profile_text, keywords)
        matched = kw is not None
        if matched:
            notes = f"Matched keyword: '{kw}'"
        else:
            notes = "No keyword match found"
        matched_weight = importance if matched else 0.0

    chunk_id = None
    snippet = None
    source_file = None
    if matched:
        chunk_id, snippet, source_file = _find_evidence_chunk(profile, chunks_by_id, keywords)

    return ScoreComponent(
        category=category,
        item_name=name,
        description=description,
        importance=importance,
        matched=matched,
        matched_weight=matched_weight,
        chunk_id=chunk_id,
        snippet=snippet,
        source_file=source_file,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Candidate-level scoring
# ---------------------------------------------------------------------------


def evaluate_candidate(
    profile: Dict[str, Any],
    weight_config: Dict[str, Any],
    role_bucket: str = "",
    chunks_by_id: Optional[Dict[str, Dict[str, Any]]] = None,
) -> CandidateScore:
    """Score one parsed profile against a weight config.

    Args:
        profile: Parsed profile dict (from ``parse_resume``).
        weight_config: Recruiter-filled weight config JSON.
        role_bucket: Used for metadata.
        chunks_by_id: Optional ``{chunk_id: chunk_dict}`` map. If provided,
            matched components link to a citation chunk.
    """
    max_score, scale = compute_scale_factor(weight_config)
    profile_text = _profile_text(profile)
    chunks_by_id = chunks_by_id or {}

    components: List[ScoreComponent] = []
    raw_score = 0.0
    for category in weight_config.get("categories", []):
        cat_name = category.get("name", "")
        for item in category.get("items", []):
            comp = score_item(cat_name, item, profile, profile_text, chunks_by_id)
            raw_score += comp.matched_weight
            components.append(comp)

    normalized = raw_score * scale
    return CandidateScore(
        candidate_id=profile.get("candidate_id") or "cand_unknown",
        role_bucket=role_bucket or profile.get("role_bucket", ""),
        raw_score=raw_score,
        max_score=max_score,
        normalized_score=normalized,
        scale_factor=scale,
        components=components,
        source_file=profile.get("source_file"),
    )


def rank_candidates(scores: List[CandidateScore]) -> List[CandidateScore]:
    """Rank by normalized_score desc, ties broken by matched components desc."""
    return sorted(
        scores,
        key=lambda s: (s.normalized_score, sum(1 for c in s.components if c.matched)),
        reverse=True,
    )


# ---------------------------------------------------------------------------
# Batch scoring
# ---------------------------------------------------------------------------


def _load_chunks_index(role_bucket: str) -> Dict[str, Dict[str, Any]]:
    """Load ``data/chunks/<role_bucket>/*.jsonl`` into a chunk_id -> chunk map."""
    from src.rag.index import CHUNKS_DIR

    out: Dict[str, Dict[str, Any]] = {}
    chunk_dir = CHUNKS_DIR / role_bucket
    if not chunk_dir.exists():
        return out
    for path in chunk_dir.glob("*.jsonl"):
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                out[rec["chunk_id"]] = rec
    return out


def evaluate_batch(
    profiles: List[Dict[str, Any]],
    weight_config: Dict[str, Any],
    role_bucket: str = "",
    include_chunks: bool = True,
) -> List[CandidateScore]:
    """Score every profile in a list and return ranked results."""
    chunks_by_id = _load_chunks_index(role_bucket) if include_chunks else {}
    scores = [
        evaluate_candidate(p, weight_config, role_bucket=role_bucket, chunks_by_id=chunks_by_id)
        for p in profiles
    ]
    return rank_candidates(scores)


def load_profiles_for_role(role_bucket: str) -> List[Dict[str, Any]]:
    """Read all profile JSONs in ``data/processed/<role_bucket>/``."""
    from src.resume_parsing.batch_parse import PROCESSED  # type: ignore[attr-defined]

    profiles: List[Dict[str, Any]] = []
    pdir = PROCESSED / role_bucket
    if not pdir.exists():
        return profiles
    for path in sorted(pdir.glob("*.json")):
        with path.open("r", encoding="utf-8") as fh:
            profiles.append(json.load(fh))
    return profiles


def evaluate_role(
    role_bucket: str,
    weight_config_path: Path,
    output_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """End-to-end: load all profiles for a role, score them, write ranked output."""
    profiles = load_profiles_for_role(role_bucket)
    if not profiles:
        return []
    weight_config = load_weight_config(weight_config_path)
    ranked = evaluate_batch(profiles, weight_config, role_bucket=role_bucket, include_chunks=True)
    results = [s.to_dict() for s in ranked]
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as fh:
            json.dump(results, fh, ensure_ascii=False, indent=2)
    return results

