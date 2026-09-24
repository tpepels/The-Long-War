from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .fingerprint import artifact_directory, experiment_identity

ROOT = Path(__file__).resolve().parents[2]

DECKS = ("reference", "avaros", "mara", "sera")
CANONICAL_DECK_PATHS = {
    "reference": "decks/reference.json",
    "avaros": "decks/avaros-line.json",
    "mara": "decks/mara-rear.json",
    "sera": "decks/sera-support.json",
}
VARIANT_PROFILES = {
    "control": "force-automatic",
    "paid-free": "force-paid-free",
    "auto-discard9": "force-auto-discard9",
    "auto-discard7": "force-auto-discard7",
    "auto-cap10": "force-auto-cap10",
    # Retained for regression comparisons with the original experiment.
    "automatic": "force-automatic",
    "paid": "force-paid",
}
EXPERIMENT_VARIANTS = (
    "control",
    "paid-free",
    "auto-discard9",
    "auto-discard7",
    "auto-cap10",
)


@dataclass(frozen=True)
class Preset:
    games: int
    belief_samples: int
    depth: int
    width: int
    node_budget: int


PRESETS = {
    "quick": Preset(
        games=8,
        belief_samples=2,
        depth=4,
        width=4,
        node_budget=4_000,
    ),
    "deep": Preset(
        games=20,
        belief_samples=4,
        depth=6,
        width=5,
        node_budget=20_000,
    ),
    "max": Preset(
        games=20,
        belief_samples=6,
        depth=8,
        width=6,
        node_budget=60_000,
    ),
}


@dataclass(frozen=True)
class Run:
    variant: str
    deck: str
    seed: int
    output: Path


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--preset",
        choices=tuple(PRESETS),
        default="deep",
        help="AI/search preset. deep is the normal experiment setting.",
    )
    parser.add_argument(
        "--variant",
        "--mode",
        dest="variant",
        choices=("experiment", "all", *VARIANT_PROFILES),
        default="experiment",
        help=(
            "experiment runs control + A-D. all also includes the original "
            "paid baseline. --mode remains as a compatibility alias."
        ),
    )
    parser.add_argument(
        "--deck",
        choices=("all", *DECKS),
        default="all",
    )
    parser.add_argument("--games", type=int)
    parser.add_argument("--belief-samples", type=int)
    parser.add_argument("--depth", type=int)
    parser.add_argument("--width", type=int)
    parser.add_argument("--node-budget", type=int)
    parser.add_argument(
        "--agent",
        choices=("ismcts", "strategic_heuristic"),
        default="ismcts",
        help="Strong simulation agent; ISMCTS is the default.",
    )
    parser.add_argument("--ismcts-belief-samples", type=int)
    parser.add_argument("--ismcts-iterations", type=int)
    parser.add_argument("--ismcts-rollout-depth", type=int)
    parser.add_argument("--ismcts-exploration", "--exploration", type=float, default=2 ** 0.5)
    parser.add_argument(
        "--ismcts-progressive-widening", "--progressive-widening",
        type=float,
        default=0.0,
    )
    parser.add_argument(
        "--ismcts-rollout-policy",
        choices=("greedy", "cheap", "random"),
        default="cheap",
    )
    parser.add_argument(
        "--backend",
        choices=("auto", "cython", "python"),
        default="auto",
        help="Strategic search backend; auto prefers compiled Cython.",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=8,
        help="Number of deck/mode simulations to run in parallel (default: 8).",
    )
    parser.add_argument("--seed", type=int, default=26092334)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "Result directory. Defaults to "
            "artifacts/cardflow/<preset>/."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without executing them.",
    )


def selected_runs(args: argparse.Namespace) -> list[Run]:
    if args.variant == "experiment":
        variants = EXPERIMENT_VARIANTS
    elif args.variant == "all":
        variants = tuple(VARIANT_PROFILES)
    else:
        variants = (args.variant,)
    decks = DECKS if args.deck == "all" else (args.deck,)
    output_dir = resolve(
        args.output_dir
        if args.output_dir is not None
        else Path("artifacts") / "cardflow" / args.preset
    )
    runs: list[Run] = []
    for deck_index, deck in enumerate(decks):
        # Every variant uses the same seed for a deck, keeping comparisons
        # paired as closely as the differing card-flow rules allow.
        seed = args.seed + DECKS.index(deck)
        for variant in variants:
            runs.append(
                Run(
                    variant=variant,
                    deck=deck,
                    seed=seed,
                    output=output_dir / f"{variant}--{deck}.json",
                )
            )
    return runs


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def effective_preset(args: argparse.Namespace) -> Preset:
    base = PRESETS[args.preset]
    preset = Preset(
        games=args.games if args.games is not None else base.games,
        belief_samples=(
            args.belief_samples
            if args.belief_samples is not None
            else base.belief_samples
        ),
        depth=args.depth if args.depth is not None else base.depth,
        width=args.width if args.width is not None else base.width,
        node_budget=(
            args.node_budget
            if args.node_budget is not None
            else base.node_budget
        ),
    )
    if min(
        preset.games,
        preset.belief_samples,
        preset.depth,
        preset.width,
        preset.node_budget,
    ) <= 0:
        raise SystemExit("Games and all search settings must be positive.")
    if args.jobs <= 0:
        raise SystemExit("--jobs must be positive.")
    return preset


def ismcts_preset(name: str) -> tuple[int, int, int]:
    """belief states, iterations, rollout depth"""
    return {
        "quick": (8, 10_000, 5),
        "deep": (12, 100_000, 5),
        "max": (16, 500_000, 5),
    }[name]


def command_for(
    run: Run,
    preset: Preset,
    preset_name: str,
    backend: str,
    agent: str,
    ismcts_settings: tuple[int, int, int] | None = None,
    ismcts_rollout_policy: str = "cheap",
    ismcts_progressive_widening: float = 0.0,
    ismcts_exploration: float = 2 ** 0.5,
) -> list[str]:
    rules_profile = VARIANT_PROFILES[run.variant]
    command = [
        sys.executable,
        str(ROOT / "tools" / "simulate.py"),
        "--games",
        str(preset.games),
        "--seed",
        str(run.seed),
        "--rules-profile",
        rules_profile,
        "--card-file",
        "cards/cards.json",
        "--deck-a",
        CANONICAL_DECK_PATHS[run.deck],
        "--deck-b",
        CANONICAL_DECK_PATHS[run.deck],
        "--agent-a",
        agent,
        "--agent-b",
        agent,
    ]
    if agent == "ismcts":
        # MCTS iterations are full simulations, not alpha-beta nodes.
        beliefs, iterations, rollout = (
            ismcts_settings
            if ismcts_settings is not None
            else ismcts_preset(preset_name)
        )
        command.extend([
            "--ismcts-belief-samples", str(beliefs),
            "--ismcts-iterations", str(iterations),
            "--ismcts-rollout-depth", str(rollout),
            "--ismcts-exploration", str(ismcts_exploration),
            "--ismcts-progressive-widening", str(ismcts_progressive_widening),
            "--ismcts-rollout-policy", ismcts_rollout_policy,
        ])
    else:
        command.extend([
            "--strategic-belief-samples", str(preset.belief_samples),
            "--strategic-search-depth", str(preset.depth),
            "--strategic-candidate-width", str(preset.width),
            "--strategic-node-budget", str(preset.node_budget),
            "--strategic-search-backend", backend,
        ])
    command.extend([
        "--progress-file",
        str(run.output.with_suffix(".progress")),
        "--output",
        str(run.output),
    ])
    return command


def printable_command(command: list[str]) -> str:
    return " ".join(
        f"'{part}'" if any(char.isspace() for char in part) else part
        for part in command
    )


def execute(run: Run, command: list[str]) -> tuple[Run, str]:
    run.output.parent.mkdir(parents=True, exist_ok=True)
    process = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if process.returncode != 0:
        raise RuntimeError(
            f"{run.variant}/{run.deck} failed with exit code "
            f"{process.returncode}:\n{process.stdout}"
        )
    return run, process.stdout


def read_progress(path: Path) -> int:
    try:
        return max(0, int(path.read_text(encoding="utf-8").strip() or "0"))
    except (OSError, ValueError):
        return 0


def format_duration(seconds: float) -> str:
    seconds = max(0, int(round(seconds)))
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:d}h {minutes:02d}m"
    if minutes:
        return f"{minutes:d}m {seconds:02d}s"
    return f"{seconds:d}s"


def render_progress(
    runs: list[Run],
    *,
    games_per_run: int,
    finished_cells: int,
    started_at: float,
) -> str:
    total_games = games_per_run * len(runs)
    completed_games = min(
        total_games,
        sum(
            min(games_per_run, read_progress(run.output.with_suffix(".progress")))
            for run in runs
        ),
    )
    fraction = completed_games / total_games if total_games else 1.0
    width = 30
    filled = min(width, int(fraction * width))
    bar = "#" * filled + "-" * (width - filled)
    elapsed = time.perf_counter() - started_at
    if completed_games:
        rate = completed_games / elapsed if elapsed > 0 else 0.0
        eta = (
            (total_games - completed_games) / rate
            if rate > 0 and completed_games < total_games
            else 0.0
        )
        eta_text = format_duration(eta)
    else:
        eta_text = "calculating..."
    return (
        f"[{bar}] {completed_games:>3}/{total_games} "
        f"({fraction * 100:5.1f}%) | "
        f"elapsed {format_duration(elapsed)} | ETA {eta_text} | "
        f"cells {finished_cells}/{len(runs)}"
    )


def safe_ratio(numerator: float, denominator: float) -> float | None:
    if not denominator:
        return None
    return numerator / denominator


def row_for(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    telemetry = payload["telemetry"]
    human = telemetry["human_flow"]
    actions = telemetry["actions"]
    battles = int(telemetry["battles"]["count"])
    decisions = (
        telemetry["decisions"].get("ismcts")
        or telemetry["decisions"].get("strategic_heuristic", {})
    )
    completions = sum(
        int(stats.get("completions", 0))
        for stats in telemetry["legend_combinations"].values()
    )
    variant, deck = path.stem.rsplit("--", 1)
    return {
        "variant": variant,
        "deck": deck,
        "games": int(payload["games"]),
        "battles": battles,
        "force_per_battle": safe_ratio(actions.get("PlaySubject", 0), battles),
        "bond_per_battle": safe_ratio(actions.get("PlayLink", 0), battles),
        "name_per_battle": safe_ratio(actions.get("PlayName", 0), battles),
        "completion_per_battle": safe_ratio(completions, battles),
        "paid_draw_per_battle": safe_ratio(actions.get("Draw", 0), battles),
        "opening_zero_force_rate": human["opening_zero_force_rate"],
        "opening_zero_or_one_force_rate": human["opening_zero_or_one_force_rate"],
        "mean_opening_forces": human["mean_opening_forces"],
        "no_playable_force_decision_rate": human[
            "no_playable_force_decision_rate"
        ],
        "longest_no_playable_force_streak": human[
            "longest_no_playable_force_streak"
        ],
        "mean_cards_drawn_per_player_battle": human[
            "mean_cards_drawn_per_player_battle"
        ],
        "mean_deck_seen_fraction_per_player_battle": human[
            "mean_deck_seen_fraction_per_player_battle"
        ],
        "mean_hand_size_at_pass": human["mean_hand_size_at_pass"],
        "early_first_pass_rate": human["early_first_pass_rate"],
        "completion_command_refund": human[
            "mean_completion_command_refund_per_player_battle"
        ],
        "battle_end_discards_per_player_battle": human.get(
            "mean_battle_end_discards_per_player_battle"
        ),
        "mean_operations_before_pass": human.get(
            "mean_operations_before_pass"
        ),
        "final_operation_abs_margin_swing": human[
            "mean_final_operation_abs_margin_swing"
        ],
        "reshuffles": human["reshuffles"],
        "mean_candidate_count": decisions.get("mean_candidate_count"),
        "mean_completed_depth": decisions.get("mean_completed_depth"),
        "mean_search_nodes": decisions.get("mean_search_nodes"),
        "first_player_win_rate": payload["first_player_win_rate"],
        "search_backends": telemetry.get("search_backends", {}),
    }


def fmt(value: Any, digits: int = 2) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def write_summary(
    rows: list[dict[str, Any]],
    *,
    output_dir: Path,
    preset_name: str,
    preset: Preset,
    agent: str,
    ismcts_settings: tuple[int, int, int] | None = None,
    ismcts_rollout_policy: str = "cheap",
    ismcts_progressive_widening: float = 0.0,
    ismcts_exploration: float = 2 ** 0.5,
) -> None:
    variant_order = {
        name: index
        for index, name in enumerate((*EXPERIMENT_VARIANTS, "automatic", "paid"))
    }
    rows.sort(
        key=lambda row: (
            row["deck"],
            variant_order.get(row["variant"], 999),
        )
    )
    if agent == "ismcts":
        beliefs, iterations, rollout = (
            ismcts_settings
            if ismcts_settings is not None
            else ismcts_preset(preset_name)
        )
        settings = {
            "agent": "ismcts",
            "games": preset.games,
            "belief_samples": beliefs,
            "iterations": iterations,
            "rollout_depth": rollout,
            "rollout_policy": ismcts_rollout_policy,
            "exploration": ismcts_exploration,
            "progressive_widening": ismcts_progressive_widening,
        }
    else:
        settings = {
            "agent": "strategic_heuristic",
            "games": preset.games,
            "belief_samples": preset.belief_samples,
            "depth": preset.depth,
            "width": preset.width,
            "node_budget": preset.node_budget,
        }
    summary = {
        "preset": preset_name,
        "settings": settings,
        "rows": rows,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )

    if agent == "ismcts":
        beliefs, iterations, rollout = (
            ismcts_settings
            if ismcts_settings is not None
            else ismcts_preset(preset_name)
        )
        settings_line = (
            f"Preset **{preset_name}** — {preset.games} games/run, "
            f"Cython ISMCTS, {beliefs} belief states, "
            f"{iterations:,} iterations/decision, rollout depth {rollout}, "
            f"rollout policy {ismcts_rollout_policy}, "
            f"c {ismcts_exploration:g}, pw {ismcts_progressive_widening:g}."
        )
    else:
        settings_line = (
            f"Preset **{preset_name}** — {preset.games} games/run, "
            f"{preset.belief_samples} belief samples, max depth {preset.depth}, "
            f"beam {preset.width}, {preset.node_budget:,} nodes/decision."
        )
    lines = [
        "# Local Force-rich card-flow comparison",
        "",
        settings_line,
        "",
        "| Deck | Variant | Forces/B | Names/B | Complete/B | No playable Force | Draws/player-B | Deck seen | Pass hand | Ops/pass | Cleanup discards/PB | Reshuffles | AI depth | AI nodes |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    row["deck"],
                    row["variant"],
                    fmt(row["force_per_battle"]),
                    fmt(row["name_per_battle"]),
                    fmt(row["completion_per_battle"]),
                    fmt(row["no_playable_force_decision_rate"]),
                    fmt(row["mean_cards_drawn_per_player_battle"]),
                    fmt(row["mean_deck_seen_fraction_per_player_battle"]),
                    fmt(row["mean_hand_size_at_pass"]),
                    fmt(row["mean_operations_before_pass"]),
                    fmt(row["battle_end_discards_per_player_battle"]),
                    fmt(row["reshuffles"], 0),
                    fmt(row["mean_completed_depth"]),
                    fmt(row["mean_search_nodes"], 0),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "Additional metrics, including pass timing, final-operation swing, "
            "Command refunds, reshuffles, decision-space size and paid Draw use, "
            "are retained in summary.json and the raw per-run JSON files.",
        ]
    )
    markdown = "\n".join(lines) + "\n"
    (output_dir / "summary.md").write_text(markdown, encoding="utf-8")
    print(markdown)


def run(args: argparse.Namespace) -> None:
    preset = effective_preset(args)

    ismcts_settings = None
    if args.agent == "ismcts":
        default_beliefs, default_iterations, default_rollout = ismcts_preset(
            args.preset
        )
        ismcts_settings = (
            args.ismcts_belief_samples if args.ismcts_belief_samples is not None else default_beliefs,
            args.ismcts_iterations if args.ismcts_iterations is not None else default_iterations,
            (
                args.ismcts_rollout_depth
                if args.ismcts_rollout_depth is not None
                else default_rollout
            ),
        )
        beliefs, iterations, rollout = ismcts_settings
        if min(beliefs, iterations) <= 0 or rollout < 0:
            raise SystemExit("ISMCTS beliefs/iterations must be positive and rollout depth non-negative")
        print(
            f"Preset {args.preset}: games={preset.games}, "
            f"ISMCTS beliefs={beliefs}, iterations={iterations:,}, "
            f"rollout={rollout}"
        )
    else:
        print(
            f"Preset {args.preset}: games={preset.games}, "
            f"beliefs={preset.belief_samples}, depth={preset.depth}, "
            f"width={preset.width}, nodes={preset.node_budget:,}"
        )
    config = {key: value for key, value in vars(args).items()
              if key not in {"output_dir", "jobs", "dry_run", "command"}}
    identity = experiment_identity(config)
    if args.output_dir is None:
        args.output_dir = artifact_directory(
            ROOT / "artifacts" / "cardflow" / args.preset, identity,
            write=not args.dry_run,
        )
    output_dir = resolve(args.output_dir)
    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        manifest = output_dir / "config.json"
        if manifest.exists() and json.loads(manifest.read_text()) != identity:
            raise SystemExit("Output directory belongs to a different experiment; choose --output-dir")
        manifest.write_text(json.dumps(identity, indent=2, sort_keys=True) + "\n")
    runs = selected_runs(args)
    print(
        f"Parallel jobs: {min(args.jobs, len(runs))} | "
        f"agent={args.agent} | backend={args.backend}"
    )
    print()

    commands = [
        (
            run,
            command_for(
                run,
                preset,
                args.preset,
                args.backend,
                args.agent,
                ismcts_settings,
                args.ismcts_rollout_policy,
                args.ismcts_progressive_widening,
                args.ismcts_exploration,
            ),
        )
        for run in runs
    ]
    for run, command in commands:
        print(f"[{run.variant}/{run.deck}] {printable_command(command)}")

    if args.dry_run:
        return

    print()
    for run in runs:
        run.output.with_suffix(".progress").unlink(missing_ok=True)

    started_at = time.perf_counter()
    finished_cells = 0
    with ThreadPoolExecutor(max_workers=min(args.jobs, len(runs))) as pool:
        futures = {
            pool.submit(execute, run, command): run
            for run, command in commands
        }
        pending = set(futures)
        last_line = ""
        while pending:
            done, pending = wait(
                pending,
                timeout=1.0,
                return_when=FIRST_COMPLETED,
            )
            for future in done:
                run = futures[future]
                try:
                    future.result()
                except Exception as exc:
                    for remaining in pending:
                        remaining.cancel()
                    print()
                    raise SystemExit(str(exc)) from exc
                finished_cells += 1

            line = render_progress(
                runs,
                games_per_run=preset.games,
                finished_cells=finished_cells,
                started_at=started_at,
            )
            if line != last_line:
                print("\r" + line + " " * max(0, len(last_line) - len(line)), end="", flush=True)
                last_line = line

        final_line = render_progress(
            runs,
            games_per_run=preset.games,
            finished_cells=finished_cells,
            started_at=started_at,
        )
        print("\r" + final_line + " " * max(0, len(last_line) - len(final_line)))

    for run in runs:
        run.output.with_suffix(".progress").unlink(missing_ok=True)

    rows = [row_for(run.output) for run in runs]
    output_dir.mkdir(parents=True, exist_ok=True)
    write_summary(
        rows,
        output_dir=output_dir,
        preset_name=args.preset,
        preset=preset,
        agent=args.agent,
        ismcts_settings=ismcts_settings,
        ismcts_rollout_policy=args.ismcts_rollout_policy,
        ismcts_progressive_widening=args.ismcts_progressive_widening,
        ismcts_exploration=args.ismcts_exploration,
    )
    print(f"Raw results: {output_dir}")
    print(f"Summary: {output_dir / 'summary.md'}")

