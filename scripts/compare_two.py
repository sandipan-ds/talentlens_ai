"""Compare two candidates side-by-side and generate a "Why A ranked above B" narrative.

This script loads two candidate profiles, their scores, and generates a recruiter-
friendly comparison using the LLM to explain score differences and highlight key
differentiators.

Usage:
    python scripts/compare_two.py --candidate-a <id_a> --candidate-b <id_b> --role <role>
    
Example:
    python scripts/compare_two.py --candidate-a cand_f920c9c311de --candidate-b cand_abc123 --role BusinessAnalyst
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Optional
import os
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from hireintel_ai.core.config import Settings
from hireintel_ai.llm.service import LlmService


def _load_candidate_profile(role: str, candidate_id_or_file: str) -> Optional[dict]:
    """Load a candidate's full parsed profile from data/processed.
    
    Args:
        role: Job role bucket (e.g., 'BusinessAnalyst')
        candidate_id_or_file: Either candidate_id (e.g., '8c5959c7993cb7a1') or
                              full candidate_id (e.g., 'cand_f920c9c311de')
    """
    settings = Settings()
    profile_dir = settings.resolved_processed_data_dir / role
    
    if not profile_dir.exists():
        return None
    
    # Try exact match first
    profile_file = profile_dir / f"{candidate_id_or_file}.json"
    if profile_file.exists():
        with open(profile_file, "r", encoding="utf-8") as f:
            return json.load(f)
    
    # Search by partial match (file stem contains the ID)
    for file in profile_dir.glob("*.json"):
        if candidate_id_or_file in file.stem:
            with open(file, "r", encoding="utf-8") as f:
                return json.load(f)
    
    return None


def _load_scores(role: str, strategy: str = "graded") -> dict:
    """Load all scored candidates for a role.

    Per ``docs/AI_DESIGN_RATIONALE.md`` §5, HireIntel AI uses the
    single canonical graded scorer. Legacy ``--strategy`` values
    (``hybrid`` / ``keyword`` / ``semantic``) are accepted for
    backward compatibility and forwarded to the graded output.
    """
    possible_paths = [
        Path("data/scores") / "graded" / f"{role}_ranked.json",
        Path("data/scores") / strategy / f"{role}_ranked.json",   # legacy
        Path("data/scores") / f"{role}_ranked.json",              # legacy fallback
    ]

    for scores_file in possible_paths:
        if scores_file.exists():
            with open(scores_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {row["candidate_id"]: row for row in data}

    return {}


def _resolve_candidate_id(role: str, user_input: str, all_scores: dict) -> Optional[str]:
    """Resolve user input to a canonical candidate_id in the scores.

    Args:
        role: Job role bucket
        user_input: User-provided candidate identifier (file stem or candidate_id)
        all_scores: Loaded scores dict

    Returns:
        Canonical candidate_id from scores, or None if not found.
    """
    # 1. Direct match against a candidate_id in the scores
    if user_input in all_scores:
        return user_input

    # 2. Match against source_file basename in the score record
    for cid, score_rec in all_scores.items():
        source_file = score_rec.get("source_file", "")
        if source_file and user_input in source_file:
            return cid

    # 3. The user gave us a profile file stem — load it directly and use
    #    its ``candidate_id`` (which is what the graded output uses).
    settings = Settings()
    profile_dir = settings.resolved_processed_data_dir / role
    profile_file = profile_dir / f"{user_input}.json"

    if profile_file.exists():
        with open(profile_file, "r", encoding="utf-8") as f:
            profile = json.load(f)
        cand_id = profile.get("candidate_id")
        if cand_id and cand_id in all_scores:
            return cand_id
        # Fall back: maybe the profile's candidate_id matches a score we
        # haven't loaded yet — try the partial-match sweep as a last resort.
        for cid in all_scores:
            if cand_id and cand_id in cid:
                return cid

    # 4. Partial match against any known candidate_id
    for cid in all_scores:
        if user_input in cid:
            return cid

    return None


def _extract_candidate_info(profile: dict) -> dict:
    """Extract key candidate information for comparison."""
    return {
        "name": profile.get("name", {}).get("value", "N/A"),
        "email": profile.get("contact", {}).get("emails", ["N/A"])[0] if profile.get("contact", {}).get("emails") else "N/A",
        "summary": profile.get("summary", {}).get("value", "N/A")[:300],  # Truncate for readability
        "experience_count": len(profile.get("experience", {}).get("entries", [])),
        "education": profile.get("education", {}).get("value", "N/A")[:200],
        "skills": profile.get("skills", [])[:5] if isinstance(profile.get("skills", []), list) else [],
    }


def _flatten_items(score: Optional[dict]) -> List[dict]:
    """Flatten the graded score's categories → items into one list."""
    if not score:
        return []
    items: List[dict] = []
    for cat in score.get("categories", []):
        for item in cat.get("items", []):
            items.append({**item, "_category": cat.get("name", "")})
    return items


def _graded_score_value(score: Optional[dict]) -> float:
    """Read the canonical 0-100 score from a graded score row."""
    if not score:
        return 0.0
    return float(score.get("total", score.get("final_score", score.get("normalized_score", 0.0))))


def _build_comparison_table(
    candidate_a: dict,
    candidate_b: dict,
    profile_a: dict,
    profile_b: dict,
    score_a: Optional[dict],
    score_b: Optional[dict],
) -> str:
    """Build a formatted comparison table using graded scoring."""
    table = []
    table.append("=" * 120)
    table.append("CANDIDATE COMPARISON")
    table.append("=" * 120)
    table.append("")

    # Extract info
    info_a = _extract_candidate_info(profile_a)
    info_b = _extract_candidate_info(profile_b)

    score_a_val = _graded_score_value(score_a)
    score_b_val = _graded_score_value(score_b)

    # Header
    table.append(f"{'Attribute':<30} {'Candidate A':<40} {'Candidate B':<40}")
    table.append("-" * 120)

    # Basic info
    table.append(f"{'Name':<30} {info_a['name']:<40} {info_b['name']:<40}")
    table.append(f"{'Email':<30} {str(info_a['email'])[:39]:<40} {str(info_b['email'])[:39]:<40}")
    table.append(f"{'Experience Entries':<30} {info_a['experience_count']:<40} {info_b['experience_count']:<40}")
    table.append("")

    # Scores
    table.append(f"{'Graded Score':<30} {score_a_val:<40.2f} {score_b_val:<40.2f}")
    table.append(
        f"{'Score Difference':<30} "
        f"{score_a_val - score_b_val:+.2f} "
        f"{'(A ahead)' if score_a_val > score_b_val else '(B ahead)' if score_b_val > score_a_val else '(Tie)':<40}"
    )
    table.append("")

    # Component breakdown (graded)
    items_a = _flatten_items(score_a)
    items_b = _flatten_items(score_b)

    table.append("COMPONENT BREAKDOWN (graded):")
    table.append("-" * 120)

    if items_a:
        a_matched = sum(1 for c in items_a if c.get("matched"))
        table.append(
            f"{'Matched Items (A)':<30} {a_matched:<40} {len(items_a):<40}"
        )

    if items_b:
        b_matched = sum(1 for c in items_b if c.get("matched"))
        table.append(
            f"{'Matched Items (B)':<30} {'':40} {b_matched:<40}"
        )

    table.append("")

    # Top strengths for A
    if items_a:
        table.append("Top Strengths — Candidate A:")
        matched_a = [c for c in items_a if c.get("matched")]
        matched_a.sort(key=lambda c: c.get("raw_score", 0.0), reverse=True)
        for comp in matched_a[:3]:
            snippet = comp.get("snippet") or comp.get("reason", "N/A")
            if isinstance(snippet, str):
                snippet = snippet[:60] + "..." if len(snippet) > 60 else snippet
            else:
                snippet = "N/A"
            raw = float(comp.get("raw_score", 0.0))
            imp = float(comp.get("importance", 1.0)) or 1.0
            table.append(
                f"  + {comp.get('item_name', 'Unknown'):<36s}  "
                f"{raw:>5.1f} / {imp:>4.1f}  | {snippet}"
            )
        table.append("")

    # Top strengths for B
    if items_b:
        table.append("Top Strengths — Candidate B:")
        matched_b = [c for c in items_b if c.get("matched")]
        matched_b.sort(key=lambda c: c.get("raw_score", 0.0), reverse=True)
        for comp in matched_b[:3]:
            snippet = comp.get("snippet") or comp.get("reason", "N/A")
            if isinstance(snippet, str):
                snippet = snippet[:60] + "..." if len(snippet) > 60 else snippet
            else:
                snippet = "N/A"
            raw = float(comp.get("raw_score", 0.0))
            imp = float(comp.get("importance", 1.0)) or 1.0
            table.append(
                f"  + {comp.get('item_name', 'Unknown'):<36s}  "
                f"{raw:>5.1f} / {imp:>4.1f}  | {snippet}"
            )
        table.append("")

    # Biggest gaps
    if items_a or items_b:
        table.append("Biggest Gaps:")
        gaps_a = sorted(
            [c for c in items_a if not c.get("matched")],
            key=lambda c: float(c.get("importance", 0.0)),
            reverse=True,
        )
        gaps_b = sorted(
            [c for c in items_b if not c.get("matched")],
            key=lambda c: float(c.get("importance", 0.0)),
            reverse=True,
        )
        for comp in gaps_a[:2]:
            table.append(
                f"  A gap: {comp.get('item_name', 'Unknown')} "
                f"(importance {comp.get('importance', 0.0)})"
            )
        for comp in gaps_b[:2]:
            table.append(
                f"  B gap: {comp.get('item_name', 'Unknown')} "
                f"(importance {comp.get('importance', 0.0)})"
            )
        table.append("")

    table.append("=" * 120)

    return "\n".join(table)


def _generate_llm_explanation(
    candidate_a_id: str,
    candidate_b_id: str,
    score_a: Optional[dict],
    score_b: Optional[dict],
    profile_a: dict,
    profile_b: dict,
    role: str,
) -> str:
    """Generate an LLM-powered explanation of why A ranked above B.

    Uses the LLM service to narrate the deterministic score delta.
    Falls back to a deterministic narrative when the LLM is not
    configured. The score itself is never produced by the LLM.
    """
    score_a_val = _graded_score_value(score_a)
    score_b_val = _graded_score_value(score_b)

    info_a = _extract_candidate_info(profile_a)
    info_b = _extract_candidate_info(profile_b)

    # Flatten graded items for both candidates.
    components_a = _flatten_items(score_a)
    components_b = _flatten_items(score_b)

    # Try LLM explanation
    llm = LlmService()
    explanation = []
    explanation.append("WHY THIS RANKING?")
    explanation.append("=" * 60)
    explanation.append("")

    if llm.is_configured():
        explanation.append("[LLM Analysis]")
        llm_explanation = llm.explain_candidate_score(
            info_a['name'],
            info_b['name'],
            score_a_val,
            score_b_val,
            components_a,
            components_b,
        )
        explanation.append(llm_explanation)
    else:
        # Fallback to deterministic explanation
        explanation.append("[Deterministic Analysis - LLM not configured]")
        if score_a_val > score_b_val:
            diff = score_a_val - score_b_val
            explanation.append(f"{info_a['name']} ranked HIGHER by {diff:.1f} points.")

            a_matched = sum(1 for c in components_a if c.get("matched"))
            b_matched = sum(1 for c in components_b if c.get("matched"))
            if a_matched > 0 or b_matched > 0:
                explanation.append(f"Matched {a_matched} requirements vs {b_matched} for {info_b['name']}.")

        elif score_b_val > score_a_val:
            diff = score_b_val - score_a_val
            explanation.append(f"{info_b['name']} ranked HIGHER by {diff:.1f} points.")

            b_matched = sum(1 for c in components_b if c.get("matched"))
            a_matched = sum(1 for c in components_a if c.get("matched"))
            if b_matched > 0 or a_matched > 0:
                explanation.append(f"Matched {b_matched} requirements vs {a_matched} for {info_a['name']}.")
        else:
            explanation.append(f"Both candidates scored EQUALLY at {score_a_val:.1f} points.")
            explanation.append("Consider other factors like cultural fit, growth potential, or recent experience.")

    explanation.append("")
    explanation.append("RECRUITER NOTE:")
    explanation.append("Review the component breakdown above. Scores are deterministic")
    explanation.append("(canonical graded scorer) and reflect objective requirement matching.")
    explanation.append("Consider scheduling interviews with both top candidates.")

    return "\n".join(explanation)


def compare_candidates(
    candidate_a_input: str,
    candidate_b_input: str,
    role: str,
    strategy: str = "graded",
) -> None:
    """Load and compare two candidates."""

    # Load scores first
    all_scores = _load_scores(role, strategy)

    if not all_scores:
        print(f"[X] No scores found for role '{role}' and strategy '{strategy}'.")
        print(f"    Run `python -m src.scoring.batch_score --role {role}` first.")
        return
    
    # Resolve candidate IDs
    candidate_a_id = _resolve_candidate_id(role, candidate_a_input, all_scores)
    candidate_b_id = _resolve_candidate_id(role, candidate_b_input, all_scores)
    
    if not candidate_a_id:
        print(f"[X] Could not find candidate A: {candidate_a_input}")
        print(f"   Available candidates: {', '.join(list(all_scores.keys())[:5])}...")
        return
    
    if not candidate_b_id:
        print(f"[X] Could not find candidate B: {candidate_b_input}")
        print(f"   Available candidates: {', '.join(list(all_scores.keys())[:5])}...")
        return
    
    # Load profiles
    profile_a = _load_candidate_profile(role, candidate_a_input)
    profile_b = _load_candidate_profile(role, candidate_b_input)
    
    if not profile_a:
        print(f"[X] Could not load profile for candidate A: {candidate_a_input}")
        return
    
    if not profile_b:
        print(f"[X] Could not load profile for candidate B: {candidate_b_input}")
        return
    
    # Get scores
    score_a = all_scores.get(candidate_a_id)
    score_b = all_scores.get(candidate_b_id)
    
    # Display comparison table
    table = _build_comparison_table(
        candidate_a_id,
        candidate_b_id,
        profile_a,
        profile_b,
        score_a,
        score_b,
    )
    print(table)
    print()
    
    # Display LLM-powered explanation
    explanation = _generate_llm_explanation(
        candidate_a_id,
        candidate_b_id,
        score_a,
        score_b,
        profile_a,
        profile_b,
        role,
    )
    print(explanation)
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Compare two candidates side-by-side with score breakdown and ranking explanation."
    )
    parser.add_argument(
        "--candidate-a",
        required=True,
        help="ID of first candidate (e.g., cand_f920c9c311de or a short name like '8c5959c7993cb7a1')",
    )
    parser.add_argument(
        "--candidate-b",
        required=True,
        help="ID of second candidate",
    )
    parser.add_argument(
        "--role",
        default="BusinessAnalyst",
        help="Job role to compare for (default: BusinessAnalyst)",
    )
    parser.add_argument(
        "--strategy",
        choices=["graded", "keyword", "semantic", "hybrid"],
        default="graded",
        help=(
            "Scoring strategy to use. 'graded' (default) reads the canonical "
            "single scorer output; legacy values are kept as deprecated aliases."
        ),
    )
    
    args = parser.parse_args()
    
    compare_candidates(
        args.candidate_a,
        args.candidate_b,
        args.role,
        args.strategy,
    )


if __name__ == "__main__":
    main()

