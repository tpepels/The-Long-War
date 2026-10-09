from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from longwar.cards import load_card_file, validate_card_data
from longwar.game import Front, GameEngine, PlayForce, Position, Rank
from longwar.testing import GameScenario
from longwar.game.engine import InvalidDeck
from longwar.rules import GameRules

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def data():
    return load_card_file(ROOT / "cards/cards.json")


@pytest.mark.parametrize(
    "field",
    ["id", "title", "type", "unique", "classes", "text", "design_rules", "rule_blocks"],
)
def test_required_card_fields_are_validated(data, field) -> None:
    del data["cards"][0][field]
    with pytest.raises(ValueError, match="missing required fields"):
        validate_card_data(data)


@pytest.mark.parametrize(
    "invalid",
    [None, [], {"schema_version": True, "cards": []}, {"schema_version": 1, "cards": [None]}],
)
def test_malformed_payload_is_a_validation_error(invalid) -> None:
    with pytest.raises(ValueError):
        validate_card_data(invalid)


def test_unknown_mechanic_is_rejected(data) -> None:
    card = next(card for card in data["cards"] if card.get("design_rules"))
    card["design_rules"]["unsupported_test_mechanic"] = True

    with pytest.raises(ValueError, match="unsupported mechanic"):
        validate_card_data(data)


def test_unsupported_rules_channel_is_rejected(data) -> None:
    data["cards"][0]["rules"] = {}
    with pytest.raises(ValueError, match="rules field is unsupported"):
        validate_card_data(data)


@pytest.mark.parametrize("value", [True, 1.5, -1, 128])
def test_strength_and_command_cost_fit_native_schema(data, value) -> None:
    for field in ("strength", "command_cost"):
        changed = copy.deepcopy(data)
        changed["cards"][0][field] = value
        with pytest.raises(ValueError):
            validate_card_data(changed)


def test_unknown_target_selector_is_rejected(data) -> None:
    effect = None
    for card in data["cards"]:
        groups = [card.get("design_rules", {}).get("effects", [])]
        groups.extend(card.get("design_rules", {}).get("modes", {}).values())
        for effects in groups:
            for candidate in effects:
                if "target" in candidate:
                    effect = candidate
                    break
            if effect is not None:
                break
        if effect is not None:
            break

    assert effect is not None, "expected at least one targeted card effect"
    effect["target"] = "unsupported-test-target"
    with pytest.raises(ValueError, match="unsupported target"):
        validate_card_data(data)


def test_direct_engine_input_rejects_duplicate_ids(data) -> None:
    data["cards"].append(copy.deepcopy(data["cards"][0]))
    with pytest.raises(ValueError, match="Duplicate card id"):
        GameEngine(data)


@pytest.mark.parametrize(
    "changes",
    [
        {"opening_hand_size": 0},
        {"opening_hand_size": True},
        {"command_cap": "20"},
        {"hand_limit": 7.5},
    ],
)
def test_rules_do_not_silently_coerce_values(changes) -> None:
    with pytest.raises(ValueError):
        GameRules(**changes)


def test_runtime_deck_validation_has_no_arbitrary_64_card_cap(data) -> None:
    engine = GameEngine(data)
    large_legal = [
        card["id"]
        for card in data["cards"]
        for _ in range(1 if card["unique"] else 2)
    ]
    assert len(large_legal) > 64
    engine.validate_deck(large_legal)

    with pytest.raises(InvalidDeck, match="list of card ids"):
        engine.validate_deck([{}] * 34)


def _expanded_pool(data, size: int):
    template = next(card for card in data["cards"] if not card["unique"])
    while len(data["cards"]) < size:
        card = copy.deepcopy(template)
        card["id"] = f"test-card-{len(data['cards'])}"
        card["title"] = f"Test Card {len(data['cards'])}"
        data["cards"].append(card)
    return data


def test_card_identity_capacity_is_checked_before_native_packing(data) -> None:
    # Current paper pool has more than 128 identities. Reserve signed-byte
    # overflow checks for actual native packing, not physical card count.
    GameEngine(_expanded_pool(copy.deepcopy(data), 192))
    with pytest.raises(ValueError, match="at most 192"):
        GameEngine(_expanded_pool(copy.deepcopy(data), 193))


def test_card_with_index_above_signed_byte_range_survives_native_transition(data) -> None:
    # Verify hand -> packed state -> legal action -> battlefield round trip.
    # Extra identities are synthetic; published card data is unchanged.
    expanded = _expanded_pool(copy.deepcopy(data), max(len(data["cards"]) + 1, 132))
    late_force = expanded["cards"][-1]["id"]
    engine = GameEngine(expanded)
    deck = json.loads(
        (ROOT / "decks" / "mobility-open-bonds.json").read_text(encoding="utf-8")
    )["cards"]
    state = engine.new_game(
        deck, deck, seed=132, first_player=0, opening_bonus=False
    )
    GameScenario(state).battle(3).hand(0, late_force)
    action = PlayForce(late_force, Position(Front.FIRST, Rank.FRONT))

    assert action in engine.legal_actions(state)
    engine.apply(state, action)
    assert state.slot(0, Position(Front.FIRST, Rank.FRONT)).force == late_force
