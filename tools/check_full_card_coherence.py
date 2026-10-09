"""Check the full 131-card physical design inventory and Opening Order reactions.

This is a print-data audit, NOT a match simulation or a native engine test.
Run: python tools/check_full_card_coherence.py
"""
from __future__ import annotations

from collections import Counter
import json

from print_cards import ROOT, load_print_cards

CATALOG = ROOT / "cards/full-card-coherence-audit.json"
MATRIX = ROOT / "cards/stratagem-opening-interactions.json"
MAIN = ROOT / "cards/playtest-decks.json"
LABS = ROOT / "cards/mechanic-coverage-decks.json"
RULES = ROOT / "rules/rulebook.md"
SHORT = ROOT / "rules/player-rulebook.md"

FAMILIES = {
    "force": 33, "bond": 24, "name": 20, "hero": 11,
    "tactic": 14, "stratagem": 11, "narrative": 12, "order": 6,
}
NEW = {
    "had-been-ordered-forward", "every-bow-was-strung",
    "the-scouts-had-warned-them",
}
CUES = {
    "had-been-ordered-forward": ("bonded", "Opening Orders", "Maneuvers", "Move"),
    "every-bow-was-strung": ("continuous", "Opening Orders", "Bonded Archers", "Strike", "Middle Force"),
    "the-scouts-had-warned-them": ("hidden", "Opening Orders are revealed", "Scout or Seer", "destination"),
}
WINDOWS = {
    "opening_reveal": 1,
    "move_reaction": 1,
    "attack_or_tactic_prevention": 1,
    "after_attack_reaction": 1,
    "negative_marker_reaction": 1,
    "named_completion": 1,
    "front_resolution": 5,
}


def effects(card):
    if card["type"] == "hero":
        return [
            *card["modes"]["force"]["effects"],
            *card["modes"]["name"]["effects"],
        ]
    return card["effects"]


def run() -> None:
    printed = load_print_cards()
    cards = {card["id"]: card for card in printed["cards"]}
    audit = json.loads(CATALOG.read_text(encoding="utf-8"))
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    rows = {row["id"]: row for row in audit["cards"]}
    plans = {row["id"]: row for row in matrix["stratagems"]}
    assert len(cards) == len(rows) == 131
    assert set(cards) == set(rows)
    assert Counter(c["type"] for c in cards.values()) == FAMILIES
    assert Counter(r["review"] for r in rows.values()) == {
        "coherent_on_paper": 101, "watch": 27, "new_opening_card": 3,
    }
    assert {cid for cid, r in rows.items() if r["review"] == "new_opening_card"} == NEW
    assert len(plans) == 11 == sum(c["type"] == "stratagem" for c in cards.values())
    assert set(plans) == {c["id"] for c in cards.values() if c["type"] == "stratagem"}
    assert Counter(p["window"] for p in plans.values()) == WINDOWS

    decks = []
    for file in (MAIN, LABS):
        decks.extend(json.loads(file.read_text(encoding="utf-8"))["decks"])
    assert len(decks) == 10
    assert all(sum(x["copies"] for x in d["cards"]) == 48 for d in decks)
    seen = set()
    for deck in decks:
        assert len({r["id"] for r in deck["cards"]}) == len(deck["cards"])
        for item in deck["cards"]:
            assert item["id"] in cards
            seen.add(item["id"])
    assert seen == set(cards)

    all_texts = []
    force_prices = []
    for cid, card in cards.items():
        row = rows[cid]
        assert row["title"] == card["title"] and row["type"] == card["type"]
        actual = effects(card)
        maximum = max((len(e["text"]) for e in actual), default=0)
        assert row["printed_effect_max_chars"] == maximum, (cid, "stale length")
        assert row["in_test_decks"] == [
            deck["id"] for deck in decks
            if any(entry["id"] == cid for entry in deck["cards"])
        ], (cid, "deck presence")
        if row["review"] == "watch":
            assert len(row["watch_reason"]) >= 30, cid
        for e in actual:
            assert e["text"] and e["timing"]
        if card["type"] == "hero":
            assert row["price"] == (
                f'Force {card["hero_force_command_cost"]} / '
                f'Name {card["hero_name_command_cost"]}'
            ), cid
        else:
            assert row["price"] == card["command_cost"], (cid, "price", row["price"], card["command_cost"])
            if card["type"] == "force":
                assert row["printed_strength"] == card["strength"]
                force_prices.append(card["command_cost"])
        joined = " ".join(e["text"] for e in actual)
        if joined:
            all_texts.append(joined.casefold())

    assert len(force_prices) == 33 and sum(force_prices) == 118
    assert Counter(force_prices) == {3: 17, 4: 13, 5: 3}
    assert len(all_texts) == len(set(all_texts)), "identical printed effects"

    for cid, (timing, *parts) in CUES.items():
        card = cards[cid]
        assert len(effects(card)) == 1 and effects(card)[0]["timing"] == timing
        text = effects(card)[0]["text"]
        assert len(text) <= 160
        assert all(part in text for part in parts), (cid, text)
        assert rows[cid]["review"] == "new_opening_card"
    assert cards["had-been-ordered-forward"]["strength_modifier"] == 0
    assert cards["every-bow-was-strung"]["command_cost"] == 1
    assert cards["the-scouts-had-warned-them"]["command_cost"] == 1

    for cid, strat in plans.items():
        assert strat["trigger"] and strat["effect"] and strat["distinct"]
        assert strat["window"] in WINDOWS
        if strat["window"] == "front_resolution":
            assert "At resolution" in " ".join(e["text"] for e in effects(cards[cid]))
        if strat["window"] == "opening_reveal":
            assert "Opening Orders are revealed" in " ".join(e["text"] for e in effects(cards[cid]))
    detailed = RULES.read_text(encoding="utf-8")
    simple = SHORT.read_text(encoding="utf-8")
    assert "a triggered reveal, not the later single" in detailed.lower()
    assert "The Scouts Had Warned Them" in detailed
    assert "The Battle Turned East" in detailed
    assert "The Archers Were Ready" in detailed and "No Step Back" in detailed
    assert "before either Strike's effects" not in detailed or "start of their paired Strike step" in detailed
    assert "resolution Stratagems wait until Opening Orders are complete" in simple
    print("PASS: 131 distinct printed identities, costs and roles; all ten 48-card decks cover 131")
    print("PASS: three Opening Order abilities and 11 disjoint Stratagem timing categories")
    print("PASS: 27 concrete watch cases preserved without pretending playtested balance")


if __name__ == "__main__":
    run()
