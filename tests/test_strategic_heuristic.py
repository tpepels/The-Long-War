from __future__ import annotations

import json
from pathlib import Path

import pytest

from longwar.agents.strategic_heuristic_agent import StrategicHeuristicAgent
from longwar.belief import BeliefSampler, DeckHypothesis, HypothesisDeckPrior
from longwar.cards import load_card_file
from longwar.game import GameEngine
from longwar.game.actions import Draw, Pass, action_key
from longwar.game.model import Phase
from longwar.rules import GameRules
from longwar.simulate import simulate_games

ROOT = Path(__file__).resolve().parents[1]
CARD_FILE = ROOT / "cards" / "cards.json"
DECK_FILE = ROOT / "decks" / "reference.json"


def load_deck() -> list[str]:
    return json.loads(DECK_FILE.read_text(encoding="utf-8"))["cards"]


def standard_engine() -> GameEngine:
    return GameEngine(load_card_file(CARD_FILE), rules=GameRules.standard())


def test_default_belief_sampler_uses_actual_state_deck_size() -> None:
    deck = load_deck()
    engine = standard_engine()

    # Prove the default belief path follows the supplied deck, not a 34-card
    # rules constant.
    for card_id, card in engine.cards.items():
        maximum = 1 if card["unique"] else 2
        while deck.count(card_id) < maximum and len(deck) < 40:
            deck.append(card_id)
        if len(deck) == 40:
            break
    assert len(deck) == 40

    state = engine.new_game(deck, deck, seed=7301, first_player=0)
    sampler = BeliefSampler(engine)
    sampled = sampler.sample(
        state,
        0,
        __import__("random").Random(7302),
    )

    assert sampler._deck_size_from_state(state, 1) == 40
    assert sampler._deck_size_from_state(sampled, 1) == 40


def test_strategic_heuristic_returns_legal_action_without_true_hand_access() -> None:
    deck = load_deck()
    engine = standard_engine()
    state = engine.new_game(deck, deck, seed=7310, first_player=0)
    priors = (
        HypothesisDeckPrior(engine, [DeckHypothesis(tuple(deck), label="a")]),
        HypothesisDeckPrior(engine, [DeckHypothesis(tuple(deck), label="b")]),
    )
    agent = StrategicHeuristicAgent(
        engine,
        seed=7311,
        priors=priors,
        belief_samples=2,
        rollout_plies=3,
        candidate_width=4,
        node_budget=2_000,
    )

    legal = engine.legal_actions(state)
    action = agent.choose(engine, state)

    assert action in legal
    assert agent.last_decision["policy_source"] == "strategic_heuristic"
    assert agent.last_decision["belief_samples"] == 2
    assert 0 <= agent.last_decision["completed_depth"] <= 3
    assert agent.last_decision["search_nodes"] <= 2_000


def test_short_strategic_candidate_simulation_finishes() -> None:
    deck = load_deck()
    engine = standard_engine()

    report = simulate_games(
        engine,
        deck,
        deck,
        games=2,
        seed=7320,
        agent_names=("strategic_heuristic", "strategic_heuristic"),
        strategic_belief_samples=2,
        strategic_rollout_plies=2,
        strategic_candidate_width=4,
        strategic_node_budget=2_000,
    )

    assert sum(report.wins) == 2
    assert report.telemetry["depletion"]["player_game_deck_exhaustion_rate"] is not None
    decisions = report.telemetry["decisions"]["strategic_heuristic"]
    assert decisions["mean_search_nodes"] is not None
    assert decisions["mean_completed_depth"] is not None


def test_candidate_simulation_reports_depletion() -> None:
    deck = load_deck()
    engine = standard_engine()

    report = simulate_games(
        engine,
        deck,
        deck,
        games=4,
        seed=7330,
        agent_names=("heuristic", "heuristic"),
    )

    depletion = report.telemetry["depletion"]
    assert 0 <= depletion["player_game_deck_exhaustion_rate"] <= 1
    assert 0 <= depletion["deck_empty_decision_rate"] <= 1
    assert depletion["mean_deck_remaining_at_pass"] is not None


def test_cython_and_python_backends_agree_on_root_decision() -> None:
    pytest.importorskip("longwar._fast_search")

    deck = load_deck()
    engine = standard_engine()
    state = engine.new_game(deck, deck, seed=7340, first_player=0)
    priors = (
        HypothesisDeckPrior(engine, [DeckHypothesis(tuple(deck), label="a")]),
        HypothesisDeckPrior(engine, [DeckHypothesis(tuple(deck), label="b")]),
    )
    common = dict(
        engine=engine,
        seed=7341,
        priors=priors,
        belief_samples=2,
        rollout_plies=3,
        candidate_width=4,
        node_budget=3_000,
    )
    python_agent = StrategicHeuristicAgent(
        **common,
        search_backend="python",
    )
    cython_agent = StrategicHeuristicAgent(
        **common,
        search_backend="cython",
    )

    python_action = python_agent.choose(engine, state.clone())
    cython_action = cython_agent.choose(engine, state.clone())

    assert cython_action == python_action
    assert cython_agent.last_decision["search_backend"] == "cython"
    assert python_agent.last_decision["search_backend"] == "python"
    assert (
        cython_agent.last_decision["completed_depth"]
        == python_agent.last_decision["completed_depth"]
    )


def test_cython_alpha_beta_wall_clock_budget_reports_actual_work() -> None:
    pytest.importorskip("longwar._fast_search")

    deck = load_deck()
    engine = standard_engine()
    state = engine.new_game(deck, deck, seed=7350, first_player=0)
    priors = (
        HypothesisDeckPrior(engine, [DeckHypothesis(tuple(deck), label="a")]),
        HypothesisDeckPrior(engine, [DeckHypothesis(tuple(deck), label="b")]),
    )
    agent = StrategicHeuristicAgent(
        engine,
        seed=7351,
        priors=priors,
        belief_samples=2,
        rollout_plies=32,
        candidate_width=4,
        node_budget=50,
        time_budget_seconds=0.01,
        search_backend="cython",
    )

    action = agent.choose(engine, state)
    info = agent.last_decision

    assert action in engine.legal_actions(state)
    assert info["search_time_budget_seconds"] == pytest.approx(0.01)
    assert info["search_timed_out"] is True
    assert int(info["search_nodes"]) >= 256
    assert float(info["decision_seconds"]) > 0.0


def _root_candidate_snapshot(
    agent: StrategicHeuristicAgent,
    engine: GameEngine,
    state,
) -> tuple[list[str], list[str], dict[str, float]]:
    root_player = state.active_player
    actions = engine.legal_actions(state)
    candidates = agent._python_search.ordered_actions(
        state,
        root_player,
        width=agent.candidate_width,
    )
    for action in actions:
        if isinstance(action, (Pass, Draw)) and action not in candidates:
            candidates.append(action)
    return (
        [action_key(action) for action in actions],
        [action_key(action) for action in candidates],
        {
            action_key(action): agent.evaluator._score_action(
                engine,
                state,
                root_player,
                action,
            )
            for action in candidates
        },
    )


@pytest.mark.legacy_rule_experiment
@pytest.mark.parametrize("game_index", (0, 1))
def test_paid_profile_python_cython_match_each_root_decision(
    game_index: int,
) -> None:
    """Reproduce the validation games and stop at the first backend divergence."""
    pytest.importorskip("longwar._fast_search")

    base_seed = 26092334
    game_seed = base_seed + game_index
    first_player = game_index % 2
    deck = load_deck()
    engine = GameEngine(
        load_card_file(CARD_FILE),
        rules=GameRules.force_candidate("paid"),
    )
    priors = (
        HypothesisDeckPrior(engine, [DeckHypothesis(tuple(deck), label="deck-a")]),
        HypothesisDeckPrior(engine, [DeckHypothesis(tuple(deck), label="deck-b")]),
    )

    common = dict(
        engine=engine,
        priors=priors,
        belief_samples=2,
        rollout_plies=3,
        candidate_width=4,
        node_budget=3_000,
    )
    python_agents = [
        StrategicHeuristicAgent(
            **common,
            seed=base_seed * 10_000 + game_index * 2 + player + 1,
            search_backend="python",
        )
        for player in range(2)
    ]
    cython_agents = [
        StrategicHeuristicAgent(
            **common,
            seed=base_seed * 10_000 + game_index * 2 + player + 1,
            search_backend="cython",
        )
        for player in range(2)
    ]

    preview = engine.new_game(
        deck,
        deck,
        seed=game_seed,
        first_player=first_player,
        opening_bonus=False,
    )
    python_mulligans = tuple(
        agent.choose_mulligan(engine, preview.players[player].hand)
        for player, agent in enumerate(python_agents)
    )
    cython_mulligans = tuple(
        agent.choose_mulligan(engine, preview.players[player].hand)
        for player, agent in enumerate(cython_agents)
    )
    assert cython_mulligans == python_mulligans

    state = engine.new_game(
        deck,
        deck,
        seed=game_seed,
        first_player=first_player,
        mulligan_indices=python_mulligans,
    )
    saw_paid_draw = False
    decision = 0

    while state.phase is not Phase.COMPLETE:
        assert decision < 500
        actor = state.active_player
        python_agent = python_agents[actor]
        cython_agent = cython_agents[actor]

        python_root = _root_candidate_snapshot(python_agent, engine, state)
        cython_root = _root_candidate_snapshot(cython_agent, engine, state)
        assert cython_root == python_root

        legal_keys, candidate_keys, root_scores = python_root
        if "draw" in legal_keys:
            saw_paid_draw = True
            assert "draw" in candidate_keys
            assert "draw" in root_scores

        # The paired agents must enter search with the same belief RNG state;
        # otherwise an action difference would not be a backend parity result.
        assert cython_agent.rng.getstate() == python_agent.rng.getstate()

        python_action = python_agent.choose(engine, state.clone())
        cython_action = cython_agent.choose(engine, state.clone())

        assert cython_agent.rng.getstate() == python_agent.rng.getstate()
        assert (
            cython_agent.last_decision["completed_depth"]
            == python_agent.last_decision["completed_depth"]
        )
        assert action_key(cython_action) == action_key(python_action), (
            f"paid backend divergence in game {game_index}, decision {decision}, "
            f"battle {state.battle}, turn {state.turn_number}, actor {actor}; "
            f"legal={legal_keys}; candidates={candidate_keys}; "
            f"scores={root_scores}; python={action_key(python_action)}; "
            f"cython={action_key(cython_action)}"
        )

        engine.apply(state, python_action)
        decision += 1

    assert saw_paid_draw
