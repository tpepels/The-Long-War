from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from longwar.cards import load_card_file
from longwar.game import GameEngine
from longwar.mccfr import MCCFRTrainer
from longwar.mccfr_core import BACKEND

ROOT = Path(__file__).resolve().parents[1]


def load_deck(path: Path) -> list[str]:
    resolved = path if path.is_absolute() else ROOT / path
    return list(json.loads(resolved.read_text(encoding="utf-8"))["cards"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=25)
    parser.add_argument("--depth", type=int, default=2)
    parser.add_argument("--seed", type=int, default=1701)
    parser.add_argument("--deck", type=Path, default=Path("decks/reference.json"))
    args = parser.parse_args()

    engine = GameEngine(load_card_file(ROOT / "cards" / "cards.json"))
    deck = load_deck(args.deck)
    trainer = MCCFRTrainer(
        engine,
        deck,
        deck,
        seed=args.seed,
        max_depth=args.depth,
    )

    started = time.perf_counter()
    summary = trainer.train(args.iterations)
    elapsed = time.perf_counter() - started
    traversals_per_second = (
        summary.traversals / elapsed if elapsed > 0 else float("inf")
    )

    print(f"Backend: {BACKEND}")
    print(f"Iterations: {summary.iterations}")
    print(f"Traversals: {summary.traversals}")
    print(f"Depth: {summary.max_depth}")
    print(f"Information sets: {summary.information_sets}")
    print(f"Elapsed seconds: {elapsed:.4f}")
    print(f"Traversals/second: {traversals_per_second:.2f}")


if __name__ == "__main__":
    main()
