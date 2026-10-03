from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "cards" / "v2" / "cards.json").read_text(encoding="utf-8"))
CARDS = DATA["cards"]
DECKS = json.loads((ROOT / "cards" / "v2" / "playtest-decks.json").read_text(encoding="utf-8"))["decks"]

EXPECTED_COUNTS = {"force":30,"bond":22,"name":20,"hero":11,"tactic":14,"stratagem":11,"narrative":12}

def effects(card: dict) -> list[dict]:
    if card["type"] == "hero":
        return [*card["modes"]["force"]["effects"], *card["modes"]["name"]["effects"]]
    return card.get("effects", [])

def test_v2_pool_is_120_cards() -> None:
    assert len(CARDS) == 120
    assert Counter(card["type"] for card in CARDS) == EXPECTED_COUNTS

def test_bonded_named_and_transition_are_explicit() -> None:
    states = DATA["formation_states"]
    assert "Force + Bond" in states["bonded"]
    assert "Force + Bond + Name" in states["named"]
    assert "state, not a trigger" in states["bonded_state"]
    assert "state, not a trigger" in states["named_state"]
    assert "BECOMES NAMED" in states["becomes_named"]

def test_buried_cards_never_need_lifting() -> None:
    allowed = {"play","once_per_battle","bonded","while_named"}
    for card in CARDS:
        if card["type"] in {"force","bond"}:
            for effect in card["effects"]:
                assert effect["timing"] in allowed, card["title"]
                if effect["timing"] != "play":
                    assert effect.get("exposed"), card["title"]
                    assert len(effect["exposed"]) <= 32

def test_hero_force_mode_obeys_force_grammar() -> None:
    allowed = {"play","once_per_battle","bonded","while_named"}
    for card in CARDS:
        if card["type"] == "hero":
            for effect in card["modes"]["force"]["effects"]:
                assert effect["timing"] in allowed, card["title"]
                if effect["timing"] != "play":
                    assert effect.get("exposed"), card["title"]

def test_names_are_visible_and_resolution_stays_clean() -> None:
    allowed = {"becomes_named","action","trigger","continuous","while_named"}
    for card in CARDS:
        if card["type"] == "name":
            assert all(e["timing"] in allowed for e in card["effects"])
    assert not any(e["timing"] == "resolution" for card in CARDS for e in effects(card))

def test_tactics_are_hostile_stratagems_and_narratives_are_self_support() -> None:
    for card in CARDS:
        if card["type"] == "tactic":
            assert all(e["timing"] == "play" and e["scope"] == "opponent" for e in card["effects"])
        if card["type"] == "stratagem":
            assert all(e["timing"] == "hidden" and e["scope"] == "self" for e in card["effects"])
        if card["type"] == "narrative":
            assert all(e["timing"] in {"continuous","once_per_battle"} and e["scope"] == "self" for e in card["effects"])

def test_classifications_are_layered_and_top_line_stays_small() -> None:
    allowed = set(DATA["classification_vocabulary"])
    grouped = {x for values in DATA["classification_groups"].values() for x in values}
    assert grouped == allowed
    for card in CARDS:
        assert len(card.get("classes", [])) <= 3
        assert set(card.get("classes", [])) <= allowed
        assert set(card.get("references", [])) <= allowed

def test_core_packages_have_testable_depth() -> None:
    carriers=Counter(); refs=Counter()
    for card in CARDS:
        carriers.update(card.get("classes", [])); refs.update(card.get("references", []))
    for value in {"archer","guard","scout","rider","raider","captain"}:
        assert carriers[value] + refs[value] >= 7
    assert carriers["ship"] >= 2
    assert carriers["stronghold"] >= 2
    assert carriers["healer"] >= 2

def test_movement_and_row_locks_remain_minor() -> None:
    movement=[c for c in CARDS if re.search(r"\b(?:move|moves|maneuver|maneuvers)\b", c.get("text",""), re.I)]
    assert len(movement) <= DATA["design_limits"]["max_movement_cards"]
    assert len([c for c in CARDS if c["type"]=="force" and c.get("placement")]) <= DATA["design_limits"]["max_hard_row_restricted_forces"]

def test_no_obsolete_row_or_retreat_language() -> None:
    old=re.compile(r"\b(?:Frontline|Reserve|Retreat|driven off|drive off)\b",re.I)
    assert all(not old.search(c.get("text","")) for c in CARDS)

def test_every_card_has_playtest_tags() -> None:
    assert all(card.get("design_tags") for card in CARDS)

def test_diagnostic_decks_are_legal_34_card_experiments() -> None:
    known={c["id"]:c for c in CARDS}
    assert len(DECKS)==6
    for deck in DECKS:
        assert sum(x["copies"] for x in deck["cards"])==34
        for item in deck["cards"]:
            card=known[item["id"]]
            assert item["copies"] <= (1 if card.get("unique") else 4)
