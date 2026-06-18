"""Rank candidates using deterministic scoring."""

from typing import List, Dict, Any


def rank_candidates(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort candidates by score in descending order."""
    return sorted(candidates, key=lambda x: x.get("score", 0), reverse=True)
