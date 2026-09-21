from __future__ import annotations

import json
from pathlib import Path

from longwar.agents import HeuristicAgent
from longwar.cards import load_card_file
from longwar.game import Front, GameEngine, Pass, Position, Rank

ROOT = Path(__file__).resolve().parents[1]


def engine_and_state():
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "reference.json").read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(data)
    state = engine.new_game(deck, deck, seed=91, first_player=0)
    return engine, state


def test_heuristic_always_returns_legal_action() -> None:
    engine, state = engine_and_state()
    agent = HeuristicAgent(seed=5, exploration=0.0)
    action = agent.choose(engine, state)
    assert action in engine.legal_actions(state)


def test_heuristic_does_not_use_opponent_hand_identities() -> None:
    engine, state = engine_and_state()
    state.players[0].hand = [
        "the-fifty-men",
        "followed",
        "namar",
        "the-story-is-false",
    ]
    state.players[1].hand = [
        "oren",
        "iria",
        "teyra",
        "he-never-came",
    ]

    first = HeuristicAgent(seed=7, exploration=0.0).choose(engine, state)

    # Change only hidden identities; keep public hand size identical.
    state.players[1].hand = [
        "the-fifty-men",
        "seven-black-ships",
        "followed",
        "swore-to",
    ]
    second = HeuristicAgent(seed=7, exploration=0.0).choose(engine, state)

    assert first == second


def test_heuristic_prefers_to_pass_when_opponent_has_passed_and_battle_is_won() -> None:
    engine, state = engine_and_state()
    state.players[0].hand = ["the-fifty-men"]
    state.players[1].hand = []
    state.slot(0, Position(Front.LEFT, Rank.FRONT)).subject = "the-fifty-men"
    state.slot(0, Position(Front.CENTER, Rank.FRONT)).subject = "the-fifty-men"
    state.players[1].passed = True
    state.pass_order = [1]
    state.active_player = 0

    action = HeuristicAgent(seed=1, exploration=0.0).choose(engine, state)
    assert isinstance(action, Pass)
