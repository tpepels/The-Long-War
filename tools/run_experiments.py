from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
import time
from dataclasses import asdict
from itertools import combinations
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from longwar.agents.ismcts_agent import DEFAULT_ISMCTS_EXPLORATION, ISMCTSAgent
from longwar.agents.strategic_heuristic_agent import StrategicHeuristicAgent
from longwar.belief import DeckHypothesis, HypothesisDeckPrior
from longwar.balance import validate_command_costs
from longwar.cards import load_card_file
from longwar.game import GameEngine
from longwar.fingerprint import artifact_directory, experiment_identity
from longwar.health import wilson_interval
from longwar.rules import GameRules

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "run_experiments.py"
VALIDATION_ROOT = ROOT / "artifacts" / "search-validation"
BENCH_ROOT = ROOT / "artifacts" / "search-benchmark"
CANONICAL_DECK_PATHS = {
    "reference": "decks/reference.json",
    "avaros": "decks/avaros-line.json",
    "mara": "decks/mara-rear.json",
    "sera": "decks/sera-support.json",
}


def validate_data() -> None:
    """Validate the canonical card/deck data under every shipped rule profile."""
    data = load_card_file(ROOT / "cards" / "cards.json")
    validate_command_costs(data)
    deck_paths = [
        ROOT / path
        for path in CANONICAL_DECK_PATHS.values()
    ]
    for profile in GameRules.profile_names():
        engine = GameEngine(data, rules=GameRules.from_profile(profile))
        for path in deck_paths:
            deck = json.loads(path.read_text(encoding="utf-8"))["cards"]
            engine.validate_deck(deck)
            engine.legal_actions(engine.new_game(deck, deck, seed=1701))
    print(
        f"Validated canonical data: {len(data['cards'])} cards, "
        f"{len(deck_paths)} decks, {len(GameRules.profile_names())} profiles"
    )


def balance_run(args: argparse.Namespace) -> Path:
    """Canonical balance pipeline; experimental rules stay in `run`."""
    from longwar.balance import build_report
    from longwar.counterfactual import run_counterfactual_card_sweep
    from longwar.health import analyze_simulation
    from longwar.playability import build_playability_report
    from longwar.simulate import simulate_games

    games = args.games if args.games is not None else (8 if args.preset == "quick" else 2000)
    if games <= 0 or args.contexts <= 0 or args.games_per_context <= 0:
        raise SystemExit("Game/context counts must be positive")
    validate_data()
    config = {"preset": args.preset, "games_per_cell": games, "seed": args.seed,
              "agents": ["heuristic", "heuristic"], "rules_profile": "standard",
              "contexts": args.contexts, "games_per_context": args.games_per_context}
    identity = experiment_identity(config)
    output = artifact_directory(ROOT / "artifacts" / "balance" / args.preset, identity)

    def save(name: str, data: dict[str, Any]) -> None:
        (output / f"{name}.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    data = load_card_file(ROOT / "cards" / "cards.json")
    engine = GameEngine(data)
    decks = {p.stem: json.loads(p.read_text(encoding="utf-8"))["cards"]
             for p in sorted((ROOT / "decks").glob("*.json"))}
    cells = [(name, name) for name in decks]
    if args.preset == "deep":
        for left, right in combinations(decks, 2):
            cells.extend([(left, right), (right, left)])
    save("static", {**build_report(data), **identity})
    simulations = []
    for index, (left, right) in enumerate(cells):
        seed = args.seed + index * games
        report = simulate_games(engine, decks[left], decks[right], games=games, seed=seed)
        payload = {**asdict(report), "game_fingerprint": identity["game_fingerprint"],
                   "seed": seed, "rules": asdict(engine.rules),
                   "deck_a": decks[left], "deck_b": decks[right],
                   "first_player_win_rate": report.first_player_win_rate,
                   "first_player_wilson_95": wilson_interval(report.first_player_wins, games)}
        name = f"{left}--{right}"
        save(name, payload)
        save(f"{name}-health", analyze_simulation(payload, data))
        simulations.append(payload)
        print(f"{name}: {games} games, first-player wins {report.first_player_wins}; "
              f"95% interval {payload['first_player_wilson_95']}")
    save("playability", build_playability_report(simulations))
    if args.preset == "deep":
        causal = run_counterfactual_card_sweep(
            data, contexts=args.contexts, games_per_context=args.games_per_context,
            seed=args.seed, bootstrap_resamples=2000,
        )
        save("counterfactual", {**causal, "game_fingerprint": identity["game_fingerprint"]})
    save("summary", {**identity, "cells": len(cells), "simulation_games": games * len(cells),
                     "interpretation": "Policy-specific diagnostics. Conditional win rates are correlations; use paired counterfactual intervals for card value."})
    print(f"Balance artifacts: {output}")
    return output


def run_command(
    command: list[str],
    *,
    capture: bool = False,
    echo: bool | None = None,
) -> subprocess.CompletedProcess[str]:
    if echo is None:
        echo = not capture
    if echo:
        print(f"$ {' '.join(command)}", flush=True)
    try:
        return subprocess.run(
            command,
            cwd=ROOT,
            check=True,
            text=True,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.STDOUT if capture else None,
        )
    except subprocess.CalledProcessError as exc:
        if capture and exc.stdout:
            print(exc.stdout, end="" if exc.stdout.endswith("\n") else "\n")
        raise


def require_cython() -> None:
    try:
        from longwar._fast_search import (  # noqa: F401
            FastEngine,
            NativeSearchBudget,
            native_search_value,
            ismcts_search,
        )
    except ImportError as exc:
        raise SystemExit(
            "Packed Cython search extension is not available.\n"
            "Run: make dev-setup"
        ) from exc
    print("Canonical Cython engine/search extension: OK")


def normalized_payload(path: Path) -> dict[str, Any]:
    """Strip backend-internal diagnostics before semantic parity checks.

    Python and packed Cython deliberately have different node accounting and
    may assign different numeric score gaps while still choosing the same
    actions. Those are performance/search diagnostics, not game outcomes.
    Search depth remains part of parity.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload = copy.deepcopy(payload)

    strategic = payload.get("strategic_config", {})
    strategic.pop("backend_requested", None)

    telemetry = payload.get("telemetry", {})
    telemetry.pop("search_backends", None)

    for stats in telemetry.get("decisions", {}).values():
        stats.pop("mean_search_nodes", None)
        stats.pop("mean_score_gap", None)
        stats.pop("mean_decision_seconds", None)
        stats.pop("max_decision_seconds", None)
        stats.pop("mean_searched_decision_seconds", None)

    return payload


def parity_case(mode: str, *, seed: int) -> None:
    print(f"\nBackend parity: {mode} draw")
    common = [
        "--preset",
        "quick",
        "--games",
        "2",
        "--jobs",
        "1",
        "--mode",
        mode,
        "--deck",
        "reference",
        "--agent",
        "strategic_heuristic",
        "--belief-samples",
        "2",
        "--depth",
        "3",
        "--width",
        "4",
        "--node-budget",
        "3000",
        "--seed",
        str(seed),
    ]
    output = artifact_directory(
        VALIDATION_ROOT,
        experiment_identity({"command": "backend-parity", "arguments": common}),
    )
    python_dir = output / f"{mode}-python"
    cython_dir = output / f"{mode}-cython"

    run_command(
        [
            sys.executable,
            str(RUNNER),
            "run",
            *common,
            "--backend",
            "python",
            "--output-dir",
            str(python_dir),
        ]
    )
    run_command(
        [
            sys.executable,
            str(RUNNER),
            "run",
            *common,
            "--backend",
            "cython",
            "--output-dir",
            str(cython_dir),
        ]
    )

    filename = f"{mode}--reference.json"
    python_payload = normalized_payload(python_dir / filename)
    cython_payload = normalized_payload(cython_dir / filename)

    if python_payload != cython_payload:
        left = output / f"{mode}-normalized-python.json"
        right = output / f"{mode}-normalized-cython.json"
        left.parent.mkdir(parents=True, exist_ok=True)
        left.write_text(json.dumps(python_payload, indent=2) + "\n", encoding="utf-8")
        right.write_text(json.dumps(cython_payload, indent=2) + "\n", encoding="utf-8")
        raise SystemExit(
            f"Backend parity FAILED for {mode}.\n"
            f"Normalized outputs written to:\n  {left}\n  {right}"
        )

    print(f"Backend parity {mode}: OK")


def validate() -> None:
    print("The Long War — native search validation")
    print("=" * 45)
    require_cython()

    print("\nFocused rules and strategic-search tests")
    run_command(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/test_engine.py",
            "tests/test_cardflow_profiles.py",
            "tests/test_strategic_heuristic.py",
            "tests/test_fast_search_state.py",
            "tests/test_architecture_boundaries.py",
            "tests/test_ismcts.py",
            "tests/test_ismcts_validation.py",
        ]
    )

    parity_case("automatic", seed=26092334)
    parity_case("paid", seed=26092334)

    print("\nVALIDATION PASSED")
    print(
        "Rules, ISMCTS invariants, architecture boundaries, and fixed-seed "
        "Python/Cython parity passed."
    )


def benchmark(node_budget: int) -> None:
    """Compare Python and Cython alpha-beta on one identical root decision."""
    require_cython()
    if node_budget <= 0:
        raise SystemExit("--nodes must be positive.")

    card_data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "reference.json").read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(card_data, rules=GameRules.standard())
    state = engine.new_game(deck, deck, seed=26092334, first_player=0)
    priors = (
        HypothesisDeckPrior(
            engine,
            [DeckHypothesis(tuple(deck), label="reference")],
        ),
        HypothesisDeckPrior(
            engine,
            [DeckHypothesis(tuple(deck), label="reference")],
        ),
    )

    results: dict[str, dict[str, Any]] = {}
    print(
        "Benchmark: one fixed strategic decision, "
        f"2 beliefs, depth 5, beam 5, {node_budget:,} node budget"
    )

    for backend in ("python", "cython"):
        agent = StrategicHeuristicAgent(
            engine,
            seed=26092335,
            priors=priors,
            belief_samples=2,
            rollout_plies=5,
            candidate_width=5,
            node_budget=node_budget,
            search_backend=backend,
        )
        benchmark_state = state.clone()
        start = time.perf_counter()
        action = agent.choose(engine, benchmark_state)
        elapsed = time.perf_counter() - start
        nodes = int(agent.last_decision["search_nodes"])
        results[backend] = {
            "elapsed": elapsed,
            "nodes": nodes,
            "nodes_per_second": nodes / elapsed if elapsed else float("inf"),
            "action": action,
            "depth": int(agent.last_decision["completed_depth"]),
        }
        detail = agent.last_decision.get("search_backend_detail", backend)
        print(
            f"{backend.capitalize():6}: {elapsed:.3f}s | "
            f"{nodes:,} nodes | "
            f"{results[backend]['nodes_per_second']:,.0f} nodes/s | "
            f"depth {results[backend]['depth']} | "
            f"{type(action).__name__} | {detail}"
        )

    python_result = results["python"]
    cython_result = results["cython"]
    if python_result["action"] != cython_result["action"]:
        raise SystemExit(
            "Benchmark parity FAILED: Python and Cython selected "
            "different root actions."
        )

    speedup = (
        python_result["elapsed"] / cython_result["elapsed"]
        if cython_result["elapsed"]
        else float("inf")
    )
    print(f"Speedup: {speedup:.2f}x")
    print("Root-action parity: OK")


def benchmark_ismcts(
    iterations: int,
    rollout_policy: str = "cheap",
    progressive_widening: float = 0.0,
    exploration: float = DEFAULT_ISMCTS_EXPLORATION,
) -> None:
    """Benchmark one fixed Cython ISMCTS decision."""
    require_cython()
    if iterations <= 0:
        raise SystemExit("--iterations must be positive.")

    card_data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "reference.json").read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(card_data, rules=GameRules.standard())
    state = engine.new_game(deck, deck, seed=26092334, first_player=0)
    priors = (
        HypothesisDeckPrior(
            engine,
            [DeckHypothesis(tuple(deck), label="reference")],
        ),
        HypothesisDeckPrior(
            engine,
            [DeckHypothesis(tuple(deck), label="reference")],
        ),
    )
    agent = ISMCTSAgent(
        engine,
        seed=26092335,
        priors=priors,
        belief_samples=12,
        iterations=iterations,
        rollout_depth=5,
        tree_depth_limit=96,
        exploration=exploration,
        progressive_widening=progressive_widening,
        rollout_policy=rollout_policy,
    )

    start = time.perf_counter()
    action = agent.choose(engine, state)
    elapsed = time.perf_counter() - start
    rate = iterations / elapsed if elapsed else float("inf")
    print(
        "Cython ISMCTS benchmark: "
        f"{iterations:,} iterations | {elapsed:.3f}s | "
        f"{rate:,.0f} iterations/s | "
        f"tree={agent.last_decision['ismcts_tree_nodes']:,} infosets | "
        f"depth={agent.last_decision['completed_depth']} | "
        f"storage={agent.last_decision.get('ismcts_tree_storage', 'unknown')} | "
        f"{type(action).__name__} | rollout={rollout_policy} | "
        f"c={exploration:g} | pw={progressive_widening:g}"
    )
    _print_ismcts_cutoffs(_ismcts_cutoff_summary(agent.last_decision))


def _ismcts_cutoff_summary(info: dict[str, Any]) -> dict[str, float | int | None]:
    terminal = int(info.get("ismcts_rollouts_stopped_terminal", 0))
    boundary = int(info.get("ismcts_rollouts_stopped_battle_boundary", 0))
    depth = int(info.get("ismcts_rollouts_stopped_depth", 0))
    rollout_actions = int(info.get("ismcts_rollout_actions", 0))
    iterations = terminal + boundary + depth
    return {
        "iterations": iterations,
        "terminal": terminal,
        "battle_boundary": boundary,
        "depth": depth,
        "terminal_rate": terminal / iterations if iterations else None,
        "battle_boundary_rate": boundary / iterations if iterations else None,
        "depth_rate": depth / iterations if iterations else None,
        "rollout_actions": rollout_actions,
        "mean_rollout_actions_per_iteration": (
            rollout_actions / iterations if iterations else None
        ),
    }


def _print_ismcts_cutoffs(cutoffs: dict[str, float | int | None]) -> None:
    iterations = int(cutoffs["iterations"] or 0)
    if not iterations:
        print("ISMCTS rollout cutoffs: no searched iterations")
        return
    print(
        "ISMCTS rollout cutoffs: "
        f"terminal={100.0 * float(cutoffs['terminal_rate']):.1f}% "
        f"Battle-boundary={100.0 * float(cutoffs['battle_boundary_rate']):.1f}% "
        f"depth={100.0 * float(cutoffs['depth_rate']):.1f}% "
        f"| rollout actions/iteration="
        f"{float(cutoffs['mean_rollout_actions_per_iteration']):.2f} "
        f"| iterations={iterations:,}"
    )


def paired_strength_interval(outcomes: dict[str, dict[str, list[dict[str, int]]]]) -> dict[str, Any]:
    """Bootstrap deals, keeping the two seat orientations together."""
    from longwar.counterfactual import estimate
    contrasts = []
    for orientations in outcomes.values():
        first = {row["seed"]: row for row in orientations["mcts-first"]}
        second = {row["seed"]: row for row in orientations["alpha-first"]}
        if first.keys() != second.keys():
            raise ValueError("Mirrored strength cells must contain identical deal seeds")
        for seed, left in first.items():
            right = second[seed]
            contrasts.append(int(left["winner"] == 0) + int(right["winner"] == 1) - 1)
    effect = estimate(contrasts, seed=1701, bootstrap_resamples=2000)
    return {"win_rate": (effect.mean + 1) / 2,
            "ci95": [max(0.0, (effect.ci95[0] + 1) / 2), min(1.0, (effect.ci95[1] + 1) / 2)],
            "independent_deals": len(contrasts), "ci_method": effect.ci_method,
            "resampling_unit": "same-seed mirrored seat pair"}


def paired_ismcts_interval(
    outcomes: dict[str, dict[str, list[dict[str, int]]]],
) -> dict[str, Any]:
    """Bootstrap matched deals for candidate A versus candidate B."""
    from longwar.counterfactual import estimate

    contrasts = []
    for orientations in outcomes.values():
        first = {row["seed"]: row for row in orientations["a-first"]}
        second = {row["seed"]: row for row in orientations["b-first"]}
        if first.keys() != second.keys():
            raise ValueError("Mirrored ISMCTS cells must contain identical deal seeds")
        for seed, left in first.items():
            right = second[seed]
            contrasts.append(
                int(left["winner"] == 0)
                + int(right["winner"] == 1)
                - 1
            )
    effect = estimate(contrasts, seed=1701, bootstrap_resamples=2000)
    return {
        "a_win_rate": (effect.mean + 1) / 2,
        "ci95": [
            max(0.0, (effect.ci95[0] + 1) / 2),
            min(1.0, (effect.ci95[1] + 1) / 2),
        ],
        "independent_deals": len(contrasts),
        "ci_method": effect.ci_method,
        "resampling_unit": "same-seed mirrored seat pair",
    }


def benchmark_ismcts_match(
    *,
    games_per_orientation: int,
    jobs: int,
    iterations: int,
    time_budget_seconds: float,
    exploration_a: float,
    exploration_b: float,
    progressive_widening_a: float,
    progressive_widening_b: float,
    reuse_tree_a: bool,
    reuse_tree_b: bool,
    rollout_depth_a: int,
    rollout_depth_b: int,
    rollout_policy_a: str,
    rollout_policy_b: str,
    seed: int = 26092400,
) -> None:
    """Direct, equal-time ISMCTS configuration comparison."""
    require_cython()
    if games_per_orientation <= 0 or jobs <= 0 or iterations <= 0:
        raise SystemExit("games, jobs, and iterations must be positive")
    if time_budget_seconds <= 0.0:
        raise SystemExit("--time-budget-seconds must be positive")
    for value in (exploration_a, exploration_b, progressive_widening_a, progressive_widening_b):
        if value < 0.0:
            raise SystemExit("ISMCTS exploration/PW values must be non-negative")
    if rollout_depth_a < 0 or rollout_depth_b < 0:
        raise SystemExit("ISMCTS rollout depths must be non-negative")
    valid_rollout_policies = {"greedy", "cheap", "random"}
    if rollout_policy_a not in valid_rollout_policies or rollout_policy_b not in valid_rollout_policies:
        raise SystemExit("ISMCTS rollout policy must be greedy, cheap, or random")

    decks = ("reference", "avaros", "mara", "sera")
    config_a = {
        "ismcts_exploration": exploration_a,
        "ismcts_progressive_widening": progressive_widening_a,
        "ismcts_reuse_tree": reuse_tree_a,
        "ismcts_rollout_depth": rollout_depth_a,
        "ismcts_rollout_policy": rollout_policy_a,
    }
    config_b = {
        "ismcts_exploration": exploration_b,
        "ismcts_progressive_widening": progressive_widening_b,
        "ismcts_reuse_tree": reuse_tree_b,
        "ismcts_rollout_depth": rollout_depth_b,
        "ismcts_rollout_policy": rollout_policy_b,
    }
    identity = experiment_identity({
        "command": "ismcts-match",
        "games_per_orientation": games_per_orientation,
        "seed": seed,
        "iterations_base": iterations,
        "time_budget_seconds": time_budget_seconds,
        "candidate_a": config_a,
        "candidate_b": config_b,
        "rules_profile": "standard",
        "decks": list(decks),
    })
    output_dir = artifact_directory(BENCH_ROOT / "ismcts-match", identity)

    cells: list[tuple[str, str, Path, list[str]]] = []
    for deck_index, deck in enumerate(decks):
        cell_seed = seed + deck_index * games_per_orientation
        deck_path = CANONICAL_DECK_PATHS[deck]
        for orientation, seat_configs, seat_labels, seat_seed_offsets in (
            (
                "a-first",
                (config_a, config_b),
                ("candidate-a", "candidate-b"),
                (1, 2),
            ),
            (
                "b-first",
                (config_b, config_a),
                ("candidate-b", "candidate-a"),
                (2, 1),
            ),
        ):
            output = output_dir / f"{deck}--{orientation}.json"
            command = [
                sys.executable,
                str(ROOT / "tools" / "simulate.py"),
                "--games", str(games_per_orientation),
                "--seed", str(cell_seed),
                "--rules-profile", "standard",
                "--card-file", "cards/cards.json",
                "--deck-a", deck_path,
                "--deck-b", deck_path,
                "--agent-a", "ismcts",
                "--agent-b", "ismcts",
                "--agent-a-label", seat_labels[0],
                "--agent-b-label", seat_labels[1],
                "--agent-a-seed-offset", str(seat_seed_offsets[0]),
                "--agent-b-seed-offset", str(seat_seed_offsets[1]),
                "--agent-a-options-json", json.dumps(seat_configs[0], separators=(",", ":")),
                "--agent-b-options-json", json.dumps(seat_configs[1], separators=(",", ":")),
                "--ismcts-belief-samples", "12",
                "--ismcts-iterations", str(iterations),
                "--ismcts-time-budget-seconds", str(time_budget_seconds),
                "--output", str(output),
            ]
            cells.append((deck, orientation, output, command))

    print(
        f"ISMCTS A/B | {len(cells) * games_per_orientation} games | "
        f"{time_budget_seconds:g}s/searched move"
    )
    print(
        f"A c={exploration_a:g} pw={progressive_widening_a:g} "
        f"{'reuse' if reuse_tree_a else 'cold'} "
        f"rollout={rollout_policy_a}/{rollout_depth_a} | "
        f"B c={exploration_b:g} pw={progressive_widening_b:g} "
        f"{'reuse' if reuse_tree_b else 'cold'} "
        f"rollout={rollout_policy_b}/{rollout_depth_b}"
    )
    print("\nProgress")
    print("deck       orientation   A-B    elapsed")

    def run_cell(cell):
        deck, orientation, output, command = cell
        started = time.perf_counter()
        run_command(command, capture=True)
        elapsed = time.perf_counter() - started
        payload = json.loads(output.read_text(encoding="utf-8"))
        labels = payload["agents"]
        a_wins = int(payload["wins"][labels.index("candidate-a")])
        b_wins = int(payload["wins"][labels.index("candidate-b")])
        return deck, orientation, output, elapsed, a_wins, b_wins

    results = []
    with ThreadPoolExecutor(max_workers=min(jobs, len(cells))) as pool:
        futures = [pool.submit(run_cell, cell) for cell in cells]
        for future in as_completed(futures):
            deck, orientation, output, elapsed, a_wins, b_wins = future.result()
            print(
                f"{deck:10} {orientation:11} "
                f"{a_wins:>2}-{b_wins:<2}  {elapsed:7.1f}s"
            )
            results.append((deck, orientation, output, elapsed))

    totals = {deck: {"a": 0, "b": 0, "games": 0} for deck in decks}
    paired_outcomes: dict[str, dict[str, list[dict[str, int]]]] = {}
    resources = {
        "candidate-a": {
            "searched_decisions": 0,
            "decision_seconds": 0.0,
            "search_work": 0.0,
            "timeouts": 0,
        },
        "candidate-b": {
            "searched_decisions": 0,
            "decision_seconds": 0.0,
            "search_work": 0.0,
            "timeouts": 0,
        },
    }
    wall_sum = 0.0

    for deck, orientation, output, elapsed in results:
        payload = json.loads(output.read_text(encoding="utf-8"))
        labels = payload["agents"]
        a_index = labels.index("candidate-a")
        b_index = labels.index("candidate-b")
        a_wins = int(payload["wins"][a_index])
        b_wins = int(payload["wins"][b_index])
        totals[deck]["a"] += a_wins
        totals[deck]["b"] += b_wins
        totals[deck]["games"] += int(payload["games"])
        paired_outcomes.setdefault(deck, {})[orientation] = payload["game_outcomes"]
        wall_sum += elapsed
        decisions = payload.get("telemetry", {}).get("decisions", {})
        for label in ("candidate-a", "candidate-b"):
            stats = decisions.get(label, {})
            all_count = int(stats.get("decisions", 0) or 0)
            searched = int(stats.get("searched_decisions", 0) or 0)
            resources[label]["searched_decisions"] += searched
            resources[label]["decision_seconds"] += searched * float(
                stats.get("mean_searched_decision_seconds", 0.0) or 0.0
            )
            resources[label]["search_work"] += all_count * float(
                stats.get("mean_search_nodes", 0.0) or 0.0
            )
            resources[label]["timeouts"] += int(
                stats.get("timed_out_decisions", 0) or 0
            )

    overall_a = sum(row["a"] for row in totals.values())
    overall_b = sum(row["b"] for row in totals.values())
    total_games = overall_a + overall_b
    paired = paired_ismcts_interval(paired_outcomes)
    low, high = paired["ci95"]

    print("\nHead-to-head result")
    print("===================")
    for deck in decks:
        row = totals[deck]
        deck_pair = paired_ismcts_interval({deck: paired_outcomes[deck]})
        dlow, dhigh = deck_pair["ci95"]
        rate = row["a"] / row["games"] if row["games"] else 0.0
        print(
            f"{deck:9}: A {row['a']:>3}-{row['b']:<3} B "
            f"| {rate * 100:5.1f}% (95% CI {dlow * 100:4.1f}–{dhigh * 100:4.1f}%)"
        )
    rate = overall_a / total_games if total_games else 0.0
    print(
        f"OVERALL  : A {overall_a}-{overall_b} B | {rate * 100:.1f}% "
        f"(95% CI {low * 100:.1f}–{high * 100:.1f}%)"
    )

    resource_summary = {}
    for label, stats in resources.items():
        count = int(stats["searched_decisions"])
        resource_summary[label] = {
            "searched_decisions": count,
            "mean_searched_decision_seconds": (
                stats["decision_seconds"] / count if count else None
            ),
            "mean_iterations": stats["search_work"] / count if count else None,
            "timeout_rate": stats["timeouts"] / count if count else None,
        }
        if count:
            print(
                f"{label}: "
                f"{resource_summary[label]['mean_searched_decision_seconds']:.3f}s/searched decision, "
                f"{resource_summary[label]['mean_iterations']:,.0f} iterations, "
                f"timeouts={100.0 * resource_summary[label]['timeout_rate']:.1f}%"
            )

    summary = {
        **identity,
        "rules_profile": "standard",
        "games_per_orientation": games_per_orientation,
        "time_budget_seconds": time_budget_seconds,
        "candidate_a": config_a,
        "candidate_b": config_b,
        "decks": totals,
        "overall": {
            "candidate_a_wins": overall_a,
            "candidate_b_wins": overall_b,
            "games": total_games,
            "candidate_a_win_rate": rate,
            "paired_uncertainty": paired,
        },
        "resources": resource_summary,
        "sum_cell_wall_seconds": wall_sum,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Summary: {output_dir / 'summary.json'}")


def benchmark_strength(
    *,
    games_per_orientation: int,
    jobs: int,
    ismcts_iterations: int,
    alpha_nodes: int,
    rollout_policy: str = "cheap",
    rollout_depth: int = 5,
    progressive_widening: float = 0.0,
    exploration: float = DEFAULT_ISMCTS_EXPLORATION,
    reuse_tree: bool = True,
    time_budget_seconds: float | None = None,
    seed: int = 26092400,
) -> None:
    """Mirrored ISMCTS-vs-alpha-beta matches on all canonical reference decks."""
    require_cython()
    if games_per_orientation <= 0:
        raise SystemExit("--games must be positive")
    if jobs <= 0:
        raise SystemExit("--jobs must be positive")
    if ismcts_iterations <= 0 or alpha_nodes <= 0:
        raise SystemExit("Search budgets must be positive")
    if rollout_depth < 0:
        raise SystemExit("--rollout-depth must be non-negative")
    if time_budget_seconds is not None and time_budget_seconds <= 0.0:
        raise SystemExit("--time-budget-seconds must be positive")

    decks = ("reference", "avaros", "mara", "sera")
    c_label = f"{exploration:g}".replace(".", "p")
    tree_label = "reuse" if reuse_tree else "cold"
    parts = ["strength", tree_label, f"c-{c_label}"]
    if progressive_widening > 0.0:
        pw_label = f"{progressive_widening:g}".replace(".", "p")
        parts.append(f"pw-{pw_label}")
    else:
        parts.append("pw-0")
    identity = experiment_identity({
        "games_per_orientation": games_per_orientation, "seed": seed,
        "ismcts_iterations": ismcts_iterations, "alpha_nodes": alpha_nodes,
        "rollout_policy": rollout_policy, "rollout_depth": rollout_depth,
        "exploration": exploration,
        "progressive_widening": progressive_widening, "reuse_tree": reuse_tree,
        "time_budget_seconds": time_budget_seconds,
        "rules_profile": "standard", "decks": list(decks),
    })
    output_dir = artifact_directory(BENCH_ROOT / "-".join(parts), identity)

    cells: list[tuple[str, str, Path, list[str]]] = []
    for deck_index, deck in enumerate(decks):
        cell_seed = seed + deck_index * games_per_orientation
        deck_path = CANONICAL_DECK_PATHS[deck]
        for orientation, agents, seed_offsets in (
            ("mcts-first", ("ismcts", "strategic_heuristic"), (1, 2)),
            ("alpha-first", ("strategic_heuristic", "ismcts"), (2, 1)),
        ):
            output = output_dir / f"{deck}--{orientation}.json"
            command = [
                sys.executable,
                str(ROOT / "tools" / "simulate.py"),
                "--games",
                str(games_per_orientation),
                "--seed",
                str(cell_seed),
                "--rules-profile",
                "standard",
                "--card-file",
                "cards/cards.json",
                "--deck-a",
                deck_path,
                "--deck-b",
                deck_path,
                "--agent-a",
                agents[0],
                "--agent-b",
                agents[1],
                "--agent-a-seed-offset",
                str(seed_offsets[0]),
                "--agent-b-seed-offset",
                str(seed_offsets[1]),
                "--ismcts-belief-samples",
                "12",
                "--ismcts-iterations",
                str(ismcts_iterations),
                "--ismcts-rollout-depth",
                str(rollout_depth),
                "--ismcts-exploration",
                str(exploration),
                "--ismcts-progressive-widening",
                str(progressive_widening),
                "--ismcts-rollout-policy",
                rollout_policy,
                "--strategic-belief-samples",
                "4",
                "--strategic-search-depth",
                "32" if time_budget_seconds is not None else "6",
                "--strategic-candidate-width",
                "5",
                "--strategic-node-budget",
                str(alpha_nodes),
                "--strategic-search-backend",
                "cython",
                "--output",
                str(output),
            ]
            if time_budget_seconds is not None:
                command.extend([
                    "--ismcts-time-budget-seconds",
                    str(time_budget_seconds),
                    "--strategic-time-budget-seconds",
                    str(time_budget_seconds),
                ])
            if not reuse_tree:
                command.append("--ismcts-no-tree-reuse")
            cells.append((deck, orientation, output, command))

    budget_label = (
        f"{time_budget_seconds:g}s/searched move"
        if time_budget_seconds is not None
        else f"{ismcts_iterations:,} iters vs {alpha_nodes:,} nodes"
    )
    print(
        f"ISMCTS vs alpha-beta | {len(cells) * games_per_orientation} games | "
        f"{budget_label}"
    )
    print(
        f"ISMCTS c={exploration:g} pw={progressive_widening:g} "
        f"{'reuse' if reuse_tree else 'cold'} "
        f"rollout={rollout_policy}/{rollout_depth}"
    )
    print("\nProgress")
    print("deck       orientation    MCTS-AB  elapsed")

    def run_cell(cell):
        deck, orientation, output, command = cell
        started = time.perf_counter()
        run_command(command, capture=True)
        elapsed = time.perf_counter() - started
        payload = json.loads(output.read_text(encoding="utf-8"))
        labels = payload["agents"]
        mcts_wins = int(payload["wins"][labels.index("ismcts")])
        alpha_wins = int(payload["wins"][labels.index("strategic_heuristic")])
        return deck, orientation, output, elapsed, mcts_wins, alpha_wins

    results = []
    with ThreadPoolExecutor(max_workers=min(jobs, len(cells))) as pool:
        futures = [pool.submit(run_cell, cell) for cell in cells]
        for future in as_completed(futures):
            deck, orientation, output, elapsed, mcts_wins, alpha_wins = future.result()
            print(
                f"{deck:10} {orientation:12} "
                f"{mcts_wins:>2}-{alpha_wins:<2}    {elapsed:7.1f}s"
            )
            results.append((deck, orientation, output, elapsed))

    totals = {
        deck: {"mcts": 0, "alpha": 0, "games": 0}
        for deck in decks
    }
    overall_mcts = 0
    overall_alpha = 0
    paired_outcomes: dict[str, dict[str, list[dict[str, int]]]] = {}
    wall_sum = 0.0
    resource_totals = {
        "ismcts": {
            "searched_decisions": 0,
            "decision_seconds": 0.0,
            "search_work": 0.0,
            "timeouts": 0,
        },
        "strategic_heuristic": {
            "searched_decisions": 0,
            "decision_seconds": 0.0,
            "search_work": 0.0,
            "timeouts": 0,
        },
    }
    cutoff_totals = {
        "iterations": 0,
        "terminal": 0,
        "battle_boundary": 0,
        "depth": 0,
        "rollout_actions": 0,
    }
    reuse_totals = {
        "searched_decisions": 0,
        "root_reused_decisions": 0,
        "tree_nodes_before_total": 0,
        "tree_nodes_added_total": 0,
        "root_prior_visits_total": 0,
        "tree_nodes_discarded_total": 0,
        "tree_capacity_cutoffs": 0,
    }
    reset_totals: dict[str, int] = {}

    for deck, orientation, output, elapsed in results:
        payload = json.loads(output.read_text(encoding="utf-8"))
        wins = payload["wins"]
        agents = payload["agents"]
        mcts_index = agents.index("ismcts")
        alpha_index = agents.index("strategic_heuristic")
        mcts_wins = int(wins[mcts_index])
        alpha_wins = int(wins[alpha_index])
        totals[deck]["mcts"] += mcts_wins
        totals[deck]["alpha"] += alpha_wins
        totals[deck]["games"] += int(payload["games"])
        overall_mcts += mcts_wins
        overall_alpha += alpha_wins
        paired_outcomes.setdefault(deck, {})[orientation] = payload["game_outcomes"]
        wall_sum += elapsed
        all_decision_stats = payload.get("telemetry", {}).get("decisions", {})
        for label in ("ismcts", "strategic_heuristic"):
            stats = all_decision_stats.get(label, {})
            all_count = int(stats.get("decisions", 0) or 0)
            searched = int(stats.get("searched_decisions", 0) or 0)
            resource_totals[label]["searched_decisions"] += searched
            resource_totals[label]["decision_seconds"] += searched * float(
                stats.get("mean_searched_decision_seconds", 0.0) or 0.0
            )
            resource_totals[label]["search_work"] += all_count * float(
                stats.get("mean_search_nodes", 0.0) or 0.0
            )
            resource_totals[label]["timeouts"] += int(
                stats.get("timed_out_decisions", 0) or 0
            )
        decision_stats = all_decision_stats.get("ismcts", {})
        cutoffs = decision_stats.get("ismcts_rollout_cutoffs", {})
        for key in cutoff_totals:
            cutoff_totals[key] += int(cutoffs.get(key, 0) or 0)
        reuse = decision_stats.get("ismcts_tree_reuse", {})
        for key in reuse_totals:
            reuse_totals[key] += int(reuse.get(key, 0) or 0)
        for reason, count in reuse.get("tree_resets", {}).items():
            reset_totals[reason] = reset_totals.get(reason, 0) + int(count)

    total_games = overall_mcts + overall_alpha
    paired = paired_strength_interval(paired_outcomes)
    low, high = paired["ci95"]
    rate = overall_mcts / total_games if total_games else 0.0

    print()
    print("Head-to-head result")
    print("===================")
    for deck in decks:
        row = totals[deck]
        deck_rate = row["mcts"] / row["games"] if row["games"] else 0.0
        dlow, dhigh = paired_strength_interval({deck: paired_outcomes[deck]})["ci95"]
        print(
            f"{deck:9}: ISMCTS {row['mcts']:>3}-{row['alpha']:<3} alpha-beta "
            f"| {deck_rate * 100:5.1f}% "
            f"(95% CI {dlow * 100:4.1f}–{dhigh * 100:4.1f}%)"
        )

    print(
        f"OVERALL  : ISMCTS {overall_mcts}-{overall_alpha} alpha-beta "
        f"| {rate * 100:.1f}% "
        f"(95% CI {low * 100:.1f}–{high * 100:.1f}%)"
    )
    print(
        "Interpretation: above 50% favors ISMCTS; the confidence interval "
        "resamples mirrored deal pairs to keep their dependence intact."
    )

    cutoff_iterations = cutoff_totals["iterations"]
    cutoff_summary = {
        **cutoff_totals,
        "terminal_rate": (
            cutoff_totals["terminal"] / cutoff_iterations
            if cutoff_iterations else None
        ),
        "battle_boundary_rate": (
            cutoff_totals["battle_boundary"] / cutoff_iterations
            if cutoff_iterations else None
        ),
        "depth_rate": (
            cutoff_totals["depth"] / cutoff_iterations
            if cutoff_iterations else None
        ),
        "mean_rollout_actions_per_iteration": (
            cutoff_totals["rollout_actions"] / cutoff_iterations
            if cutoff_iterations else None
        ),
    }
    _print_ismcts_cutoffs(cutoff_summary)

    searched_decisions = reuse_totals["searched_decisions"]
    reuse_summary = {
        **reuse_totals,
        "tree_resets": reset_totals,
        "root_reuse_rate": (
            reuse_totals["root_reused_decisions"] / searched_decisions
            if searched_decisions else None
        ),
        "mean_tree_nodes_before": (
            reuse_totals["tree_nodes_before_total"] / searched_decisions
            if searched_decisions else None
        ),
        "mean_tree_nodes_added": (
            reuse_totals["tree_nodes_added_total"] / searched_decisions
            if searched_decisions else None
        ),
        "mean_root_prior_visits": (
            reuse_totals["root_prior_visits_total"] / searched_decisions
            if searched_decisions else None
        ),
    }
    if searched_decisions:
        print(
            "ISMCTS tree reuse: "
            f"root reused={100.0 * float(reuse_summary['root_reuse_rate']):.1f}% "
            f"| prior root visits/decision="
            f"{float(reuse_summary['mean_root_prior_visits']):.1f} "
            f"| new infosets/decision="
            f"{float(reuse_summary['mean_tree_nodes_added']):.1f} "
            f"| tree infosets before/decision="
            f"{float(reuse_summary['mean_tree_nodes_before']):.1f}"
        )

    resource_summary = {}
    for label, stats in resource_totals.items():
        count = int(stats["searched_decisions"])
        resource_summary[label] = {
            "searched_decisions": count,
            "mean_searched_decision_seconds": (
                stats["decision_seconds"] / count if count else None
            ),
            "mean_search_work": stats["search_work"] / count if count else None,
            "timeout_rate": stats["timeouts"] / count if count else None,
        }
        if count:
            unit = "iterations" if label == "ismcts" else "nodes"
            print(
                f"{label}: "
                f"{resource_summary[label]['mean_searched_decision_seconds']:.3f}s/searched decision, "
                f"{resource_summary[label]['mean_search_work']:,.0f} {unit}, "
                f"timeouts={100.0 * resource_summary[label]['timeout_rate']:.1f}%"
            )

    summary = {
        **identity,
        "rules_profile": "standard",
        "games_per_orientation": games_per_orientation,
        "ismcts": {
            "belief_samples": 12,
            "iterations": ismcts_iterations,
            "rollout_depth": 5,
            "rollout_policy": rollout_policy,
            "exploration": exploration,
            "time_budget_seconds": time_budget_seconds,
            "tree_reuse_enabled": reuse_tree,
            "tree_reuse": reuse_summary,
            "progressive_widening": progressive_widening,
            "progressive_widening_alpha": (
                0.5 if progressive_widening > 0 else 0.0
            ),
            "rollout_cutoffs": cutoff_summary,
        },
        "alpha_beta": {
            "belief_samples": 4,
            "max_depth": 32 if time_budget_seconds is not None else 6,
            "beam": 5,
            "node_budget": alpha_nodes,
            "time_budget_seconds": time_budget_seconds,
        },
        "decks": totals,
        "overall": {
            "mcts_wins": overall_mcts,
            "alpha_beta_wins": overall_alpha,
            "games": total_games,
            "mcts_win_rate": rate,
            "paired_uncertainty": paired,
        },
        "resources": resource_summary,
        "sum_cell_wall_seconds": wall_sum,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Summary: {output_dir / 'summary.json'}")


def benchmark_searches(
    *,
    ismcts_iterations: int,
    alpha_nodes: int,
    rollout_policy: str = "cheap",
    progressive_widening: float = 0.0,
    exploration: float = DEFAULT_ISMCTS_EXPLORATION,
) -> None:
    """Side-by-side wall-time benchmark on the same root position."""
    require_cython()
    if ismcts_iterations <= 0 or alpha_nodes <= 0:
        raise SystemExit("Search budgets must be positive")

    card_data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "reference.json").read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(card_data, rules=GameRules.standard())
    state = engine.new_game(deck, deck, seed=26092334, first_player=0)
    priors = (
        HypothesisDeckPrior(
            engine,
            [DeckHypothesis(tuple(deck), label="reference")],
        ),
        HypothesisDeckPrior(
            engine,
            [DeckHypothesis(tuple(deck), label="reference")],
        ),
    )

    alpha = StrategicHeuristicAgent(
        engine,
        seed=26092335,
        priors=priors,
        belief_samples=4,
        rollout_plies=6,
        candidate_width=5,
        node_budget=alpha_nodes,
        search_backend="cython",
    )
    mcts = ISMCTSAgent(
        engine,
        seed=26092335,
        priors=priors,
        belief_samples=12,
        iterations=ismcts_iterations,
        rollout_depth=5,
        tree_depth_limit=96,
        exploration=exploration,
        progressive_widening=progressive_widening,
        rollout_policy=rollout_policy,
    )

    rows = []
    for name, agent in (("alpha-beta", alpha), ("ISMCTS", mcts)):
        benchmark_state = state.clone()
        started = time.perf_counter()
        action = agent.choose(engine, benchmark_state)
        elapsed = time.perf_counter() - started
        rows.append((name, elapsed, action, dict(agent.last_decision)))

    print("Search speed benchmark — same root position")
    print("===========================================")
    for name, elapsed, action, info in rows:
        if name == "ISMCTS":
            rate = ismcts_iterations / elapsed if elapsed else float("inf")
            work = (
                f"{ismcts_iterations:,} iterations, "
                f"{rate:,.0f} iterations/s, "
                f"{int(info['ismcts_tree_nodes']):,} infosets, "
                f"depth {int(info['completed_depth'])}, "
                f"selected-root-share "
                f"{int(info['ismcts_selected_action_visits']) / ismcts_iterations:.1%}, "
                f"c={exploration:g}, pw={progressive_widening:g}"
            )
        else:
            nodes = int(info["search_nodes"])
            rate = nodes / elapsed if elapsed else float("inf")
            work = (
                f"{nodes:,} nodes, {rate:,.0f} nodes/s, "
                f"completed depth {int(info['completed_depth'])}, "
                f"TT hits {int(info.get('transposition_hits', 0)):,}, "
                f"stores {int(info.get('transposition_stores', 0)):,}"
            )
        print(
            f"{name:10}: {elapsed:7.3f}s | {work} | "
            f"{type(action).__name__}"
        )

    mcts_info = rows[1][3]
    _print_ismcts_cutoffs(_ismcts_cutoff_summary(mcts_info))
    ratio = rows[1][1] / rows[0][1] if rows[0][1] else float("inf")
    print(f"ISMCTS / alpha-beta wall-time ratio: {ratio:.2f}x")


def benchmark_exploration_sweep(
    *,
    iterations: int,
    values: list[float],
    rollout_policy: str = "cheap",
    progressive_widening: float = 0.0,
) -> None:
    """Compare UCT exploration constants on one fixed ISMCTS root."""
    require_cython()
    if iterations <= 0:
        raise SystemExit("--iterations must be positive")
    if not values or any(value < 0.0 for value in values):
        raise SystemExit("Exploration values must be non-negative")

    card_data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "reference.json").read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(card_data, rules=GameRules.standard())
    state = engine.new_game(deck, deck, seed=26092334, first_player=0)
    priors = (
        HypothesisDeckPrior(
            engine,
            [DeckHypothesis(tuple(deck), label="reference")],
        ),
        HypothesisDeckPrior(
            engine,
            [DeckHypothesis(tuple(deck), label="reference")],
        ),
    )

    print("ISMCTS UCT exploration sweep - same root position")
    print("=" * 51)
    print(
        f"iterations={iterations:,}, rollout={rollout_policy}, "
        f"pw={progressive_widening:g}"
    )
    print(
        "c      sec    iter/s   infosets depth  root-share  "
        "terminal boundary depth-cut  rollout/iter action"
    )

    for exploration in values:
        agent = ISMCTSAgent(
            engine,
            seed=26092335,
            priors=priors,
            belief_samples=12,
            iterations=iterations,
            rollout_depth=5,
            tree_depth_limit=96,
            exploration=exploration,
            progressive_widening=progressive_widening,
            rollout_policy=rollout_policy,
        )
        started = time.perf_counter()
        action = agent.choose(engine, state.clone())
        elapsed = time.perf_counter() - started
        info = agent.last_decision
        cutoffs = _ismcts_cutoff_summary(info)
        rate = iterations / elapsed if elapsed else float("inf")
        root_share = int(info["ismcts_selected_action_visits"]) / iterations
        print(
            f"{exploration:<5g} "
            f"{elapsed:6.3f} "
            f"{rate:9.0f} "
            f"{int(info['ismcts_tree_nodes']):8d} "
            f"{int(info['completed_depth']):5d} "
            f"{root_share:10.1%} "
            f"{float(cutoffs['terminal_rate'] or 0.0):8.1%} "
            f"{float(cutoffs['battle_boundary_rate'] or 0.0):8.1%} "
            f"{float(cutoffs['depth_rate'] or 0.0):9.1%} "
            f"{float(cutoffs['mean_rollout_actions_per_iteration'] or 0.0):12.2f} "
            f"{type(action).__name__}"
        )


def run_suite(args: argparse.Namespace) -> None:
    print("=== 1/3 Search speed comparison ===")
    benchmark_searches(
        ismcts_iterations=args.iterations,
        alpha_nodes=args.alpha_nodes,
        rollout_policy=args.rollout_policy,
        progressive_widening=args.progressive_widening,
        exploration=args.exploration,
    )

    print("\n=== 2/3 Playing-strength benchmark ===")
    benchmark_strength(
        games_per_orientation=args.games,
        jobs=args.jobs,
        ismcts_iterations=args.iterations,
        alpha_nodes=args.alpha_nodes,
        rollout_policy=args.rollout_policy,
        progressive_widening=args.progressive_widening,
        exploration=args.exploration,
    )

    print("\n=== 3/3 Card-flow experiment ===")
    command = [
        sys.executable,
        str(RUNNER),
            "run",
        "--preset",
        args.cardflow_preset,
        "--jobs",
        str(args.jobs),
        "--backend",
        "cython",
        "--agent",
        "ismcts",
        "--variant",
        "experiment",
        "--deck",
        "all",
        "--ismcts-iterations",
        str(args.iterations),
        "--ismcts-rollout-depth",
        "5",
        "--ismcts-exploration",
        str(args.exploration),
        "--ismcts-progressive-widening",
        str(args.progressive_widening),
        "--ismcts-rollout-policy",
        args.rollout_policy,
    ]
    run_command(command)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Local validation, search benchmarks, and gameplay experiments."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("validate-data", help="Validate all shipped card sets and decks.")
    balance = sub.add_parser("balance", help="Canonical static, playability and paired balance pipeline.")
    balance.add_argument("--preset", choices=("quick", "deep"), default="quick")
    balance.add_argument("--games", type=int, help="Games per matchup cell (quick: 8; deep: 2000).")
    balance.add_argument("--seed", type=int, default=1701)
    balance.add_argument("--contexts", type=int, default=3)
    balance.add_argument("--games-per-context", type=int, default=4)

    sub.add_parser(
        "validate",
        help="Run focused tests plus exact Python/Cython simulation parity.",
    )

    bench = sub.add_parser(
        "bench",
        help="Benchmark Python and Cython on the same deep-search cell.",
    )
    bench.add_argument(
        "--nodes",
        type=int,
        default=5_000,
        help="Search-node budget for each backend (default: 5000).",
    )

    search_bench = sub.add_parser(
        "search-bench",
        help="Compare Cython ISMCTS and alpha-beta speed on one root.",
    )
    search_bench.add_argument("--iterations", type=int, default=10_000)
    search_bench.add_argument("--alpha-nodes", type=int, default=20_000)
    search_bench.add_argument("--exploration", type=float, default=DEFAULT_ISMCTS_EXPLORATION)
    search_bench.add_argument(
        "--progressive-widening",
        type=float,
        default=0.0,
        help="Square-root widening constant; 0 keeps the baseline tree policy.",
    )
    search_bench.add_argument(
        "--rollout-policy",
        choices=("greedy", "cheap", "random"),
        default="cheap",
    )

    ismcts_match = sub.add_parser(
        "ismcts-match",
        help="Direct equal-time comparison of two ISMCTS configurations.",
    )
    ismcts_match.add_argument(
        "--games",
        type=int,
        default=24,
        help=(
            "Games per deck/orientation. Default 24 gives 192 games total "
            "and 96 independent mirrored deal pairs."
        ),
    )
    ismcts_match.add_argument("--jobs", type=int, default=8)
    ismcts_match.add_argument("--iterations", type=int, default=100_000)
    ismcts_match.add_argument("--time-budget-seconds", type=float, default=2.0)
    ismcts_match.add_argument("--seed", type=int, default=26092400)
    ismcts_match.add_argument("--a-exploration", type=float, default=DEFAULT_ISMCTS_EXPLORATION)
    ismcts_match.add_argument("--b-exploration", type=float, default=DEFAULT_ISMCTS_EXPLORATION)
    ismcts_match.add_argument("--a-pw", type=float, default=0.0)
    ismcts_match.add_argument("--b-pw", type=float, default=0.0)
    ismcts_match.add_argument("--a-no-tree-reuse", action="store_true")
    ismcts_match.add_argument("--b-no-tree-reuse", action="store_true")
    ismcts_match.add_argument("--a-rollout-depth", type=int, default=5)
    ismcts_match.add_argument("--b-rollout-depth", type=int, default=5)
    ismcts_match.add_argument(
        "--a-rollout-policy",
        choices=("greedy", "cheap", "random"),
        default="cheap",
    )
    ismcts_match.add_argument(
        "--b-rollout-policy",
        choices=("greedy", "cheap", "random"),
        default="cheap",
    )

    strength_bench = sub.add_parser(
        "strength-bench",
        help="Mirrored ISMCTS-vs-alpha-beta matches across all canonical decks.",
    )
    strength_bench.add_argument(
        "--games",
        type=int,
        default=8,
        help="Games per deck/orientation; total games are 8x this value.",
    )
    strength_bench.add_argument("--jobs", type=int, default=8)
    strength_bench.add_argument("--iterations", type=int, default=100_000)
    strength_bench.add_argument("--seed", type=int, default=26092400)
    strength_bench.add_argument("--alpha-nodes", type=int, default=20_000)
    strength_bench.add_argument("--exploration", type=float, default=DEFAULT_ISMCTS_EXPLORATION)
    strength_bench.add_argument(
        "--time-budget-seconds",
        type=float,
        help="Give ISMCTS and alpha-beta the same wall-clock budget per non-forced decision.",
    )
    strength_bench.add_argument(
        "--no-tree-reuse",
        action="store_true",
        help="Use a fresh ISMCTS tree for every move.",
    )
    strength_bench.add_argument(
        "--progressive-widening",
        type=float,
        default=0.0,
        help="Square-root widening constant; 0 keeps the baseline tree policy.",
    )
    strength_bench.add_argument("--rollout-depth", type=int, default=5)
    strength_bench.add_argument(
        "--rollout-policy",
        choices=("greedy", "cheap", "random"),
        default="cheap",
    )

    suite = sub.add_parser(
        "suite",
        help=(
            "Run search speed comparison, mirrored playing-strength benchmark, "
            "then the five-way card-flow experiment."
        ),
    )
    suite.add_argument("--jobs", type=int, default=8)
    suite.add_argument("--games", type=int, default=8)
    suite.add_argument("--iterations", type=int, default=100_000)
    suite.add_argument("--alpha-nodes", type=int, default=20_000)
    suite.add_argument("--exploration", type=float, default=DEFAULT_ISMCTS_EXPLORATION)
    suite.add_argument("--progressive-widening", type=float, default=0.0)
    suite.add_argument(
        "--rollout-policy",
        choices=("greedy", "cheap", "random"),
        default="cheap",
    )
    suite.add_argument(
        "--cardflow-preset",
        choices=("quick", "deep", "max"),
        default="deep",
    )

    mcts_bench = sub.add_parser(
        "mcts-bench",
        help="Benchmark one fixed Cython ISMCTS decision.",
    )
    mcts_bench.add_argument(
        "--iterations",
        type=int,
        default=100_000,
        help="ISMCTS iterations for the benchmark (default: 100000).",
    )
    mcts_bench.add_argument("--exploration", type=float, default=DEFAULT_ISMCTS_EXPLORATION)
    mcts_bench.add_argument(
        "--progressive-widening",
        type=float,
        default=0.0,
    )
    mcts_bench.add_argument(
        "--rollout-policy",
        choices=("greedy", "cheap", "random"),
        default="cheap",
    )

    exploration_sweep = sub.add_parser(
        "exploration-sweep",
        help="Sweep UCT exploration constants on one fixed ISMCTS root.",
    )
    exploration_sweep.add_argument("--iterations", type=int, default=100_000)
    exploration_sweep.add_argument(
        "--values",
        type=float,
        nargs="+",
        default=[0.20, 0.30, 0.40, 0.50, 0.65, 0.80, 1.00],
    )
    exploration_sweep.add_argument(
        "--progressive-widening",
        type=float,
        default=0.0,
    )
    exploration_sweep.add_argument(
        "--rollout-policy",
        choices=("greedy", "cheap", "random"),
        default="cheap",
    )

    run = sub.add_parser(
        "run",
        help="Run the local draw experiment.",
    )
    from longwar.cardflow import add_arguments
    add_arguments(run)

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "validate-data":
        validate_data()
    elif args.command == "balance":
        balance_run(args)
    elif args.command == "validate":
        validate()
    elif args.command == "bench":
        benchmark(args.nodes)
    elif args.command == "mcts-bench":
        benchmark_ismcts(
            args.iterations,
            args.rollout_policy,
            args.progressive_widening,
            args.exploration,
        )
    elif args.command == "search-bench":
        benchmark_searches(
            ismcts_iterations=args.iterations,
            alpha_nodes=args.alpha_nodes,
            rollout_policy=args.rollout_policy,
            progressive_widening=args.progressive_widening,
            exploration=args.exploration,
        )
    elif args.command == "ismcts-match":
        benchmark_ismcts_match(
            games_per_orientation=args.games,
            jobs=args.jobs,
            iterations=args.iterations,
            time_budget_seconds=args.time_budget_seconds,
            exploration_a=args.a_exploration,
            exploration_b=args.b_exploration,
            progressive_widening_a=args.a_pw,
            progressive_widening_b=args.b_pw,
            reuse_tree_a=not args.a_no_tree_reuse,
            reuse_tree_b=not args.b_no_tree_reuse,
            rollout_depth_a=args.a_rollout_depth,
            rollout_depth_b=args.b_rollout_depth,
            rollout_policy_a=args.a_rollout_policy,
            rollout_policy_b=args.b_rollout_policy,
            seed=args.seed,
        )
    elif args.command == "strength-bench":
        benchmark_strength(
            games_per_orientation=args.games,
            jobs=args.jobs,
            ismcts_iterations=args.iterations,
            alpha_nodes=args.alpha_nodes,
            rollout_policy=args.rollout_policy,
            rollout_depth=args.rollout_depth,
            progressive_widening=args.progressive_widening,
            exploration=args.exploration,
            reuse_tree=not args.no_tree_reuse,
            time_budget_seconds=args.time_budget_seconds,
            seed=args.seed,
        )
    elif args.command == "exploration-sweep":
        benchmark_exploration_sweep(
            iterations=args.iterations,
            values=args.values,
            rollout_policy=args.rollout_policy,
            progressive_widening=args.progressive_widening,
        )
    elif args.command == "suite":
        run_suite(args)
    elif args.command == "run":
        from longwar.cardflow import run
        run(args)
    else:
        raise AssertionError(args.command)


if __name__ == "__main__":
    main()
