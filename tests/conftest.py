"""Test bootstrap: put agent/ on the path and ensure a well-formed DATABASE_URL exists.

The pure functions under test (resolution parser, fraud gate, audit hash) never open a DB
connection, but importing `debate_engine` loads `database.connection`, which builds the async
engine from DATABASE_URL at import time. A valid URL string is enough — no live DB required.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "agent"))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except Exception:
    pass

os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5434/vericlaim"
)
