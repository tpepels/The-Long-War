from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "cards" / "v2" / "cards.json").read_text(encoding="utf-8"))
CARDS = DATA["cards"]

EXPECTED_COUNTS = {
    "force": 24,
    "bond": 18,
    "name": 16,
    "hero": 9,
    "tactic": 10,
    "stratagem": 9,
    "narrative": 9,
}

def effects(card: dict) -> list[dict]:
    if card["type"] == "hero":
        return [*card["modes"]["force"]["effects"], *card["modes"]["name"]["effects"]]
    return card.get("effects", [])

def test_v2_pool_is_exactly_95_and_keeps_type_budget() -> None:
    assert len(CARDS) == 95
    assert Counter(card["type"] for card in CARDS) == EXPECTED_COUNTS

def test_formation_state_vocabulary_is_explicit() -> None:
    states = DATA["formation_states"]
    assert "Force + Bond" in states["bonded"]
    assert "Force + Bond + Name" in states["named"]
    assert "also Bonded" in states["named"]
    assert "not Named" in states["formation_with_name"]
    assert "changes from not having all three" in states["becomes_named"]

def test_force_and_bond_rules_can_be_played_without_lifting_cards() -> None:
    for card in CARDS:
        if card["type"] not in {"force", "bond"}:
            continue
        for effect in card["effects"]:
            assert effect["timing"] in {"play", "once_per_battle"}, card["title"]
            assert effect["timing"] != "trigger"
            if effect["timing"] == "once_per_battle":
                assert effect.get("exposed"), card["title"]
                assert len(effect["exposed"]) <= 30, card["title"]

def test_hero_force_mode_obeys_force_grammar() -> None:
    for card in CARDS:
        if card["type"] != "hero":
            continue
        for effect in card["modes"]["force"]["effects"]:
            assert effect["timing"] in {"play", "once_per_battle"}, card["title"]
            if effect["timing"] == "once_per_battle":
                assert effect.get("exposed"), card["title"]

def test_tactics_are_immediate_and_hostile() -> None:
    for card in CARDS:
        if card["type"] == "tactic":
            assert card["effects"], card["title"]
            assert all(e["timing"] == "play" for e in card["effects"])
            assert all(e["scope"] == "opponent" for e in card["effects"])

def test_stratagems_and_narratives_support_own_side() -> None:
    for card in CARDS:
        if card["type"] == "stratagem":
            assert all(e["timing"] == "hidden" and e["scope"] == "self" for e in card["effects"])
            assert all("face_down_source" in e["memory"] for e in card["effects"])
        if card["type"] == "narrative":
            assert all(e["scope"] == "self" for e in card["effects"])
            assert all(e["timing"] in {"continuous", "once_per_battle"} for e in card["effects"])

def test_classifications_are_concrete_and_supported() -> None:
    allowed = set(DATA["classification_vocabulary"])
    abstract = {"movement", "pressure", "focus", "identity", "necessity", "defence", "control", "journey", "loss", "muster"}
    own_counts = Counter()
    referenced = Counter()
    for card in CARDS:
        for value in card.get("classes", []):
            assert value in allowed, (card["title"], value)
            assert value not in abstract
            own_counts[value] += 1
        for value in card.get("references", []):
            assert value in allowed, (card["title"], value)
            referenced[value] += 1
    for value in allowed:
        assert own_counts[value] >= 2 or referenced[value] >= 1, value

def test_movement_is_a_minor_theme_and_row_locks_are_rare() -> None:
    movement = [
        card for card in CARDS
        if re.search(r"\b(?:move|moves|maneuver|maneuvers)\b", card.get("text", ""), re.I)
    ]
    assert len(movement) <= DATA["design_limits"]["max_movement_cards"]
    restricted = [card for card in CARDS if card["type"] == "force" and card.get("placement")]
    assert len(restricted) <= DATA["design_limits"]["max_hard_row_restricted_forces"]

def test_old_row_and_retreat_language_is_absent() -> None:
    obsolete = re.compile(r"\b(?:Frontline|Reserve|Retreat|driven off|drive off)\b", re.I)
    for card in CARDS:
        assert not obsolete.search(card.get("text", "")), card["title"]

def test_v2_preview_locks_three_fonts_and_shows_type_symbols() -> None:
    css = (ROOT / "web" / "cards-v2.css").read_text(encoding="utf-8")
    js = (ROOT / "web" / "cards-v2.js").read_text(encoding="utf-8")
    assert "EBGaramond-SemiBold.otf" in css
    assert "GentiumBook-Regular.ttf" in css
    assert "Arial,sans-serif" in css
    assert "force:'<svg" in js
    assert "command-badge" in css
    assert "effect-block" in css


def test_v2_lab_cache_busts_data_across_schema_changes() -> None:
    js = (ROOT / "web" / "cards-v2.js").read_text(encoding="utf-8")
    assert 'cards-v2-redesign.json?v=' in js
    assert 'cache:"no-cache"' in js
    assert "modeEffects" in js
    assert "Array.isArray(card?.effects)" in js


def test_every_v2_card_has_playtest_design_tags() -> None:
    for card in CARDS:
        assert isinstance(card.get("design_tags"), list)
        assert card["design_tags"], card["title"]
