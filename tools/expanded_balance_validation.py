from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from longwar.cards import load_card_file
from longwar.game import canonical_game_engine
from longwar.simulate import simulate_games

ROOT = Path(__file__).resolve().parents[1]
DECKS = {
    "avaros": ROOT / "decks" / "avaros-line.json",
    "mara": ROOT / "decks" / "mara-rear.json",
    "sera": ROOT / "decks" / "sera-support.json",
}


def load_deck(path: Path) -> list[str]:
    return list(json.loads(path.read_text(encoding="utf-8"))["cards"])


def main() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    engine = canonical_game_engine(data)
    decks = {name: load_deck(path) for name, path in DECKS.items()}
    games = 2000
    seed = 26092400
    results: dict[str, object] = {"games_per_direction": games, "mirrors": {}, "pairs": {}}

    for index, name in enumerate(decks):
        report = simulate_games(
            engine, decks[name], decks[name], games=games,
            seed=seed + index * 10000,
            agent_names=("heuristic", "heuristic"),
        )
        results["mirrors"][name] = {
            "first_player_win_rate": report.first_player_win_rate,
            "wins": list(report.wins),
            "mean_turns": report.mean_turns,
        }
        print("MIRROR", name, results["mirrors"][name])

    names = list(decks)
    pair_index = 0
    for a_index in range(len(names)):
        for b_index in range(a_index + 1, len(names)):
            a, b = names[a_index], names[b_index]
            ab = simulate_games(
                engine, decks[a], decks[b], games=games,
                seed=seed + 50000 + pair_index * 20000,
                agent_names=("heuristic", "heuristic"),
            )
            ba = simulate_games(
                engine, decks[b], decks[a], games=games,
                seed=seed + 60000 + pair_index * 20000,
                agent_names=("heuristic", "heuristic"),
            )
            a_wins = ab.wins[0] + ba.wins[1]
            total = games * 2
            row = {
                "a": a,
                "b": b,
                "a_win_rate": a_wins / total,
                "b_win_rate": 1.0 - a_wins / total,
                "a_as_p0": ab.wins[0] / games,
                "a_as_p1": ba.wins[1] / games,
                "first_player_ab": ab.first_player_win_rate,
                "first_player_ba": ba.first_player_win_rate,
            }
            results["pairs"][f"{a}_vs_{b}"] = row
            print("PAIR", row)
            pair_index += 1

    output = ROOT / "artifacts" / "expanded-archetype-round-robin.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print("WROTE", output)


if __name__ == "__main__":
    main()
