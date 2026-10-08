"""Lightweight print-only content checks; no native/Webgame compilation.

Run from repository root: python tools/check_print_cards.py
For actual physical text fit: python tools/check_card_layout.py --surface print --require-browser
"""
from __future__ import annotations

import json
from pathlib import Path

from print_cards import CANONICAL, OVERRIDES, load_print_cards


def main() -> None:
    executable_before = CANONICAL.read_bytes()
    base = json.loads(executable_before)
    overrides = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    printed = load_print_cards(base, overrides)
    before = {card["id"]: card for card in base["cards"]}
    after = {card["id"]: card for card in printed["cards"]}

    assert len(before) == len(after) == 131, "Card count changed"
    assert set(before) == set(after), "Card identities changed"
    assert printed["print_only"] is True, "Print cards not marked as separate source"
    assert all("design_rules" not in c for c in after.values()), "Stale engine spec leaked into print"
    assert all(before[i]["type"] == after[i]["type"] for i in before), "Card type changed"
    assert len(set(item["id"] for item in overrides["replacements"])) == len(overrides["replacements"]), "Duplicate print replacements"
    assert len(set(item["id"] for item in overrides.get("cost_adjustments", []))) == len(overrides.get("cost_adjustments", [])), "Duplicate cost adjustments"

    changed = set()
    for source in overrides["replacements"]:
        card_id = source["id"]
        changed.add(card_id)
        card = after[card_id]
        assert card["text"] != before[card_id]["text"], "Replacement not applied: " + card_id
        assert len(card["effects"]) == len(card["rule_blocks"]), "Rule blocks mismatch: " + card_id
        assert all(effect["text"] == block["text"]
                   for effect, block in zip(card["effects"], card["rule_blocks"])), card_id
        assert card["command_cost"] == source.get("command_cost", before[card_id]["command_cost"]), card_id
        if "allowed_rows" in source:
            assert card["allowed_rows"] == source["allowed_rows"], card_id
        if "strength_value" in source:
            key = "strength_modifier" if card["type"] == "bond" else "strength"
            assert card[key] == source["strength_value"], card_id
        for effect, block in zip(card["effects"], card["rule_blocks"]):
            if effect.get("limit") == "once_per_battle":
                assert "1/BATTLE" in block["label"], card_id
    for card_id in overrides["once_per_battle_text_fixes"]:
        changed.add(card_id)
        assert after[card_id]["text"].startswith("ACTION · 1/BATTLE"), card_id
        assert after[card_id]["effects"][0]["limit"] == "once_per_battle", card_id

    live = {"action", "attack", "reaction", "bonded", "while_named",
            "continuous", "front", "middle", "rear", "exhausted", "tireless", "mobile"}
    live_count = 0
    for card in printed["cards"]:
        if card["type"] not in ("force", "bond"):
            continue
        for effect in card.get("effects", []):
            if effect["timing"] in live:
                live_count += 1
                assert effect.get("exposed"), "Buried live ability missing: " + card["id"]
                assert len(effect["exposed"]) <= 75, "Very long print reminder: " + card["id"]

    for entry in overrides.get("cost_adjustments", []):
        card_id = entry["id"]
        changed.add(card_id)
        assert after[card_id]["command_cost"] == entry["command_cost"], card_id
        assert after[card_id]["command_cost"] != before[card_id]["command_cost"], card_id
        if card_id not in overrides["once_per_battle_text_fixes"]:
            assert after[card_id]["text"] == before[card_id]["text"], card_id

    # Verify representative counterplay and cost changes, not just text counts.
    assert after["the-first-spear"]["allowed_rows"] == ["front"]
    assert after["the-iron-boars"]["allowed_rows"] == ["front"]
    assert after["the-red-duelists"]["allowed_rows"] == ["front"]
    assert "Empowered" in after["the-crow-archers"]["text"]
    assert "Guarded" in after["guarded"]["text"]
    assert "Inspired" in after["endured-with"]["text"]
    assert "Depleted" in after["the-iron-boars"]["text"]
    assert after["no-one-would-be-first-to-leave"]["effects"][0]["limit"] == "once_per_battle"
    assert after["the-crows-came-down"]["effects"][0]["limit"] == "once_per_battle"

    for card_id in set(before) - changed:
        # Existing rules, stats and identities stay unchanged. Exposed-strip
        # text is a print-only display change, never a gameplay redesign.
        original, revised = before[card_id], after[card_id]
        assert revised["command_cost"] == original["command_cost"], card_id
        assert revised.get("strength") == original.get("strength"), card_id
        assert revised.get("strength_modifier") == original.get("strength_modifier"), card_id
        assert revised["text"] == original["text"], card_id

    assert CANONICAL.read_bytes() == executable_before, "Modified executable source"
    print(
        f"PASS: {len(after)} printed cards, {len(overrides['replacements'])} print replacements, "
        f"{len(overrides.get('cost_adjustments', []))} cost-only adjustments, "
        f"{len(overrides['once_per_battle_text_fixes'])} legacy printed limits, "
        f"{len(overrides['exposed_only'])} legacy strip fixes, {live_count} exposed live rules. "
        "Canonical native/Webgame cards unchanged."
    )


if __name__ == "__main__":
    main()
