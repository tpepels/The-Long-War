from __future__ import annotations

import argparse
import hashlib
import json
import time
from copy import deepcopy
from pathlib import Path

import longwar.mccfr as mccfr_module
from longwar.cards import load_card_file
from longwar.game import GameEngine
from longwar.mccfr import MCCFRTrainer, information_set_observation
from longwar.game.model import GameState
from longwar.mccfr_core import (
    BACKEND,
    _python_external_sampling_traverse,
)

ROOT = Path(__file__).resolve().parents[1]


def load_deck(path: Path) -> list[str]:
    resolved = path if path.is_absolute() else ROOT / path
    return list(json.loads(resolved.read_text(encoding="utf-8"))["cards"])


def legacy_information_set_id(state, player: int) -> str:
    payload = json.dumps(
        information_set_observation(state, player),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def legacy_clone(state: GameState) -> GameState:
    return deepcopy(state)


def run_benchmark(
    engine: GameEngine,
    deck: list[str],
    *,
    iterations: int,
    depth: int,
    seed: int,
) -> tuple[float, float, int]:
    trainer = MCCFRTrainer(
        engine,
        deck,
        deck,
        seed=seed,
        max_depth=depth,
    )
    started = time.perf_counter()
    summary = trainer.train(iterations)
    elapsed = time.perf_counter() - started
    traversals_per_second = (
        summary.traversals / elapsed if elapsed > 0 else float("inf")
    )
    return elapsed, traversals_per_second, summary.information_sets


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=25)
    parser.add_argument("--depth", type=int, default=2)
    parser.add_argument("--seed", type=int, default=1701)
    parser.add_argument("--deck", type=Path, default=Path("decks/reference.json"))
    parser.add_argument(
        "--compare-python",
        action="store_true",
        help="also run the identical search with the pure-Python traversal",
    )
    parser.add_argument(
        "--compare-legacy",
        action="store_true",
        help="also approximate the old deepcopy + JSON/SHA hot path",
    )
    args = parser.parse_args()

    engine = GameEngine(load_card_file(ROOT / "cards" / "cards.json"))
    deck = load_deck(args.deck)

    elapsed, rate, information_sets = run_benchmark(
        engine,
        deck,
        iterations=args.iterations,
        depth=args.depth,
        seed=args.seed,
    )

    print(f"Backend: {BACKEND}")
    print(f"Iterations: {args.iterations}")
    print(f"Traversals: {args.iterations * 2}")
    print(f"Depth: {args.depth}")
    print(f"Information sets: {information_sets}")
    print(f"Elapsed seconds: {elapsed:.4f}")
    print(f"Traversals/second: {rate:.2f}")

    if args.compare_python:
        original = mccfr_module.external_sampling_traverse
        try:
            mccfr_module.external_sampling_traverse = _python_external_sampling_traverse
            py_elapsed, py_rate, py_infosets = run_benchmark(
                engine,
                deck,
                iterations=args.iterations,
                depth=args.depth,
                seed=args.seed,
            )
        finally:
            mccfr_module.external_sampling_traverse = original

        print("Python fallback:")
        print(f"  Information sets: {py_infosets}")
        print(f"  Elapsed seconds: {py_elapsed:.4f}")
        print(f"  Traversals/second: {py_rate:.2f}")
        if elapsed > 0:
            print(f"Native speedup vs optimized Python: {py_elapsed / elapsed:.2f}x")

    if args.compare_legacy:
        original_traverse = mccfr_module.external_sampling_traverse
        original_key = mccfr_module.information_set_key
        original_clone = GameState.clone
        try:
            mccfr_module.external_sampling_traverse = _python_external_sampling_traverse
            mccfr_module.information_set_key = legacy_information_set_id
            GameState.clone = legacy_clone
            legacy_elapsed, legacy_rate, legacy_infosets = run_benchmark(
                engine,
                deck,
                iterations=args.iterations,
                depth=args.depth,
                seed=args.seed,
            )
        finally:
            mccfr_module.external_sampling_traverse = original_traverse
            mccfr_module.information_set_key = original_key
            GameState.clone = original_clone

        print("Legacy-like Python hot path:")
        print(f"  Information sets: {legacy_infosets}")
        print(f"  Elapsed seconds: {legacy_elapsed:.4f}")
        print(f"  Traversals/second: {legacy_rate:.2f}")
        if elapsed > 0:
            print(f"Native speedup vs legacy-like path: {legacy_elapsed / elapsed:.2f}x")


if __name__ == "__main__":
    main()
