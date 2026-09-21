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
        "--deck-a",
        type=Path,
        default=ROOT / "decks" / "reference.json",
    )
    parser.add_argument(
        "--deck-b",
        type=Path,
        default=ROOT / "decks" / "reference.json",
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
    )

    payload = asdict(report)
    payload["win_rates"] = report.win_rates
    payload["first_player_win_rate"] = report.first_player_win_rate

    output = ROOT / "artifacts" / "simulation-report.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"Games: {report.games}")
    print(f"Wins: P0={report.wins[0]} P1={report.wins[1]}")
    print(f"First-player win rate: {report.first_player_win_rate:.3f}")
    print(f"Mean actions: {report.mean_turns:.2f}")
    print(f"Max actions: {report.max_turns}")
    print(f"Wrote {output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
