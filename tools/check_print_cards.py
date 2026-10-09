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
        # A pure printed-Strength revision can deliberately retain the same
        # 'No special rules' text (e.g. The Fifty Men). Do not force a fake
        # ability onto a baseline Force merely to satisfy a text diff.
        assert (card["text"] != before[card_id]["text"]
                or card.get("strength") != before[card_id].get("strength")
                or card.get("strength_modifier") != before[card_id].get("strength_modifier")
                or card.get("command_cost") != before[card_id].get("command_cost")
                or card.get("allowed_rows") != before[card_id].get("allowed_rows")), (
                    "Replacement not applied: " + card_id)
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
    # Every live Force/Bond or Hero-Force ability gets a short cue.
    # It tells players when to check the body text without summarising payoff.
    edge_cues = overrides["edge_cues"]
    assert len(edge_cues) == printed["print_edge_cue_count"] == 32
    assert len({(x["id"], x["index"]) for x in edge_cues}) == len(edge_cues)
    for x in edge_cues:
        card = after[x["id"]]
        effects = (card["modes"]["force"]["effects"] if card["type"] == "hero"
                   else card["effects"])
        cue = effects[x["index"]]["edge_cue"]
        assert cue == x["cue"]
        assert len(cue) <= 16
        assert not any(word in cue for word in ("STRENGTH", "COMMAND", "COST", "DRAW", "MOVE"))
        # The printed effect array may differ from the canonical version;
        # checking the same index can be invalid after a replacement pass.
        original = before[x["id"]]
        original_effects = (original["modes"]["force"]["effects"]
                            if card["type"] == "hero" else original["effects"])
        assert all("edge_cue" not in effect for effect in original_effects), (
            "Print cue leaked into executable engine: " + x["id"]
        )

    # Hero copy fixes must not alter either playable mode or the canonical
    # engine card. Only an explicit effect text in the printable copy changes.
    for fix in overrides.get("hero_mode_wording", []):
        cid, mode, index = fix["id"], fix["mode"], fix["index"]
        assert before[cid]["type"] == "hero"
        assert before[cid]["modes"][mode]["effects"][index]["text"] == fix["old_text"]
        assert after[cid]["modes"][mode]["effects"][index]["text"] == fix["text"]
        assert len(after[cid]["modes"][mode]["effects"]) == len(
            before[cid]["modes"][mode]["effects"])

    # Physical Hero cards choose a role on PLAY; their printed Command cost
    # must be attached to that role. The two costs are independent and do
    # not grant both role abilities or both Strength values at once.
    hero_costs = overrides.get("hero_mode_costs", [])
    assert len(hero_costs) == 11, "All physical Heroes need explicit mode costs"
    assert len({item["id"] for item in hero_costs}) == len(hero_costs)
    assert {item["id"] for item in hero_costs} == {
        cid for cid, card in before.items() if card["type"] == "hero"
    }
    for entry in hero_costs:
        cid = entry["id"]
        changed.add(cid)
        original, revised = before[cid], after[cid]
        assert revised["command_cost"] == entry["force_cost"]
        assert revised["hero_force_command_cost"] == entry["force_cost"]
        assert revised["hero_name_command_cost"] == entry["name_cost"]
        for mode, cost_key in (("force", "force_cost"), ("name", "name_cost")):
            assert revised["modes"][mode]["command_cost"] == entry[cost_key]
        assert revised["force_strength"] == original["force_strength"]
        assert revised["name_strength_modifier"] == original["name_strength_modifier"]
        assert revised["classes"] == original["classes"]
        assert [x["timing"] for x in revised["modes"]["force"]["effects"]] == [
            x["timing"] for x in original["modes"]["force"]["effects"]]
        assert [x["timing"] for x in revised["modes"]["name"]["effects"]] == [
            x["timing"] for x in original["modes"]["name"]["effects"]]
    assert printed["print_hero_mode_price_count"] == 11

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
    # Every odd-Strength Force has an on-card compensation for the rounded
    # half-Strength step; even simple Thirty Spears now pay full baseline.
    assert after["the-fifty-men"]["strength"] == 5
    assert after["the-fifty-men"]["command_cost"] == 4
    assert "+1 Strength this Battle" in after["the-fifty-men"]["text"]
    assert "Frontline" in after["the-aradai"]["text"]
    assert after["the-damar"]["command_cost"] == 4
    assert after["thirty-spears"]["command_cost"] == 3
    assert "another friendly formation" in after["thirty-spears"]["text"]
    assert after["stood-fast-with"]["effects"][0]["exposed"]
    assert after["oren"]["effects"][1]["limit"] == "once_per_battle"
    assert after["the-thornbow-hunters"]["effects"][0]["timing"] == "rear"
    assert after["the-king-had-given-the-order"]["command_cost"] == 2
    assert after["the-king-had-given-the-order"]["effects"][0]["timing"] == "play"

    assert after["the-first-spear"]["allowed_rows"] == ["front"]
    assert after["the-iron-boars"]["allowed_rows"] == ["front"]
    assert after["the-red-duelists"]["allowed_rows"] == ["front"]
    assert "Empowered" in after["the-crow-archers"]["text"]
    assert "Guarded" in after["guarded"]["text"]
    assert "Inspired" in after["endured-with"]["text"]
    assert "Shaken" in after["the-iron-boars"]["text"]
    for card_id in ("no-one-would-be-first-to-leave", "the-crows-came-down"):
        effects = after[card_id]["effects"]
        assert effects[0]["timing"] == "play", card_id
        assert any(e["timing"] == "action" and e.get("limit") == "once_per_battle"
                   for e in effects), card_id

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
        f"{len(overrides['exposed_only'])} legacy strip fixes, "
        f"{len(edge_cues)} compact check cues, {live_count} exposed live rules. "
        "Canonical native/Webgame cards unchanged."
    )


if __name__ == "__main__":
    main()
