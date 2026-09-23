from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .agents import HeuristicAgent, RandomAgent
from .agents.strategic_heuristic_agent import StrategicHeuristicAgent
from .agents.online_mccfr_agent import OnlineMCCFRAgent
from .belief import DeckHypothesis, DeckPrior, HypothesisDeckPrior
from .agents.mccfr_agent import MCCFRAgent
from .game.engine import GameEngine
from .game.model import Phase
from .human_flow import HumanFlowDiagnostics
from .telemetry import Telemetry


@dataclass(frozen=True)
class SimulationReport:
    games: int
    agents: tuple[str, str]
    wins: tuple[int, int]
    first_player_wins: int
    mean_turns: float
    max_turns: int
    telemetry: dict[str, Any]

    @property
    def win_rates(self) -> tuple[float, float]:
        return tuple(win / self.games for win in self.wins)  # type: ignore[return-value]

    @property
    def first_player_win_rate(self) -> float:
        return self.first_player_wins / self.games


def make_agent(
    name: str,
    engine: GameEngine,
    seed: int,
    *,
    policy: dict[str, Any] | None = None,
    online_iterations: int = 8,
    online_depth: int = 2,
    priors: tuple[DeckPrior, DeckPrior] | None = None,
    strategic_belief_samples: int = 3,
    strategic_rollout_plies: int = 3,
    strategic_candidate_width: int = 8,
):
    if name == "random":
        return RandomAgent(seed)
    if name == "heuristic":
        return HeuristicAgent(seed)
    if name == "strategic_heuristic":
        return StrategicHeuristicAgent(
            engine,
            seed,
            priors=priors,
            belief_samples=strategic_belief_samples,
            rollout_plies=strategic_rollout_plies,
            candidate_width=strategic_candidate_width,
        )
    if name == "mccfr":
        if policy is None:
            raise ValueError("MCCFR agent requires an exported policy")
        return MCCFRAgent(seed, policy)
    if name == "online_mccfr":
        return OnlineMCCFRAgent(
            engine,
            seed,
            iterations=online_iterations,
            max_depth=online_depth,
        )
    raise ValueError(f"Unknown agent: {name}")


def simulate_games(
    engine: GameEngine,
    deck_a: list[str],
    deck_b: list[str],
    *,
    games: int,
    seed: int = 0,
    max_actions: int = 500,
    agent_names: tuple[str, str] = ("heuristic", "heuristic"),
    agent_policies: tuple[dict[str, Any] | None, dict[str, Any] | None] = (None, None),
    online_iterations: int = 8,
    online_depth: int = 2,
    strategic_belief_samples: int = 3,
    strategic_rollout_plies: int = 3,
    strategic_candidate_width: int = 8,
) -> SimulationReport:
    if games <= 0:
        raise ValueError("games must be positive")

    wins = [0, 0]
    first_player_wins = 0
    total_turns = 0
    maximum_turns = 0
    telemetry = Telemetry()
    human_flow = HumanFlowDiagnostics()
    priors: tuple[DeckPrior, DeckPrior] = (
        HypothesisDeckPrior(
            engine,
            [DeckHypothesis(tuple(deck_a), label="deck-a")],
        ),
        HypothesisDeckPrior(
            engine,
            [DeckHypothesis(tuple(deck_b), label="deck-b")],
        ),
    )

    for game_index in range(games):
        first_player = game_index % 2
        preview = engine.new_game(
            deck_a,
            deck_b,
            seed=seed + game_index,
            first_player=first_player,
            opening_bonus=False,
        )
        agents = [
            make_agent(
                agent_names[0],
                engine,
                seed * 10_000 + game_index * 2 + 1,
                policy=agent_policies[0],
                online_iterations=online_iterations,
                online_depth=online_depth,
                priors=priors,
                strategic_belief_samples=strategic_belief_samples,
                strategic_rollout_plies=strategic_rollout_plies,
                strategic_candidate_width=strategic_candidate_width,
            ),
            make_agent(
                agent_names[1],
                engine,
                seed * 10_000 + game_index * 2 + 2,
                policy=agent_policies[1],
                online_iterations=online_iterations,
                online_depth=online_depth,
                priors=priors,
                strategic_belief_samples=strategic_belief_samples,
                strategic_rollout_plies=strategic_rollout_plies,
                strategic_candidate_width=strategic_candidate_width,
            ),
        ]
        mulligan_indices = tuple(
            agent.choose_mulligan(engine, preview.players[player].hand)
            if hasattr(agent, "choose_mulligan")
            else ()
            for player, agent in enumerate(agents)
        )
        state = engine.new_game(
            deck_a,
            deck_b,
            seed=seed + game_index,
            first_player=first_player,
            mulligan_indices=mulligan_indices,
        )
        telemetry.start_game(state)
        human_flow.start_game(engine, state)

        action_count = 0
        while state.phase is not Phase.COMPLETE:
            if action_count >= max_actions:
                raise RuntimeError(
                    f"Simulation exceeded {max_actions} actions in game {game_index}"
                )

            actor = state.active_player
            agent = agents[actor]
            action = agent.choose(engine, state)

            decision_info = getattr(agent, "last_decision", None)
            if decision_info is not None:
                decision_info = dict(decision_info)
                decision_info["agent"] = agent_names[actor]

            human_flow.before_action(engine, state, actor, action)
            before = telemetry.before_action(
                engine,
                state,
                actor,
                action,
                decision_info,
            )
            engine.apply(state, action)
            telemetry.after_action(engine, before, state, actor, action)
            human_flow.after_action(engine, before, state, actor, action)
            action_count += 1

        winner = state.winner
        if winner is None:
            raise RuntimeError("Completed game has no winner")

        telemetry.finish_game(winner)
        wins[winner] += 1
        if winner == first_player:
            first_player_wins += 1
        total_turns += action_count
        maximum_turns = max(maximum_turns, action_count)

    telemetry_summary = telemetry.summary()
    telemetry_summary["human_flow"] = human_flow.summary()
    return SimulationReport(
        games=games,
        agents=agent_names,
        wins=(wins[0], wins[1]),
        first_player_wins=first_player_wins,
        mean_turns=total_turns / games,
        max_turns=maximum_turns,
        telemetry=telemetry_summary,
    )
