"""Pytest fixtures for orchestrator unit tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Make ``src`` importable without installing the package.
SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# All tests use the stub backend.
os.environ.setdefault("NYAYAI_LLM_BACKEND", "stub")
