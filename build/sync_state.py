"""Ledger of everything the automation has already looked at.

`resources/sync-state.json` is committed to the repository. An item recorded
here (a Google Scholar paper, a conf.researchr.org contribution, a news line)
is never imported, rewritten, or announced again, so anything fixed by hand in
the sources stays fixed. To make the automation reconsider an item, delete its
entry from the JSON file.
"""
from __future__ import annotations

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = ROOT / "resources" / "sync-state.json"


def load_state(path: Path = STATE_FILE) -> dict:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return data


def save_state(state: dict, path: Path = STATE_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
