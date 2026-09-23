from __future__ import annotations

import json
from pathlib import Path

from longwar.agents.strategic_heuristic_agent import StrategicHeuristicAgent
from longwar.belief import BeliefSampler, DeckHypothesis, HypothesisDeckPrior
from longwar.cards import load_card_file
from longwar.game import GameEngine
from longwar.simulate import simulate_games

ROOT = Path(__file__).resolve().parents[1]


def load_deck(path: str) -> list[str]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))["cards"]


def command_engine(*, deck_size: int, hand_size: int, recycle: bool = True) -> GameEngine:
    data = load_card_file(ROOT / "cards" / "cards.json")
    return GameEngine(
        data,
        opening_hand_size=hand_size,
        draw_action_enabled=False,
        deck_size=deck_size,
        recycle_between_battles=recycle,
        command_enabled=True,
        starting_command=20,
        battle_command_gain=10,
        command_cap=20,
        cycle_command_cost=1,
    )


def test_default_belief_sampler_uses_engine_deck_size_for_36_cards() -> None:
    deck = load_deck("decks/experiments/name-rich-36-reference.json")
    engine = command_engine(deck_size=36, hand_size=12)
    state = engine.new_game(deck, deck, seed=7301, first_player=0)
    sampled = BeliefSampler(engine).sample(state, 0, __import__("random").Random(7302))

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
    assert len(opponent.hand) + len(opponent.deck) + public_count <= 36


def test_strategic_heuristic_returns_a_legal_action_without_true_hand_access() -> None:
    deck = load_deck("decks/experiments/name-rich-reference.json")
    engine = command_engine(deck_size=30, hand_size=10)
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


def test_short_strategic_command_simulation_finishes() -> None:
    deck = load_deck("decks/experiments/name-rich-reference.json")
    engine = command_engine(deck_size=30, hand_size=11)

    report = simulate_games(
        engine,
        deck,
        deck,
        games=4,
        seed=7320,
        agent_names=("strategic_heuristic", "strategic_heuristic"),
        strategic_belief_samples=2,
        strategic_rollout_plies=2,
        strategic_candidate_width=4,
        strategic_node_budget=2_000,
    )

    assert sum(report.wins) == 4
    assert report.telemetry["depletion"]["player_game_deck_exhaustion_rate"] is not None
    assert "strategic_heuristic" in report.telemetry["decisions"]
    decisions = report.telemetry["decisions"]["strategic_heuristic"]
    assert decisions["mean_search_nodes"] is not None
    assert decisions["mean_completed_depth"] is not None


def test_persistent_command_simulation_reports_depletion() -> None:
    deck = load_deck("decks/experiments/name-rich-reference.json")
    engine = command_engine(deck_size=30, hand_size=12, recycle=False)

    report = simulate_games(
        engine,
        deck,
        deck,
        games=8,
        seed=7330,
        agent_names=("heuristic", "heuristic"),
    )

    depletion = report.telemetry["depletion"]
    assert 0 <= depletion["player_game_deck_exhaustion_rate"] <= 1
    assert 0 <= depletion["deck_empty_decision_rate"] <= 1
    assert depletion["mean_deck_remaining_at_pass"] is not None


def test_cython_and_python_backends_agree_on_root_decision() -> None:
    __import__("pytest").importorskip("longwar._alphabeta_accel")

    deck = load_deck("decks/experiments/name-rich-reference.json")
    engine = command_engine(deck_size=30, hand_size=10)
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
    assert cython_agent.last_decision["completed_depth"] == python_agent.last_decision["completed_depth"]
