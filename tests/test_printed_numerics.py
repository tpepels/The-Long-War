"""The executable catalogue must use the same exact numbers as printed cards.

Only numeric/row fields are asserted here. Printed effects require their own
explicit compiled rule specifications and are audited separately.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from longwar.game.engine import GameEngine
from longwar.physical_values import (
    CANONICAL_CARD_IDS, PRINTED_STAT_OVERRIDES, apply_printed_numeric_values,
)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from print_cards import load_print_cards  # noqa: E402


def test_printed_numerical_catalogue_is_exact():
    source = json.loads((ROOT / "cards" / "cards.json").read_text())
    printed = load_print_cards(base=source)
    engine = GameEngine(source)
    by_id = {c["id"]: c for c in printed["cards"]}
    assert set(engine.cards) == CANONICAL_CARD_IDS
    assert len(PRINTED_STAT_OVERRIDES) >= 50
    keys = (
        "command_cost", "strength", "strength_modifier", "allowed_rows",
        "hero_force_command_cost", "hero_name_command_cost",
    )
    for card_id, actual in engine.cards.items():
        expected = by_id[card_id]
        for key in keys:
            assert actual.get(key) == expected.get(key), (card_id, key, actual.get(key), expected.get(key))
        if actual["type"] == "hero":
            for mode in ("force", "name"):
                assert (
                    actual["modes"][mode]["command_cost"]
                    == expected["modes"][mode]["command_cost"]
                )


def test_custom_card_sets_and_explicit_opt_out_remain_unmodified():
    source = json.loads((ROOT / "cards" / "cards.json").read_text())
    original = {c["id"]: c for c in source["cards"]}
    engine = GameEngine(source, use_printed_numeric_values=False)
    assert engine.cards["the-fifty-men"]["strength"] == original["the-fifty-men"]["strength"]
    # A tiny independent toy catalogue cannot be silently rewritten.
    subset = {"cards": [dict(source["cards"][0])]}
    assert apply_printed_numeric_values(subset) is subset
