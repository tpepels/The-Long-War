from __future__ import annotations

import json
from pathlib import Path

from longwar.cards import load_card_file
from longwar.game import Cycle, Draw, GameEngine
from longwar.rules import GameRules


ROOT = Path(__file__).resolve().parents[1]


def game_with_obsolete_flags(**changes):
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "reference.json").read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(
        data,
        rules=GameRules.standard().with_overrides(**changes),
    )
    state = engine.new_game(
        deck,
        deck,
        seed=26092334,
        first_player=0,
        opening_bonus=False,
    )
    return engine, state


def test_generic_draw_cannot_be_reenabled_by_legacy_flags() -> None:
    engine, state = game_with_obsolete_flags(
        automatic_draw=False,
        paid_draw_enabled=True,
        draw_action_enabled=True,
    )
    assert not any(isinstance(action, Draw) for action in engine.legal_actions(state))


def test_generic_cycle_cannot_be_reenabled_by_legacy_flags() -> None:
    engine, state = game_with_obsolete_flags(cycle_enabled=True)
    assert not any(isinstance(action, Cycle) for action in engine.legal_actions(state))


def test_standard_rules_have_no_between_battle_recycle_or_cleanup_limit() -> None:
    rules = GameRules.standard()
    assert rules.recycle_between_battles is False
    assert rules.battle_end_hand_limit is None
    assert rules.hand_limit == 10
