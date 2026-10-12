"""Physical-only D6 prototype: project legacy art/costs into a separate printable Force pool.

Do not import this module from the engine, balance tools or AI. Existing
cards.json and print-overrides.json remain unchanged historical sources.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

try:
    from .print_cards import load_print_cards
except ImportError:
    from print_cards import load_print_cards

ROOT = Path(__file__).resolve().parents[1]
PAPER_D6 = ROOT / "cards" / "paper-d6.json"
PAPER_D6_DECKS = ROOT / "cards" / "paper-d6-decks.json"
PAPER_D6_SUPPORT = ROOT / "cards" / "paper-d6-support.json"


def load_paper_d6_cards(base=None, combat=None) -> dict:
    if combat is None:
        combat = json.loads(PAPER_D6.read_text(encoding="utf-8"))
    if combat.get("schema_version") != 1 or combat.get("status") != "experimental-paper-only":
        raise ValueError("Unknown D6 paper schema")
    legacy = load_print_cards(base)
    legacy_by_id = {card["id"]: card for card in legacy["cards"]}
    ids = [entry["id"] for entry in combat["cards"]]
    if len(ids) != len(set(ids)) or len(ids) != 44:
        raise ValueError("D6 paper pool must have 44 unique Force/Hero identities")
    cards = []
    for entry in combat["cards"]:
        original = legacy_by_id.get(entry["id"])
        if original is None or original["type"] not in ("force", "hero"):
            raise ValueError("D6 card is not a Force or Hero: " + entry["id"])
        if not 1 <= entry["force"] <= 6 or not 0 <= entry["command_cost"] <= 20:
            raise ValueError("Invalid D6 Force/cost for " + entry["id"])
        faces = entry["faces"]
        outcomes = entry["outcomes"]
        if len(faces) != 6 or len(set(faces)) != 4 or set(faces) != set(outcomes):
            raise ValueError("A Force must have six faces and exactly four outcomes: " + entry["id"])
        if any(not isinstance(value.get("title"), str) or not value.get("effect")
               for value in outcomes.values()):
            raise ValueError("Missing printed outcome: " + entry["id"])
        card = deepcopy(original)
        card["paper_d6"] = {
            "role": entry["role"],
            "force": entry["force"],
            "faces": faces,
            "outcomes": deepcopy(outcomes),
        }
        card["strength"] = entry["force"]
        card["command_cost"] = entry["command_cost"]
        card["effects"] = []
        card["rule_blocks"] = []
        card["text"] = "Use the D6 results and your drawn Order."
        card.pop("modes", None)
        card.pop("hero_name_strength", None)
        card.pop("name_strength_modifier", None)
        card.pop("hero_force_command_cost", None)
        card.pop("hero_name_command_cost", None)
        card.pop("design_rules", None)
        card.pop("combat_redesign_proposal", None)
        card["print_revision"] = "force-only-d6"
        cards.append(card)
    return {
        "schema_version": legacy["schema_version"],
        "status": "experimental-paper-d6",
        "print_only": True,
        "rules_model": "force-only-d6-drawable-orders",
        "cards": cards,
    }



def load_paper_d6_support_cards() -> list[dict]:
    """Non-Force cards share the physical-card art and Command seal."""
    data = json.loads(PAPER_D6_SUPPORT.read_text(encoding="utf-8"))
    if data["schema_version"] != 1 or data["status"] != "canonical-paper-only":
        raise ValueError("Unknown Holding/Tactic schema")
    cards = data["cards"]
    if len(cards) != 12 or len({card["id"] for card in cards}) != 12:
        raise ValueError("Expected six Holdings and six Tactics")
    if sum(card["type"] == "holding" for card in cards) != 6 or sum(
        card["type"] == "tactic" for card in cards
    ) != 6:
        raise ValueError("Incorrect support type counts")
    output = []
    for entry in cards:
        if not 1 <= entry["command_cost"] <= 5 or not entry["effect"]:
            raise ValueError("Invalid non-Force card: " + entry["id"])
        output.append({
            "id": entry["id"],
            "title": entry["title"],
            "type": entry["type"],
            "art_id": entry["art_id"],
            "command_cost": entry["command_cost"],
            "paper_support": {"type": entry["type"], "effect": entry["effect"]},
            "unique": False,
            "classes": [],
            "effects": [],
            "rule_blocks": [],
            "text": entry["effect"],
            "print_revision": "war-deck",
        })
    return output


def load_paper_d6_war_cards(base=None, combat=None) -> dict:
    """Union for site/gallery/deck printing; old Force checks stay Force-only."""
    forces = load_paper_d6_cards(base, combat)
    supports = load_paper_d6_support_cards()
    ids = [card["id"] for card in forces["cards"] + supports]
    if len(ids) != len(set(ids)):
        raise ValueError("Force and non-Force IDs must be distinct")
    return {**forces, "cards": forces["cards"] + supports,
            "rules_model": "war-deck-d6-drawable-orders"}



def load_paper_d6_decks(card_data: dict | None = None) -> dict:
    if card_data is None:
        card_data = load_paper_d6_cards()
    data = json.loads(PAPER_D6_DECKS.read_text(encoding="utf-8"))
    known = {c["id"]: c for c in card_data["cards"]}
    for card in load_paper_d6_support_cards():
        known[card["id"]] = card
    ids = []
    for deck in data["decks"]:
        ids.append(deck["id"])
        seen = set()
        total = 0
        for item in deck["cards"]:
            cid, copies = item["id"], item["copies"]
            if cid not in known or cid in seen:
                raise ValueError("Unknown/duplicate paper D6 deck card: " + cid)
            seen.add(cid)
            if type(copies) is not int or not 1 <= copies <= (1 if known[cid]["unique"] else 4):
                raise ValueError("Invalid copy limit in paper D6 deck: " + cid)
            total += copies
        if total != 24:
            raise ValueError("War deck must contain 24 cards: " + deck["id"])
        force_count = sum(
            item["copies"] for item in deck["cards"]
            if known[item["id"]]["type"] in ("force", "hero")
        )
        if force_count < 16:
            raise ValueError("War deck must contain at least 16 Forces: " + deck["id"])
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate D6 deck IDs")
    return data
