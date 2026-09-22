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


def test_opening_mulligan_rejects_unenabled_names_first() -> None:
    engine, _ = engine_and_state()
    hand = [
        "namar",
        "iria",
        "the-fifty-men",
        "seven-black-ships",
        "the-lamps-went-dark",
        "the-storm-broke",
        "the-house-at-orra",
        "the-children-of-the-salt-road",
        "the-road-was-cut",
        "the-three-brothers-of-avar",
    ]
    agent = HeuristicAgent(seed=5, exploration=0.0)
    assert agent.choose_mulligan(engine, hand) == (0, 1)


def test_opening_mulligan_keeps_enabled_bond_over_dead_name() -> None:
    engine, _ = engine_and_state()
    hand = [
        "the-fifty-men",
        "seven-black-ships",
        "followed",
        "namar",
        "iria",
        "the-lamps-went-dark",
        "the-storm-broke",
        "the-house-at-orra",
        "the-road-was-cut",
        "the-three-brothers-of-avar",
    ]
    agent = HeuristicAgent(seed=5, exploration=0.0)
    mulligan = agent.choose_mulligan(engine, hand)
    assert 2 not in mulligan
    assert 3 in mulligan or 4 in mulligan

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

def test_heuristic_penalizes_fragile_leads_after_passing() -> None:
    engine, state = engine_and_state()
    state.players[0].hand = ["oren", "iria"]
    state.players[1].hand = ["namar", "teyra", "followed", "swore-to"]
    state.slot(0, Position(Front.LEFT, Rank.FRONT)).subject = "the-fifty-men"
    state.slot(0, Position(Front.CENTER, Rank.FRONT)).subject = "the-fifty-men"

    live_value = HeuristicAgent(seed=2, exploration=0.0).evaluate(engine, state, 0)

    passed = state.clone()
    passed.players[0].passed = True
    passed.pass_order = [0]
    passed_value = HeuristicAgent(seed=2, exploration=0.0).evaluate(engine, passed, 0)

    assert passed_value < live_value


def test_heuristic_values_tempo_after_opponent_passes() -> None:
    engine, state = engine_and_state()
    state.players[0].hand = ["the-fifty-men", "followed", "oren"]
    state.players[1].hand = []
    state.slot(1, Position(Front.LEFT, Rank.FRONT)).subject = "the-fifty-men"

    live_value = HeuristicAgent(seed=2, exploration=0.0).evaluate(engine, state, 0)

    opponent_passed = state.clone()
    opponent_passed.players[1].passed = True
    opponent_passed.pass_order = [1]
    tempo_value = HeuristicAgent(seed=2, exploration=0.0).evaluate(
        engine,
        opponent_passed,
        0,
    )

    assert tempo_value > live_value

