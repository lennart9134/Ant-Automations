"""Pytest configuration — ensure the service's src package is importable."""

import sys
from pathlib import Path

# Add the service root so `from src.<module>` works in tests.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
