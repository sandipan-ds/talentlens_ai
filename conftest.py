"""Pytest configuration — add project root to sys.path for src imports."""

import sys
from pathlib import Path

# Ensure the project root is on sys.path so that
# ``from src.xxx import yyy`` works from the tests/ directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
