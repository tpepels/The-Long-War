from __future__ import annotations

import json
from pathlib import Path

import pytest

from longwar.cards import load_card_file
from longwar.game import Front, GameEngine, GameState, Position, Rank
from longwar.game.model import PlayerState
from longwar.mccfr import action_key
from longwar.online_mccfr import OnlineMCCFRResolver

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.algorithm


def setup():
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "reference.json").read_text(encoding="utf-8")
    )["cards"]
    return GameEngine(data), deck


def test_online_resolver_has_root_coverage_without_true_opponent_deck() -> None:
    engine, deck = setup()
    state = engine.new_game(deck, deck, seed=12, first_player=0)
    resolver = OnlineMCCFRResolver(
        engine,
        seed=44,
        iterations=4,
        max_depth=1,
    )

    result = resolver.solve(state)
    legal_keys = {action_key(action) for action in engine.legal_actions(state)}

    assert result.root_coverage == 1.0
    assert result.root_average_visits > 0
    assert set(result.strategy) == legal_keys
    assert sum(result.strategy.values()) == pytest.approx(1.0)
    assert result.belief_prior == "CardPoolDeckPrior"


def test_online_resolver_handles_final_operation_with_unknown_deck() -> None:
    engine, deck = setup()

    p0_hidden = list(deck)
    p0_hidden.remove("the-fifty-men")
    p0_hidden.remove("the-three-brothers-of-avar")
    p0_hidden.remove("seven-black-ships")
    state = GameState(
        players=[
            PlayerState(
                deck=p0_hidden,
                hand=["seven-black-ships"],
                command=engine.starting_command,
            ),
            PlayerState(
                deck=list(deck),
                hand=[],
                victories=1,
                passed=True,
                command=engine.starting_command,
            ),
        ],
        active_player=0,
        battle=3,
        pass_order=[1],
        operations_this_battle=[1, 1],
    )
    state.slot(0, Position(Front.FIRST, Rank.FRONT)).force = "the-fifty-men"
    state.slot(0, Position(Front.SECOND, Rank.FRONT)).force = "the-three-brothers-of-avar"

    legal = engine.legal_actions(state)
    legal_keys = {action_key(action) for action in legal}
    assert "pass" in legal_keys
    assert len(legal_keys) > 1

    pass_state = state.clone()
    pass_action = next(action for action in legal if action_key(action) == "pass")
    engine.apply(pass_state, pass_action)
    assert pass_state.battle == 4
    assert pass_state.winner is None

    resolver = OnlineMCCFRResolver(
        engine,
        seed=123,
        iterations=50,
        max_depth=1,
    )
    result = resolver.solve(state)

    assert result.root_coverage == 1.0
    assert set(result.strategy) == legal_keys
    assert sum(result.strategy.values()) == pytest.approx(1.0)
