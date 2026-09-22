from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from longwar.cards import load_card_file
from longwar.parallel_mccfr import train_parallel_mccfr

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument("--depth", type=int, default=2)
    parser.add_argument("--seed", type=int, default=1701)
    parser.add_argument("--leaf-scale", type=float, default=100.0)
    args = parser.parse_args()

    workers = args.workers or max(1, os.cpu_count() or 1)
    if workers < 2:
        print("Parallel benchmark skipped: fewer than two CPUs/workers")
        return

    card_data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "reference.json").read_text(encoding="utf-8")
    )["cards"]

    started = time.perf_counter()
    _, summary = train_parallel_mccfr(
        card_data,
        deck,
        deck,
        seed=args.seed,
        iterations_per_worker=args.iterations,
        workers=workers,
        max_depth=args.depth,
        leaf_scale=args.leaf_scale,
    )
    elapsed = time.perf_counter() - started

    print(f"Detected CPUs: {os.cpu_count()}")
    print(f"Workers: {workers}")
    print(f"Iterations/worker: {args.iterations}")
    print(f"Total iterations: {summary['iterations']}")
    print(f"Total traversals: {summary['traversals']}")
    print(f"Elapsed seconds: {elapsed:.4f}")
    print(f"Effective traversals/second: {summary['traversals'] / elapsed:.2f}")


if __name__ == "__main__":
    main()
