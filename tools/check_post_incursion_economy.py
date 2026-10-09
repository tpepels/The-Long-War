"""Post-Incursion paper-card price and mechanics audit.

Validates exactly the PRINTED pool, not executable/native card content.
These static assertions are coherence checks, not evidence of play balance.
    python tools/check_post_incursion_economy.py
"""
from __future__ import annotations

from collections import Counter
import json

from print_cards import ROOT, load_print_cards

LEDGER = ROOT / "cards/force-pricing.json"
RULES = ROOT / "rules/player-rulebook.md"
COSTLY_FREE_ATTACK = {"the-damar", "the-grey-riders"}
WATCH_EFFECTS = {
    "the-fifty-men", "the-aradai", "the-damar",
    "a-volley-before-dawn", "shared-the-spoils-with", "brannoc",
}
EXPECTED_TYPES = {
    "force": 33, "bond": 24, "name": 20, "hero": 11,
    "tactic": 14, "stratagem": 11, "narrative": 12, "order": 6,
}


def main() -> None:
    printed = load_print_cards()
    cards = {c["id"]: c for c in printed["cards"]}
    assert len(cards) == 131 and Counter(c["type"] for c in cards.values()) == EXPECTED_TYPES
    forces = {cid: c for cid, c in cards.items() if c["type"] == "force"}
    rows = json.loads(LEDGER.read_text(encoding="utf-8"))["forces"]
    prices = {row["id"]: row for row in rows}
    assert len(prices) == len(rows) == len(forces) == 33
    odd = []
    discount = []
    ability_premiums = []
    for cid, force in forces.items():
        p = prices[cid]
        strength = force["strength"]
        tariff = 1 + (strength + 1) // 2
        premium = p["premium"]
        credit = p.get("unused_half_point_credit", 0)
        assert premium in (0, 1) and credit == 0
        assert force["command_cost"] == tariff + premium - credit, (cid, strength, force["command_cost"], tariff, premium, credit)
        assert force["command_cost"] >= 3, cid
        if premium:
            ability_premiums.append(cid)
        if strength % 2:
            odd.append(cid)
            # On the rounded-up step, every odd Force has a useful
            # printed effect, never a below-baseline price credit.
            assert force["effects"] and credit == 0, (cid, "odd Strength without an ability")
        if credit:
            discount.append(cid)
        if cid in COSTLY_FREE_ATTACK:
            assert premium == 1, (cid, "free Attack must pay premium")
    assert discount == [], "Strict Force base tariff has no discount exceptions"
    assert len(odd) >= 20
    assert cards["thirty-spears"]["command_cost"] == 3
    assert "another friendly formation" in cards["thirty-spears"]["effects"][0]["text"]
    assert cards["the-damar"]["command_cost"] == 4
    assert cards["the-fifty-men"]["strength"] == 5
    assert cards["the-aradai"]["command_cost"] == 3
    assert "another friendly Human" in cards["the-fifty-men"]["effects"][0]["text"]
    assert "opposing Frontline" in cards["the-aradai"]["effects"][0]["text"]

    # Basic shared Attacks changed exactly in the human-facing handbook;
    # supplemental precision and per-card exceptions stay off this page.
    rules = RULES.read_text(encoding="utf-8")
    assert "| **Archer** | Opposing Rear in same Front | Shake |" in rules
    assert "Raider" in rules and "successful Incursion" in rules
    assert "Choose **one Force in each lost Front**" in rules
    assert "Only a **card effect** can combine" in rules

    # No role-specific rule may create an unlimited Attack/action cascade.
    grey = cards["the-grey-riders"]["effects"]
    damar = cards["the-damar"]["effects"]
    vardai = cards["the-vardai"]["effects"]
    assert len(grey) == len(damar) == len(vardai) == 1
    assert grey[0]["timing"] == "continuous"
    assert "unused basic Rider Attack" in grey[0]["text"]
    assert damar[0]["timing"] == "play" and "newly legal" in damar[0]["text"]
    assert vardai[0]["timing"] == "action" and vardai[0]["limit"] == "once_per_battle"
    assert "Pay 1 Command" in vardai[0]["text"]

    def text(cid):
        return " ".join(e["text"] for e in cards[cid]["effects"])

    # No stale empty-Frontline restrictions on attachment-raiding Forces.
    for cid in ("the-river-raiders", "seven-black-ships"):
        assert "basic Raider Attack" in text(cid)
        assert "Frontline here is empty" not in text(cid)
    # Different tactical classes can now set up a break, exploit it, or
    # rescue a formation, instead of all copying Raider depletion.
    assert "Shaken" in text("the-iron-boars")
    assert "Shaken" in text("the-unnamed-host") and "Depleted" in text("the-unnamed-host")
    assert "Shaken" in text("the-black-company")
    assert "Shaken" in text("brannoc")
    assert "Shaken" in text("a-volley-before-dawn")
    assert "Move" in text("shared-the-spoils-with")
    assert "opponent loses" not in text("shared-the-spoils-with")
    assert cards["shared-the-spoils-with"]["strength_modifier"] == 0
    # Preserve alternate Exhaustion interactions rather than converting
    # every piece of the deck to Shaken.
    for cid in ("the-baggage-was-abandoned", "they-were-gathering-there",
                "the-crows-came-down"):
        assert "Exhaust" in text(cid), cid
    assert "Exhausted" in text("the-trap-closed") or "negative marker" in text("the-trap-closed")
    # Brannoc's separately PAID ACTION remains repeatable; migration of
    # its named-completion check must not quietly limit the old ability.
    assert cards["brannoc"]["effects"][1]["timing"] == "action"
    assert "limit" not in cards["brannoc"]["effects"][1]

    # Survey remaining card families for core economic protection:
    # no incidental repricing of Bonds or Heroes or unpriced free Orders.
    bonds = [c for c in cards.values() if c["type"] == "bond"]
    heroes = [c for c in cards.values() if c["type"] == "hero"]
    tactics = [c for c in cards.values() if c["type"] == "tactic"]
    orders = [c for c in cards.values() if c["type"] == "order"]
    assert all(c["command_cost"] == 1 for c in bonds)
    assert all(0 <= c["command_cost"] <= 2 for c in tactics + orders)
    assert all(c["hero_force_command_cost"] >= 3 and c["hero_name_command_cost"] >= 1 for c in heroes)
    assert sum(c["command_cost"] for c in forces.values()) >= 118
    for cid in WATCH_EFFECTS:
        c = cards[cid]
        assert all(0 < len(e["text"]) <= 190 for e in c["effects"]), cid

    print(f"PASS: 131 cards, 33 Force price identities, {len(odd)} odd-Strength Forces")
    print(f"  1 + ceil(STR/2) + priced premium, no below-tariff discount; {len(ability_premiums)} premium Forces")
    print(f"  Explicit plain-Force discount: {discount}")
    print("  Tactical consistency: Archer Shake, Raider Incursion, chosen Force Exhaustion,")
    print("  paid combined Actions, Shaken/Exhausted support and eight card families.")
    print("LIMIT: no direct gameplay sampling or claim of card balance.")


if __name__ == "__main__":
    main()
