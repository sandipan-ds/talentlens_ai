"""Security helpers for local path validation and sensitive data handling."""

from pathlib import Path


def ensure_path_within_workspace(path: Path, workspace_root: Path) -> Path:
    """Validate that a path remains inside the configured workspace.

    Args:
        path: Candidate path to validate.
        workspace_root: Allowed workspace root.

    Returns:
        Resolved absolute path.

    Raises:
        ValueError: If the path resolves outside the workspace root.
    """
    resolved_path = path.resolve()
    resolved_root = workspace_root.resolve()

    if resolved_path == resolved_root or resolved_root in resolved_path.parents:
        return resolved_path

    raise ValueError(f"Path is outside workspace: {resolved_path}")

