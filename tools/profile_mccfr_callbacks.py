from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path

import longwar.mccfr as mccfr_module
from longwar.cards import load_card_file
from longwar.game import GameEngine
from longwar.game.model import GameState
from longwar.mccfr import MCCFRTrainer

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=40)
    parser.add_argument("--depth", type=int, default=2)
    parser.add_argument("--seed", type=int, default=1701)
    args = parser.parse_args()

    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads((ROOT / "decks" / "reference.json").read_text())["cards"]
    engine = GameEngine(data)
    trainer = MCCFRTrainer(
        engine,
        deck,
        deck,
        seed=args.seed,
        max_depth=args.depth,
    )

    totals = defaultdict(float)
    counts = defaultdict(int)

    original_legal = engine.legal_actions
    original_apply = engine.apply
    original_front_strength = engine.front_strength
    original_position_strength = engine.position_strength
    original_clone = GameState.clone
    original_copy_from = GameState.copy_from
    original_info = mccfr_module.information_set_key
    original_leaf = trainer._leaf_value

    def timed(name, fn):
        def wrapper(*a, **kw):
            started = time.perf_counter_ns()
            try:
                return fn(*a, **kw)
            finally:
                totals[name] += time.perf_counter_ns() - started
                counts[name] += 1
        return wrapper

    engine.legal_actions = timed("legal_actions", original_legal)
    engine.apply = timed("apply", original_apply)
    engine.front_strength = timed("front_strength", original_front_strength)
    engine.position_strength = timed("position_strength", original_position_strength)
    GameState.clone = timed("clone", original_clone)
    GameState.copy_from = timed("copy_from", original_copy_from)
    mccfr_module.information_set_key = timed("information_set_key", original_info)
    trainer._leaf_value = timed("leaf_value", original_leaf)

    started = time.perf_counter()
    try:
        summary = trainer.train(args.iterations)
    finally:
        engine.legal_actions = original_legal
        engine.apply = original_apply
        engine.front_strength = original_front_strength
        engine.position_strength = original_position_strength
        GameState.clone = original_clone
        GameState.copy_from = original_copy_from
        mccfr_module.information_set_key = original_info
        trainer._leaf_value = original_leaf
    elapsed = time.perf_counter() - started

    print(f"Elapsed: {elapsed:.6f}s")
    print(f"Traversals/sec: {summary.traversals / elapsed:.2f}")
    for name in sorted(totals, key=totals.get, reverse=True):
        seconds = totals[name] / 1e9
        average_us = seconds * 1e6 / counts[name]
        print(
            f"{name}: calls={counts[name]} total={seconds:.6f}s "
            f"avg={average_us:.2f}us share={seconds / elapsed:.1%}"
        )


if __name__ == "__main__":
    main()
