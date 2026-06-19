"""Parsing evaluation metric helpers."""


def calculate_f1_score(precision: float, recall: float) -> float:
    """Calculate F1 score from precision and recall.

    Args:
        precision: Precision value between 0 and 1.
        recall: Recall value between 0 and 1.

    Returns:
        F1 score, or 0 when both inputs are zero.
    """
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)

