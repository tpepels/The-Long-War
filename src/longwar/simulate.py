from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .agents import HeuristicAgent, ISMCTSAgent, RandomAgent
from .agents.ismcts_agent import DEFAULT_ISMCTS_EXPLORATION, DEFAULT_ISMCTS_ITERATIONS
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
    game_outcomes: list[dict[str, int]]

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
    heuristic_exploration: float = 0.0,
    online_iterations: int = 8,
    online_depth: int = 2,
    priors: tuple[DeckPrior, DeckPrior] | None = None,
    strategic_belief_samples: int = 3,
    strategic_rollout_plies: int = 3,
    strategic_candidate_width: int = 8,
    strategic_node_budget: int = 20_000,
    strategic_time_budget_seconds: float | None = None,
    strategic_search_backend: str = "auto",
    ismcts_belief_samples: int = 12,
    ismcts_iterations: int = DEFAULT_ISMCTS_ITERATIONS,
    ismcts_time_budget_seconds: float | None = None,
    ismcts_rollout_depth: int = 5,
    ismcts_tree_depth_limit: int = 96,
    ismcts_exploration: float = DEFAULT_ISMCTS_EXPLORATION,
    ismcts_progressive_widening: float = 0.0,
    ismcts_reuse_tree: bool = True,
    ismcts_max_tree_nodes: int | None = None,
    ismcts_rollout_epsilon: float = 0.12,
    ismcts_rollout_policy: str = "cheap",
):
    if name == "random":
        return RandomAgent(seed)
    if name == "heuristic":
        return HeuristicAgent(seed, exploration=heuristic_exploration)
    if name == "strategic_heuristic":
        return StrategicHeuristicAgent(
            engine,
            seed,
            priors=priors,
            belief_samples=strategic_belief_samples,
            rollout_plies=strategic_rollout_plies,
            candidate_width=strategic_candidate_width,
            node_budget=strategic_node_budget,
            time_budget_seconds=strategic_time_budget_seconds,
            search_backend=strategic_search_backend,
        )
    if name == "ismcts":
        return ISMCTSAgent(
            engine,
            seed,
            priors=priors,
            belief_samples=ismcts_belief_samples,
            iterations=ismcts_iterations,
            time_budget_seconds=ismcts_time_budget_seconds,
            rollout_depth=ismcts_rollout_depth,
            tree_depth_limit=ismcts_tree_depth_limit,
            exploration=ismcts_exploration,
            progressive_widening=ismcts_progressive_widening,
            reuse_tree=ismcts_reuse_tree,
            max_tree_nodes=ismcts_max_tree_nodes,
            rollout_epsilon=ismcts_rollout_epsilon,
            rollout_policy=ismcts_rollout_policy,
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
    heuristic_exploration: float = 0.0,
    online_iterations: int = 8,
    online_depth: int = 2,
    strategic_belief_samples: int = 3,
    strategic_rollout_plies: int = 3,
    strategic_candidate_width: int = 8,
    strategic_node_budget: int = 20_000,
    strategic_time_budget_seconds: float | None = None,
    strategic_search_backend: str = "auto",
    ismcts_belief_samples: int = 12,
    ismcts_iterations: int = DEFAULT_ISMCTS_ITERATIONS,
    ismcts_time_budget_seconds: float | None = None,
    ismcts_rollout_depth: int = 5,
    ismcts_tree_depth_limit: int = 96,
    ismcts_exploration: float = DEFAULT_ISMCTS_EXPLORATION,
    ismcts_progressive_widening: float = 0.0,
    ismcts_reuse_tree: bool = True,
    ismcts_max_tree_nodes: int | None = None,
    ismcts_rollout_epsilon: float = 0.12,
    ismcts_rollout_policy: str = "cheap",
    agent_overrides: tuple[dict[str, Any] | None, dict[str, Any] | None] = (None, None),
    agent_labels: tuple[str, str] | None = None,
    agent_seed_offsets: tuple[int, int] | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> SimulationReport:
    if games <= 0:
        raise ValueError("games must be positive")

    wins = [0, 0]
    first_player_wins = 0
    total_turns = 0
    maximum_turns = 0
    game_outcomes: list[dict[str, int]] = []
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
    labels = agent_labels or agent_names
    if agent_seed_offsets is not None and len(agent_seed_offsets) != 2:
        raise ValueError("agent_seed_offsets must contain exactly two entries")
    if len(agent_overrides) != 2:
        raise ValueError("agent_overrides must contain exactly two entries")
    base_agent_options: dict[str, Any] = {
        "heuristic_exploration": heuristic_exploration,
        "online_iterations": online_iterations,
        "online_depth": online_depth,
        "strategic_belief_samples": strategic_belief_samples,
        "strategic_rollout_plies": strategic_rollout_plies,
        "strategic_candidate_width": strategic_candidate_width,
        "strategic_node_budget": strategic_node_budget,
        "strategic_time_budget_seconds": strategic_time_budget_seconds,
        "strategic_search_backend": strategic_search_backend,
        "ismcts_belief_samples": ismcts_belief_samples,
        "ismcts_iterations": ismcts_iterations,
        "ismcts_time_budget_seconds": ismcts_time_budget_seconds,
        "ismcts_rollout_depth": ismcts_rollout_depth,
        "ismcts_tree_depth_limit": ismcts_tree_depth_limit,
        "ismcts_exploration": ismcts_exploration,
        "ismcts_progressive_widening": ismcts_progressive_widening,
        "ismcts_reuse_tree": ismcts_reuse_tree,
        "ismcts_max_tree_nodes": ismcts_max_tree_nodes,
        "ismcts_rollout_epsilon": ismcts_rollout_epsilon,
        "ismcts_rollout_policy": ismcts_rollout_policy,
    }

    for game_index in range(games):
        first_player = game_index % 2
        preview = engine.new_game(
            deck_a,
            deck_b,
            seed=seed + game_index,
            first_player=first_player,
            opening_bonus=False,
        )
        agents = []
        for player in range(2):
            options = dict(base_agent_options)
            override = agent_overrides[player]
            if override is not None:
                if not isinstance(override, dict):
                    raise TypeError("agent override must be a dict or None")
                options.update(override)
            agents.append(
                make_agent(
                    agent_names[player],
                    engine,
                    (
                        seed * 10_000 + game_index * 2 + player + 1
                        if agent_seed_offsets is None
                        else seed * 10_000 + game_index * 100 + agent_seed_offsets[player]
                    ),
                    policy=agent_policies[player],
                    priors=priors,
                    **options,
                )
            )
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
                decision_info["agent"] = labels[actor]

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
        game_outcomes.append({
            "seed": seed + game_index,
            "first_player": first_player,
            "winner": winner,
        })
        wins[winner] += 1
        if winner == first_player:
            first_player_wins += 1
        total_turns += action_count
        maximum_turns = max(maximum_turns, action_count)
        if progress_callback is not None:
            progress_callback(game_index + 1, games)

    telemetry_summary = telemetry.summary()
    telemetry_summary["human_flow"] = human_flow.summary()
    return SimulationReport(
        games=games,
        agents=labels,
        wins=(wins[0], wins[1]),
        first_player_wins=first_player_wins,
        mean_turns=total_turns / games,
        max_turns=maximum_turns,
        telemetry=telemetry_summary,
        game_outcomes=game_outcomes,
    )
