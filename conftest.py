"""conftest.py — pytest root configuration.

Ensures repo root is on sys.path so all modules are importable
regardless of the working directory from which pytest is run.
"""
import sys
import pathlib

# Insert repo root at front of path
ROOT = pathlib.Path(__file__).parent.resolve()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
