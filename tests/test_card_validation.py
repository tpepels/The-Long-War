from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from longwar.cards import load_card_file, validate_card_data
from longwar.game import GameEngine
from longwar.game.engine import InvalidDeck
from longwar.rules import GameRules

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def data():
    return load_card_file(ROOT / "cards/cards.json")


@pytest.mark.parametrize("field", ["id", "title", "type", "unique", "classes", "text", "rules", "rule_blocks"])
def test_required_card_fields_are_validated(data, field):
    del data["cards"][0][field]
    with pytest.raises(ValueError, match="missing required fields"):
        validate_card_data(data)


@pytest.mark.parametrize("invalid", [None, [], {"schema_version": True, "cards": []}, {"schema_version": 1, "cards": [None]}])
def test_malformed_payload_is_a_validation_error(invalid):
    with pytest.raises(ValueError):
        validate_card_data(invalid)


@pytest.mark.parametrize("rules", [
    {"strength_bouns": 1},
    {"strength_modifiers": [{"amount": 1, "when": {"unknown": True}}]},
    {"placement": {"rank": "back"}},
    {"placement": {}},
    {"on_link_attached": {"temporary_strength": True}},
    {"adjacent_strength_aura": 128},
    {"strength_modifiers": [{"amount": 1, "when": {"own_discard_at_least": 1}}] * 2},
])
def test_unsupported_subject_rules_cannot_silently_become_noops(data, rules):
    data["cards"][0]["rules"] = rules
    with pytest.raises(ValueError):
        validate_card_data(data)


@pytest.mark.parametrize("card_id, rules", [
    ("iria", {"on_name_attached": "teleport"}),
    ("the-story-is-false", {"effect": "destroy_everything"}),
    ("the-lamps-went-dark", {"scheme": {"trigger": "oponent_passes", "effect": "reinforce_front"}}),
    ("the-storm-broke", {"stratagem": {"trigger": {"event": "subject_played", "roles": ["wizard"]}}}),
    ("the-storm-broke", {"stratagem": {"trigger": {"event": "subject_played"}, "continuous": {"rank_strength_modifiers": {"back": 1}}}}),
])
def test_effect_trigger_and_role_references_are_validated(data, card_id, rules):
    next(card for card in data["cards"] if card["id"] == card_id)["rules"] = rules
    with pytest.raises(ValueError):
        validate_card_data(data)


@pytest.mark.parametrize("value", [True, 1.5, -1, 128])
def test_strength_and_command_cost_fit_the_native_schema(data, value):
    for field in ("strength", "command_cost"):
        card = copy.deepcopy(data)
        card["cards"][0][field] = value
        with pytest.raises(ValueError):
            validate_card_data(card)


def test_force_roles_are_optional_descriptive_labels(data):
    force = next(card for card in data["cards"] if card["type"] == "force")
    force.pop("role", None)
    validate_card_data(data)

    force["role"] = "skirmisher"
    validate_card_data(data)


def test_extended_rule_block_kinds_and_command_costs_are_valid(data):
    card = data["cards"][0]
    card["command_cost"] = 5
    card["rule_blocks"] = [
        {"kind": "cost", "label": "COST", "text": "Costs 1 less Command."},
        {"kind": "replacement", "label": "REPLACE", "text": "Use this instead."},
    ]
    validate_card_data(data)


def test_direct_engine_input_is_validated_before_indexing(data):
    data["cards"].append(copy.deepcopy(data["cards"][0]))
    with pytest.raises(ValueError, match="Duplicate card id"):
        GameEngine(data)


def test_engine_default_profile_is_exactly_standard(data):
    assert GameEngine(data).rules == GameRules.standard()


def test_rule_overrides_use_canonical_cards():
    data = load_card_file(ROOT / "cards/cards.json")
    variants = (
        GameRules.standard(),
        GameRules.standard().with_overrides(command_cap=19, starting_command=19),
    )
    for rules in variants:
        GameEngine(data, rules=rules)


@pytest.mark.parametrize("changes", [{"opening_hand_size": 0}, {"opening_hand_size": True}, {"command_cap": "20"}, {"hand_limit": 7.5}])
def test_rules_do_not_silently_coerce_values(changes):
    with pytest.raises(ValueError):
        GameRules(**changes)


def test_runtime_deck_validation_rejects_malformed_entries_but_not_large_known_decks(data):
    engine = GameEngine(data)
    engine.validate_deck(["followed"] * 65)
    with pytest.raises(InvalidDeck, match="list of card ids"):
        engine.validate_deck([{}] * 30)


def _expanded_pool(data, size):
    template = next(card for card in data["cards"] if card["id"] == "followed")
    while len(data["cards"]) < size:
        card = copy.deepcopy(template)
        card["id"] = f"test-bond-{len(data['cards'])}"
        data["cards"].append(card)
    return data


def test_expanded_pool_keeps_actions_and_information_keys_safe(data):
    engine = GameEngine(_expanded_pool(data, 127))
    deck = json.loads((ROOT / "decks/reference.json").read_text())["cards"]
    state = engine.new_game(deck, deck, seed=17, first_player=0)
    # 60 distinct Bonds produce 360 legal placements, beyond the old buffer.
    state.players[0].deck = []
    state.players[0].hand = [card_id for card_id in engine.cards if card_id.startswith("test-bond-")][-60:]
    legal = engine.legal_actions(state)
    assert len(legal) == 360
    assert all(getattr(action, "card_id", None) is not None for action in legal)
    assert any(getattr(action, "card_id", None) == "test-bond-126" for action in legal)
    for player in state.players:
        player.deck = []
        player.hand = []
        player.discard = ["followed"] * 64
    native = engine._native_core()
    key = native.information_key(native.from_game_state(state), 0)
    assert len(key) > 512
    assert key == native.information_key(native.from_game_state(state), 0)
    state.players[0].discard.append("followed")
    with pytest.raises(ValueError, match="native capacity"):
        native.from_game_state(state)


def test_card_identity_capacity_is_checked_before_packing(data):
    with pytest.raises(ValueError, match="at most 127"):
        GameEngine(_expanded_pool(data, 128))
