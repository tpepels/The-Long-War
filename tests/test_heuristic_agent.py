from __future__ import annotations

import json
from pathlib import Path

from longwar.agents import HeuristicAgent
from longwar.cards import load_card_file
from longwar.game import Front, GameEngine, Pass, Position, Rank, SetStratagem

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


def test_equal_stratagem_scores_do_not_fall_back_to_card_id_order() -> None:
    engine, state = engine_and_state()
    # Tide and Ground have the same public-board estimate here: each improves
    # the current relative position by two points if revealed.
    state.players[0].hand = ["the-tide-rose", "the-ground-gave-way"]
    state.players[1].hand = []
    state.slot(1, Position(Front.LEFT, Rank.FRONT)).subject = "the-fifty-men"
    state.slot(1, Position(Front.CENTER, Rank.FRONT)).subject = "the-fifty-men"

    selected = {
        action.card_id
        for seed in range(12)
        for action in [HeuristicAgent(seed=seed, exploration=0.0).choose(engine, state)]
        if isinstance(action, SetStratagem)
    }

    assert selected == {"the-tide-rose", "the-ground-gave-way"}

def test_heuristic_prefers_two_front_control_over_overkill() -> None:
    engine, state = engine_and_state()
    agent = HeuristicAgent(seed=3, exploration=0.0)

    spread = state.clone()
    spread.players[0].hand = []
    spread.players[1].hand = []
    spread.slot(0, Position(Front.LEFT, Rank.FRONT)).subject = "the-fifty-men"
    spread.slot(0, Position(Front.CENTER, Rank.FRONT)).subject = "the-fifty-men"
    spread.slot(1, Position(Front.RIGHT, Rank.FRONT)).subject = "the-fifty-men"
    spread.slot(1, Position(Front.CENTER, Rank.REAR)).subject = "seven-black-ships"

    overkill = state.clone()
    overkill.players[0].hand = []
    overkill.players[1].hand = []
    overkill.slot(0, Position(Front.LEFT, Rank.FRONT)).subject = "the-fifty-men"
    overkill.slot(0, Position(Front.LEFT, Rank.REAR)).subject = "seven-black-ships"
    overkill.slot(0, Position(Front.LEFT, Rank.FRONT)).temporary_strength = 10
    overkill.slot(1, Position(Front.CENTER, Rank.FRONT)).subject = "the-fifty-men"
    overkill.slot(1, Position(Front.RIGHT, Rank.FRONT)).subject = "the-fifty-men"

    assert agent.evaluate(engine, spread, 0) > agent.evaluate(engine, overkill, 0)


def test_heuristic_uses_public_board_to_choose_stratagem() -> None:
    engine, state = engine_and_state()
    state.players[0].hand = ["the-storm-broke", "the-wooden-gift"]
    state.players[1].hand = ["oren", "iria", "teyra", "he-never-came"]

    for front, name in ((Front.LEFT, "namar"), (Front.CENTER, "oren")):
        slot = state.slot(1, Position(front, Rank.FRONT))
        slot.subject = "the-fifty-men"
        slot.link = "followed"
        slot.name = name

    action = HeuristicAgent(seed=4, exploration=0.0).choose(engine, state)

    assert isinstance(action, SetStratagem)
    assert action.card_id == "the-wooden-gift"

