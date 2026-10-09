"""Validate all physical playtest decks and report enabler/payoff availability.

The two-group calculation measures only *seeing* cards in a random draw:
having an enabler and payoff in hand does NOT mean they can legally combine
on the current battlefield. No simulation or win rates are claimed.
"""
from __future__ import annotations

import json
from math import comb

from print_cards import ROOT, load_print_cards

DECK_SIZE = 48
MAIN_PATH = ROOT / "cards" / "playtest-decks.json"
COVERAGE_PATH = ROOT / "cards" / "mechanic-coverage-decks.json"


def _at_least_one_pair(total: int, enablers: int, payoffs: int, draws: int) -> float:
    """Exact hypergeometric probability for two disjoint card groups."""
    assert 0 <= draws <= total and enablers >= 0 and payoffs >= 0
    assert enablers + payoffs <= total

    def chance_no_group(excluded: int) -> float:
        remaining = total - excluded
        return comb(remaining, draws) / comb(total, draws) if remaining >= draws else 0.0

    return 1 - chance_no_group(enablers) - chance_no_group(payoffs) + chance_no_group(enablers + payoffs)


def _counts(deck: dict, cards: dict, *, require_named: bool = True) -> dict[str, int]:
    entries = deck["cards"]
    ids = [item["id"] for item in entries]
    assert len(ids) == len(set(ids)), deck["id"] + ": repeated catalogue entry"
    counts: dict[str, int] = {}
    for item in entries:
        ident, copies = item["id"], item["copies"]
        assert ident in cards, f"{deck['id']}: unknown card {ident}"
        assert type(copies) is int and 1 <= copies <= (1 if cards[ident].get("unique") else 4), (
            deck["id"], ident, copies)
        counts[ident] = copies
    assert sum(counts.values()) == DECK_SIZE, f"{deck['id']}: not 48 cards"
    type_count = lambda kind: sum(copies for cid, copies in counts.items()
                                  if cards[cid]["type"] == kind)
    assert type_count("force") >= 14 and type_count("name") >= (5 if require_named else 0), (
        deck["id"], "insufficient Forces / printed Names")
    return counts


def run() -> None:
    cards = {c["id"]: c for c in load_print_cards()["cards"]}
    assert len(cards) == 131
    main = json.loads(MAIN_PATH.read_text(encoding="utf-8"))
    labs = json.loads(COVERAGE_PATH.read_text(encoding="utf-8"))
    assert main["deck_size"] == labs["deck_size"] == DECK_SIZE
    assert len(main["decks"]) == 6 and len(labs["decks"]) == 4
    assert len({d["id"] for d in main["decks"]}) == 6
    assert len({d["id"] for d in labs["decks"]}) == 4
    assert set(d["id"] for d in main["decks"]).isdisjoint(d["id"] for d in labs["decks"])
    assert labs["not_standard_playtest_decks"] is True

    for deck in main["decks"]:
        counts = _counts(deck, cards)
        assert len(deck["combo_notes"]) >= 3 and len(deck["hypothesis"]) >= 25
        assert 2 <= len(deck["combo_packages"]) <= 5
        singletons = sum(v == 1 for v in counts.values())
        if deck["id"] not in {"the-last-watch", "broken-oaths"}:
            assert singletons <= 18, (deck["id"], "too many one-copy dependencies", singletons)
        else:
            print("    coverage-extension deck: includes rare one-copy cards intentionally")
        printed_command = sum(cards[i]["command_cost"] * n for i, n in counts.items())
        base_strength = sum(cards[i]["strength"] * n for i, n in counts.items()
                            if cards[i]["type"] == "force")
        print(f"  {deck['title']}: {len(counts)} titles, {singletons} singletons; "
              f"{printed_command} printed Command; {base_strength} printed Force Strength")
        for package in deck["combo_packages"]:
            assert package["label"] and package["enablers"] and package["payoffs"]
            assert set(package["enablers"]).isdisjoint(package["payoffs"]), (
                deck["id"], package["label"], "overlapping roles")
            assert set(package["enablers"] + package["payoffs"]) <= set(counts), (
                deck["id"], package["label"], "unlisted dependency")
            enabled = sum(counts[x] for x in package["enablers"])
            rewarded = sum(counts[x] for x in package["payoffs"])
            assert enabled >= 3 and rewarded >= 2, (
                deck["id"], package["label"], "missing redundant combo support")
            opening = _at_least_one_pair(DECK_SIZE, enabled, rewarded, 10)
            later = _at_least_one_pair(DECK_SIZE, enabled, rewarded, 20)
            # A deliberately modest availability floor, not gameplay strength.
            assert opening >= 0.4 and later >= 0.8, (
                deck["id"], package["label"], f"{opening:.0%} / {later:.0%}")
            print(f"    {package['label']}: {enabled} enablers + {rewarded} payoffs; "
                  f"10 seen {opening:.1%}, 20 seen {later:.1%}")

    for lab in labs["decks"]:
        counts = _counts(lab, cards)
        assert lab["focus"] and len(lab["observations"]) >= 3
        print(f"  COVERAGE {lab['title']}: {len(counts)} titles; {sum(counts.values())} cards")

    lab_cards = {d["id"]: {e["id"] for e in d["cards"]} for d in labs["decks"]}
    assert {"the-grey-riders", "the-dust-riders", "the-long-march",
            "the-battle-turned-east"} <= lab_cards["rider-flank-lab"]
    assert {"iria", "lysa-the-listener", "the-scouts-had-warned-them",
            "before-sunset-the-ford-would-be-ours"} <= lab_cards["seer-hidden-lab"]
    assert {"no-road-was-too-long", "the-house-of-reed", "the-field-train",
            "swore-again-to"} <= lab_cards["front-exchange-lab"]
    raw = next(d for d in labs["decks"] if d["id"] == "raw-strength-control")
    raw_force_ids = {e["id"] for e in raw["cards"]
                     if cards[e["id"]]["type"] == "force"}
    assert raw_force_ids == {"the-fifty-men", "thirty-spears", "a-hundred-shields",
                             "the-aradai"}
    assert all(not cards[cid]["effects"] for cid in raw_force_ids), (
        "Raw Force baseline should contain no printed Force abilities")
    # The exact catalogue requirement applies across ALL playable main
    # and diagnostic decks; newly authored cards must also be covered.
    covered = {e["id"] for d in main["decks"] + labs["decks"]
               for e in d["cards"]}
    missing = set(cards) - covered
    assert not missing, "No physical playtest deck for: " + ", ".join(sorted(missing))
    assert len(covered) == 131
    print(f"PASS: six combo/coverage-extension decks, four diagnostic decks, "
          f"all {len(covered)} printed identities represented; "
          "availability is NOT combo legality, card utility or win rate")


if __name__ == "__main__":
    run()
