from __future__ import annotations

import json
from pathlib import Path

import pytest

from longwar.agents.strategic_heuristic_agent import StrategicHeuristicAgent
from longwar.belief import BeliefSampler, DeckHypothesis, HypothesisDeckPrior
from longwar.cards import load_card_file
from longwar.game import GameEngine
from longwar.rules import GameRules
from longwar.simulate import simulate_games

ROOT = Path(__file__).resolve().parents[1]
CARD_FILE = ROOT / "cards" / "cards.json"
DECK_FILE = ROOT / "decks" / "reference.json"


def load_deck() -> list[str]:
    return json.loads(DECK_FILE.read_text(encoding="utf-8"))["cards"]


def standard_engine() -> GameEngine:
    return GameEngine(load_card_file(CARD_FILE), rules=GameRules.standard())


def test_default_belief_sampler_uses_engine_deck_size() -> None:
    deck = load_deck()
    engine = standard_engine()
    state = engine.new_game(deck, deck, seed=7301, first_player=0)
    sampled = BeliefSampler(engine).sample(
        state,
        0,
        __import__("random").Random(7302),
    )

    opponent = sampled.players[1]
    public_count = (
        len(opponent.discard)
        + sum(
            int(slot.subject is not None)
            + int(slot.link is not None)
            + int(slot.name is not None)
            for front in sampled.board[1]
            for slot in front
        )
    )
    assert len(opponent.hand) + len(opponent.deck) + public_count <= 34


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
