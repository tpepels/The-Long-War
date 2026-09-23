from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from longwar.cards import load_card_file
from longwar.game import GameEngine
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=1701)
    choices = ["heuristic", "strategic_heuristic", "random", "mccfr", "online_mccfr"]
    parser.add_argument("--agent-a", choices=choices, default="heuristic")
    parser.add_argument("--agent-b", choices=choices, default="heuristic")
    parser.add_argument("--policy-a", type=Path)
    parser.add_argument("--policy-b", type=Path)
    parser.add_argument("--online-iterations", type=int, default=8)
    parser.add_argument("--online-depth", type=int, default=2)
    parser.add_argument("--strategic-belief-samples", type=int, default=3)
    parser.add_argument("--strategic-rollout-plies", type=int, default=3)
    parser.add_argument("--strategic-candidate-width", type=int, default=8)
    parser.add_argument(
        "--hand-size",
        type=int,
        default=10,
        help="Base opening and between-Battle refill hand target.",
    )
    parser.add_argument(
        "--deck-size",
        type=int,
        default=30,
        help="Required deck size for this simulation variant.",
    )
    deck_mode = parser.add_mutually_exclusive_group()
    deck_mode.add_argument(
        "--between-battle-recycle",
        action="store_true",
        help="Legacy variant: reshuffle all non-hand cards between Battles.",
    )
    deck_mode.add_argument(
        "--no-between-battle-recycle",
        action="store_true",
        help="Explicitly keep the canonical persistent draw pile between Battles.",
    )
    reshuffle_mode = parser.add_mutually_exclusive_group()
    reshuffle_mode.add_argument(
        "--reshuffle-on-empty",
        action="store_true",
        help="Explicitly use the canonical discard reshuffle when the deck empties.",
    )
    reshuffle_mode.add_argument(
        "--no-reshuffle-on-empty",
        action="store_true",
        help="Experiment variant: allow the persistent draw pile to exhaust.",
    )
    draw_mode = parser.add_mutually_exclusive_group()
    draw_mode.add_argument(
        "--enable-draw",
        action="store_true",
        help="Legacy variant: enable the once-per-Battle generic Draw action.",
    )
    draw_mode.add_argument(
        "--disable-draw",
        action="store_true",
        help="Explicitly use the canonical no-generic-Draw rules.",
    )
    parser.add_argument(
        "--completion-draw-names",
        nargs="*",
        default=[],
        help="Name ids that draw 1 when their formation becomes complete.",
    )
    command_mode = parser.add_mutually_exclusive_group()
    command_mode.add_argument(
        "--command",
        action="store_true",
        help="Explicitly enable the canonical Command economy.",
    )
    command_mode.add_argument(
        "--no-command",
        action="store_true",
        help="Legacy variant: disable Command and Cycle.",
    )
    parser.add_argument("--starting-command", type=int, default=20)
    parser.add_argument("--battle-command-gain", type=int, default=10)
    parser.add_argument("--command-cap", type=int, default=20)
    parser.add_argument("--cycle-command-cost", type=int, default=1)
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
    args = parser.parse_args()

    card_data = load_card_file(ROOT / "cards" / "cards.json")
    engine = GameEngine(
        card_data,
        opening_hand_size=args.hand_size,
        draw_action_enabled=args.enable_draw and not args.disable_draw,
        completion_draw_names=args.completion_draw_names,
        deck_size=args.deck_size,
        recycle_between_battles=args.between_battle_recycle and not args.no_between_battle_recycle,
        command_enabled=not args.no_command,
        starting_command=args.starting_command,
        battle_command_gain=args.battle_command_gain,
        command_cap=args.command_cap,
        cycle_command_cost=args.cycle_command_cost,
        reshuffle_on_empty=not args.no_reshuffle_on_empty,
    )
    deck_a = load_deck(args.deck_a)
    deck_b = load_deck(args.deck_b)
    policies = (load_policy(args.policy_a), load_policy(args.policy_b))
    game_fingerprint = current_game_fingerprint()
    for policy in policies:
        if policy is not None and policy.get("game_fingerprint") != game_fingerprint:
            raise SystemExit("MCCFR policy belongs to an older ruleset; retrain it before simulation")

    report = simulate_games(
        engine,
        deck_a,
        deck_b,
        games=args.games,
        seed=args.seed,
        agent_names=(args.agent_a, args.agent_b),
        agent_policies=policies,
        online_iterations=args.online_iterations,
        online_depth=args.online_depth,
        strategic_belief_samples=args.strategic_belief_samples,
        strategic_rollout_plies=args.strategic_rollout_plies,
        strategic_candidate_width=args.strategic_candidate_width,
    )

    payload = asdict(report)
    payload["game_fingerprint"] = game_fingerprint
    payload["seed"] = args.seed
    payload["win_rates"] = report.win_rates
    payload["first_player_win_rate"] = report.first_player_win_rate
    payload["online_config"] = {
        "iterations": args.online_iterations,
        "depth": args.online_depth,
    }
    payload["strategic_config"] = {
        "belief_samples": args.strategic_belief_samples,
        "rollout_plies": args.strategic_rollout_plies,
        "candidate_width": args.strategic_candidate_width,
    }
    payload["simulation_variant"] = {
        "base_hand_size": args.hand_size,
        "draw_action_enabled": args.enable_draw and not args.disable_draw,
        "battle_one_starter_bonus": 1,
        "completion_draw_names": sorted(args.completion_draw_names),
        "deck_size": args.deck_size,
        "recycle_between_battles": args.between_battle_recycle and not args.no_between_battle_recycle,
        "reshuffle_on_empty": not args.no_reshuffle_on_empty,
        "command_enabled": not args.no_command,
        "starting_command": args.starting_command if not args.no_command else None,
        "battle_command_gain": args.battle_command_gain if not args.no_command else None,
        "command_cap": args.command_cap if not args.no_command else None,
        "cycle_command_cost": args.cycle_command_cost if not args.no_command else None,
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
        f"hand={args.hand_size} "
        f"draw={'on' if args.enable_draw and not args.disable_draw else 'off'} "
        f"completion_draw_names={','.join(sorted(args.completion_draw_names)) or 'none'} "
        f"deck={args.deck_size} "
        f"recycle={'on' if args.between_battle_recycle and not args.no_between_battle_recycle else 'off'} "
        f"reshuffle_on_empty={'off' if args.no_reshuffle_on_empty else 'on'} "
        f"command={'off' if args.no_command else 'on'} "
        "starter_bonus=+1"
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

    print(f"Wrote {output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
