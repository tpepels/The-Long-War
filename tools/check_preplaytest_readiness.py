"""Pre-playtest usefulness gate for the 131 physical-print cards.

Checks coverage, counterfactual probes, obvious dominance/no-op regressions
and opportunity accounting. This is NOT a rules simulator or a win-rate test.

    python tools/check_preplaytest_readiness.py
    python tools/check_preplaytest_readiness.py --inventory
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json

from print_cards import ROOT, load_print_cards

FOCUS_PATH = ROOT / "cards/preplaytest-focus.json"
MAIN_PATH = ROOT / "cards/playtest-decks.json"
LAB_PATH = ROOT / "cards/mechanic-coverage-decks.json"
EXPECTED_TYPES = {
    "force": 33, "bond": 24, "name": 20, "hero": 11,
    "tactic": 14, "stratagem": 11, "narrative": 12, "order": 6,
}
ALL_NONBASELINE = {"tactic", "stratagem", "narrative", "order"}
BASELINE_TYPES = {"force", "bond", "name", "hero"}
# Guardrails for problems already established by literal printed text.
DOMINATED_PAIR = ("all-banners-forward", "they-let-them-through")
EMPTY_MOVE = "the-ilyri"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def effect_texts(card):
    if card["type"] == "hero":
        return [
            mode + ":" + effect["text"]
            for mode in ("force", "name")
            for effect in card["modes"][mode]["effects"]
        ]
    return [effect["text"] for effect in card.get("effects", [])]


def baseline(card):
    kind = card["type"]
    if kind == "force":
        return f'{card["strength"]} Strength + classifications/Attacks'
    if kind == "bond":
        value = card.get("strength_modifier", 0)
        return f'{value:+} Strength; unlocks Named completion'
    if kind == "name":
        return f'{card.get("strength_modifier", 1):+} Strength; completes Named formation'
    if kind == "hero":
        return (
            f'{card["modes"]["force"]["strength"] if "strength" in card["modes"]["force"] else card["force_strength"]} Force Strength OR '
            f'+1 Name Strength; only one mode per play'
        )
    return "NO BODY: useful target and immediate/hidden payoff required"


def run(inventory=False):
    catalogue = load_print_cards()["cards"]
    cards = {card["id"]: card for card in catalogue}
    assert len(catalogue) == len(cards) == 131
    assert Counter(card["type"] for card in catalogue) == EXPECTED_TYPES

    main = read(MAIN_PATH)["decks"]
    labs = read(LAB_PATH)["decks"]
    assert len(main) == 6 and len(labs) == 4
    standard, specialist = defaultdict(list), defaultdict(list)
    for label, decks, holder in (("standard", main, standard), ("lab", labs, specialist)):
        for deck in decks:
            for entry in deck["cards"]:
                cid = entry["id"]
                assert cid in cards, (label, deck["id"], cid)
                holder[cid].append((deck["id"], entry["copies"]))
    assert set(standard) | set(specialist) == set(cards), "Unrepresented printable card"

    uncovered_standard = set(cards) - set(standard)
    assert len(uncovered_standard) == 20, (
        "Re-examine standard-only coverage changes instead of hiding them",
        len(uncovered_standard),
    )
    focus = read(FOCUS_PATH)
    assert focus["schema_version"] == 1
    rows = focus["focus"]
    focus_ids = [case["id"] for case in rows]
    assert len(rows) >= 40, "Too few targeted no-op / tempo / specialist probes"
    assert len(focus_ids) == len(set(focus_ids))
    assert set(focus_ids) <= set(cards)
    assert uncovered_standard <= set(focus_ids), (
        "Cards missing from standard decks must all have specific lab probes",
        sorted(uncovered_standard - set(focus_ids)),
    )
    for case in rows:
        for field in ("opportunity", "comparison", "failure_signal"):
            assert isinstance(case.get(field), str) and len(case[field]) >= 55, (
                case["id"], "Weak or missing " + field,
            )
        assert "Compare " in case["comparison"] or "compare " in case["comparison"], (
            case["id"], "No explicit counterfactual"
        )

    for card in catalogue:
        kind, texts = card["type"], effect_texts(card)
        assert kind in BASELINE_TYPES or kind in ALL_NONBASELINE
        if kind in ALL_NONBASELINE:
            assert texts and all(text.strip() for text in texts), (
                card["id"], "No body or operative effects"
            )
        elif kind == "hero":
            assert card["modes"]["force"]["effects"] and card["modes"]["name"]["effects"], card["id"]
        assert all(text.strip() for text in texts), card["id"]

    # Prevent the exact dominated action-denial pairing from returning.
    all_banners, let_through = [cards[i] for i in DOMINATED_PAIR]
    assert all_banners["command_cost"] == let_through["command_cost"] == 1
    first, second = " ".join(effect_texts(all_banners)), " ".join(effect_texts(let_through))
    assert "King or Captain" in first and "Shaken" in first, first
    assert "another opposing formation" in first and "−1 Strength" in first, first
    assert "ACTION abilities cannot be used" not in first, "Dominated leader Tactic returned"
    assert "ACTION abilities cannot be used" in second and "Name contributes no Strength" in second

    # Moving to an empty square at PLAY is usually indistinguishable from simply
    # choosing that deployment square. A swap into occupied spaces has real utility.
    ilyri = cards[EMPTY_MOVE]
    assert ilyri["strength"] == 2 and ilyri["command_cost"] == 3
    ilyri_text = " ".join(effect_texts(ilyri))
    assert "swap this formation" in ilyri_text and "Guarded" in ilyri_text, ilyri_text
    assert "adjacent active empty position" not in ilyri_text

    # A 2-Strength/3C support must create an immediate, paid-for choice;
    # the Relief Column's 3 Strength remains a viable floor but its ability
    # must do more than restore a rare Maneuver permission.
    train, signal, relief = (cards[i] for i in
        ("the-field-train", "the-signal-company", "the-relief-column"))
    assert train["strength"] == signal["strength"] == 2
    assert all(c["command_cost"] == 3 for c in (train, signal, relief))
    assert all(c["allowed_rows"] == ["middle"] for c in (train, signal, relief))
    assert relief["strength"] == 3
    assert all(c["effects"][0]["timing"] == "play"
               for c in (train, signal, relief))
    assert "without another Action" in " ".join(effect_texts(train))
    assert "adjacent active Front" in " ".join(effect_texts(train))
    assert "Guarded" in " ".join(effect_texts(train))
    assert "another friendly formation" in " ".join(effect_texts(signal))
    assert "flanked" in " ".join(effect_texts(signal))
    assert "draw 1 card" in " ".join(effect_texts(signal))
    assert "negative markers" in " ".join(effect_texts(relief))
    assert "Guarded" in " ".join(effect_texts(relief))

    # Similar-looking Tactics have different payoffs, and the zero-Command
    # alternative is not accidentally identical to the paid fallback.
    bait = " ".join(effect_texts(cards["the-line-was-baited"]))
    far = " ".join(effect_texts(cards["they-had-gone-too-far"]))
    assert cards["the-line-was-baited"]["command_cost"] == 0
    assert cards["they-had-gone-too-far"]["command_cost"] == 1
    assert "Depleted" in bait and "Shaken" in far, "Forced-retreat differentiation lost"

    only_labs = Counter(cards[cid]["type"] for cid in uncovered_standard)
    focused = Counter(cards[cid]["type"] for cid in focus_ids)
    no_bodies = sum(cards[cid]["type"] in ALL_NONBASELINE for cid in cards)
    print(
        f"PASS: {len(cards)} physical identities reviewed; "
        f"{len(focus_ids)} specific counterfactual probes, "
        f"{len(uncovered_standard)} lab-only cards all in focus cases; "
        f"{no_bodies} cards without a formation-strength baseline"
    )
    print("  Lab-only by family:", dict(sorted(only_labs.items())))
    print("  Focus cases by family:", dict(sorted(focused.items())))
    print("  Distinct leader disruption, non-vacuous Ilyri swap, "
          "and differentiated retreat Tactics checked")
    if inventory:
        print("\nID | TYPE | CMD | DEFAULT VALUE | STANDARD DECKS | LAB DECKS | PROBE")
        for card in catalogue:
            cid = card["id"]
            c = (f'{card["hero_force_command_cost"]}/{card["hero_name_command_cost"]}'
                 if card["type"] == "hero" else str(card["command_cost"]))
            deck_list = lambda source: ",".join(f"{name}x{num}" for name,num in source.get(cid, [])) or "-"
            risk = "FOCUS" if cid in focus_ids else "BASELINE/ROUTINE"
            print(f'{cid} | {card["type"]} | {c} | {baseline(card)} | '
                  f'{deck_list(standard)} | {deck_list(specialist)} | {risk}')
        print("\nTargeted questions, to be answered by human playtests:")
        for case in rows:
            print(f'\n{cards[case["id"]]["title"]}: {case["opportunity"]}')
            print(f'  Counterfactual: {case["comparison"]}')
            print(f'  Failure: {case["failure_signal"]}')
    print(
        "LIMIT: legal setup and meaningful choice are prospective tabletop probes. "
        "Neither coverage, a printed baseline nor a synthetic case establishes "
        "activation rates, utility, Command efficiency or win rates."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", action="store_true", help="Print every card and all 44+ focused probes")
    opts = parser.parse_args()
    run(opts.inventory)
