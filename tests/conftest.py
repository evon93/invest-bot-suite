"""
Pytest configuration for invest-bot-suite.

Ensures repo root is in sys.path for both `python -m pytest` and `pytest` entrypoint.
AG-3I-1-2: Added autouse fixture for TimeProvider singleton isolation.
"""
import sys
from pathlib import Path

import pytest

# Add repo root to sys.path if not already present
_repo_root = Path(__file__).resolve().parents[1]
_repo_root_str = str(_repo_root)

if _repo_root_str not in sys.path:
    sys.path.insert(0, _repo_root_str)


# -----------------------------------------------------------------------------
# AG-3I-1-2: TimeProvider test isolation fixture
# -----------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_time_provider_singleton():
    """
    Reset global time provider singleton before and after each test.
    
    Prevents test contamination from tests that call set_time_provider().
    AG-3I-1-2: Added per DS audit recommendation.
    """
    from engine.time_provider import set_time_provider
    
    # Reset before test
    set_time_provider(None)
    
    yield
    
    # Reset after test (cleanup)
    set_time_provider(None)

