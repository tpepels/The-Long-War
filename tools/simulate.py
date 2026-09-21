from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from longwar.cards import load_card_file
from longwar.game import GameEngine
from longwar.simulate import simulate_games

ROOT = Path(__file__).resolve().parents[1]


def load_deck(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data["cards"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=1701)
    parser.add_argument(
        "--agent-a",
        choices=["heuristic", "random"],
        default="heuristic",
    )
    parser.add_argument(
        "--agent-b",
        choices=["heuristic", "random"],
        default="heuristic",
    )
    parser.add_argument(
        "--deck-a",
        type=Path,
        default=ROOT / "decks" / "reference.json",
    )
    parser.add_argument(
        "--deck-b",
        type=Path,
        default=ROOT / "decks" / "reference.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts" / "simulation-report.json",
    )
    args = parser.parse_args()

    card_data = load_card_file(ROOT / "cards" / "cards.json")
    engine = GameEngine(card_data)
    deck_a = load_deck(args.deck_a)
    deck_b = load_deck(args.deck_b)

    report = simulate_games(
        engine,
        deck_a,
        deck_b,
        games=args.games,
        seed=args.seed,
        agent_names=(args.agent_a, args.agent_b),
    )

    payload = asdict(report)
    payload["win_rates"] = report.win_rates
    payload["first_player_win_rate"] = report.first_player_win_rate

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Agents: {report.agents[0]} vs {report.agents[1]}")
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

    most_played = sorted(
        report.telemetry["cards"].items(),
        key=lambda item: item[1]["plays"],
        reverse=True,
    )[:5]
    print("Most played cards:")
    for card_id, stats in most_played:
        print(
            f"  {card_id}: plays={stats['plays']} "
            f"dead-pass={stats['dead_on_pass_rate']} "
            f"swing={stats['mean_immediate_front_swing']}"
        )

    print(f"Wrote {args.output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
