from __future__ import annotations

from collections import Counter, deque
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
import ctypes
import gc
import sys
import traceback
from typing import Any, Callable

from .agents.heuristic_agent import HeuristicAgent
from .agents.ismcts_agent import (
    DEFAULT_ISMCTS_BELIEF_SAMPLES,
    DEFAULT_ISMCTS_EXPLORATION,
    DEFAULT_ISMCTS_ITERATIONS,
    DEFAULT_ISMCTS_MAX_TREE_NODES,
    DEFAULT_ISMCTS_PROGRESSIVE_WIDENING,
    DEFAULT_ISMCTS_PROGRESSIVE_WIDENING_ALPHA,
    DEFAULT_ISMCTS_REUSE_TREE,
    DEFAULT_ISMCTS_ROLLOUT_DEPTH,
    DEFAULT_ISMCTS_POST_BATTLE_ROLLOUT_DEPTH,
    DEFAULT_ISMCTS_ROLLOUT_EPSILON,
    DEFAULT_ISMCTS_ROLLOUT_POLICY,
    DEFAULT_ISMCTS_DECISIVE_GREEDY_PROBABILITY,
    DEFAULT_ISMCTS_LEAF_SCALE,
    ISMCTSAgent,
)
from .agents.random_agent import RandomAgent
from .agents.strategic_heuristic_agent import StrategicHeuristicAgent
from .agents.online_mccfr_agent import OnlineMCCFRAgent
from .belief import DeckHypothesis, DeckPrior, HypothesisDeckPrior
from .agents.mccfr_agent import MCCFRAgent
from .game.actions import Pass, action_key
from .game.engine import GameEngine, all_positions
from .game.model import Phase
from .human_flow import HumanFlowDiagnostics
from .heuristics import HeuristicWeights, coerce_heuristic_weights
from .parallelism import DEFAULT_WORKERS
from .protocol import AgentKind
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


def _owned_card_counter(state, player: int) -> Counter[str]:
    """Count every card currently owned by one player across canonical zones."""
    cards: Counter[str] = Counter(state.players[player].deck)
    cards.update(state.players[player].hand)
    cards.update(state.players[player].discard)
    for position in all_positions():
        slot = state.slot(player, position)
        cards.update(
            card_id
            for card_id in (slot.force, slot.bond, slot.name)
            if card_id is not None
        )
    cards.update(narrative.card_id for narrative in state.narratives[player])
    stratagem = state.stratagems[player]
    if stratagem is not None:
        cards[stratagem.card_id] += 1
    return cards


def _assert_card_conservation(
    state,
    expected: tuple[Counter[str], Counter[str]],
    *,
    action: object | None = None,
) -> None:
    """Fail at the first transition that loses, duplicates, or changes ownership."""
    for player in range(2):
        actual = _owned_card_counter(state, player)
        if actual == expected[player]:
            continue
        missing = expected[player] - actual
        extra = actual - expected[player]
        action_text = "<initial-state>" if action is None else action_key(action)
        raise RuntimeError(
            "Card conservation violated: "
            f"player={player} battle={state.battle} turn={state.turn_number} "
            f"action={action_text}; missing={dict(sorted(missing.items()))} "
            f"extra={dict(sorted(extra.items()))}"
        )


@dataclass(frozen=True)
class SimulationReport:
    games: int
    agents: tuple[str, str]
    wins: tuple[int, int]
    draws: int
    censored_games: int
    failed_games: int
    first_player_wins: int
    mean_turns: float
    max_turns: int
    telemetry: dict[str, Any]
    game_outcomes: list[dict[str, Any]]
    failed_game_outcomes: list[dict[str, Any]]

    @property
    def decisive_games(self) -> int:
        return self.games - self.censored_games - self.failed_games - self.draws

    @property
    def win_rates(self) -> tuple[float, float]:
        denominator = self.decisive_games
        if denominator <= 0:
            return (0.0, 0.0)
        return tuple(win / denominator for win in self.wins)  # type: ignore[return-value]

    @property
    def draw_rate(self) -> float:
        resolved = self.decisive_games + self.draws
        return self.draws / resolved if resolved > 0 else 0.0

    @property
    def censor_rate(self) -> float:
        return self.censored_games / self.games

    @property
    def failure_rate(self) -> float:
        return self.failed_games / self.games

    @property
    def completed_games(self) -> int:
        return self.games - self.failed_games

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


@dataclass(frozen=True)
class SimulationBatchCell:
    """One independently seeded simulation cell for a shared worker pool."""

    key: str
    deck_a: list[str]
    deck_b: list[str]
    games: int
    seed: int
    options: dict[str, Any] | None = None


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
    ismcts_post_battle_rollout_depth: int = DEFAULT_ISMCTS_POST_BATTLE_ROLLOUT_DEPTH,
    ismcts_tree_depth_limit: int = 96,
    ismcts_exploration: float = DEFAULT_ISMCTS_EXPLORATION,
    ismcts_progressive_widening: float = DEFAULT_ISMCTS_PROGRESSIVE_WIDENING,
    ismcts_progressive_widening_alpha: float = DEFAULT_ISMCTS_PROGRESSIVE_WIDENING_ALPHA,
    ismcts_reuse_tree: bool = DEFAULT_ISMCTS_REUSE_TREE,
    ismcts_max_tree_nodes: int | None = DEFAULT_ISMCTS_MAX_TREE_NODES,
    ismcts_rollout_epsilon: float = DEFAULT_ISMCTS_ROLLOUT_EPSILON,
    ismcts_rollout_policy: str = DEFAULT_ISMCTS_ROLLOUT_POLICY,
    ismcts_decisive_greedy_probability: float = DEFAULT_ISMCTS_DECISIVE_GREEDY_PROBABILITY,
    ismcts_leaf_scale: float = DEFAULT_ISMCTS_LEAF_SCALE,
    heuristic_weights: HeuristicWeights | dict[str, float] | None = None,
):
    weights = coerce_heuristic_weights(heuristic_weights)
    if name == AgentKind.RANDOM:
        return RandomAgent(seed)
    if name == AgentKind.HEURISTIC:
        return HeuristicAgent(
            seed,
            exploration=heuristic_exploration,
            heuristic_weights=weights,
        )
    if name == AgentKind.STRATEGIC_HEURISTIC:
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
            heuristic_weights=weights,
        )
    if name == AgentKind.ISMCTS:
        return ISMCTSAgent(
            engine,
            seed,
            priors=priors,
            belief_samples=ismcts_belief_samples,
            iterations=ismcts_iterations,
            time_budget_seconds=ismcts_time_budget_seconds,
            rollout_depth=ismcts_rollout_depth,
            post_battle_rollout_depth=ismcts_post_battle_rollout_depth,
            tree_depth_limit=ismcts_tree_depth_limit,
            exploration=ismcts_exploration,
            progressive_widening=ismcts_progressive_widening,
            progressive_widening_alpha=ismcts_progressive_widening_alpha,
            reuse_tree=ismcts_reuse_tree,
            max_tree_nodes=ismcts_max_tree_nodes,
            rollout_epsilon=ismcts_rollout_epsilon,
            rollout_policy=ismcts_rollout_policy,
            decisive_greedy_probability=ismcts_decisive_greedy_probability,
            leaf_scale=ismcts_leaf_scale,
            heuristic_weights=weights,
        )
    if name == AgentKind.MCCFR:
        if policy is None:
            raise ValueError("MCCFR agent requires an exported policy")
        return MCCFRAgent(seed, policy)
    if name == AgentKind.ONLINE_MCCFR:
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
    agent_names: tuple[str, str] = (AgentKind.HEURISTIC, AgentKind.HEURISTIC),
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
    ismcts_post_battle_rollout_depth: int = DEFAULT_ISMCTS_POST_BATTLE_ROLLOUT_DEPTH,
    ismcts_tree_depth_limit: int = 96,
    ismcts_exploration: float = DEFAULT_ISMCTS_EXPLORATION,
    ismcts_progressive_widening: float = DEFAULT_ISMCTS_PROGRESSIVE_WIDENING,
    ismcts_progressive_widening_alpha: float = DEFAULT_ISMCTS_PROGRESSIVE_WIDENING_ALPHA,
    ismcts_reuse_tree: bool = DEFAULT_ISMCTS_REUSE_TREE,
    ismcts_max_tree_nodes: int | None = DEFAULT_ISMCTS_MAX_TREE_NODES,
    ismcts_rollout_epsilon: float = DEFAULT_ISMCTS_ROLLOUT_EPSILON,
    ismcts_rollout_policy: str = DEFAULT_ISMCTS_ROLLOUT_POLICY,
    ismcts_decisive_greedy_probability: float = DEFAULT_ISMCTS_DECISIVE_GREEDY_PROBABILITY,
    ismcts_leaf_scale: float = DEFAULT_ISMCTS_LEAF_SCALE,
    agent_overrides: tuple[dict[str, Any] | None, dict[str, Any] | None] = (None, None),
    agent_labels: tuple[str, str] | None = None,
    agent_seed_offsets: tuple[int, int] | None = None,
    progress_callback: Callable[[int, int, tuple[int, int]], None] | None = None,
    game_index_start: int = 0,
    skip_failed_games: bool = False,
    _return_raw: bool = False,
) -> SimulationReport | _RawSimulationResult:
    if games <= 0:
        raise ValueError("games must be positive")

    wins = [0, 0]
    draws = 0
    censored_games = 0
    failed_games = 0
    first_player_wins = 0
    total_turns = 0
    maximum_turns = 0
    game_outcomes: list[dict[str, Any]] = []
    failed_game_outcomes: list[dict[str, Any]] = []
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
        "ismcts_post_battle_rollout_depth": ismcts_post_battle_rollout_depth,
        "ismcts_tree_depth_limit": ismcts_tree_depth_limit,
        "ismcts_exploration": ismcts_exploration,
        "ismcts_progressive_widening": ismcts_progressive_widening,
        "ismcts_progressive_widening_alpha": ismcts_progressive_widening_alpha,
        "ismcts_reuse_tree": ismcts_reuse_tree,
        "ismcts_max_tree_nodes": ismcts_max_tree_nodes,
        "ismcts_rollout_epsilon": ismcts_rollout_epsilon,
        "ismcts_rollout_policy": ismcts_rollout_policy,
        "ismcts_decisive_greedy_probability": ismcts_decisive_greedy_probability,
        "ismcts_leaf_scale": ismcts_leaf_scale,
    }

    for game_index in range(games):
        global_game_index = game_index_start + game_index
        first_player = global_game_index % 2
        game_seed = seed + global_game_index
        agents: list[object] = []
        preview = None
        state = None
        game_telemetry = Telemetry()
        game_human_flow = HumanFlowDiagnostics()
        action_count = 0
        turn_consuming_action_count = 0
        censored = False
        recent_actions: deque[str] = deque(maxlen=24)
        expected_cards = (Counter(deck_a), Counter(deck_b))

        try:
            preview = engine.new_game(
                deck_a,
                deck_b,
                seed=game_seed,
                first_player=first_player,
                opening_bonus=False,
            )
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
                seed=game_seed,
                first_player=first_player,
                mulligan_indices=mulligan_indices,
            )
            _assert_card_conservation(state, expected_cards)
            game_telemetry.start_game(
                state,
                engine,
                simulation_game_index=global_game_index,
                seed=game_seed,
                first_player=first_player,
            )
            game_human_flow.start_game(engine, state)

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

                game_human_flow.before_action(engine, state, actor, action)
                before = game_telemetry.before_action(
                    engine,
                    state,
                    actor,
                    action,
                    decision_info,
                )
                recent_actions.append(action_key(action))
                is_turn_consuming_action = engine.action_consumes_operation(
                    state,
                    actor,
                    action,
                )
                engine.apply(state, action)
                _assert_card_conservation(
                    state,
                    expected_cards,
                    action=action,
                )
                game_telemetry.after_action(engine, before, state, actor, action)
                game_human_flow.after_action(engine, before, state, actor, action)
                action_count += 1
                if is_turn_consuming_action:
                    turn_consuming_action_count += 1

                del decision_info, before, action, agent

            winner = None if censored else state.winner
            draw = (
                not censored
                and state.phase is Phase.COMPLETE
                and winner is None
            )

            game_telemetry.finish_game(
                winner,
                state,
                censored=censored,
            )
            telemetry.merge(game_telemetry)
            human_flow.merge(game_human_flow)
            censor_reason = None
            if censored:
                if state.pending_effects:
                    censor_reason = "pending-effect-action-horizon"
                elif (
                    state.players[0].command == 0
                    and state.players[1].command == 0
                ):
                    censor_reason = "zero-command-action-horizon"
                else:
                    censor_reason = "active-action-horizon"

            game_outcomes.append({
                "game": global_game_index,
                "seed": game_seed,
                "first_player": first_player,
                "winner": winner,
                "draw": draw,
                "censored": censored,
                "censor_reason": censor_reason,
                "actions_completed": action_count,
                "turn_consuming_actions_completed": turn_consuming_action_count,
                "final_battle": int(state.battle),
                "final_command": [
                    int(state.players[0].command),
                    int(state.players[1].command),
                ],
                "pending_effects": len(state.pending_effects),
                "recent_actions": list(recent_actions),
            })
            if censored:
                censored_games += 1
            elif draw:
                draws += 1
            else:
                assert winner in (0, 1)
                wins[winner] += 1
                if winner == first_player:
                    first_player_wins += 1
            total_turns += action_count
            maximum_turns = max(maximum_turns, action_count)

        except Exception as exc:
            if not skip_failed_games:
                raise
            failed_games += 1
            failed_game_outcomes.append({
                "game": global_game_index,
                "seed": game_seed,
                "first_player": first_player,
                "error_type": type(exc).__name__,
                "error": str(exc),
                "traceback": traceback.format_exc(),
                "actions_completed": action_count,
                "turn_consuming_actions_completed": turn_consuming_action_count,
                "final_battle": (
                    None if state is None else int(state.battle)
                ),
                "final_command": (
                    None
                    if state is None
                    else [
                        int(state.players[0].command),
                        int(state.players[1].command),
                    ]
                ),
                "recent_actions": list(recent_actions),
            })

        finally:
            if progress_callback is not None:
                progress_callback(game_index + 1, games, (wins[0], wins[1]))
            for finished_agent in agents:
                _release_agent_search_memory(finished_agent)
            del agents, state, preview, game_telemetry, game_human_flow
            _release_process_memory()

    telemetry_summary = telemetry.summary()
    _release_process_memory()
    telemetry_summary["human_flow"] = human_flow.summary()
    completed_games = games - failed_games
    report = SimulationReport(
        games=games,
        agents=labels,
        wins=(wins[0], wins[1]),
        draws=draws,
        censored_games=censored_games,
        failed_games=failed_games,
        first_player_wins=first_player_wins,
        mean_turns=(total_turns / completed_games if completed_games else 0.0),
        max_turns=maximum_turns,
        telemetry=telemetry_summary,
        game_outcomes=game_outcomes,
        failed_game_outcomes=failed_game_outcomes,
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
    game_index_start: int,
    games: int,
    options: dict[str, Any],
) -> _RawSimulationResult:
    engine = GameEngine(card_data, rules=rules)
    result = _simulate_games_serial(
        engine,
        deck_a,
        deck_b,
        games=games,
        seed=seed,
        game_index_start=game_index_start,
        _return_raw=True,
        **options,
    )
    assert isinstance(result, _RawSimulationResult)
    return result


def _aggregate_raw_simulation_results(
    results: list[_RawSimulationResult],
    games: int,
) -> SimulationReport:
    """Merge deterministic one-game worker results into one report."""
    if not results:
        raise ValueError("At least one simulation result is required")

    results.sort(key=lambda item: item.game_index_start)
    telemetry = Telemetry()
    human_flow = HumanFlowDiagnostics()
    wins = [0, 0]
    draws = 0
    censored_games = 0
    failed_games = 0
    first_player_wins = 0
    total_turns = 0.0
    completed_games = 0
    maximum_turns = 0
    game_outcomes: list[dict[str, Any]] = []
    failed_game_outcomes: list[dict[str, Any]] = []
    agents = results[0].report.agents

    for result in results:
        report = result.report
        telemetry.merge(result.telemetry)
        human_flow.merge(result.human_flow)
        wins[0] += report.wins[0]
        wins[1] += report.wins[1]
        draws += report.draws
        censored_games += report.censored_games
        failed_games += report.failed_games
        first_player_wins += report.first_player_wins
        completed_games += report.completed_games
        total_turns += report.mean_turns * report.completed_games
        maximum_turns = max(maximum_turns, report.max_turns)
        game_outcomes.extend(report.game_outcomes)
        failed_game_outcomes.extend(report.failed_game_outcomes)

    telemetry_summary = telemetry.summary()
    telemetry_summary["human_flow"] = human_flow.summary()
    return SimulationReport(
        games=games,
        agents=agents,
        wins=(wins[0], wins[1]),
        draws=draws,
        censored_games=censored_games,
        failed_games=failed_games,
        first_player_wins=first_player_wins,
        mean_turns=(total_turns / completed_games if completed_games else 0.0),
        max_turns=maximum_turns,
        telemetry=telemetry_summary,
        game_outcomes=game_outcomes,
        failed_game_outcomes=failed_game_outcomes,
    )


def simulate_games_batch(
    engine: GameEngine,
    cells: list[SimulationBatchCell],
    *,
    jobs: int,
    common_options: dict[str, Any],
    progress_callback: Callable[[str, int, int], None] | None = None,
) -> dict[str, SimulationReport]:
    """Run multiple simulation cells through one work-conserving process pool.

    Games from every cell are queued together, so a worker that finishes the
    tail of one matchup can immediately start a game from another matchup.
    """
    if jobs <= 0:
        raise ValueError("jobs must be positive")
    if not cells:
        return {}

    keys = [cell.key for cell in cells]
    if len(keys) != len(set(keys)):
        raise ValueError("Simulation batch cell keys must be unique")
    if any(cell.games <= 0 for cell in cells):
        raise ValueError("Simulation batch cell game counts must be positive")

    worker_count = min(jobs, sum(cell.games for cell in cells))
    raw_by_key: dict[str, list[_RawSimulationResult]] = {
        cell.key: [] for cell in cells
    }
    completed_by_key = {cell.key: 0 for cell in cells}

    with ProcessPoolExecutor(max_workers=worker_count) as pool:
        future_keys = {}
        for cell in cells:
            options = dict(common_options)
            if cell.options:
                options.update(cell.options)
            for game_index in range(cell.games):
                future = pool.submit(
                    _simulate_games_worker,
                    engine.card_data,
                    engine.rules,
                    cell.deck_a,
                    cell.deck_b,
                    cell.seed,
                    game_index,
                    1,
                    options,
                )
                future_keys[future] = cell.key

        for future in as_completed(future_keys):
            key = future_keys[future]
            raw_by_key[key].append(future.result())
            completed_by_key[key] += 1
            if progress_callback is not None:
                total = next(cell.games for cell in cells if cell.key == key)
                progress_callback(key, completed_by_key[key], total)

    return {
        cell.key: _aggregate_raw_simulation_results(
            raw_by_key[cell.key],
            cell.games,
        )
        for cell in cells
    }


def simulate_games(
    engine: GameEngine,
    deck_a: list[str],
    deck_b: list[str],
    *,
    games: int,
    seed: int = 0,
    jobs: int = DEFAULT_WORKERS,
    max_actions: int = 500,
    agent_names: tuple[str, str] = (AgentKind.HEURISTIC, AgentKind.HEURISTIC),
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
    ismcts_post_battle_rollout_depth: int = DEFAULT_ISMCTS_POST_BATTLE_ROLLOUT_DEPTH,
    ismcts_tree_depth_limit: int = 96,
    ismcts_exploration: float = DEFAULT_ISMCTS_EXPLORATION,
    ismcts_progressive_widening: float = DEFAULT_ISMCTS_PROGRESSIVE_WIDENING,
    ismcts_progressive_widening_alpha: float = DEFAULT_ISMCTS_PROGRESSIVE_WIDENING_ALPHA,
    ismcts_reuse_tree: bool = DEFAULT_ISMCTS_REUSE_TREE,
    ismcts_max_tree_nodes: int | None = DEFAULT_ISMCTS_MAX_TREE_NODES,
    ismcts_rollout_epsilon: float = DEFAULT_ISMCTS_ROLLOUT_EPSILON,
    ismcts_rollout_policy: str = DEFAULT_ISMCTS_ROLLOUT_POLICY,
    ismcts_decisive_greedy_probability: float = DEFAULT_ISMCTS_DECISIVE_GREEDY_PROBABILITY,
    ismcts_leaf_scale: float = DEFAULT_ISMCTS_LEAF_SCALE,
    agent_overrides: tuple[dict[str, Any] | None, dict[str, Any] | None] = (None, None),
    agent_labels: tuple[str, str] | None = None,
    agent_seed_offsets: tuple[int, int] | None = None,
    progress_callback: Callable[[int, int, tuple[int, int]], None] | None = None,
    skip_failed_games: bool = False,
) -> SimulationReport:
    """Simulate matches, using independent worker processes when requested."""
    if jobs <= 0:
        raise ValueError("jobs must be positive")

    options: dict[str, Any] = {
        "max_actions": max_actions,
        "agent_names": agent_names,
        "agent_policies": agent_policies,
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
        "ismcts_post_battle_rollout_depth": ismcts_post_battle_rollout_depth,
        "ismcts_tree_depth_limit": ismcts_tree_depth_limit,
        "ismcts_exploration": ismcts_exploration,
        "ismcts_progressive_widening": ismcts_progressive_widening,
        "ismcts_reuse_tree": ismcts_reuse_tree,
        "ismcts_max_tree_nodes": ismcts_max_tree_nodes,
        "ismcts_rollout_epsilon": ismcts_rollout_epsilon,
        "ismcts_rollout_policy": ismcts_rollout_policy,
        "agent_overrides": agent_overrides,
        "agent_labels": agent_labels,
        "agent_seed_offsets": agent_seed_offsets,
        "skip_failed_games": skip_failed_games,
    }

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

    # Schedule one game per future rather than assigning fixed multi-game
    # chunks to workers. ProcessPoolExecutor keeps at most worker_count
    # processes active and immediately feeds the next queued game to whichever
    # worker finishes first. This avoids the long low-utilization tail caused
    # by uneven ISMCTS game runtimes while preserving deterministic per-game
    # seeds through game_index_start.
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
                1,
                options,
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
    draws = 0
    censored_games = 0
    failed_games = 0
    first_player_wins = 0
    total_turns = 0.0
    completed_games = 0
    maximum_turns = 0
    game_outcomes: list[dict[str, Any]] = []
    failed_game_outcomes: list[dict[str, Any]] = []
    agents = results[0].report.agents

    for result in results:
        report = result.report
        telemetry.merge(result.telemetry)
        human_flow.merge(result.human_flow)
        wins[0] += report.wins[0]
        wins[1] += report.wins[1]
        draws += report.draws
        censored_games += report.censored_games
        failed_games += report.failed_games
        first_player_wins += report.first_player_wins
        completed_games += report.completed_games
        total_turns += report.mean_turns * report.completed_games
        maximum_turns = max(maximum_turns, report.max_turns)
        game_outcomes.extend(report.game_outcomes)
        failed_game_outcomes.extend(report.failed_game_outcomes)

    telemetry_summary = telemetry.summary()
    telemetry_summary["human_flow"] = human_flow.summary()
    return SimulationReport(
        games=games,
        agents=agents,
        wins=(wins[0], wins[1]),
        draws=draws,
        censored_games=censored_games,
        failed_games=failed_games,
        first_player_wins=first_player_wins,
        mean_turns=(total_turns / completed_games if completed_games else 0.0),
        max_turns=maximum_turns,
        telemetry=telemetry_summary,
        game_outcomes=game_outcomes,
        failed_game_outcomes=failed_game_outcomes,
    )
