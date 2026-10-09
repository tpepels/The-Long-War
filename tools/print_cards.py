"""Assemble physical-print card faces without changing native/Webgame card data.

The canonical cards.json remains executable input. Print-only revisions in
cards/print-overrides.json are applied solely to Pages' printable catalogue,
playtest decks and print layout checker.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OVERRIDES = ROOT / "cards" / "print-overrides.json"
CANONICAL = ROOT / "cards" / "cards.json"

LABELS = {
    "play": "PLAY", "attack": "ATTACK", "middle": "MIDDLE",
    "bonded": "BONDED", "hidden": "HIDDEN", "continuous": "CONTINUOUS", "becomes_named": "BECOMES NAMED",
    "action": "ACTION", "reaction": "REACTION", "trigger": "TRIGGER",
    "front": "FRONT", "rear": "REAR", "while_named": "WHILE NAMED",
}
ONGOING = {"attack", "middle", "bonded", "while_named", "action", "reaction", "front", "rear", "continuous", "tireless", "mobile"}
CARD_TYPES = {"force", "bond", "name", "hero", "tactic", "order", "stratagem", "narrative"}
RANKS = {"front", "middle", "rear"}


def print_effect_label(effect: dict) -> str:
    label = LABELS[effect["timing"]]
    if effect.get("limit") == "once_per_battle":
        return label + " · 1/BATTLE"
    return label


def load_print_cards(base: dict | None = None, overrides: dict | None = None) -> dict:
    """Return an independent print-only copy; never mutate executable source."""
    if base is None:
        base = json.loads(CANONICAL.read_text(encoding="utf-8"))
    if overrides is None:
        overrides = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    if overrides.get("format") != "physical-print-overrides-v1":
        raise ValueError("Unknown print override version")

    printed = deepcopy(base)
    by_id = {card["id"]: card for card in printed["cards"]}
    if len(by_id) != len(printed["cards"]):
        raise ValueError("Duplicate canonical card identity")
    seen = set()

    for change in overrides["replacements"]:
        card_id = change["id"]
        if card_id in seen or card_id not in by_id:
            raise ValueError("Unknown or duplicate print replacement: " + card_id)
        seen.add(card_id)
        card = by_id[card_id]
        if "command_cost" in change:
            card["command_cost"] = change["command_cost"]
        if "allowed_rows" in change:
            allowed = change["allowed_rows"]
            if card["type"] != "force" or not isinstance(allowed, list) or not allowed or len(set(allowed)) != len(allowed) or not set(allowed) <= RANKS:
                raise ValueError("Invalid printable row restriction: " + card_id)
            card["allowed_rows"] = deepcopy(allowed)
        if "strength_value" in change:
            key = "strength_modifier" if card["type"] == "bond" else "strength"
            if card["type"] not in ("bond", "force"):
                raise ValueError("Invalid strength override: " + card_id)
            card[key] = change["strength_value"]
        effects = deepcopy(change["effects"])
        for effect in effects:
            if effect["timing"] not in LABELS:
                raise ValueError("Unsupported print timing for " + card_id)
            if not effect.get("text"):
                raise ValueError("Empty print effect for " + card_id)
            if effect["timing"] in ONGOING and card["type"] in ("force", "bond") and not effect.get("exposed"):
                raise ValueError("Buried live effect has no exposed strip: " + card_id)
        if card["type"] == "hero":
            raise ValueError("Hero mode replacement requires explicit print model")
        card["effects"] = effects
        card["text"] = "\n".join(print_effect_label(e) + " - " + e["text"] for e in effects) or "No special rules."
        card["rule_blocks"] = [
            {"kind": "continuous" if e["timing"] in ONGOING else "effect",
             "label": print_effect_label(e), "text": e["text"]}
            for e in effects
        ]
        card["print_revision"] = "physical-rules-v2"
        # Executable specs from the source would describe the OLD effects.
        # Never leak stale design_rules into the physical-print JSON.
        card.pop("design_rules", None)
        card.pop("combat_redesign_proposal", None)

    # Hero Force/Name faces are stored in separate mode effect arrays.
    # Support presentation-only wording corrections without replacing either
    # mode or mutating the native/Webgame canonical card definitions.
    hero_fixes = overrides.get("hero_mode_wording", [])
    hero_targets = set()
    for fix in hero_fixes:
        card_id = fix["id"]
        mode = fix["mode"]
        index = fix["index"]
        key = (card_id, mode, index)
        if key in hero_targets or card_id not in by_id or by_id[card_id]["type"] != "hero":
            raise ValueError("Invalid or duplicate Hero wording override: " + str(key))
        hero_targets.add(key)
        if mode not in ("force", "name"):
            raise ValueError("Unknown Hero mode in print override: " + str(key))
        effects = by_id[card_id]["modes"][mode]["effects"]
        if type(index) is not int or not 0 <= index < len(effects):
            raise ValueError("Invalid Hero effect index: " + str(key))
        if effects[index]["text"] != fix["old_text"] or not fix.get("text"):
            raise ValueError("Hero wording override stale or empty: " + str(key))
        effects[index]["text"] = fix["text"]
        by_id[card_id]["print_revision"] = "hero-wording"
        by_id[card_id].pop("design_rules", None)
        by_id[card_id].pop("combat_redesign_proposal", None)

    limit_ids = overrides.get("once_per_battle_text_fixes", [])
    if len(set(limit_ids)) != len(limit_ids):
        raise ValueError("Duplicate print timing fix")
    for card_id in limit_ids:
        if card_id not in by_id or card_id in seen:
            raise ValueError("Invalid print timing fix: " + card_id)
        card = by_id[card_id]
        if len(card.get("effects", [])) != 1 or card["effects"][0]["timing"] != "action":
            raise ValueError("Unexpected action shape: " + card_id)
        card["effects"][0]["limit"] = "once_per_battle"
        card["text"] = "ACTION · 1/BATTLE - " + card["effects"][0]["text"]
        card["rule_blocks"] = [
            {"kind": "effect", "label": "ACTION · 1/BATTLE",
             "text": card["effects"][0]["text"]}
        ]
        card["print_revision"] = "timing-correction"
        card.pop("design_rules", None)
        card.pop("combat_redesign_proposal", None)

    for fix in overrides.get("exposed_only", []):
        card_id = fix["id"]
        if card_id in seen or card_id in limit_ids or card_id not in by_id:
            raise ValueError("Invalid pre-existing print strip reminder: " + card_id)
        card = by_id[card_id]
        if card["type"] not in ("force", "bond"):
            raise ValueError("Live reminder must belong to Force or Bond: " + card_id)
        index = fix["index"]
        effects = card.get("effects", [])
        if not isinstance(index, int) or index < 0 or index >= len(effects):
            raise ValueError("Invalid live reminder effect index: " + card_id)
        if effects[index]["timing"] not in ONGOING:
            raise ValueError("Cannot expose non-live effect: " + card_id)
        if not fix.get("exposed"):
            raise ValueError("Empty live reminder: " + card_id)
        effects[index]["exposed"] = fix["exposed"]
        card["print_revision"] = "stack-reminder"
        card.pop("design_rules", None)
        card.pop("combat_redesign_proposal", None)

    cost_seen = set()
    for change in overrides.get("cost_adjustments", []):
        card_id = change["id"]
        if card_id not in by_id or card_id in seen or card_id in cost_seen:
            raise ValueError("Invalid print-only cost adjustment: " + card_id)
        cost_seen.add(card_id)
        new_cost = change["command_cost"]
        if not isinstance(new_cost, int) or isinstance(new_cost, bool) or not 0 <= new_cost <= 20:
            raise ValueError("Invalid printed Command cost: " + card_id)
        card = by_id[card_id]
        card["command_cost"] = new_cost
        card["print_revision"] = "command-cost-correction"
        card.pop("design_rules", None)
        card.pop("combat_redesign_proposal", None)

    # All buried, live abilities need a visible reminder; no silent fallback to
    # 100+ character body text which would overflow the 10.5 mm exposed edge.
    for card in printed["cards"]:
        if card["type"] not in ("force", "bond"):
            continue
        for effect in card.get("effects", []):
            if effect.get("timing") in ONGOING and not effect.get("exposed"):
                raise ValueError("Buried effect lacks an exposed reminder: " + card["id"])

    # Printed cards are presentation data, not an executable rules source.
    # Drop stale engine instructions and unimplemented proposal fields in ALL
    # cards to prevent this separate export being mistaken for cards.json.
    for card in printed["cards"]:
        card.pop("design_rules", None)
        card.pop("combat_redesign_proposal", None)

    if set(by_id) != {c["id"] for c in base["cards"]}:
        raise ValueError("Print overlays changed card identities")
    if len(printed["cards"]) != len(base["cards"]):
        raise ValueError("Print overlay changed card count")

    printed["status"] = "physical-print-only"
    printed["print_only"] = True
    printed["print_override_count"] = len(seen)
    printed["print_hero_wording_count"] = len(hero_targets)
    printed["print_timing_fix_count"] = len(limit_ids)
    printed["print_cost_adjustment_count"] = len(cost_seen)
    return printed
