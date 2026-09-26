from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from longwar.agents.ismcts_agent import (
    DEFAULT_ISMCTS_BELIEF_SAMPLES,
    DEFAULT_ISMCTS_EXPLORATION,
    DEFAULT_ISMCTS_ITERATIONS,
    DEFAULT_ISMCTS_MAX_TREE_NODES,
    DEFAULT_ISMCTS_PROGRESSIVE_WIDENING,
    DEFAULT_ISMCTS_ROLLOUT_DEPTH,
    DEFAULT_ISMCTS_ROLLOUT_EPSILON,
    DEFAULT_ISMCTS_ROLLOUT_POLICY,
)
from longwar.cards import load_card_file
from longwar.game import GameEngine
from longwar.rules import GameRules
from longwar.fingerprint import current_game_fingerprint
from longwar.simulate import simulate_games

ROOT = Path(__file__).resolve().parents[1]


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def load_deck(path: Path) -> list[str]:
    data = json.loads(resolve(path).read_text(encoding="utf-8"))
    return list(data["cards"])


def load_policy(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    return json.loads(resolve(path).read_text(encoding="utf-8"))


def _write_progress_snapshot(
    path: Path,
    completed: int,
    total: int,
    wins: tuple[int, int],
) -> None:
    """Atomically publish one simulation progress snapshot."""
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps({
            "completed": completed,
            "total": total,
            "wins": [wins[0], wins[1]],
        }) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    defaults = GameRules.standard()
    parser.add_argument("--games", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=1701)
    choices = ["heuristic", "strategic_heuristic", "ismcts", "random", "mccfr", "online_mccfr"]
    parser.add_argument("--agent-a", choices=choices, default="heuristic")
    parser.add_argument("--agent-b", choices=choices, default="heuristic")
    parser.add_argument("--policy-a", type=Path)
    parser.add_argument("--policy-b", type=Path)
    parser.add_argument("--agent-a-label")
    parser.add_argument("--agent-b-label")
    parser.add_argument("--agent-a-seed-offset", type=int)
    parser.add_argument("--agent-b-seed-offset", type=int)
    parser.add_argument(
        "--agent-a-options-json",
        default="{}",
        help="Internal per-seat agent overrides as a JSON object.",
    )
    parser.add_argument(
        "--agent-b-options-json",
        default="{}",
        help="Internal per-seat agent overrides as a JSON object.",
    )
    parser.add_argument(
        "--heuristic-exploration",
        type=float,
        default=0.0,
        help="Random exploration probability for the one-ply heuristic agent.",
    )
    parser.add_argument("--online-iterations", type=int, default=8)
    parser.add_argument("--online-depth", type=int, default=2)
    parser.add_argument("--strategic-belief-samples", type=int, default=3)
    parser.add_argument(
        "--strategic-rollout-plies",
        "--strategic-search-depth",
        dest="strategic_rollout_plies",
        type=int,
        default=5,
        help="Maximum iterative-deepening alpha-beta depth in plies.",
    )
    parser.add_argument("--strategic-candidate-width", type=int, default=6)
    parser.add_argument(
        "--strategic-node-budget",
        type=int,
        default=20_000,
        help="Maximum alpha-beta nodes per strategic decision.",
    )
    parser.add_argument(
        "--strategic-time-budget-seconds",
        type=float,
        help="Optional wall-clock budget per non-forced alpha-beta decision.",
    )
    parser.add_argument(
        "--strategic-search-backend",
        choices=("auto", "cython", "python"),
        default="auto",
        help="Search backend. auto prefers the compiled Cython accelerator.",
    )
    parser.add_argument("--ismcts-belief-samples", type=int, default=DEFAULT_ISMCTS_BELIEF_SAMPLES)
    parser.add_argument("--ismcts-iterations", type=int, default=DEFAULT_ISMCTS_ITERATIONS)
    parser.add_argument(
        "--ismcts-time-budget-seconds",
        type=float,
        help="Optional wall-clock budget per non-forced ISMCTS decision.",
    )
    parser.add_argument("--ismcts-rollout-depth", type=int, default=DEFAULT_ISMCTS_ROLLOUT_DEPTH)
    parser.add_argument("--ismcts-tree-depth-limit", type=int, default=96)
    parser.add_argument("--ismcts-exploration", type=float, default=DEFAULT_ISMCTS_EXPLORATION)
    parser.add_argument(
        "--ismcts-progressive-widening",
        type=float,
        default=0.0,
        help=(
            "Square-root progressive-widening constant. 0 disables widening; "
            "positive c allows floor(c * sqrt(N + 1)) legal actions per node."
        ),
    )
    parser.add_argument(
        "--ismcts-no-tree-reuse",
        action="store_true",
        help="Rebuild the ISMCTS tree from scratch for every decision.",
    )
    parser.add_argument(
        "--ismcts-max-tree-nodes",
        type=int,
        help=(
            "Maximum persistent ISMCTS information-set nodes. "
            "Default is four times the iteration budget."
        ),
    )
    parser.add_argument("--ismcts-rollout-epsilon", type=float, default=DEFAULT_ISMCTS_ROLLOUT_EPSILON)
    parser.add_argument(
        "--ismcts-rollout-policy",
        choices=("greedy", "cheap", "random"),
        default=DEFAULT_ISMCTS_ROLLOUT_POLICY,
    )
    parser.add_argument(
        "--hand-size",
        type=int,
        default=defaults.opening_hand_size,
        help="Base opening and between-Battle refill hand target.",
    )
    parser.add_argument(
        "--card-file",
        type=Path,
        default=Path("cards/cards.json"),
        help="Card data file for this simulation variant.",
    )
    recycle_group = parser.add_mutually_exclusive_group()
    recycle_group.add_argument("--between-battle-recycle", dest="recycle", action="store_true")
    recycle_group.add_argument("--no-between-battle-recycle", dest="recycle", action="store_false")
    reshuffle_group = parser.add_mutually_exclusive_group()
    reshuffle_group.add_argument("--reshuffle-on-empty", dest="reshuffle", action="store_true")
    reshuffle_group.add_argument("--no-reshuffle-on-empty", dest="reshuffle", action="store_false")
    draw_group = parser.add_mutually_exclusive_group()
    draw_group.add_argument("--enable-draw", dest="draw_enabled", action="store_true")
    draw_group.add_argument("--disable-draw", dest="draw_enabled", action="store_false")
    parser.set_defaults(
        recycle=defaults.recycle_between_battles,
        reshuffle=defaults.reshuffle_on_empty,
        draw_enabled=defaults.draw_action_enabled,
    )
    parser.add_argument(
        "--completion-draw-names",
        nargs="*",
        default=[],
        help="Name ids that draw 1 when their formation becomes complete.",
    )
    command_group = parser.add_mutually_exclusive_group()
    command_group.add_argument("--command", action="store_true")
    command_group.add_argument("--no-command", dest="command", action="store_false")
    parser.set_defaults(command=defaults.command_enabled)
    parser.add_argument("--starting-command", type=int, default=20)
    parser.add_argument("--battle-command-gain", type=int, default=10)
    parser.add_argument("--command-cap", type=int, default=20)
    parser.add_argument(
        "--cycle-command-cost",
        type=int,
        default=defaults.cycle_command_cost,
    )
    cycle_group = parser.add_mutually_exclusive_group()
    cycle_group.add_argument(
        "--enable-cycle",
        dest="cycle_enabled",
        action="store_true",
        help="Enable the Command Cycle operation.",
    )
    cycle_group.add_argument(
        "--disable-cycle",
        dest="cycle_enabled",
        action="store_false",
        help="Disable the Command Cycle operation.",
    )
    parser.set_defaults(cycle_enabled=defaults.cycle_enabled)

    turn_draw_group = parser.add_mutually_exclusive_group()
    turn_draw_group.add_argument(
        "--automatic-draw",
        dest="turn_draw_mode",
        action="store_const",
        const="automatic",
        help="At the start of every turn, draw one card before the operation.",
    )
    turn_draw_group.add_argument(
        "--paid-draw",
        dest="turn_draw_mode",
        action="store_const",
        const="paid",
        help="Enable Draw as a paid Command operation with no discard.",
    )
    turn_draw_group.add_argument(
        "--no-turn-draw",
        dest="turn_draw_mode",
        action="store_const",
        const="none",
        help="Disable both automatic and paid Command draw modes.",
    )
    parser.set_defaults(
        turn_draw_mode=(
            "automatic"
            if defaults.automatic_draw
            else "paid"
            if defaults.paid_draw_enabled
            else "none"
        )
    )
    parser.add_argument(
        "--paid-draw-command-cost",
        type=int,
        default=defaults.paid_draw_command_cost,
    )

    paid_operation_group = parser.add_mutually_exclusive_group()
    paid_operation_group.add_argument(
        "--paid-draw-consumes-operation",
        dest="paid_draw_consumes_operation",
        action="store_true",
    )
    paid_operation_group.add_argument(
        "--paid-draw-keeps-operation",
        dest="paid_draw_consumes_operation",
        action="store_false",
    )
    parser.set_defaults(
        paid_draw_consumes_operation=defaults.paid_draw_consumes_operation
    )
    parser.add_argument(
        "--automatic-draw-hand-limit",
        type=int,
        default=defaults.automatic_draw_hand_limit,
    )
    parser.add_argument(
        "--battle-end-hand-limit",
        type=int,
        default=defaults.battle_end_hand_limit,
    )

    parser.add_argument(
        "--completion-command-refund",
        type=int,
        default=defaults.completion_command_refund,
    )
    stratagem_group = parser.add_mutually_exclusive_group()
    stratagem_group.add_argument(
        "--public-stratagems",
        dest="public_stratagems",
        action="store_true",
        help="Play Stratagems face-up so their Battle rule is active immediately.",
    )
    stratagem_group.add_argument(
        "--hidden-stratagems",
        dest="public_stratagems",
        action="store_false",
        help="Use hidden triggered Stratagems for legacy experiments.",
    )
    parser.set_defaults(public_stratagems=defaults.public_stratagems)
    parser.add_argument(
        "--deck-a",
        type=Path,
        default=Path("decks/reference.json"),
    )
    parser.add_argument(
        "--deck-b",
        type=Path,
        default=Path("decks/reference.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/simulation-report.json"),
    )
    parser.add_argument(
        "--progress-file",
        type=Path,
        help="Optional file updated after each completed game.",
    )
    args = parser.parse_args()

    def parse_agent_options(raw: str, label: str) -> dict[str, Any]:
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{label} must be valid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise SystemExit(f"{label} must decode to a JSON object")
        return value

    agent_overrides = (
        parse_agent_options(args.agent_a_options_json, "--agent-a-options-json"),
        parse_agent_options(args.agent_b_options_json, "--agent-b-options-json"),
    )
    agent_labels = (
        args.agent_a_label or args.agent_a,
        args.agent_b_label or args.agent_b,
    )

    if (args.agent_a_seed_offset is None) != (args.agent_b_seed_offset is None):
        raise SystemExit("Provide both --agent-a-seed-offset and --agent-b-seed-offset")
    agent_seed_offsets = (
        None
        if args.agent_a_seed_offset is None
        else (args.agent_a_seed_offset, args.agent_b_seed_offset)
    )

    card_data = load_card_file(resolve(args.card_file))
    rules = GameRules(
        opening_hand_size=args.hand_size,
        draw_action_enabled=args.draw_enabled,
        completion_draw_names=tuple(args.completion_draw_names),
        recycle_between_battles=args.recycle,
        command_enabled=args.command,
        starting_command=args.starting_command,
        battle_command_gain=args.battle_command_gain,
        command_cap=args.command_cap,
        cycle_command_cost=args.cycle_command_cost,
        reshuffle_on_empty=args.reshuffle,
        automatic_draw=args.turn_draw_mode == "automatic",
        paid_draw_enabled=args.turn_draw_mode == "paid",
        paid_draw_command_cost=args.paid_draw_command_cost,
        paid_draw_consumes_operation=args.paid_draw_consumes_operation,
        automatic_draw_hand_limit=args.automatic_draw_hand_limit,
        battle_end_hand_limit=args.battle_end_hand_limit,
        cycle_enabled=args.cycle_enabled,
        completion_command_refund=args.completion_command_refund,
        public_stratagems=args.public_stratagems,
    )
    engine = GameEngine(card_data, rules=rules)
    deck_a = load_deck(args.deck_a)
    deck_b = load_deck(args.deck_b)
    policies = (load_policy(args.policy_a), load_policy(args.policy_b))
    game_fingerprint = current_game_fingerprint()
    for policy in policies:
        if policy is not None and policy.get("game_fingerprint") != game_fingerprint:
            raise SystemExit("MCCFR policy belongs to an older ruleset; retrain it before simulation")

    progress_path = resolve(args.progress_file) if args.progress_file else None

    def write_progress(
        completed: int,
        total: int,
        wins: tuple[int, int],
    ) -> None:
        if progress_path is None:
            return
        _write_progress_snapshot(progress_path, completed, total, wins)

    if progress_path is not None:
        progress_path.parent.mkdir(parents=True, exist_ok=True)
        write_progress(0, args.games, (0, 0))

    def report_progress(
        completed: int,
        total: int,
        wins: tuple[int, int],
    ) -> None:
        write_progress(completed, total, wins)

    report = simulate_games(
        engine,
        deck_a,
        deck_b,
        games=args.games,
        seed=args.seed,
        agent_names=(args.agent_a, args.agent_b),
        agent_policies=policies,
        heuristic_exploration=args.heuristic_exploration,
        online_iterations=args.online_iterations,
        online_depth=args.online_depth,
        strategic_belief_samples=args.strategic_belief_samples,
        strategic_rollout_plies=args.strategic_rollout_plies,
        strategic_candidate_width=args.strategic_candidate_width,
        strategic_node_budget=args.strategic_node_budget,
        strategic_time_budget_seconds=args.strategic_time_budget_seconds,
        strategic_search_backend=args.strategic_search_backend,
        ismcts_belief_samples=args.ismcts_belief_samples,
        ismcts_iterations=args.ismcts_iterations,
        ismcts_time_budget_seconds=args.ismcts_time_budget_seconds,
        ismcts_rollout_depth=args.ismcts_rollout_depth,
        ismcts_tree_depth_limit=args.ismcts_tree_depth_limit,
        ismcts_exploration=args.ismcts_exploration,
        ismcts_progressive_widening=args.ismcts_progressive_widening,
        ismcts_reuse_tree=not args.ismcts_no_tree_reuse,
        ismcts_max_tree_nodes=args.ismcts_max_tree_nodes,
        ismcts_rollout_epsilon=args.ismcts_rollout_epsilon,
        ismcts_rollout_policy=args.ismcts_rollout_policy,
        agent_overrides=agent_overrides,
        agent_labels=agent_labels,
        agent_seed_offsets=agent_seed_offsets,
        progress_callback=report_progress if progress_path is not None else None,
    )

    payload = asdict(report)
    payload["game_fingerprint"] = game_fingerprint
    payload["seed"] = args.seed
    payload["win_rates"] = report.win_rates
    payload["first_player_win_rate"] = report.first_player_win_rate
    payload["heuristic_config"] = {
        "exploration": args.heuristic_exploration,
    }
    payload["online_config"] = {
        "iterations": args.online_iterations,
        "depth": args.online_depth,
    }
    payload["strategic_config"] = {
        "belief_samples": args.strategic_belief_samples,
        "rollout_plies": args.strategic_rollout_plies,
        "candidate_width": args.strategic_candidate_width,
        "node_budget": args.strategic_node_budget,
        "time_budget_seconds": args.strategic_time_budget_seconds,
        "search": "belief-sampled iterative-deepening alpha-beta",
        "backend_requested": args.strategic_search_backend,
    }
    payload["ismcts_config"] = {
        "belief_samples": args.ismcts_belief_samples,
        "iterations": args.ismcts_iterations,
        "time_budget_seconds": args.ismcts_time_budget_seconds,
        "rollout_depth": args.ismcts_rollout_depth,
        "tree_depth_limit": args.ismcts_tree_depth_limit,
        "exploration": args.ismcts_exploration,
        "progressive_widening": args.ismcts_progressive_widening,
        "tree_reuse": not args.ismcts_no_tree_reuse,
        "max_tree_nodes": args.ismcts_max_tree_nodes,
        "progressive_widening_alpha": (
            0.5 if args.ismcts_progressive_widening > 0 else 0.0
        ),
        "rollout_epsilon": args.ismcts_rollout_epsilon,
        "rollout_policy": args.ismcts_rollout_policy,
        "search": "root-belief-sampled Cython ISMCTS",
    }
    payload["agent_overrides"] = [agent_overrides[0], agent_overrides[1]]
    payload["agent_labels"] = list(agent_labels)
    payload["agent_seed_offsets"] = (
        list(agent_seed_offsets) if agent_seed_offsets is not None else None
    )
    payload["simulation_variant"] = {
        "base_hand_size": rules.opening_hand_size,
        "draw_action_enabled": rules.draw_action_enabled,
        "battle_one_starter_bonus": (
            0 if (rules.automatic_draw or rules.paid_draw_enabled) else 1
        ),
        "completion_draw_names": sorted(rules.completion_draw_names),
        "deck_sizes": [len(deck_a), len(deck_b)],
        "recycle_between_battles": rules.recycle_between_battles,
        "reshuffle_on_empty": rules.reshuffle_on_empty,
        "command_enabled": rules.command_enabled,
        "starting_command": rules.starting_command if rules.command_enabled else None,
        "battle_command_gain": (
            rules.battle_command_gain if rules.command_enabled else None
        ),
        "command_cap": rules.command_cap if rules.command_enabled else None,
        "cycle_command_cost": (
            rules.cycle_command_cost
            if rules.command_enabled and rules.cycle_enabled
            else None
        ),
        "cycle_enabled": rules.cycle_enabled,
        "automatic_draw": rules.automatic_draw,
        "paid_draw_enabled": rules.paid_draw_enabled,
        "paid_draw_command_cost": (
            rules.paid_draw_command_cost if rules.paid_draw_enabled else None
        ),
        "paid_draw_consumes_operation": rules.paid_draw_consumes_operation,
        "automatic_draw_hand_limit": rules.automatic_draw_hand_limit,
        "battle_end_hand_limit": rules.battle_end_hand_limit,
        "completion_command_refund": rules.completion_command_refund,
        "public_stratagems": rules.public_stratagems,
        "card_file": str(args.card_file),
    }

    output = resolve(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Seed: {args.seed}")
    print(f"Agents: {report.agents[0]} vs {report.agents[1]}")
    print(
        "Variant: "
        f"hand={rules.opening_hand_size} "
        f"draw={'on' if rules.draw_action_enabled else 'off'} "
        f"completion_draw_names={','.join(sorted(rules.completion_draw_names)) or 'none'} "
        f"decks={len(deck_a)}/{len(deck_b)} "
        f"recycle={'on' if rules.recycle_between_battles else 'off'} "
        f"reshuffle_on_empty={'on' if rules.reshuffle_on_empty else 'off'} "
        f"command={'on' if rules.command_enabled else 'off'} "
        f"cycle={'on' if rules.cycle_enabled else 'off'} "
        f"auto_draw={'on' if rules.automatic_draw else 'off'} "
        f"paid_draw={'on' if rules.paid_draw_enabled else 'off'} "
        f"paid_draw_operation={'yes' if rules.paid_draw_consumes_operation else 'no'} "
        f"auto_hand_limit={rules.automatic_draw_hand_limit or 'none'} "
        f"battle_hand_limit={rules.battle_end_hand_limit or 'none'} "
        f"completion_refund={rules.completion_command_refund} "
        f"stratagems={'public' if rules.public_stratagems else 'hidden'} "
        f"starter_bonus={'turn-draw' if rules.automatic_draw else ('none' if rules.paid_draw_enabled else '+1')}"
    )
    print(f"Games: {report.games}")
    print(f"Wins: P0={report.wins[0]} P1={report.wins[1]}")
    print(f"First-player win rate: {report.first_player_win_rate:.3f}")
    print(f"Mean actions: {report.mean_turns:.2f}")
    print(f"Max actions: {report.max_turns}")

    passes = report.telemetry["passes"]
    print(
        "Passes: "
        f"first-passer battle WR={passes['first_passer_battle_win_rate']}, "
        f"mean hand={passes['mean_hand_size']}"
    )

    policy_sources = report.telemetry.get("policy_sources", {})
    if policy_sources:
        print("Policy sources:")
        for source, count in sorted(policy_sources.items()):
            print(f"  {source}: {count}")

    online = report.telemetry.get("online_resolution", {})
    if online.get("decisions"):
        print(
            "Online MCCFR: "
            f"decisions={online['decisions']} "
            f"root_coverage={online['mean_root_coverage']:.3f} "
            f"belief_samples={online['mean_belief_samples']:.1f} "
            f"infosets={online['mean_information_sets']:.1f}"
        )

    most_played = sorted(
        report.telemetry["cards"].items(),
        key=lambda item: item[1]["plays"],
        reverse=True,
    )
    print("Card play diagnostics:")
    for card_id, stats in most_played:
        print(
            f"  {card_id}: draws={stats['draws']} plays={stats['plays']} "
            f"play/draw={stats['plays_per_draw']} "
            f"unplayable={stats['unplayable_turn_rate']} "
            f"dead-pass={stats['dead_on_pass_rate']} "
            f"win-played={stats['win_rate_when_played']} "
            f"swing={stats['mean_immediate_front_swing']}"
        )

    print(f"Wrote {output.relative_to(ROOT) if output.is_relative_to(ROOT) else output}")


if __name__ == "__main__":
    main()
