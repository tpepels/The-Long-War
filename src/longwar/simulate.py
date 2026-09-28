from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
import ctypes
import gc
import sys
from typing import Any, Callable

from .agents import HeuristicAgent, ISMCTSAgent, RandomAgent
from .agents.ismcts_agent import (
    DEFAULT_ISMCTS_BELIEF_SAMPLES,
    DEFAULT_ISMCTS_EXPLORATION,
    DEFAULT_ISMCTS_ITERATIONS,
    DEFAULT_ISMCTS_MAX_TREE_NODES,
    DEFAULT_ISMCTS_PROGRESSIVE_WIDENING,
    DEFAULT_ISMCTS_REUSE_TREE,
    DEFAULT_ISMCTS_ROLLOUT_DEPTH,
    DEFAULT_ISMCTS_ROLLOUT_EPSILON,
    DEFAULT_ISMCTS_ROLLOUT_POLICY,
)
from .agents.strategic_heuristic_agent import StrategicHeuristicAgent
from .agents.online_mccfr_agent import OnlineMCCFRAgent
from .belief import DeckHypothesis, DeckPrior, HypothesisDeckPrior
from .agents.mccfr_agent import MCCFRAgent
from .game.engine import GameEngine
from .game.model import Phase
from .human_flow import HumanFlowDiagnostics
from .telemetry import Telemetry


def _release_process_memory() -> None:
    """Promptly return dead simulation/search memory to the OS when possible."""
    gc.collect()
    if not sys.platform.startswith("linux"):
        return
    try:
        libc = ctypes.CDLL(None)
        malloc_trim = getattr(libc, "malloc_trim", None)
        if malloc_trim is not None:
            malloc_trim(0)
    except (AttributeError, OSError):
        pass


def _release_agent_search_memory(agent: object) -> None:
    """Drop persistent per-game search state before discarding an agent."""
    release = getattr(agent, "release_search_memory", None)
    if callable(release):
        release()



@dataclass(frozen=True)
class SimulationReport:
    games: int
    agents: tuple[str, str]
    wins: tuple[int, int]
    censored_games: int
    first_player_wins: int
    mean_turns: float
    max_turns: int
    telemetry: dict[str, Any]
    game_outcomes: list[dict[str, int | bool | None]]

    @property
    def decisive_games(self) -> int:
        return self.games - self.censored_games

    @property
    def win_rates(self) -> tuple[float, float]:
        denominator = self.decisive_games
        if denominator <= 0:
            return (0.0, 0.0)
        return tuple(win / denominator for win in self.wins)  # type: ignore[return-value]

    @property
    def censor_rate(self) -> float:
        return self.censored_games / self.games

    @property
    def first_player_win_rate(self) -> float:
        denominator = self.decisive_games
        return self.first_player_wins / denominator if denominator > 0 else 0.0


@dataclass
class _RawSimulationResult:
    game_index_start: int
    report: SimulationReport
    telemetry: Telemetry
    human_flow: HumanFlowDiagnostics


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
    ismcts_belief_samples: int = DEFAULT_ISMCTS_BELIEF_SAMPLES,
    ismcts_iterations: int = DEFAULT_ISMCTS_ITERATIONS,
    ismcts_time_budget_seconds: float | None = None,
    ismcts_rollout_depth: int = DEFAULT_ISMCTS_ROLLOUT_DEPTH,
    ismcts_tree_depth_limit: int = 96,
    ismcts_exploration: float = DEFAULT_ISMCTS_EXPLORATION,
    ismcts_progressive_widening: float = DEFAULT_ISMCTS_PROGRESSIVE_WIDENING,
    ismcts_reuse_tree: bool = DEFAULT_ISMCTS_REUSE_TREE,
    ismcts_max_tree_nodes: int | None = DEFAULT_ISMCTS_MAX_TREE_NODES,
    ismcts_rollout_epsilon: float = DEFAULT_ISMCTS_ROLLOUT_EPSILON,
    ismcts_rollout_policy: str = DEFAULT_ISMCTS_ROLLOUT_POLICY,
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


def _simulate_games_serial(
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
    ismcts_belief_samples: int = DEFAULT_ISMCTS_BELIEF_SAMPLES,
    ismcts_iterations: int = DEFAULT_ISMCTS_ITERATIONS,
    ismcts_time_budget_seconds: float | None = None,
    ismcts_rollout_depth: int = DEFAULT_ISMCTS_ROLLOUT_DEPTH,
    ismcts_tree_depth_limit: int = 96,
    ismcts_exploration: float = DEFAULT_ISMCTS_EXPLORATION,
    ismcts_progressive_widening: float = DEFAULT_ISMCTS_PROGRESSIVE_WIDENING,
    ismcts_reuse_tree: bool = DEFAULT_ISMCTS_REUSE_TREE,
    ismcts_max_tree_nodes: int | None = DEFAULT_ISMCTS_MAX_TREE_NODES,
    ismcts_rollout_epsilon: float = DEFAULT_ISMCTS_ROLLOUT_EPSILON,
    ismcts_rollout_policy: str = DEFAULT_ISMCTS_ROLLOUT_POLICY,
    agent_overrides: tuple[dict[str, Any] | None, dict[str, Any] | None] = (None, None),
    agent_labels: tuple[str, str] | None = None,
    agent_seed_offsets: tuple[int, int] | None = None,
    progress_callback: Callable[[int, int, tuple[int, int]], None] | None = None,
    game_index_start: int = 0,
    _return_raw: bool = False,
) -> SimulationReport | _RawSimulationResult:
    if games <= 0:
        raise ValueError("games must be positive")

    wins = [0, 0]
    censored_games = 0
    first_player_wins = 0
    total_turns = 0
    maximum_turns = 0
    game_outcomes: list[dict[str, int | bool | None]] = []
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
        global_game_index = game_index_start + game_index
        first_player = global_game_index % 2
        preview = engine.new_game(
            deck_a,
            deck_b,
            seed=seed + global_game_index,
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
                        seed * 10_000 + global_game_index * 2 + player + 1
                        if agent_seed_offsets is None
                        else seed * 10_000 + global_game_index * 100 + agent_seed_offsets[player]
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
            seed=seed + global_game_index,
            first_player=first_player,
            mulligan_indices=mulligan_indices,
        )
        telemetry.start_game(state, engine)
        human_flow.start_game(engine, state)

        action_count = 0
        censored = False
        while state.phase is not Phase.COMPLETE:
            if action_count >= max_actions:
                censored = True
                break

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

            # Search creates large short-lived belief states, packed states,
            # and native scratch allocations. Reclaim dead objects after each
            # move without clearing an ISMCTS tree that is intentionally
            # reused within the same game.
            del decision_info, before, action, agent
            _release_process_memory()

        winner = None if censored else state.winner
        if not censored and winner is None:
            raise RuntimeError("Completed game has no winner")

        telemetry.finish_game(winner, state)
        game_outcomes.append({
            "seed": seed + global_game_index,
            "first_player": first_player,
            "winner": winner,
            "censored": censored,
        })
        if censored:
            censored_games += 1
        else:
            wins[winner] += 1
            if winner == first_player:
                first_player_wins += 1
        total_turns += action_count
        maximum_turns = max(maximum_turns, action_count)
        if progress_callback is not None:
            progress_callback(game_index + 1, games, (wins[0], wins[1]))

        # No search state is useful across games. Explicitly release native
        # trees/tables before dropping the agents, then trim allocator caches.
        for finished_agent in agents:
            _release_agent_search_memory(finished_agent)
        del agents, state, preview
        _release_process_memory()

    telemetry_summary = telemetry.summary()
    _release_process_memory()
    telemetry_summary["human_flow"] = human_flow.summary()
    report = SimulationReport(
        games=games,
        agents=labels,
        wins=(wins[0], wins[1]),
        censored_games=censored_games,
        first_player_wins=first_player_wins,
        mean_turns=total_turns / games,
        max_turns=maximum_turns,
        telemetry=telemetry_summary,
        game_outcomes=game_outcomes,
    )
    if _return_raw:
        return _RawSimulationResult(
            game_index_start=game_index_start,
            report=report,
            telemetry=telemetry,
            human_flow=human_flow,
        )
    return report



def _simulate_games_worker(
    card_data: dict[str, Any],
    rules,
    deck_a: list[str],
    deck_b: list[str],
    seed: int,
    game_index: int,
    options: dict[str, Any],
) -> _RawSimulationResult:
    engine = GameEngine(card_data, rules=rules)
    result = _simulate_games_serial(
        engine,
        deck_a,
        deck_b,
        games=1,
        seed=seed,
        game_index_start=game_index,
        _return_raw=True,
        **options,
    )
    assert isinstance(result, _RawSimulationResult)
    return result


def simulate_games(
    engine: GameEngine,
    deck_a: list[str],
    deck_b: list[str],
    *,
    games: int,
    seed: int = 0,
    jobs: int = 1,
    progress_callback: Callable[[int, int, tuple[int, int]], None] | None = None,
    **options: Any,
) -> SimulationReport:
    """Simulate matches, using independent worker processes when requested."""
    if jobs <= 0:
        raise ValueError("jobs must be positive")
    if jobs == 1 or games == 1:
        result = _simulate_games_serial(
            engine,
            deck_a,
            deck_b,
            games=games,
            seed=seed,
            progress_callback=progress_callback,
            **options,
        )
        assert isinstance(result, SimulationReport)
        return result

    worker_count = min(jobs, games)
    worker_options = dict(options)
    worker_options.pop("progress_callback", None)
    results: list[_RawSimulationResult] = []
    completed = 0
    live_wins = [0, 0]
    with ProcessPoolExecutor(max_workers=worker_count) as pool:
        futures = [
            pool.submit(
                _simulate_games_worker,
                engine.card_data,
                engine.rules,
                deck_a,
                deck_b,
                seed,
                game_index,
                worker_options,
            )
            for game_index in range(games)
        ]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            live_wins[0] += result.report.wins[0]
            live_wins[1] += result.report.wins[1]
            completed += 1
            if progress_callback is not None:
                progress_callback(completed, games, (live_wins[0], live_wins[1]))

    results.sort(key=lambda item: item.game_index_start)
    telemetry = Telemetry()
    human_flow = HumanFlowDiagnostics()
    wins = [0, 0]
    censored_games = 0
    first_player_wins = 0
    total_turns = 0.0
    maximum_turns = 0
    game_outcomes: list[dict[str, int | bool | None]] = []
    agents = results[0].report.agents

    for result in results:
        report = result.report
        telemetry.merge(result.telemetry)
        human_flow.merge(result.human_flow)
        wins[0] += report.wins[0]
        wins[1] += report.wins[1]
        censored_games += report.censored_games
        first_player_wins += report.first_player_wins
        total_turns += report.mean_turns * report.games
        maximum_turns = max(maximum_turns, report.max_turns)
        game_outcomes.extend(report.game_outcomes)

    telemetry_summary = telemetry.summary()
    telemetry_summary["human_flow"] = human_flow.summary()
    return SimulationReport(
        games=games,
        agents=agents,
        wins=(wins[0], wins[1]),
        censored_games=censored_games,
        first_player_wins=first_player_wins,
        mean_turns=total_turns / games,
        max_turns=maximum_turns,
        telemetry=telemetry_summary,
        game_outcomes=game_outcomes,
    )
