"""Show the canonical graded breakdown for the top-ranked candidate.

Reads ``data/scores/graded/<role>_ranked.json`` (produced by
``python -m src.scoring.batch_score``) and prints the per-item
evidence + reason for the top candidate.

Usage:
    python scripts/demo_scoring.py
    python scripts/demo_scoring.py --role PythonDeveloper
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


SCORES_ROOT = Path("data/scores")


def _ranked_path(role: str) -> Path:
    return SCORES_ROOT / "graded" / f"{role}_ranked.json"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Show the canonical graded breakdown for the top candidate of a role."
    )
    parser.add_argument("--role", default="BusinessAnalyst", help="Role bucket.")
    args = parser.parse_args()

    ranked_path = _ranked_path(args.role)
    if not ranked_path.exists():
        print(f"{ranked_path} not found. Run `python -m src.scoring.batch_score --role {args.role}` first.")
        return

    ranked = json.loads(ranked_path.read_text(encoding="utf-8"))
    if not ranked:
        print(f"{ranked_path} is empty.")
        return

    top = ranked[0]
    print(f"=== Top candidate: {top['candidate_id']} ===")
    print(f"Role           : {top.get('role', args.role)}")
    print(f"Score          : {top['total']:.1f} / 100")
    print(f"Raw            : {top['total_raw']:.1f} / {top['total_max']:.1f}")
    print(f"Rank           : #{top.get('rank', 1)}")
    print()
    print("=== Per-category breakdown ===")
    for cat in top.get("categories", []):
        print(f"  [{cat['name']}]  score={cat['score']:.1f}  max={cat['max_score']:.1f}")
        for item in cat.get("items", []):
            mark = "+" if item.get("matched") else "-"
            print(
                f"    {mark} {item['item_name']:<40s}  "
                f"raw={item['raw_score']:>5.1f}  "
                f"imp={item['importance']:>4.1f}  "
                f"years={item.get('years_detected', 0):>4.1f}"
            )
            if item.get("section") and item.get("snippet"):
                print(
                    f"        [{item['section']}] "
                    f"{(item['snippet'] or '')[:90]!r}"
                )
            if item.get("reason"):
                print(f"        reason: {item['reason']}")
        print()


if __name__ == "__main__":
    main()