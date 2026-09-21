from __future__ import annotations

from dataclasses import dataclass

from .agents import RandomAgent
from .game.engine import GameEngine
from .game.model import Phase


@dataclass(frozen=True)
class SimulationReport:
    games: int
    wins: tuple[int, int]
    first_player_wins: int
    mean_turns: float
    max_turns: int

    @property
    def win_rates(self) -> tuple[float, float]:
        return tuple(win / self.games for win in self.wins)  # type: ignore[return-value]

    @property
    def first_player_win_rate(self) -> float:
        return self.first_player_wins / self.games


def simulate_games(
    engine: GameEngine,
    deck_a: list[str],
    deck_b: list[str],
    *,
    games: int,
    seed: int = 0,
    max_actions: int = 500,
) -> SimulationReport:
    if games <= 0:
        raise ValueError("games must be positive")

    wins = [0, 0]
    first_player_wins = 0
    total_turns = 0
    maximum_turns = 0

    for game_index in range(games):
        first_player = game_index % 2
        state = engine.new_game(
            deck_a,
            deck_b,
            seed=seed + game_index,
            first_player=first_player,
        )
        agents = [
            RandomAgent(seed * 10_000 + game_index * 2 + 1),
            RandomAgent(seed * 10_000 + game_index * 2 + 2),
        ]

        action_count = 0
        while state.phase is not Phase.COMPLETE:
            if action_count >= max_actions:
                raise RuntimeError(
                    f"Simulation exceeded {max_actions} actions in game {game_index}"
                )
            actor = state.active_player
            action = agents[actor].choose(engine, state)
            engine.apply(state, action)
            action_count += 1

        winner = state.winner
        if winner is None:
            raise RuntimeError("Completed game has no winner")

        wins[winner] += 1
        if winner == first_player:
            first_player_wins += 1
        total_turns += action_count
        maximum_turns = max(maximum_turns, action_count)

    return SimulationReport(
        games=games,
        wins=(wins[0], wins[1]),
        first_player_wins=first_player_wins,
        mean_turns=total_turns / games,
        max_turns=maximum_turns,
    )
