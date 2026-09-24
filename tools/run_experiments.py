from __future__ import annotations

import argparse
import copy
import json
import math
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from longwar.agents.ismcts_agent import ISMCTSAgent
from longwar.agents.strategic_heuristic_agent import StrategicHeuristicAgent
from longwar.belief import DeckHypothesis, HypothesisDeckPrior
from longwar.cards import load_card_file
from longwar.game import GameEngine
from longwar.rules import GameRules

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "cardflow_experiment.py"
VALIDATION_ROOT = ROOT / "artifacts" / "search-validation"
BENCH_ROOT = ROOT / "artifacts" / "search-benchmark"


def run_command(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    printable = " ".join(command)
    print(f"$ {printable}", flush=True)
    return subprocess.run(
        command,
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
    )


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

    return payload


def parity_case(mode: str, *, seed: int) -> None:
    print(f"\nBackend parity: {mode} draw")
    python_dir = VALIDATION_ROOT / f"{mode}-python"
    cython_dir = VALIDATION_ROOT / f"{mode}-cython"

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

    run_command(
        [
            sys.executable,
            str(RUNNER),
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
        left = VALIDATION_ROOT / f"{mode}-normalized-python.json"
        right = VALIDATION_ROOT / f"{mode}-normalized-cython.json"
        left.parent.mkdir(parents=True, exist_ok=True)
        left.write_text(json.dumps(python_payload, indent=2) + "\n", encoding="utf-8")
        right.write_text(json.dumps(cython_payload, indent=2) + "\n", encoding="utf-8")
        raise SystemExit(
            f"Backend parity FAILED for {mode}.\n"
            f"Normalized outputs written to:\n  {left}\n  {right}"
        )

    print(f"Backend parity {mode}: OK")


def validate() -> None:
    print("The Long War — Force/draw experiment validation")
    print("=" * 52)
    require_cython()

    print("\nFocused rules and strategic-search tests")
    run_command(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/test_engine.py",
            "tests/test_force_draw_candidate.py",
            "tests/test_strategic_heuristic.py",
            "tests/test_fast_search_state.py",
            "tests/test_architecture_boundaries.py",
            "tests/test_ismcts.py",
        ]
    )

    parity_case("automatic", seed=26092334)
    parity_case("paid", seed=26092334)

    print("\nVALIDATION PASSED")
    print("Rules tests passed and Python/Cython produced identical fixed-seed simulations.")


def benchmark(node_budget: int) -> None:
    """Compare Python and Cython alpha-beta on one identical root decision."""
    require_cython()
    if node_budget <= 0:
        raise SystemExit("--nodes must be positive.")

    card_data = load_card_file(
        ROOT / "cards" / "experiments" / "force-draw-cards.json"
    )
    deck = json.loads(
        (
            ROOT
            / "decks"
            / "experiments"
            / "force-rich-34-reference.json"
        ).read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(
        card_data,
        rules=GameRules.force_candidate("paid"),
    )
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


def benchmark_ismcts(iterations: int) -> None:
    """Benchmark one fixed Cython ISMCTS decision."""
    require_cython()
    if iterations <= 0:
        raise SystemExit("--iterations must be positive.")

    card_data = load_card_file(
        ROOT / "cards" / "experiments" / "force-draw-cards.json"
    )
    deck = json.loads(
        (
            ROOT
            / "decks"
            / "experiments"
            / "force-rich-34-reference.json"
        ).read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(
        card_data,
        rules=GameRules.force_candidate("automatic"),
    )
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
        f"{type(action).__name__}"
    )


def _wilson_interval(wins: int, games: int) -> tuple[float, float]:
    if games <= 0:
        return (0.0, 0.0)
    z = 1.959963984540054
    p = wins / games
    denominator = 1.0 + z * z / games
    center = (p + z * z / (2.0 * games)) / denominator
    margin = (
        z
        * math.sqrt(
            p * (1.0 - p) / games
            + z * z / (4.0 * games * games)
        )
        / denominator
    )
    return (max(0.0, center - margin), min(1.0, center + margin))


def benchmark_strength(
    *,
    games_per_orientation: int,
    jobs: int,
    ismcts_iterations: int,
    alpha_nodes: int,
) -> None:
    """Mirrored ISMCTS-vs-alpha-beta matches on all Force reference decks."""
    require_cython()
    if games_per_orientation <= 0:
        raise SystemExit("--games must be positive")
    if jobs <= 0:
        raise SystemExit("--jobs must be positive")
    if ismcts_iterations <= 0 or alpha_nodes <= 0:
        raise SystemExit("Search budgets must be positive")

    decks = ("reference", "avaros", "mara", "sera")
    output_dir = BENCH_ROOT / "strength"
    output_dir.mkdir(parents=True, exist_ok=True)

    cells: list[tuple[str, str, Path, list[str]]] = []
    for deck_index, deck in enumerate(decks):
        seed = 26092400 + deck_index
        deck_path = f"decks/experiments/force-rich-34-{deck}.json"
        for orientation, agents in (
            ("mcts-first", ("ismcts", "strategic_heuristic")),
            ("alpha-first", ("strategic_heuristic", "ismcts")),
        ):
            output = output_dir / f"{deck}--{orientation}.json"
            command = [
                sys.executable,
                str(ROOT / "tools" / "simulate.py"),
                "--games",
                str(games_per_orientation),
                "--seed",
                str(seed),
                "--rules-profile",
                "force-automatic",
                "--card-file",
                "cards/experiments/force-draw-cards.json",
                "--deck-a",
                deck_path,
                "--deck-b",
                deck_path,
                "--agent-a",
                agents[0],
                "--agent-b",
                agents[1],
                "--ismcts-belief-samples",
                "12",
                "--ismcts-iterations",
                str(ismcts_iterations),
                "--ismcts-rollout-depth",
                "5",
                "--strategic-belief-samples",
                "4",
                "--strategic-search-depth",
                "6",
                "--strategic-candidate-width",
                "5",
                "--strategic-node-budget",
                str(alpha_nodes),
                "--strategic-search-backend",
                "cython",
                "--output",
                str(output),
            ]
            cells.append((deck, orientation, output, command))

    print(
        "Playing-strength benchmark: "
        f"{len(decks)} decks × 2 mirrored orientations × "
        f"{games_per_orientation} games = "
        f"{len(cells) * games_per_orientation} games"
    )
    print(
        f"ISMCTS={ismcts_iterations:,} iterations/decision; "
        f"alpha-beta={alpha_nodes:,} node budget, depth 6, beam 5"
    )
    print(f"Parallel cells: {min(jobs, len(cells))}")

    def run_cell(cell):
        deck, orientation, output, command = cell
        started = time.perf_counter()
        run_command(command, capture=True)
        return deck, orientation, output, time.perf_counter() - started

    results = []
    with ThreadPoolExecutor(max_workers=min(jobs, len(cells))) as pool:
        futures = [pool.submit(run_cell, cell) for cell in cells]
        for future in as_completed(futures):
            deck, orientation, output, elapsed = future.result()
            print(
                f"  finished {deck:9} {orientation:11} "
                f"in {elapsed:.1f}s"
            )
            results.append((deck, orientation, output, elapsed))

    totals = {
        deck: {"mcts": 0, "alpha": 0, "games": 0}
        for deck in decks
    }
    overall_mcts = 0
    overall_alpha = 0
    wall_sum = 0.0

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
        wall_sum += elapsed

    total_games = overall_mcts + overall_alpha
    low, high = _wilson_interval(overall_mcts, total_games)
    rate = overall_mcts / total_games if total_games else 0.0

    print()
    print("Head-to-head result")
    print("===================")
    for deck in decks:
        row = totals[deck]
        deck_rate = row["mcts"] / row["games"] if row["games"] else 0.0
        dlow, dhigh = _wilson_interval(row["mcts"], row["games"])
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
        "shows how much uncertainty remains at this sample size."
    )

    summary = {
        "rules_profile": "force-automatic",
        "games_per_orientation": games_per_orientation,
        "ismcts": {
            "belief_samples": 12,
            "iterations": ismcts_iterations,
            "rollout_depth": 5,
        },
        "alpha_beta": {
            "belief_samples": 4,
            "max_depth": 6,
            "beam": 5,
            "node_budget": alpha_nodes,
        },
        "decks": totals,
        "overall": {
            "mcts_wins": overall_mcts,
            "alpha_beta_wins": overall_alpha,
            "games": total_games,
            "mcts_win_rate": rate,
            "wilson_95": [low, high],
        },
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
) -> None:
    """Side-by-side wall-time benchmark on the same root position."""
    require_cython()
    if ismcts_iterations <= 0 or alpha_nodes <= 0:
        raise SystemExit("Search budgets must be positive")

    card_data = load_card_file(
        ROOT / "cards" / "experiments" / "force-draw-cards.json"
    )
    deck = json.loads(
        (
            ROOT
            / "decks"
            / "experiments"
            / "force-rich-34-reference.json"
        ).read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(
        card_data,
        rules=GameRules.force_candidate("automatic"),
    )
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
                f"{int(info['ismcts_tree_nodes']):,} infosets"
            )
        else:
            nodes = int(info["search_nodes"])
            rate = nodes / elapsed if elapsed else float("inf")
            work = (
                f"{nodes:,} nodes, {rate:,.0f} nodes/s, "
                f"completed depth {int(info['completed_depth'])}"
            )
        print(
            f"{name:10}: {elapsed:7.3f}s | {work} | "
            f"{type(action).__name__}"
        )

    ratio = rows[1][1] / rows[0][1] if rows[0][1] else float("inf")
    print(f"ISMCTS / alpha-beta wall-time ratio: {ratio:.2f}x")


def run_suite(args: argparse.Namespace) -> None:
    print("=== 1/3 Search speed comparison ===")
    benchmark_searches(
        ismcts_iterations=args.iterations,
        alpha_nodes=args.alpha_nodes,
    )

    print("\n=== 2/3 Playing-strength benchmark ===")
    benchmark_strength(
        games_per_orientation=args.games,
        jobs=args.jobs,
        ismcts_iterations=args.iterations,
        alpha_nodes=args.alpha_nodes,
    )

    print("\n=== 3/3 Card-flow experiment ===")
    command = [
        sys.executable,
        str(RUNNER),
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
    ]
    run_command(command)


def run_experiment(args: argparse.Namespace) -> None:
    command = [
        sys.executable,
        str(RUNNER),
        "--preset",
        args.preset,
        "--jobs",
        str(args.jobs),
        "--backend",
        args.backend,
        "--agent",
        args.agent,
        "--variant",
        args.variant,
        "--deck",
        args.deck,
    ]
    if args.games is not None:
        command.extend(["--games", str(args.games)])
    if args.output_dir is not None:
        command.extend(["--output-dir", str(args.output_dir)])
    run_command(command)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Local validation, search benchmarks, and gameplay experiments."
    )
    sub = parser.add_subparsers(dest="command", required=True)

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

    strength_bench = sub.add_parser(
        "strength-bench",
        help="Mirrored ISMCTS-vs-alpha-beta matches across all Force decks.",
    )
    strength_bench.add_argument(
        "--games",
        type=int,
        default=8,
        help="Games per deck/orientation; total games are 8x this value.",
    )
    strength_bench.add_argument("--jobs", type=int, default=8)
    strength_bench.add_argument("--iterations", type=int, default=10_000)
    strength_bench.add_argument("--alpha-nodes", type=int, default=20_000)

    suite = sub.add_parser(
        "suite",
        help=(
            "Run search speed comparison, mirrored playing-strength benchmark, "
            "then the five-way card-flow experiment."
        ),
    )
    suite.add_argument("--jobs", type=int, default=8)
    suite.add_argument("--games", type=int, default=8)
    suite.add_argument("--iterations", type=int, default=10_000)
    suite.add_argument("--alpha-nodes", type=int, default=20_000)
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
        default=10_000,
        help="ISMCTS iterations for the benchmark (default: 10000).",
    )

    run = sub.add_parser(
        "run",
        help="Run the local draw experiment.",
    )
    run.add_argument("--preset", choices=("quick", "deep", "max"), default="deep")
    run.add_argument("--games", type=int)
    run.add_argument("--jobs", type=int, default=8)
    run.add_argument("--backend", choices=("auto", "cython", "python"), default="cython")
    run.add_argument(
        "--agent",
        choices=("ismcts", "strategic_heuristic"),
        default="ismcts",
    )
    run.add_argument(
        "--variant",
        "--mode",
        dest="variant",
        choices=(
            "experiment",
            "all",
            "control",
            "paid-free",
            "auto-discard9",
            "auto-discard7",
            "auto-cap10",
            "automatic",
            "paid",
        ),
        default="experiment",
    )
    run.add_argument("--deck", choices=("all", "reference", "avaros", "mara", "sera"), default="all")
    run.add_argument("--output-dir", type=Path)

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "validate":
        validate()
    elif args.command == "bench":
        benchmark(args.nodes)
    elif args.command == "mcts-bench":
        benchmark_ismcts(args.iterations)
    elif args.command == "search-bench":
        benchmark_searches(
            ismcts_iterations=args.iterations,
            alpha_nodes=args.alpha_nodes,
        )
    elif args.command == "strength-bench":
        benchmark_strength(
            games_per_orientation=args.games,
            jobs=args.jobs,
            ismcts_iterations=args.iterations,
            alpha_nodes=args.alpha_nodes,
        )
    elif args.command == "suite":
        run_suite(args)
    elif args.command == "run":
        run_experiment(args)
    else:
        raise AssertionError(args.command)


if __name__ == "__main__":
    main()
