from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DECKS = ("reference", "avaros", "mara", "sera")
MODES = ("automatic", "paid")


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
    mode: str
    deck: str
    seed: int
    output: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the Force-rich automatic-vs-paid draw experiment locally "
            "with the belief-sampled alpha-beta agent."
        )
    )
    parser.add_argument(
        "--preset",
        choices=tuple(PRESETS),
        default="deep",
        help="AI/search preset. deep is the normal experiment setting.",
    )
    parser.add_argument(
        "--mode",
        choices=("both", *MODES),
        default="both",
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
            "artifacts/local-force-draw/<preset>/."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without executing them.",
    )
    return parser.parse_args()


def selected_runs(args: argparse.Namespace) -> list[Run]:
    modes = MODES if args.mode == "both" else (args.mode,)
    decks = DECKS if args.deck == "all" else (args.deck,)
    output_dir = resolve(
        args.output_dir
        if args.output_dir is not None
        else Path("artifacts") / "local-force-draw" / args.preset
    )
    runs: list[Run] = []
    for deck_index, deck in enumerate(decks):
        # Automatic and paid use the same seed for the same deck so the
        # comparison is paired as closely as the differing draw rules allow.
        seed = args.seed + DECKS.index(deck)
        for mode in modes:
            runs.append(
                Run(
                    mode=mode,
                    deck=deck,
                    seed=seed,
                    output=output_dir / f"{mode}-{deck}.json",
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


def command_for(run: Run, preset: Preset, backend: str) -> list[str]:
    draw_args = (
        ["--automatic-draw"]
        if run.mode == "automatic"
        else ["--paid-draw", "--paid-draw-command-cost", "1"]
    )
    return [
        sys.executable,
        str(ROOT / "tools" / "simulate.py"),
        "--games",
        str(preset.games),
        "--seed",
        str(run.seed),
        "--card-file",
        "cards/experiments/force-draw-cards.json",
        "--deck-size",
        "34",
        "--hand-size",
        "10",
        "--disable-draw",
        "--command",
        "--disable-cycle",
        "--no-between-battle-recycle",
        "--reshuffle-on-empty",
        "--pass-final-operation",
        "--pass-requires-both-acted",
        "--first-passer-starts-next-battle",
        "--completion-command-refund",
        "1",
        "--public-stratagems",
        *draw_args,
        "--deck-a",
        f"decks/experiments/force-rich-34-{run.deck}.json",
        "--deck-b",
        f"decks/experiments/force-rich-34-{run.deck}.json",
        "--agent-a",
        "strategic_heuristic",
        "--agent-b",
        "strategic_heuristic",
        "--strategic-belief-samples",
        str(preset.belief_samples),
        "--strategic-search-depth",
        str(preset.depth),
        "--strategic-candidate-width",
        str(preset.width),
        "--strategic-node-budget",
        str(preset.node_budget),
        "--strategic-search-backend",
        backend,
        "--output",
        str(run.output),
    ]


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
            f"{run.mode}/{run.deck} failed with exit code "
            f"{process.returncode}:\n{process.stdout}"
        )
    return run, process.stdout


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
    decisions = telemetry["decisions"].get("strategic_heuristic", {})
    completions = sum(
        int(stats.get("completions", 0))
        for stats in telemetry["legend_combinations"].values()
    )
    mode = "automatic" if payload["simulation_variant"]["automatic_draw"] else "paid"
    deck = path.stem.removeprefix(f"{mode}-")
    return {
        "mode": mode,
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
) -> None:
    rows.sort(key=lambda row: (row["deck"], row["mode"]))
    summary = {
        "preset": preset_name,
        "settings": {
            "games": preset.games,
            "belief_samples": preset.belief_samples,
            "depth": preset.depth,
            "width": preset.width,
            "node_budget": preset.node_budget,
        },
        "rows": rows,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# Local Force-rich draw comparison",
        "",
        (
            f"Preset **{preset_name}** — {preset.games} games/run, "
            f"{preset.belief_samples} belief samples, max depth {preset.depth}, "
            f"beam {preset.width}, {preset.node_budget:,} nodes/decision."
        ),
        "",
        "| Deck | Draw | 0 Force | 0/1 Force | Forces/B | Names/B | Complete/B | No playable Force | Draws/player-B | Deck seen | Pass hand | AI depth | AI nodes |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    row["deck"],
                    row["mode"],
                    fmt(row["opening_zero_force_rate"]),
                    fmt(row["opening_zero_or_one_force_rate"]),
                    fmt(row["force_per_battle"]),
                    fmt(row["name_per_battle"]),
                    fmt(row["completion_per_battle"]),
                    fmt(row["no_playable_force_decision_rate"]),
                    fmt(row["mean_cards_drawn_per_player_battle"]),
                    fmt(row["mean_deck_seen_fraction_per_player_battle"]),
                    fmt(row["mean_hand_size_at_pass"]),
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


def main() -> None:
    args = parse_args()
    preset = effective_preset(args)
    runs = selected_runs(args)
    output_dir = resolve(
        args.output_dir
        if args.output_dir is not None
        else Path("artifacts") / "local-force-draw" / args.preset
    )

    print(
        f"Preset {args.preset}: games={preset.games}, "
        f"beliefs={preset.belief_samples}, depth={preset.depth}, "
        f"width={preset.width}, nodes={preset.node_budget:,}"
    )
    print(
        f"Parallel jobs: {min(args.jobs, len(runs))} | "
        f"backend={args.backend}"
    )
    print()

    commands = [
        (run, command_for(run, preset, args.backend))
        for run in runs
    ]
    for run, command in commands:
        print(f"[{run.mode}/{run.deck}] {printable_command(command)}")

    if args.dry_run:
        return

    print()
    with ThreadPoolExecutor(max_workers=min(args.jobs, len(runs))) as pool:
        futures = {
            pool.submit(execute, run, command): run
            for run, command in commands
        }
        for future in as_completed(futures):
            run = futures[future]
            try:
                _, stdout = future.result()
            except Exception as exc:
                for pending in futures:
                    pending.cancel()
                raise SystemExit(str(exc)) from exc
            final_line = stdout.rstrip().splitlines()[-1] if stdout.strip() else "done"
            print(f"[done {run.mode}/{run.deck}] {final_line}")

    rows = [row_for(run.output) for run in runs]
    output_dir.mkdir(parents=True, exist_ok=True)
    write_summary(
        rows,
        output_dir=output_dir,
        preset_name=args.preset,
        preset=preset,
    )
    print(f"Raw results: {output_dir}")
    print(f"Summary: {output_dir / 'summary.md'}")


if __name__ == "__main__":
    main()
