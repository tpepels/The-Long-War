from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

# Balance/search artifacts depend on the exact rules, card pool, deck profiles,
# and heuristic leaf policy. UI-only changes deliberately do not invalidate them.
def fingerprint_paths() -> list[Path]:
    """Include native includes and experimental inputs, never build products."""
    paths = [
        path for path in (ROOT / "src" / "longwar").rglob("*")
        if path.suffix in {".py", ".pyx", ".pxi"}
    ]
    for directory in ("cards", "decks"):
        paths.extend((ROOT / directory).rglob("*.json"))
    return sorted(paths)


def current_game_fingerprint() -> str:
    digest = hashlib.sha256()
    for path in fingerprint_paths():
        relative = path.relative_to(ROOT).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()[:16]


def experiment_identity(config: dict[str, Any]) -> dict[str, Any]:
    """A stable identity for a fully specified run and its source inputs."""
    return {"game_fingerprint": current_game_fingerprint(), "config": config}


def artifact_directory(base: Path, identity: dict[str, Any], *, write: bool = True) -> Path:
    """Separate configurations so a smoke run cannot erase a serious run."""
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    token = hashlib.sha256(encoded.encode()).hexdigest()[:12]
    output = base / token
    if write:
        output.mkdir(parents=True, exist_ok=True)
        (output / "config.json").write_text(
            json.dumps(identity, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    return output
