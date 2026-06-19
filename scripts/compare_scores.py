"""Side-by-side comparison of keyword, semantic, and hybrid rankings.

Reads:
    data/scores/keyword/<role>_ranked.json
    data/scores/semantic/<role>_ranked.json
    data/scores/hybrid/<role>_ranked.json

Prints a table that shows how each candidate's rank changes between
strategies. This is the recruiter-facing view that lets you decide which
strategy to trust for a given role.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional


SCORES_ROOT = Path("data/scores")


def _load_rank_map(path: Path, score_key: str) -> Dict[str, float]:
    """Return ``{candidate_id: score}`` from a ranked JSON file."""
    if not path.exists():
        return {}
    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    return {row["candidate_id"]: float(row.get(score_key, 0.0)) for row in data}


def _load_rank_order(path: Path) -> Dict[str, int]:
    """Return ``{candidate_id: rank}`` (rank = 1-based position in file)."""
    if not path.exists():
        return {}
    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    return {row["candidate_id"]: i + 1 for i, row in enumerate(data)}


def compare(role: str, top: int = 10) -> None:
    keyword_scores = _load_rank_map(SCORES_ROOT / "keyword" / f"{role}_ranked.json", "normalized_score")
    semantic_scores = _load_rank_map(SCORES_ROOT / "semantic" / f"{role}_ranked.json", "normalized_score")
    hybrid_scores = _load_rank_map(SCORES_ROOT / "hybrid" / f"{role}_ranked.json", "final_score")

    keyword_ranks = _load_rank_order(SCORES_ROOT / "keyword" / f"{role}_ranked.json")
    semantic_ranks = _load_rank_order(SCORES_ROOT / "semantic" / f"{role}_ranked.json")
    hybrid_ranks = _load_rank_order(SCORES_ROOT / "hybrid" / f"{role}_ranked.json")

    candidates = set(keyword_ranks) | set(semantic_ranks) | set(hybrid_ranks)
    if not candidates:
        print(f"No ranked output files found under {SCORES_ROOT}/ for role '{role}'.")
        return

    # Sort by hybrid rank (fall back to keyword, then semantic).
    def sort_key(cid: str):
        return (
            hybrid_ranks.get(cid, 10**6),
            keyword_ranks.get(cid, 10**6),
            semantic_ranks.get(cid, 10**6),
        )

    sorted_candidates = sorted(candidates, key=sort_key)

    print(f"=== Role: {role} — comparison across {len(candidates)} candidates ===")
    print()
    print(f"{'rank_kw':>7} {'kw_score':>8}   {'rank_sem':>8} {'sem_score':>9}   "
          f"{'rank_hyb':>8} {'hyb_score':>9}   candidate_id")
    print("-" * 100)
    shown = 0
    for cid in sorted_candidates:
        if shown >= top:
            break
        rk = keyword_ranks.get(cid, "-")
        kw = keyword_scores.get(cid)
        rs = semantic_ranks.get(cid, "-")
        ss = semantic_scores.get(cid)
        rh = hybrid_ranks.get(cid, "-")
        hs = hybrid_scores.get(cid)
        kw_s = f"{kw:6.1f}" if kw is not None else "  --  "
        ss_s = f"{ss:7.1f}" if ss is not None else "   --  "
        hs_s = f"{hs:7.1f}" if hs is not None else "   --  "
        print(
            f"{str(rk):>7} {kw_s:>8}   {str(rs):>8} {ss_s:>9}   "
            f"{str(rh):>8} {hs_s:>9}   {cid}"
        )
        shown += 1

    print()
    print("Notes:")
    print("  - rank_kw / rank_sem / rank_hyb = 1-based rank within that strategy.")
    print("  - '-' means the candidate has no score for that strategy.")
    print("  - candidates not shown in the top N are omitted; rerun with --top 50 etc.")
    print()
    print("How to read this:")
    print("  - A candidate that ranks high in ALL three is robustly a good fit.")
    print("  - A candidate that ranks high in only one strategy may be gaming that strategy.")
    print("  - The hybrid blend (default alpha=0.5) is the recommended production default.")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Compare keyword / semantic / hybrid rankings.")
    parser.add_argument("--role", required=True, help="Role bucket, e.g. BusinessAnalyst")
    parser.add_argument("--top", type=int, default=10, help="Show top N candidates")
    args = parser.parse_args()

    compare(args.role, top=args.top)


if __name__ == "__main__":
    main()
