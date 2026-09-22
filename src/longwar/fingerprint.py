from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Balance/search artifacts depend on the exact rules, card pool, deck profiles,
# and heuristic leaf policy. UI-only changes deliberately do not invalidate them.
FINGERPRINT_PATHS = (
    "cards/cards.json",
    "decks/reference.json",
    "decks/avaros-line.json",
    "decks/mara-rear.json",
    "decks/sera-support.json",
    "src/longwar/game/actions.py",
    "src/longwar/game/model.py",
    "src/longwar/game/engine.py",
    "src/longwar/agents/heuristic_agent.py",
)


def current_game_fingerprint() -> str:
    digest = hashlib.sha256()
    for relative in FINGERPRINT_PATHS:
        path = ROOT / relative
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()[:16]
