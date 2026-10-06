from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]


# A game fingerprint answers one narrow question: could this source change alter
# legal actions, state transitions, hidden information, evaluation/search
# choices, or the supplied card/deck content? Analysis and presentation code are
# deliberately excluded so a graph, telemetry summary, or report edit does not
# invalidate expensive match evidence.
_GAMEPLAY_PYTHON = {
    "belief.py",
    "cards.py",
    "decks.py",
    "heuristics.py",
    "mccfr.py",
    "mccfr_core.py",
    "native_engine.py",
    "native_search.py",
    "online_mccfr.py",
    "parallel_mccfr.py",
    "rules.py",
    "simulate.py",
}
_GAMEPLAY_DIRS = {"agents", "algorithms", "game"}
_NATIVE_GAME_SUFFIXES = {".pxi", ".pyx"}


def _unique_sorted(paths: Iterable[Path]) -> list[Path]:
    return sorted(set(paths))


def fingerprint_paths() -> list[Path]:
    """Return trajectory-affecting source/content paths.

    This fingerprints game/search semantics rather than every Python file in
    the repository.
    """
    package = ROOT / "src" / "longwar"
    paths: list[Path] = []

    for path in package.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(package)
        if len(relative.parts) == 1:
            name = relative.name
            if (
                name in _GAMEPLAY_PYTHON
                or (
                    path.suffix in _NATIVE_GAME_SUFFIXES
                    and path.name != "_native_source_fingerprint.generated.pxi"
                )
            ):
                paths.append(path)
        elif relative.parts[0] in _GAMEPLAY_DIRS and path.suffix == ".py":
            paths.append(path)

    # cards/cards.json is the sole canonical card-definition source. The
    # cards/v2 directory contains only design/playtest documentation and
    # exploratory deck lists, so those files do not define game semantics.
    canonical_cards = ROOT / "cards" / "cards.json"
    if canonical_cards.is_file():
        paths.append(canonical_cards)

    decks = ROOT / "decks"
    if decks.exists():
        paths.extend(decks.glob("*.json"))

    setup = ROOT / "setup.py"
    if setup.exists():
        paths.append(setup)

    return _unique_sorted(paths)


def experiment_fingerprint_paths() -> list[Path]:
    """Return orchestration inputs that can change what an experiment runs.

    These are kept separate from the game fingerprint: changing an experiment
    runner may create a different artifact identity, but it does not make old
    matches claim to have been played under different game semantics.
    """
    paths = list(fingerprint_paths())
    package = ROOT / "src" / "longwar"
    # These modules do not alter legal play, but they do alter the measured
    # evidence stored inside experiment checkpoints and summaries.
    for name in (
        "telemetry.py",
        "progression.py",
        "human_flow.py",
        "health.py",
        "playability.py",
        "counterfactual.py",
        "targeted_counterfactual.py",
    ):
        path = package / name
        if path.exists():
            paths.append(path)

    tools = ROOT / "tools"
    for name in (
        "run_experiments.py",
        "simulate.py",
        "train_mccfr.py",
        "verify_mccfr.py",
        "build_mccfr_suite.py",
        "counterfactual_balance.py",
        "targeted_online_counterfactual.py",
    ):
        path = tools / name
        if path.exists():
            paths.append(path)
    return _unique_sorted(paths)


def _fingerprint(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in _unique_sorted(paths):
        relative = path.relative_to(ROOT).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()[:16]


def current_game_fingerprint() -> str:
    return _fingerprint(fingerprint_paths())


def current_experiment_fingerprint() -> str:
    return _fingerprint(experiment_fingerprint_paths())


def experiment_identity(config: dict[str, Any]) -> dict[str, Any]:
    """Stable identity for one run without conflating runner and game changes."""
    return {
        "game_fingerprint": current_game_fingerprint(),
        "experiment_fingerprint": current_experiment_fingerprint(),
        "config": config,
    }


def artifact_directory(
    base: Path,
    identity: dict[str, Any],
    *,
    write: bool = True,
) -> Path:
    """Separate configurations so a smoke run cannot erase a serious run."""
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    token = hashlib.sha256(encoded.encode()).hexdigest()[:12]
    output = base / token
    if write:
        output.mkdir(parents=True, exist_ok=True)
        (output / "config.json").write_text(
            json.dumps(identity, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return output
