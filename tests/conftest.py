"""
Pytest configuration for invest-bot-suite.

Ensures repo root is in sys.path for both `python -m pytest` and `pytest` entrypoint.
"""
import sys
from pathlib import Path

# Add repo root to sys.path if not already present
_repo_root = Path(__file__).resolve().parents[1]
_repo_root_str = str(_repo_root)

if _repo_root_str not in sys.path:
    sys.path.insert(0, _repo_root_str)
