from __future__ import annotations

import json
from pathlib import Path

from longwar.agents.heuristic_agent import HeuristicAgent
from longwar.cards import load_card_file
from longwar.game import GameEngine
from longwar.game.actions import ChooseFirst
from longwar.game.model import Phase
from longwar.health import wilson_interval

ROOT = Path(__file__).resolve().parents[1]


def run_variant(mode: str, games: int, seed: int) -> tuple[int, float, tuple[float|None,float|None]]:
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads((ROOT / "decks" / "reference.json").read_text())["cards"]
    engine = GameEngine(data)
    first_wins = 0

    for game_index in range(games):
        first_player = game_index % 2
        state = engine.new_game(
            deck,
            deck,
            seed=seed + game_index,
            first_player=first_player,
        )
        if mode in {"opening_bonus", "battle_starter_bonus"}:
            engine._draw(state, first_player, 1)

        agents = [
            HeuristicAgent(seed * 100000 + game_index * 2 + 1),
            HeuristicAgent(seed * 100000 + game_index * 2 + 2),
        ]

        while state.phase is not Phase.COMPLETE:
            actor = state.active_player
            action = agents[actor].choose(engine, state)
            is_later_start = (
                mode == "battle_starter_bonus"
                and isinstance(action, ChooseFirst)
            )
            engine.apply(state, action)
            if is_later_start and state.phase is Phase.BATTLE:
                engine._draw(state, action.player, 1)

        if state.winner == first_player:
            first_wins += 1

    rate = first_wins / games
    return first_wins, rate, wilson_interval(first_wins, games)


def main() -> None:
    games = 5000
    for index, mode in enumerate(("control", "opening_bonus", "battle_starter_bonus")):
        wins, rate, ci = run_variant(mode, games, 26092300 + index * 100000)
        print(mode, "wins", wins, "rate", round(rate, 5), "ci95", tuple(round(v,5) for v in ci))


if __name__ == "__main__":
    main()
