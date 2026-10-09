"""Reproducible within-run native search microbenchmark.

Use the SAME runner to benchmark the pre-adapter base and adapter revision.
Only the temporary in-memory 128-card runtime subset is used while paper
game and older main disagree on card identity capacity. No authored files
are modified. This is a timing comparison, not a claim of algorithm quality.

Example:
    PYTHONPATH="$PWD/src" python tools/benchmark_native_search.py --output /tmp/native.json
"""
from __future__ import annotations

import argparse
import gc
import json
import platform
import random
import statistics
import subprocess
import sys
from math import inf
from pathlib import Path
from time import perf_counter

from longwar.cards import load_card_file
from longwar.game.engine import GameEngine
from longwar.native_search import strategic_backend, ismcts_backend, mccfr_backend


def fixture(root: Path):
    data = load_card_file(root / "cards" / "cards.json")
    deck = json.loads((root / "decks" / "mobility-open-bonds.json").read_text())["cards"]
    subset = dict(data)
    subset["cards"] = data["cards"][:128]
    if not set(deck).issubset({item["id"] for item in subset["cards"]}):
        raise RuntimeError("Benchmark deck is not contained in 128-card fixture")
    engine = GameEngine(subset)
    state = engine.new_game(
        deck, deck, seed=20261009, first_player=0, opening_bonus=False
    )
    return engine, state


def timer(fn, repeats: int):
    # Warm up the interpreter, Cython dispatch and machine caches.
    fn()
    readings = []
    for _ in range(repeats):
        gc.collect()
        start = perf_counter()
        units = fn()
        elapsed = perf_counter() - start
        readings.append({"seconds": elapsed, "units": int(units)})
    sec = [r["seconds"] for r in readings]
    throughput = [r["units"] / r["seconds"] for r in readings]
    return {
        "median_seconds": statistics.median(sec),
        "min_seconds": min(sec),
        "median_units_per_second": statistics.median(throughput),
        "runs": readings,
    }


def run(root: Path, repeats: int, iterations: int):
    engine, state = fixture(root)
    fast_type, eval_type, budget_type, _limit, tt_type, alpha_search = (
        strategic_backend()
    )
    fast = fast_type(engine)
    evaluator = eval_type(fast, sampled_opponent_resources=False)
    packed = fast.from_game_state(state)
    _fe_type, _tree_type, _eval_type, mcts_search = ismcts_backend()
    _node_type, _cfr_type, _cfr_eval, scratch_fn, cfr_traverse, _decoder = mccfr_backend()

    def alpha():
        budget = budget_type(50000)
        value = alpha_search(
            fast, state, 0, 1, -inf, inf, budget, 4, evaluator, tt_type(1024)
        )
        if not -1e20 < value < 1e20:
            raise RuntimeError("Invalid alpha-beta return value")
        return budget.nodes

    def mcts():
        result = mcts_search(
            fast, evaluator, [packed], 0,
            iterations=iterations, rollout_depth=4,
            post_battle_rollout_depth=0, tree_depth_limit=8,
            rollout_policy=2, seed=20261009,
        )
        if result["iterations"] != iterations:
            raise RuntimeError("MCTS did not execute requested iterations")
        return result["iterations"]

    def mccfr():
        nodes = {}
        rng = random.Random(20261009)
        scratch = scratch_fn(1)
        for actor in (0, 1):
            for _ in range(iterations // 10):
                cfr_traverse(
                    fast, packed, actor, depth=0, max_depth=1,
                    nodes=nodes, rng=rng, leaf_scale=100.0,
                    scratch=scratch, evaluator=evaluator,
                )
        return 2 * (iterations // 10)

    def observations():
        for _ in range(iterations * 4):
            fast.information_key(packed, 0)
        return iterations * 4

    def legal():
        for _ in range(iterations * 4):
            fast.legal_actions(packed)
        return iterations * 4

    workloads = [
        ("alpha_beta_depth_1_nodes_per_second", alpha),
        ("ismcts_iterations_per_second", mcts),
        ("mccfr_traversals_per_second", mccfr),
        ("information_keys_per_second", observations),
        ("legal_action_calls_per_second", legal),
    ]
    measurements = {name: timer(fn, repeats) for name, fn in workloads}
    revision = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()
    return {
        "version": 1,
        "revision": revision,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "fixture": "first-128-authored-cards-in-memory",
        "deck": "mobility-open-bonds",
        "seed": 20261009,
        "iterations": iterations,
        "repeats": repeats,
        "measurements": measurements,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--iterations", type=int, default=400)
    args = parser.parse_args()
    if args.repeats < 3 or args.iterations < 20:
        parser.error("repeats >= 3 and iterations >= 20 are required")
    result = run(args.root.resolve(), args.repeats, args.iterations)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    for name, item in result["measurements"].items():
        print(f"{name}: {item['median_units_per_second']:,.0f} units/s "
              f"({item['median_seconds']:.4f}s median)")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
