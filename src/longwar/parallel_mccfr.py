from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from typing import Any

from .game.engine import GameEngine
from .mccfr import MCCFRTrainer


def replica_seeds(seed: int, workers: int) -> list[int]:
    return [
        (seed + (index + 1) * 0x1E3779B1) % (2**31)
        for index in range(workers)
    ]


def _train_replica(
    card_data: dict[str, Any],
    deck_a: list[str],
    deck_b: list[str],
    seed: int,
    iterations: int,
    max_depth: int,
    leaf_scale: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    engine = GameEngine(card_data)
    trainer = MCCFRTrainer(
        engine,
        deck_a,
        deck_b,
        seed=seed,
        max_depth=max_depth,
        leaf_scale=leaf_scale,
    )
    summary = trainer.train(iterations)
    return trainer.policy_payload(), asdict(summary)


def _normalized_positive(values: dict[str, float]) -> dict[str, float]:
    positive = {
        key: max(0.0, float(value))
        for key, value in values.items()
    }
    total = sum(positive.values())
    if total > 0.0:
        return {key: value / total for key, value in positive.items()}
    if not positive:
        return {}
    probability = 1.0 / len(positive)
    return {key: probability for key in positive}


def merge_replica_policies(
    policies: list[dict[str, Any]],
    summaries: list[dict[str, Any]],
    *,
    seeds: list[int],
    iterations_per_worker: int | None = None,
    worker_iterations: list[int] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not policies:
        raise ValueError("At least one MCCFR replica is required")

    first = policies[0]
    merged_infosets: dict[str, dict[str, Any]] = {}

    for policy in policies:
        for info_id, entry in policy["infosets"].items():
            merged = merged_infosets.setdefault(
                info_id,
                {
                    "visits": 0,
                    "average_visits": 0,
                    "regret_sum": {},
                    "strategy_sum": {},
                },
            )
            merged["visits"] += int(entry.get("visits", 0))
            merged["average_visits"] += int(entry.get("average_visits", 0))

            for key, value in entry.get("regret_sum", {}).items():
                merged["regret_sum"][key] = (
                    merged["regret_sum"].get(key, 0.0) + float(value)
                )

            strategy_sum = entry.get("strategy_sum")
            if not isinstance(strategy_sum, dict):
                raise ValueError(
                    f"MCCFR infoset {info_id!r} is missing strategy_sum"
                )
            for key, value in strategy_sum.items():
                merged["strategy_sum"][key] = (
                    merged["strategy_sum"].get(key, 0.0) + float(value)
                )

    for entry in merged_infosets.values():
        strategy_sum = entry["strategy_sum"]
        total = sum(max(0.0, float(value)) for value in strategy_sum.values())
        if total > 0.0:
            entry["average_strategy"] = {
                key: max(0.0, float(value)) / total
                for key, value in strategy_sum.items()
            }
        else:
            entry["average_strategy"] = _normalized_positive(
                entry["regret_sum"]
            )
        entry["current_strategy"] = _normalized_positive(
            entry["regret_sum"]
        )

    workers = len(policies)
    if worker_iterations is None:
        if iterations_per_worker is None:
            raise ValueError(
                "Provide iterations_per_worker or worker_iterations"
            )
        worker_iterations = [iterations_per_worker] * workers
    if len(worker_iterations) != workers or any(
        iterations <= 0 for iterations in worker_iterations
    ):
        raise ValueError(
            "worker_iterations must contain one positive count per worker"
        )
    total_iterations = sum(worker_iterations)
    total_traversals = sum(int(summary["traversals"]) for summary in summaries)
    mean_p0 = sum(
        float(summary["mean_sampled_utility_p0"])
        * int(summary["iterations"])
        for summary in summaries
    ) / total_iterations
    mean_p1 = sum(
        float(summary["mean_sampled_utility_p1"])
        * int(summary["iterations"])
        for summary in summaries
    ) / total_iterations

    merged_policy = dict(first)
    merged_policy["algorithm"] = (
        "parallel_replicated_depth_limited_external_sampling_mccfr"
    )
    merged_policy["iterations"] = total_iterations
    merged_policy["traversals"] = total_traversals
    merged_policy["infosets"] = merged_infosets
    merged_policy["parallel_training"] = {
        "workers": workers,
        "iterations_per_worker": (
            worker_iterations[0]
            if len(set(worker_iterations)) == 1
            else None
        ),
        "worker_iterations": list(worker_iterations),
        "total_iterations": total_iterations,
        "replica_seeds": seeds,
        "aggregation": (
            "sum reach-weighted average-strategy accumulators across "
            "independent MCCFR replicas"
        ),
        "note": (
            "Replicas update regrets independently; this is a pooled ensemble "
            "of valid MCCFR runs, not a claim of bitwise equivalence to one "
            "sequential run."
        ),
    }

    merged_summary = {
        "iterations": total_iterations,
        "traversals": total_traversals,
        "information_sets": len(merged_infosets),
        "max_depth": int(first["max_depth"]),
        "mean_sampled_utility_p0": mean_p0,
        "mean_sampled_utility_p1": mean_p1,
        "workers": workers,
        "iterations_per_worker": (
            worker_iterations[0]
            if len(set(worker_iterations)) == 1
            else None
        ),
        "worker_iterations": list(worker_iterations),
    }
    return merged_policy, merged_summary


def train_parallel_mccfr(
    card_data: dict[str, Any],
    deck_a: list[str],
    deck_b: list[str],
    *,
    seed: int,
    iterations_per_worker: int | None = None,
    total_iterations: int | None = None,
    workers: int,
    max_depth: int,
    leaf_scale: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if workers < 2:
        raise ValueError("Parallel MCCFR requires at least two workers")
    if (iterations_per_worker is None) == (total_iterations is None):
        raise ValueError(
            "Provide exactly one of iterations_per_worker or total_iterations"
        )
    if total_iterations is not None:
        if total_iterations <= 0:
            raise ValueError("total_iterations must be positive")
        workers = min(workers, total_iterations)
        base = total_iterations // workers
        remainder = total_iterations % workers
        worker_iterations = [
            base + (1 if index < remainder else 0)
            for index in range(workers)
        ]
    else:
        if iterations_per_worker is None or iterations_per_worker <= 0:
            raise ValueError("iterations_per_worker must be positive")
        worker_iterations = [iterations_per_worker] * workers

    seeds = replica_seeds(seed, workers)
    args = [
        (
            card_data,
            list(deck_a),
            list(deck_b),
            worker_seed,
            worker_iterations[index],
            max_depth,
            leaf_scale,
        )
        for index, worker_seed in enumerate(seeds)
    ]

    with ProcessPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(_train_replica_star, args))

    policies = [policy for policy, _ in results]
    summaries = [summary for _, summary in results]
    return merge_replica_policies(
        policies,
        summaries,
        seeds=seeds,
        worker_iterations=worker_iterations,
    )


def _train_replica_star(
    args: tuple[
        dict[str, Any],
        list[str],
        list[str],
        int,
        int,
        int,
        float,
    ],
) -> tuple[dict[str, Any], dict[str, Any]]:
    return _train_replica(*args)
