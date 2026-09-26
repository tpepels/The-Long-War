from __future__ import annotations

from longwar.rules import GameRules


def test_standard_rules_use_ten_card_hand_limit() -> None:
    assert GameRules.standard().hand_limit == 10
