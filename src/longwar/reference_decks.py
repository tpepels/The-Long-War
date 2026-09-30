from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "decks" / "index.json"


def load_deck_catalog() -> tuple[dict[str, Any], ...]:
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    decks = tuple(data.get("decks", ()))
    ids = [entry.get("id") for entry in decks]
    files = [entry.get("file") for entry in decks]
    if not decks or any(
        not isinstance(value, str) or not value
        for value in ids + files
    ):
        raise ValueError(
            "decks/index.json must contain non-empty id/file entries"
        )
    if len(ids) != len(set(ids)):
        raise ValueError("decks/index.json contains duplicate deck ids")
    if len(files) != len(set(files)):
        raise ValueError("decks/index.json contains duplicate deck files")
    return decks


DECK_CATALOG = load_deck_catalog()
_DEFAULT_DECKS = tuple(
    entry for entry in DECK_CATALOG if entry.get("default")
)
if len(_DEFAULT_DECKS) != 1:
    raise ValueError("decks/index.json must mark exactly one default deck")

DEFAULT_DECK = _DEFAULT_DECKS[0]
DEFAULT_DECK_PATH = f"decks/{DEFAULT_DECK['file']}"

CANONICAL_DECK_PATHS = {
    entry["id"]: f"decks/{entry['file']}"
    for entry in DECK_CATALOG
}
MCCFR_PROFILES = tuple(
    (
        entry["id"],
        entry.get("label", entry["id"]),
        f"decks/{entry['file']}",
    )
    for entry in DECK_CATALOG
)
REFERENCE_DECK_PATHS = tuple(
    ROOT / "decks" / entry["file"]
    for entry in DECK_CATALOG
)
