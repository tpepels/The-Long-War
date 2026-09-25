from __future__ import annotations

import argparse
import copy
import json
import select
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from dataclasses import asdict
from itertools import combinations
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path
from typing import Any

try:
    import termios
    import tty
except ImportError:  # pragma: no cover - interactive skip is POSIX-only
    termios = None
    tty = None

from longwar.agents.ismcts_agent import DEFAULT_ISMCTS_EXPLORATION, DEFAULT_ISMCTS_ITERATIONS
from longwar.balance import validate_command_costs
from longwar.cards import load_card_file
from longwar.decks import PLAYTEST_DECK_SIZE, validate_deck_definition
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


class ExperimentSkipped(RuntimeError):
    """Raised when the user skips the currently running comparison."""


def validate_data() -> None:
    """Validate canonical cards/decks against the current standard rules."""
    data = load_card_file(ROOT / "cards" / "cards.json")
    validate_command_costs(data)
    deck_paths = [
        ROOT / path
        for path in CANONICAL_DECK_PATHS.values()
    ]
    engine = GameEngine(data, rules=GameRules.standard())
    for path in deck_paths:
        deck = json.loads(path.read_text(encoding="utf-8"))["cards"]
        validate_deck_definition(
            deck,
            engine.cards,
            exact_size=PLAYTEST_DECK_SIZE,
        )
        engine.validate_deck(deck)
        engine.legal_actions(engine.new_game(deck, deck, seed=1701))
    print(
        f"Validated canonical data: {len(data['cards'])} cards, "
        f"{len(deck_paths)} {PLAYTEST_DECK_SIZE}-card playtest decks, "
        "standard rules"
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
              "agents": ["heuristic", "heuristic"], "rules": GameRules.standard().as_dict(),
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


def _read_progress_state(path: Path, maximum: int) -> dict[str, Any]:
    fallback = {
        "completed": 0,
        "total": maximum,
        "wins": [0, 0],
    }
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError:
        return fallback

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        # Backward compatibility with the old integer-only progress files.
        try:
            completed = int(raw)
        except ValueError:
            return fallback
        return {
            **fallback,
            "completed": max(0, min(maximum, completed)),
        }

    if not isinstance(payload, dict):
        return fallback
    completed = payload.get("completed", 0)
    wins = payload.get("wins", [0, 0])
    if not isinstance(completed, int):
        completed = 0
    if (
        not isinstance(wins, list)
        or len(wins) != 2
        or not all(isinstance(value, int) and value >= 0 for value in wins)
    ):
        wins = [0, 0]
    return {
        "completed": max(0, min(maximum, completed)),
        "total": maximum,
        "wins": wins,
    }


def _read_progress_count(path: Path, maximum: int) -> int:
    return int(_read_progress_state(path, maximum)["completed"])


def _format_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


@contextmanager
def _skip_key_reader():
    """Yield a non-blocking single-key skip reader for interactive POSIX terminals."""
    if (
        termios is None
        or tty is None
        or not sys.stdin.isatty()
        or not sys.stdout.isatty()
    ):
        yield lambda: False
        return

    fd = sys.stdin.fileno()
    previous = termios.tcgetattr(fd)
    tty.setcbreak(fd)

    def requested() -> bool:
        ready, _, _ = select.select([sys.stdin], [], [], 0)
        if not ready:
            return False
        return sys.stdin.read(1).lower() == "s"

    try:
        yield requested
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, previous)


def _run_command_until_stop(
    command: list[str],
    stop_event: threading.Event,
) -> bool:
    """Run one simulation subprocess, terminating it promptly when skipped."""
    if stop_event.is_set():
        return False

    with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as log:
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            text=True,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        while process.poll() is None:
            if stop_event.wait(0.1):
                process.terminate()
                try:
                    process.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                return False

        if process.returncode:
            log.seek(0)
            output = log.read()
            if output:
                print(output, end="" if output.endswith("\n") else "\n")
            raise subprocess.CalledProcessError(process.returncode, command)
    return True


def _run_cells_with_live_progress(
    cells: list[tuple[str, str, Path, Path, list[str]]],
    *,
    jobs: int,
    games_per_cell: int,
    run_cell,
    format_result,
    table_header: str,
    score_labels: tuple[str, str],
    format_progress,
) -> list[Any]:
    """Run parallel cells with a live result table and interactive skip."""
    total_games = len(cells) * games_per_cell
    progress_paths = [cell[3] for cell in cells]
    started = time.perf_counter()
    results: list[Any] = []
    stop_event = threading.Event()
    skipped = False
    previous_lines = 0
    interactive = sys.stdout.isatty()

    def clear_display() -> None:
        nonlocal previous_lines
        if not interactive or previous_lines <= 0:
            return
        sys.stdout.write("\r\x1b[2K")
        for _ in range(previous_lines - 1):
            sys.stdout.write("\x1b[1A\r\x1b[2K")
        previous_lines = 0

    def render(pending_count: int, *, stopping: bool = False) -> None:
        nonlocal previous_lines
        states = [
            _read_progress_state(path, games_per_cell)
            for path in progress_paths
        ]
        completed = sum(int(state["completed"]) for state in states)
        fraction = completed / total_games if total_games else 1.0
        width = 20
        filled = min(width, int(width * fraction))
        bar = "#" * filled + "-" * (width - filled)
        elapsed = time.perf_counter() - started
        eta = (
            elapsed * (total_games - completed) / completed
            if completed and not stopping
            else None
        )
        eta_text = _format_duration(eta) if eta is not None else "--:--"

        rows: list[str] = []
        score_a = 0
        score_b = 0
        for cell, state in zip(cells, states):
            row, a_wins, b_wins = format_progress(cell, state)
            rows.append(row)
            score_a += a_wins
            score_b += b_wins

        status = (
            "Stopping current experiment..."
            if stopping
            else "Press s to skip this experiment"
        )
        lines = [
            f"Live results - {status}",
            table_header,
            *rows,
            (
                f"TOTAL {score_labels[0]} {score_a} - "
                f"{score_labels[1]} {score_b}"
            ),
            (
                f"[{bar}] {completed}/{total_games} {fraction:5.1%} "
                f"| {_format_duration(elapsed)} | ETA {eta_text} "
                f"| {pending_count} active"
            ),
        ]

        if interactive:
            clear_display()
            sys.stdout.write("\n".join(lines))
            sys.stdout.flush()
            previous_lines = len(lines)
        elif completed == total_games or stopping:
            print("\n".join(lines), flush=True)

    with _skip_key_reader() as skip_requested:
        with ThreadPoolExecutor(max_workers=min(jobs, len(cells))) as pool:
            future_to_cell = {
                pool.submit(run_cell, cell, stop_event): cell
                for cell in cells
            }
            pending = set(future_to_cell)
            render(len(pending))
            while pending:
                if not skipped and skip_requested():
                    skipped = True
                    stop_event.set()
                    render(len(pending), stopping=True)

                done, pending = wait(
                    pending,
                    timeout=0.5,
                    return_when=FIRST_COMPLETED,
                )
                for future in done:
                    result = future.result()
                    if result is not None:
                        results.append(result)
                        if not interactive:
                            print(format_result(result), flush=True)

                if not skipped:
                    render(len(pending))
                elif pending:
                    render(len(pending), stopping=True)

    if interactive:
        if not skipped:
            render(0)
        clear_display()
        if not skipped:
            # Preserve the final completed table in scrollback.
            states = [
                _read_progress_state(path, games_per_cell)
                for path in progress_paths
            ]
            print("Final cell results")
            print(table_header)
            for cell, state in zip(cells, states):
                row, _a_wins, _b_wins = format_progress(cell, state)
                print(row)
        else:
            print("Current experiment skipped.")

    if skipped:
        raise ExperimentSkipped("user requested skip")
    return results


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
            "Run: make install && make native-build"
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


def standard_backend_parity(*, seed: int) -> None:
    """Compare Python/Cython strategic search under current standard rules."""
    print("\nBackend parity: standard rules")
    common = [
        "--games",
        "2",
        "--seed",
        str(seed),
        "--card-file",
        "cards/cards.json",
        "--deck-a",
        "decks/reference.json",
        "--deck-b",
        "decks/reference.json",
        "--agent-a",
        "strategic_heuristic",
        "--agent-b",
        "strategic_heuristic",
        "--strategic-belief-samples",
        "2",
        "--strategic-search-depth",
        "3",
        "--strategic-candidate-width",
        "4",
        "--strategic-node-budget",
        "3000",
    ]
    output = artifact_directory(
        VALIDATION_ROOT,
        experiment_identity({
            "command": "standard-backend-parity",
            "arguments": common,
        }),
    )
    python_output = output / "standard-python.json"
    cython_output = output / "standard-cython.json"

    for backend, destination in (
        ("python", python_output),
        ("cython", cython_output),
    ):
        run_command(
            [
                sys.executable,
                str(ROOT / "tools" / "simulate.py"),
                *common,
                "--strategic-search-backend",
                backend,
                "--output",
                str(destination),
            ],
            capture=True,
        )

    python_payload = normalized_payload(python_output)
    cython_payload = normalized_payload(cython_output)
    if python_payload != cython_payload:
        left = output / "standard-normalized-python.json"
        right = output / "standard-normalized-cython.json"
        left.write_text(
            json.dumps(python_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        right.write_text(
            json.dumps(cython_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        raise SystemExit(
            "Backend parity FAILED for standard rules.\n"
            f"Normalized outputs written to:\n  {left}\n  {right}"
        )

    print("Backend parity standard: OK")


def validate() -> None:
    print("The Long War — native search validation")
    print("=" * 45)
    require_cython()

    print("\nFocused current-rules and strategic-search tests")
    run_command(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-m",
            "not legacy_rule_experiment",
            "tests/test_engine.py",
            "tests/test_strategic_heuristic.py",
            "tests/test_fast_search_state.py",
            "tests/test_architecture_boundaries.py",
            "tests/test_ismcts.py",
            "tests/test_ismcts_validation.py",
        ],
        capture=True,
    )
    print("Focused current-rules/search tests: OK")

    standard_backend_parity(seed=26092334)

    print("\nVALIDATION PASSED")
    print(
        "Current rules, ISMCTS invariants, architecture boundaries, and "
        "fixed-seed standard-rules Python/Cython parity passed."
    )


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
    belief_samples_a: int,
    belief_samples_b: int,
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
    rollout_epsilon_a: float,
    rollout_epsilon_b: float,
    max_tree_nodes_a: int | None,
    max_tree_nodes_b: int | None,
    seed: int = 26092400,
) -> Path:
    """Direct, equal-time ISMCTS configuration comparison."""
    require_cython()
    if games_per_orientation <= 0 or jobs <= 0 or iterations <= 0:
        raise SystemExit("games, jobs, and iterations must be positive")
    if belief_samples_a <= 0 or belief_samples_b <= 0:
        raise SystemExit("ISMCTS belief samples must be positive")
    if time_budget_seconds <= 0.0:
        raise SystemExit("--time-budget-seconds must be positive")
    for value in (exploration_a, exploration_b, progressive_widening_a, progressive_widening_b):
        if value < 0.0:
            raise SystemExit("ISMCTS exploration/PW values must be non-negative")
    if rollout_depth_a < 0 or rollout_depth_b < 0:
        raise SystemExit("ISMCTS rollout depths must be non-negative")
    if not 0.0 <= rollout_epsilon_a <= 1.0 or not 0.0 <= rollout_epsilon_b <= 1.0:
        raise SystemExit("ISMCTS rollout epsilon must be between 0 and 1")
    for value in (max_tree_nodes_a, max_tree_nodes_b):
        if value is not None and value <= 0:
            raise SystemExit("ISMCTS max tree nodes must be positive")
    valid_rollout_policies = {"greedy", "cheap", "random"}
    if rollout_policy_a not in valid_rollout_policies or rollout_policy_b not in valid_rollout_policies:
        raise SystemExit("ISMCTS rollout policy must be greedy, cheap, or random")

    decks = ("reference", "avaros", "mara", "sera")
    config_a = {
        "ismcts_belief_samples": belief_samples_a,
        "ismcts_exploration": exploration_a,
        "ismcts_progressive_widening": progressive_widening_a,
        "ismcts_reuse_tree": reuse_tree_a,
        "ismcts_rollout_depth": rollout_depth_a,
        "ismcts_rollout_policy": rollout_policy_a,
        "ismcts_rollout_epsilon": rollout_epsilon_a,
        "ismcts_max_tree_nodes": max_tree_nodes_a,
    }
    config_b = {
        "ismcts_belief_samples": belief_samples_b,
        "ismcts_exploration": exploration_b,
        "ismcts_progressive_widening": progressive_widening_b,
        "ismcts_reuse_tree": reuse_tree_b,
        "ismcts_rollout_depth": rollout_depth_b,
        "ismcts_rollout_policy": rollout_policy_b,
        "ismcts_rollout_epsilon": rollout_epsilon_b,
        "ismcts_max_tree_nodes": max_tree_nodes_b,
    }
    identity = experiment_identity({
        "command": "ismcts-match",
        "games_per_orientation": games_per_orientation,
        "seed": seed,
        "iterations_base": iterations,
        "time_budget_seconds": time_budget_seconds,
        "candidate_a": config_a,
        "candidate_b": config_b,
        "rules": GameRules.standard().as_dict(),
        "decks": list(decks),
    })
    output_dir = artifact_directory(BENCH_ROOT / "ismcts-match", identity)

    cells: list[tuple[str, str, Path, Path, list[str]]] = []
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
            progress = output.with_suffix(".progress")
            progress.unlink(missing_ok=True)
            command = [
                sys.executable,
                str(ROOT / "tools" / "simulate.py"),
                "--games", str(games_per_orientation),
                "--seed", str(cell_seed),
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
                "--ismcts-iterations", str(iterations),
                "--ismcts-time-budget-seconds", str(time_budget_seconds),
                "--progress-file", str(progress),
                "--output", str(output),
            ]
            cells.append((deck, orientation, output, progress, command))

    print(
        f"ISMCTS A/B | {len(cells) * games_per_orientation} games | "
        f"{time_budget_seconds:g}s/searched move"
    )
    print(
        f"A belief={belief_samples_a} c={exploration_a:g} "
        f"pw={progressive_widening_a:g} "
        f"{'reuse' if reuse_tree_a else 'cold'} "
        f"rollout={rollout_policy_a}/{rollout_depth_a} "
        f"eps={rollout_epsilon_a:g} tree={max_tree_nodes_a or 'auto'} | "
        f"B belief={belief_samples_b} c={exploration_b:g} "
        f"pw={progressive_widening_b:g} "
        f"{'reuse' if reuse_tree_b else 'cold'} "
        f"rollout={rollout_policy_b}/{rollout_depth_b} "
        f"eps={rollout_epsilon_b:g} tree={max_tree_nodes_b or 'auto'}"
    )
    def run_cell(cell, stop_event):
        deck, orientation, output, progress, command = cell
        started = time.perf_counter()
        if not _run_command_until_stop(command, stop_event):
            return None
        elapsed = time.perf_counter() - started
        payload = json.loads(output.read_text(encoding="utf-8"))
        labels = payload["agents"]
        a_wins = int(payload["wins"][labels.index("candidate-a")])
        b_wins = int(payload["wins"][labels.index("candidate-b")])
        return deck, orientation, output, elapsed, a_wins, b_wins

    def format_result(result) -> str:
        deck, orientation, _output, elapsed, a_wins, b_wins = result
        return (
            f"{deck:10} {orientation:11} "
            f"{a_wins:>2}-{b_wins:<2}  {elapsed:7.1f}s"
        )

    def format_progress(cell, state):
        deck, orientation, _output, _progress, _command = cell
        seat_a, seat_b = (0, 1) if orientation == "a-first" else (1, 0)
        a_wins = int(state["wins"][seat_a])
        b_wins = int(state["wins"][seat_b])
        completed = int(state["completed"])
        rate = 100.0 * a_wins / completed if completed else 0.0
        return (
            f"{deck:10} {orientation:11} "
            f"{completed:>2}/{games_per_orientation:<2} "
            f"{a_wins:>3}-{b_wins:<3} {rate:5.1f}% A",
            a_wins,
            b_wins,
        )

    completed_results = _run_cells_with_live_progress(
        cells,
        jobs=jobs,
        games_per_cell=games_per_orientation,
        run_cell=run_cell,
        format_result=format_result,
        table_header="deck       orientation played   A-B      A%",
        score_labels=("A", "B"),
        format_progress=format_progress,
    )
    results = [
        (deck, orientation, output, elapsed)
        for deck, orientation, output, elapsed, _a_wins, _b_wins
        in completed_results
    ]

    totals = {deck: {"a": 0, "b": 0, "games": 0} for deck in decks}
    paired_outcomes: dict[str, dict[str, list[dict[str, int]]]] = {}
    resources = {
        "candidate-a": {
            "searched_decisions": 0,
            "decision_seconds": 0.0,
            "search_work": 0.0,
            "timeouts": 0,
            "tree_capacity_cutoffs": 0,
            "capacity_reroots": 0,
            "root_reused_decisions": 0,
        },
        "candidate-b": {
            "searched_decisions": 0,
            "decision_seconds": 0.0,
            "search_work": 0.0,
            "timeouts": 0,
            "tree_capacity_cutoffs": 0,
            "capacity_reroots": 0,
            "root_reused_decisions": 0,
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
            reuse = stats.get("ismcts_tree_reuse", {})
            resources[label]["tree_capacity_cutoffs"] += int(
                reuse.get("tree_capacity_cutoffs", 0) or 0
            )
            resources[label]["capacity_reroots"] += int(
                reuse.get("tree_resets", {}).get("capacity_reroot", 0) or 0
            )
            resources[label]["root_reused_decisions"] += int(
                reuse.get("root_reused_decisions", 0) or 0
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
            "tree_capacity_cutoffs": int(stats["tree_capacity_cutoffs"]),
            "capacity_reroots": int(stats["capacity_reroots"]),
            "root_reuse_rate": (
                stats["root_reused_decisions"] / count if count else None
            ),
        }
        if count:
            print(
                f"{label}: "
                f"{resource_summary[label]['mean_searched_decision_seconds']:.3f}s/searched decision, "
                f"{resource_summary[label]['mean_iterations']:,.0f} iterations, "
                f"timeouts={100.0 * resource_summary[label]['timeout_rate']:.1f}%, "
                f"reuse={100.0 * resource_summary[label]['root_reuse_rate']:.1f}%, "
                f"capacity-cutoffs={resource_summary[label]['tree_capacity_cutoffs']}, "
                f"capacity-reroots={resource_summary[label]['capacity_reroots']}"
            )

    summary = {
        **identity,
        "rules": GameRules.standard().as_dict(),
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
    summary_path = output_dir / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Summary: {summary_path}")
    return summary_path


def benchmark_strength(
    *,
    games_per_orientation: int,
    jobs: int,
    ismcts_iterations: int,
    alpha_nodes: int,
    belief_samples: int = 12,
    rollout_policy: str = "cheap",
    rollout_depth: int = 5,
    progressive_widening: float = 0.0,
    exploration: float = DEFAULT_ISMCTS_EXPLORATION,
    reuse_tree: bool = True,
    rollout_epsilon: float = 0.12,
    max_tree_nodes: int | None = None,
    time_budget_seconds: float | None = None,
    seed: int = 26092400,
) -> Path:
    """Mirrored ISMCTS-vs-alpha-beta matches on all canonical reference decks."""
    require_cython()
    if games_per_orientation <= 0:
        raise SystemExit("--games must be positive")
    if jobs <= 0:
        raise SystemExit("--jobs must be positive")
    if ismcts_iterations <= 0 or alpha_nodes <= 0:
        raise SystemExit("Search budgets must be positive")
    if belief_samples <= 0:
        raise SystemExit("ISMCTS belief samples must be positive")
    if not 0.0 <= rollout_epsilon <= 1.0:
        raise SystemExit("ISMCTS rollout epsilon must be between 0 and 1")
    if max_tree_nodes is not None and max_tree_nodes <= 0:
        raise SystemExit("ISMCTS max tree nodes must be positive")
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
        "belief_samples": belief_samples,
        "rollout_policy": rollout_policy, "rollout_depth": rollout_depth,
        "rollout_epsilon": rollout_epsilon,
        "max_tree_nodes": max_tree_nodes,
        "exploration": exploration,
        "progressive_widening": progressive_widening, "reuse_tree": reuse_tree,
        "time_budget_seconds": time_budget_seconds,
        "rules": GameRules.standard().as_dict(), "decks": list(decks),
    })
    output_dir = artifact_directory(BENCH_ROOT / "-".join(parts), identity)

    cells: list[tuple[str, str, Path, Path, list[str]]] = []
    for deck_index, deck in enumerate(decks):
        cell_seed = seed + deck_index * games_per_orientation
        deck_path = CANONICAL_DECK_PATHS[deck]
        for orientation, agents, seed_offsets in (
            ("mcts-first", ("ismcts", "strategic_heuristic"), (1, 2)),
            ("alpha-first", ("strategic_heuristic", "ismcts"), (2, 1)),
        ):
            output = output_dir / f"{deck}--{orientation}.json"
            progress = output.with_suffix(".progress")
            progress.unlink(missing_ok=True)
            command = [
                sys.executable,
                str(ROOT / "tools" / "simulate.py"),
                "--games",
                str(games_per_orientation),
                "--seed",
                str(cell_seed),
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
                str(belief_samples),
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
                "--ismcts-rollout-epsilon",
                str(rollout_epsilon),
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
            if max_tree_nodes is not None:
                command.extend([
                    "--ismcts-max-tree-nodes",
                    str(max_tree_nodes),
                ])
            if time_budget_seconds is not None:
                command.extend([
                    "--ismcts-time-budget-seconds",
                    str(time_budget_seconds),
                    "--strategic-time-budget-seconds",
                    str(time_budget_seconds),
                ])
            command.extend(["--progress-file", str(progress)])
            if not reuse_tree:
                command.append("--ismcts-no-tree-reuse")
            cells.append((deck, orientation, output, progress, command))

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
    def run_cell(cell, stop_event):
        deck, orientation, output, progress, command = cell
        started = time.perf_counter()
        if not _run_command_until_stop(command, stop_event):
            return None
        elapsed = time.perf_counter() - started
        payload = json.loads(output.read_text(encoding="utf-8"))
        labels = payload["agents"]
        mcts_wins = int(payload["wins"][labels.index("ismcts")])
        alpha_wins = int(payload["wins"][labels.index("strategic_heuristic")])
        return deck, orientation, output, elapsed, mcts_wins, alpha_wins

    def format_result(result) -> str:
        deck, orientation, _output, elapsed, mcts_wins, alpha_wins = result
        return (
            f"{deck:10} {orientation:12} "
            f"{mcts_wins:>2}-{alpha_wins:<2}    {elapsed:7.1f}s"
        )

    def format_progress(cell, state):
        deck, orientation, _output, _progress, _command = cell
        seat_mcts, seat_alpha = (
            (0, 1) if orientation == "mcts-first" else (1, 0)
        )
        mcts_wins = int(state["wins"][seat_mcts])
        alpha_wins = int(state["wins"][seat_alpha])
        completed = int(state["completed"])
        rate = 100.0 * mcts_wins / completed if completed else 0.0
        return (
            f"{deck:10} {orientation:12} "
            f"{completed:>2}/{games_per_orientation:<2} "
            f"{mcts_wins:>3}-{alpha_wins:<3} {rate:5.1f}% MCTS",
            mcts_wins,
            alpha_wins,
        )

    completed_results = _run_cells_with_live_progress(
        cells,
        jobs=jobs,
        games_per_cell=games_per_orientation,
        run_cell=run_cell,
        format_result=format_result,
        table_header="deck       orientation  played   MCTS-AB  MCTS%",
        score_labels=("MCTS", "AB"),
        format_progress=format_progress,
    )
    results = [
        (deck, orientation, output, elapsed)
        for deck, orientation, output, elapsed, _mcts_wins, _alpha_wins
        in completed_results
    ]

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
        "rules": GameRules.standard().as_dict(),
        "games_per_orientation": games_per_orientation,
        "ismcts": {
            "belief_samples": belief_samples,
            "iterations": ismcts_iterations,
            "rollout_depth": rollout_depth,
            "rollout_policy": rollout_policy,
            "exploration": exploration,
            "time_budget_seconds": time_budget_seconds,
            "tree_reuse_enabled": reuse_tree,
            "max_tree_nodes": max_tree_nodes,
            "rollout_epsilon": rollout_epsilon,
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
    summary_path = output_dir / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Summary: {summary_path}")
    return summary_path


def run_suite(args: argparse.Namespace) -> Path:
    """Run the canonical non-adaptive search experiment suite."""
    if args.games < 24:
        raise SystemExit("--games must be at least 24 for the experiment suite")
    if args.jobs <= 0:
        raise SystemExit("--jobs must be positive")
    if args.time_budget_seconds <= 0.0:
        raise SystemExit("--time-budget-seconds must be positive")

    baseline = {
        "belief_samples": 12,
        "exploration": DEFAULT_ISMCTS_EXPLORATION,
        "progressive_widening": 0.0,
        "reuse_tree": True,
        "rollout_depth": 5,
        "rollout_policy": "cheap",
        "rollout_epsilon": 0.12,
        "max_tree_nodes": 400_000,
    }
    comparisons = [
        ("baseline-control", {}),
        ("tree-cold", {"reuse_tree_b": False}),
        ("pw-0p5", {"progressive_widening_b": 0.5}),
        ("rollout-greedy", {"rollout_policy_b": "greedy"}),
        ("rollout-depth-8", {"rollout_depth_b": 8}),
        ("rollout-epsilon-0", {"rollout_epsilon_b": 0.0}),
    ]
    identity = experiment_identity({
        "command": "suite",
        "games_per_orientation": args.games,
        "jobs": args.jobs,
        "time_budget_seconds": args.time_budget_seconds,
        "iterations_base": args.iterations,
        "alpha_nodes": args.alpha_nodes,
        "seed": args.seed,
        "baseline": baseline,
        "comparisons": comparisons,
    })
    output_dir = artifact_directory(BENCH_ROOT / "suite", identity)
    manifest_path = output_dir / "summary.json"
    manifest: dict[str, Any] = {
        **identity,
        "games_per_orientation": args.games,
        "jobs": args.jobs,
        "time_budget_seconds": args.time_budget_seconds,
        "iterations_base": args.iterations,
        "alpha_nodes": args.alpha_nodes,
        "seed": args.seed,
        "baseline": baseline,
        "experiments": [],
    }

    def save_manifest() -> None:
        manifest_path.write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )

    print("The Long War - search experiment suite")
    print("=" * 38)
    print(
        f"{args.games} games/deck/orientation | {args.jobs} jobs | "
        f"{args.time_budget_seconds:g}s/searched move"
    )
    print(
        "Baseline: belief=12, c=0.3, reuse, tree=400k, pw=0, "
        "rollout=cheap/5, epsilon=0.12. Each A/B changes only candidate B."
    )

    experiments = len(comparisons) + 1
    for index, (name, overrides) in enumerate(comparisons, start=1):
        print()
        print(f"=== {index}/{experiments} {name} ===")
        entry: dict[str, Any] = {
            "name": name,
            "kind": "ismcts-match",
            "candidate_b_overrides": overrides,
            "status": "running",
        }
        manifest["experiments"].append(entry)
        save_manifest()
        try:
            summary_path = benchmark_ismcts_match(
                games_per_orientation=args.games,
                jobs=args.jobs,
                iterations=args.iterations,
                time_budget_seconds=args.time_budget_seconds,
                belief_samples_a=baseline["belief_samples"],
                belief_samples_b=overrides.get(
                    "belief_samples_b",
                    baseline["belief_samples"],
                ),
                exploration_a=baseline["exploration"],
                exploration_b=overrides.get(
                    "exploration_b",
                    baseline["exploration"],
                ),
                progressive_widening_a=baseline["progressive_widening"],
                progressive_widening_b=overrides.get(
                    "progressive_widening_b",
                    baseline["progressive_widening"],
                ),
                reuse_tree_a=baseline["reuse_tree"],
                reuse_tree_b=overrides.get(
                    "reuse_tree_b",
                    baseline["reuse_tree"],
                ),
                rollout_depth_a=baseline["rollout_depth"],
                rollout_depth_b=overrides.get(
                    "rollout_depth_b",
                    baseline["rollout_depth"],
                ),
                rollout_policy_a=baseline["rollout_policy"],
                rollout_policy_b=overrides.get(
                    "rollout_policy_b",
                    baseline["rollout_policy"],
                ),
                rollout_epsilon_a=baseline["rollout_epsilon"],
                rollout_epsilon_b=overrides.get(
                    "rollout_epsilon_b",
                    baseline["rollout_epsilon"],
                ),
                max_tree_nodes_a=baseline["max_tree_nodes"],
                max_tree_nodes_b=overrides.get(
                    "max_tree_nodes_b",
                    baseline["max_tree_nodes"],
                ),
                seed=args.seed,
            )
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
            entry.update({
                "status": "passed",
                "summary": str(summary_path.relative_to(ROOT)),
                "overall": payload.get("overall", {}),
                "resources": payload.get("resources", {}),
            })
        except ExperimentSkipped:
            entry.update({"status": "skipped"})
            print(f"SKIPPED: {name}")
        except (Exception, SystemExit) as exc:
            entry.update({
                "status": "failed",
                "error": f"{type(exc).__name__}: {exc}",
            })
            print(f"EXPERIMENT FAILED: {name}: {exc}")
            if args.stop_on_error:
                save_manifest()
                raise
        save_manifest()

    name = "baseline-vs-alpha-beta"
    print()
    print(f"=== {experiments}/{experiments} {name} ===")
    entry = {
        "name": name,
        "kind": "strength-bench",
        "status": "running",
    }
    manifest["experiments"].append(entry)
    save_manifest()
    try:
        summary_path = benchmark_strength(
            games_per_orientation=args.games,
            jobs=args.jobs,
            ismcts_iterations=args.iterations,
            alpha_nodes=args.alpha_nodes,
            belief_samples=baseline["belief_samples"],
            rollout_policy=baseline["rollout_policy"],
            rollout_depth=baseline["rollout_depth"],
            progressive_widening=baseline["progressive_widening"],
            exploration=baseline["exploration"],
            reuse_tree=baseline["reuse_tree"],
            rollout_epsilon=baseline["rollout_epsilon"],
            max_tree_nodes=baseline["max_tree_nodes"],
            time_budget_seconds=args.time_budget_seconds,
            seed=args.seed,
        )
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
        entry.update({
            "status": "passed",
            "summary": str(summary_path.relative_to(ROOT)),
            "overall": payload.get("overall", {}),
            "resources": payload.get("resources", {}),
        })
    except ExperimentSkipped:
        entry.update({"status": "skipped"})
        print(f"SKIPPED: {name}")
    except (Exception, SystemExit) as exc:
        entry.update({
            "status": "failed",
            "error": f"{type(exc).__name__}: {exc}",
        })
        print(f"EXPERIMENT FAILED: {name}: {exc}")
        if args.stop_on_error:
            save_manifest()
            raise
    save_manifest()

    failures = [
        row["name"]
        for row in manifest["experiments"]
        if row["status"] == "failed"
    ]
    skipped = [
        row["name"]
        for row in manifest["experiments"]
        if row["status"] == "skipped"
    ]
    manifest["completed"] = True
    manifest["failures"] = failures
    manifest["skipped"] = skipped

    def ci_for(row: dict[str, Any], rate_key: str) -> tuple[float | None, float | None]:
        paired = row.get("overall", {}).get("paired_uncertainty", {})
        low, high = paired.get("ci95", [None, None])
        if low is None or high is None or row.get("overall", {}).get(rate_key) is None:
            return None, None
        return float(low), float(high)

    control = next(
        (row for row in manifest["experiments"] if row["name"] == "baseline-control"),
        None,
    )
    strength = next(
        (row for row in manifest["experiments"] if row["name"] == "baseline-vs-alpha-beta"),
        None,
    )
    control_ci = ci_for(control or {}, "candidate_a_win_rate")
    strength_ci = ci_for(strength or {}, "mcts_win_rate")

    challengers_beating_baseline = []
    for row in manifest["experiments"]:
        if row.get("kind") != "ismcts-match" or row.get("name") == "baseline-control":
            continue
        low, high = ci_for(row, "candidate_a_win_rate")
        if high is not None and high < 0.5:
            challengers_beating_baseline.append(row["name"])

    capacity_cutoffs = 0
    capacity_reroots = 0
    if control:
        for stats in control.get("resources", {}).values():
            capacity_cutoffs += int(stats.get("tree_capacity_cutoffs", 0) or 0)
            capacity_reroots += int(stats.get("capacity_reroots", 0) or 0)

    blockers: list[str] = []
    warnings: list[str] = []
    if failures:
        blockers.append("one or more calibration experiments failed")
    if skipped:
        warnings.append(
            "manually skipped comparisons: " + ", ".join(skipped)
        )
    if control_ci[0] is None or not (control_ci[0] <= 0.5 <= control_ci[1]):
        blockers.append("identical ISMCTS control does not calibrate around 50%")
    if challengers_beating_baseline:
        blockers.append(
            "predeclared challenger beats the baseline: "
            + ", ".join(challengers_beating_baseline)
        )
    if strength is None or strength.get("status") != "passed":
        blockers.append("ISMCTS vs strategic alpha-beta comparison did not complete")
    elif strength_ci[1] is not None and strength_ci[1] < 0.5:
        blockers.append("ISMCTS is significantly weaker than strategic alpha-beta")
    if capacity_cutoffs:
        warnings.append(
            f"baseline tree hit capacity {capacity_cutoffs} times; "
            "inspect tree capacity before treating search as converged"
        )
    if capacity_reroots:
        warnings.append(
            f"baseline tree rerooted after capacity {capacity_reroots} times"
        )
    if strength_ci[0] is not None and strength_ci[0] > 0.5:
        warnings.append(
            "ISMCTS is significantly stronger than strategic alpha-beta; "
            "use alpha-beta as a qualitative cross-check, not an equal-strength oracle"
        )

    manifest["decision_readiness"] = {
        "ready": not blockers,
        "blockers": blockers,
        "warnings": warnings,
        "baseline_control_ci95": list(control_ci),
        "ismcts_vs_alpha_beta_ci95": list(strength_ci),
        "challengers_beating_baseline": challengers_beating_baseline,
        "baseline_tree_capacity_cutoffs": capacity_cutoffs,
        "baseline_capacity_reroots": capacity_reroots,
        "policy": (
            "Use ISMCTS as primary hidden-information design evidence and "
            "strategic alpha-beta as an independent cross-check. Heuristic "
            "telemetry is exploratory/product-policy evidence only. MCCFR "
            "variants are research-only until separately validated."
        ),
    }
    save_manifest()

    print()
    print("Experiment suite complete")
    print("=========================")
    for row in manifest["experiments"]:
        status = row["status"].upper()
        if row["kind"] == "ismcts-match" and row.get("overall"):
            overall = row["overall"]
            paired = overall.get("paired_uncertainty", {})
            low, high = paired.get("ci95", [None, None])
            rate = overall.get("candidate_a_win_rate")
            detail = (
                f" A={100.0 * rate:.1f}%"
                f" CI={100.0 * low:.1f}-{100.0 * high:.1f}%"
                if rate is not None and low is not None and high is not None
                else ""
            )
        elif row["kind"] == "strength-bench" and row.get("overall"):
            overall = row["overall"]
            paired = overall.get("paired_uncertainty", {})
            low, high = paired.get("ci95", [None, None])
            rate = overall.get("mcts_win_rate")
            detail = (
                f" ISMCTS={100.0 * rate:.1f}%"
                f" CI={100.0 * low:.1f}-{100.0 * high:.1f}%"
                if rate is not None and low is not None and high is not None
                else ""
            )
        else:
            detail = ""
        print(f"{status:6} {row['name']}{detail}")
    readiness = manifest["decision_readiness"]
    print()
    print(
        "Decision readiness: "
        + ("READY" if readiness["ready"] else "NOT READY")
    )
    for blocker in readiness["blockers"]:
        print(f"BLOCKER: {blocker}")
    for warning in readiness["warnings"]:
        print(f"WARNING: {warning}")
    print(f"Suite summary: {manifest_path}")

    if failures:
        print("Failed experiments: " + ", ".join(failures))
    return manifest_path


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
    ismcts_match.add_argument("--iterations", type=int, default=DEFAULT_ISMCTS_ITERATIONS)
    ismcts_match.add_argument("--time-budget-seconds", type=float, default=2.0)
    ismcts_match.add_argument("--seed", type=int, default=26092400)
    ismcts_match.add_argument("--a-belief-samples", type=int, default=12)
    ismcts_match.add_argument("--b-belief-samples", type=int, default=12)
    ismcts_match.add_argument("--a-exploration", type=float, default=DEFAULT_ISMCTS_EXPLORATION)
    ismcts_match.add_argument("--b-exploration", type=float, default=DEFAULT_ISMCTS_EXPLORATION)
    ismcts_match.add_argument("--a-pw", type=float, default=0.0)
    ismcts_match.add_argument("--b-pw", type=float, default=0.0)
    ismcts_match.add_argument("--a-no-tree-reuse", action="store_true")
    ismcts_match.add_argument("--b-no-tree-reuse", action="store_true")
    ismcts_match.add_argument("--a-rollout-depth", type=int, default=5)
    ismcts_match.add_argument("--b-rollout-depth", type=int, default=5)
    ismcts_match.add_argument("--a-rollout-epsilon", type=float, default=0.12)
    ismcts_match.add_argument("--b-rollout-epsilon", type=float, default=0.12)
    ismcts_match.add_argument("--a-max-tree-nodes", type=int)
    ismcts_match.add_argument("--b-max-tree-nodes", type=int)
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
        default=24,
        help=(
            "Games per deck/orientation. Default 24 gives 192 games total "
            "and 96 independent mirrored deal pairs."
        ),
    )
    strength_bench.add_argument("--jobs", type=int, default=8)
    strength_bench.add_argument("--iterations", type=int, default=DEFAULT_ISMCTS_ITERATIONS)
    strength_bench.add_argument("--seed", type=int, default=26092400)
    strength_bench.add_argument("--alpha-nodes", type=int, default=20_000)
    strength_bench.add_argument("--belief-samples", type=int, default=12)
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
    strength_bench.add_argument("--rollout-epsilon", type=float, default=0.12)
    strength_bench.add_argument("--max-tree-nodes", type=int)
    strength_bench.add_argument(
        "--rollout-policy",
        choices=("greedy", "cheap", "random"),
        default="cheap",
    )

    suite = sub.add_parser(
        "suite",
        help="Run the canonical decision-grade search experiment suite.",
    )
    suite.add_argument(
        "--games",
        type=int,
        default=24,
        help=(
            "Games per deck/orientation. Minimum 24; default 96 gives "
            "768 games and 384 mirrored deal pairs per comparison."
        ),
    )
    suite.add_argument("--jobs", type=int, default=8)
    suite.add_argument("--iterations", type=int, default=DEFAULT_ISMCTS_ITERATIONS)
    suite.add_argument("--alpha-nodes", type=int, default=20_000)
    suite.add_argument("--time-budget-seconds", type=float, default=2.0)
    suite.add_argument("--seed", type=int, default=26092400)
    suite.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop immediately instead of recording a failed experiment and continuing.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "validate-data":
        validate_data()
    elif args.command == "balance":
        balance_run(args)
    elif args.command == "validate":
        validate()
    elif args.command == "ismcts-match":
        benchmark_ismcts_match(
            games_per_orientation=args.games,
            jobs=args.jobs,
            iterations=args.iterations,
            time_budget_seconds=args.time_budget_seconds,
            belief_samples_a=args.a_belief_samples,
            belief_samples_b=args.b_belief_samples,
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
            rollout_epsilon_a=args.a_rollout_epsilon,
            rollout_epsilon_b=args.b_rollout_epsilon,
            max_tree_nodes_a=args.a_max_tree_nodes,
            max_tree_nodes_b=args.b_max_tree_nodes,
            seed=args.seed,
        )
    elif args.command == "strength-bench":
        benchmark_strength(
            games_per_orientation=args.games,
            jobs=args.jobs,
            ismcts_iterations=args.iterations,
            alpha_nodes=args.alpha_nodes,
            belief_samples=args.belief_samples,
            rollout_policy=args.rollout_policy,
            rollout_depth=args.rollout_depth,
            progressive_widening=args.progressive_widening,
            exploration=args.exploration,
            reuse_tree=not args.no_tree_reuse,
            rollout_epsilon=args.rollout_epsilon,
            max_tree_nodes=args.max_tree_nodes,
            time_budget_seconds=args.time_budget_seconds,
            seed=args.seed,
        )
    elif args.command == "suite":
        run_suite(args)
    else:
        raise AssertionError(args.command)


if __name__ == "__main__":
    main()
