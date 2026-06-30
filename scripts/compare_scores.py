"""Side-by-side view of the canonical graded scoring output.

Per ``docs/AI_DESIGN_RATIONALE.md`` §5, HireIntel AI uses one
deterministic scorer (graded_scorer). This script reads the canonical
output and prints:

  * the top-N ranked candidates with their 0-100 totals,
  * per-category score breakdown,
  * per-item top strengths and gaps.

Run batch scoring first if the output file does not exist::

    python -m src.scoring.batch_score --role BusinessAnalyst
    python scripts/compare_scores.py --role BusinessAnalyst --top 10
"""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path
from typing import List


SCORES_ROOT = Path("data/scores")


def _graded_path(role: str) -> Path:
    return SCORES_ROOT / "graded" / f"{role}_ranked.json"


def _legacy_path(role: str, strategy: str) -> Path:
    """Locate a legacy keyword / semantic / hybrid file (read-only)."""
    return SCORES_ROOT / strategy / f"{role}_ranked.json"


def _load_graded(role: str) -> List[dict]:
    path = _graded_path(role)
    if not path.exists():
        # Friendly fallback: if only legacy outputs exist, warn and read them
        # so this script keeps working during the transition.
        for legacy in ("hybrid", "keyword", "semantic"):
            legacy_path = _legacy_path(role, legacy)
            if legacy_path.exists():
                warnings.warn(
                    f"No graded output at {path}; falling back to legacy "
                    f"{legacy_path}. Run "
                    f"`python -m src.scoring.batch_score --role {role}` to "
                    f"regenerate the canonical file.",
                    stacklevel=2,
                )
                return json.loads(legacy_path.read_text(encoding="utf-8"))
        raise FileNotFoundError(
            f"No scored output found for role '{role}'. "
            f"Run `python -m src.scoring.batch_score --role {role}` first."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _fmt(v, places: int = 1) -> str:
    if v is None:
        return "  --  "
    return f"{float(v):{places + 3}.{places}f}"


def _top_items_for(candidate: dict, k: int = 3) -> List[tuple[str, float, float]]:
    """Return top-k items by raw_score for a candidate.

    Each entry is (item_name, raw_score, importance).
    """
    items: list[tuple[str, float, float]] = []
    for cat in candidate.get("categories", []):
        for item in cat.get("items", []):
            items.append(
                (item.get("item_name", "?"),
                 float(item.get("raw_score", 0.0)),
                 float(item.get("importance", 0.0)))
            )
    items.sort(key=lambda t: (t[1] / max(t[2], 1e-9), t[1]), reverse=True)
    return items[:k]


def _gap_items_for(candidate: dict, k: int = 3) -> List[tuple[str, float, float]]:
    """Return bottom-k items (biggest gaps) by raw_score."""
    items: list[tuple[str, float, float]] = []
    for cat in candidate.get("categories", []):
        for item in cat.get("items", []):
            gap = float(item.get("importance", 0.0)) - float(item.get("raw_score", 0.0))
            items.append(
                (item.get("item_name", "?"), gap, float(item.get("importance", 0.0)))
            )
    items.sort(key=lambda t: t[1], reverse=True)
    return items[:k]


def compare(role: str, top: int = 10) -> None:
    rows = _load_graded(role)
    if not rows:
        print(f"No ranked candidates for role '{role}'.")
        return

    print(f"=== Role: {role} — canonical graded scoring ({len(rows)} candidates) ===")
    print()
    header = (
        f"{'rank':>4} {'total':>6}   "
        f"{'raw':>7} / {'max':>4}   "
        f"candidate_id"
    )
    print(header)
    print("-" * len(header))

    shown = rows[:top]
    for row in shown:
        rank = row.get("rank", "?")
        total = row.get("total", 0.0)
        raw = row.get("total_raw", 0.0)
        mx = row.get("total_max", 0.0)
        print(
            f"{str(rank):>4} {total:>6.1f}   "
            f"{raw:>7.1f} / {mx:>4.1f}   "
            f"{row.get('candidate_id', '')}"
        )

    print()
    print("=== Per-candidate top strengths and gaps ===")
    for row in shown:
        print()
        print(f"  #{row.get('rank', '?')}  {row.get('candidate_id', '')}  "
              f"total={row.get('total', 0.0):.1f}/100")
        strengths = _top_items_for(row, k=3)
        gaps = _gap_items_for(row, k=3)
        if strengths:
            print("    Top strengths:")
            for name, raw, imp in strengths:
                ratio = (raw / imp * 100.0) if imp else 0.0
                print(f"      [+] {name:<40s}  {raw:>5.1f} / {imp:>4.1f}  ({ratio:>5.1f}%)")
        if gaps:
            print("    Biggest gaps:")
            for name, gap, imp in gaps:
                print(f"      [-] {name:<40s}  gap {gap:>5.1f} of {imp:>4.1f}")

    print()
    print("Notes:")
    print("  - 'total' is the candidate's 0-100 normalized score (WORKING_LOGIC Step 6).")
    print("  - 'raw / max' is the sum of per-item raw scores vs the recruiter's max.")
    print("  - Top strengths and gaps are derived from the structured profile")
    print("    evidence, not from any LLM call.")
    print(f"  - All {len(rows)} candidates are in {SCORES_ROOT / 'graded' / f'{role}_ranked.json'};")
    print(f"    rerun with --top {len(rows)} to see everyone.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Display the canonical graded ranking for a role."
    )
    parser.add_argument("--role", required=True, help="Role bucket, e.g. BusinessAnalyst")
    parser.add_argument("--top", type=int, default=10, help="Show top N candidates")
    args = parser.parse_args()

    compare(args.role, top=args.top)


if __name__ == "__main__":
    main()