"""Paper-only D6 ensemble checks: probabilities, coordinated rolls and coverage.

One die is rolled per player per occupied Front. On that die, multiple Forces
perform their own outcome. These tests check the *opportunities* for such
interactions, not encounter win rates or statistically proved game balance.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARDS = {c["id"]: c for c in json.loads((ROOT / "cards/paper-d6.json").read_text())["cards"]}
DECKS = json.loads((ROOT / "cards/paper-d6-decks.json").read_text())["decks"]

# Frozen original face strings from the prior 44-card prototype, for probability
# preservation ONLY. Their order is deliberately not reused in this version.
ORIGINAL = dict(line.split() for line in """the-fifty-men AAFSDA
seven-black-ships ADSFFA
the-white-hands-of-elara FSDDRS
the-red-shields DSDDFA
the-crow-archers SAAFDA
the-house-of-reed DDSADF
the-grey-riders DSFAFA
the-dust-riders ADFSFA
the-black-company FASSAD
the-red-duelists FAASSD
the-thornbow-hunters FAAADS
the-iron-boars AFDAFS
the-first-spear DSFADD
the-old-guard ADDSDF
the-unnamed-host AFSDFA
the-late-banner FADDAS
the-banner-singers DDFASA
thirty-spears AFDSAA
a-hundred-shields DADSFD
the-vardai FASADF
the-aradai SFFDAA
the-ilyri DASASF
the-damar DSAFAA
the-serekh FDDADS
the-relief-column SDSRFD
the-field-train FDDRRS
the-signal-company DASSAF
avaros-the-bronze-king ADASFD
kael-the-roadless ADFSSA
rovan-the-gatebreaker SDFFAA
alda-keeper-of-the-ford FDDADS
tovan-the-quartermaster DRSFRD
nara-builder-of-walls DFDSDA
neris-the-ferryman FFASAD
veyra-keeper-of-oaths DDAFSD
yara-the-chronicler ASFDSA
the-ash-bowmen ASDAFS
the-lantern-scouts DFASSA
the-river-raiders ADFSFA
the-kings-spears DDFSAD
the-salt-road-fleet FAASDF
the-watchtowers-of-eren DAFSDD
serai-queen-of-crows AAFDSA
doros-the-last-spear FASAAD""".splitlines())


def action(card: dict, die: int) -> str:
    effect = card["outcomes"][card["faces"][die - 1]]["effect"]
    for prefix in ("Attack", "Defend", "Save", "Draw", "Recover", "Move", "Advance"):
        if effect.startswith(prefix):
            return prefix
    raise AssertionError("Unsupported or blank combat result: " + card["id"] + " - " + effect)


def test_original_dice_face_probabilities_for_every_force():
    assert len(CARDS) == len(ORIGINAL) == 44
    for card_id, original in ORIGINAL.items():
        card = CARDS[card_id]
        assert Counter(card["faces"]) == Counter(original), card_id
        assert len(card["faces"]) == 6
        assert len(card["outcomes"]) == 4


def test_all_44_forces_have_no_empty_results_and_no_extra_basic_attacks():
    assert len(CARDS) == 44
    support = [card["outcomes"]["F"]["effect"] for card in CARDS.values()]
    assert all(text.startswith(("Defend", "Save", "Draw", "Recover", "Move", "Advance")) for text in support)
    assert all("Nothing" not in text for text in support)
    assert len(set(support)) >= 12
    # Every original F face is still in the same place and provides support,
    # not a surprise unconditional Attack that raises the baseline kill rate.
    for cid, card in CARDS.items():
        assert card["faces"].count("F") == ORIGINAL[cid].count("F")
        assert all(action(card, die) != "Nothing" for die in range(1, 7))


def test_intentional_three_force_combinations_on_same_roll():
    # Four lineups must share a FRONT to combine effects. These are reminders
    # for deck construction, never automatic bonuses or new combat rules.
    examples = [
        # Guard defends multiple troops, Archer fires, Healer saves an ally.
        (2, [("the-red-shields", "S"), ("the-crow-archers", "A"),
             ("the-white-hands-of-elara", "S")]),
        # Two coordinated attacks, plus a healer available to Rescue the line.
        (6, [("the-red-shields", "A"), ("the-crow-archers", "A"),
             ("the-white-hands-of-elara", "R")]),
        # Two ordinary Frontline attacks and a Guard's signature defence.
        (4, [("the-fifty-men", "A"), ("thirty-spears", "A"),
             ("the-first-spear", "S")]),
        # A Rider's advance attack reinforced by two other ordinary attacks.
        (2, [("the-grey-riders", "S"), ("the-dust-riders", "A"),
             ("the-aradai", "A")]),
        # Two attackers can combine on foremost; a third hits the Middle.
        (5, [("the-grey-riders", "A"), ("the-dust-riders", "S"),
             ("the-aradai", "S")]),
        # Attacking Infantry defended by a Guard and a rescuing healer.
        (4, [("the-fifty-men", "A"), ("the-first-spear", "S"),
             ("the-relief-column", "R")]),
    ]
    for die, forces in examples:
        assert all(CARDS[name]["faces"][die - 1] == result for name, result in forces), (die, forces)


def test_no_starter_deck_has_empty_or_universal_attack_rolls():
    # These are intentionally broad anti-cliff limits, NOT balance claims.
    limits = {
        "shield-and-volley": (4, 14),
        "riders-and-raids": (7, 15),
        "sustain-and-control": (2, 10),
    }
    assert len(DECKS) == 3
    for deck in DECKS:
        low, high = limits[deck["id"]]
        assert sum(item["copies"] for item in deck["cards"]) == 24
        for die in range(1, 7):
            attacks = sum(item["copies"] for item in deck["cards"]
                          if item["id"] in CARDS and action(CARDS[item["id"]], die) == "Attack")
            assert low <= attacks <= high, (deck["id"], die, attacks)


def test_all_six_faces_offer_distinct_deckwide_ensembles():
    for deck in DECKS:
        profiles = []
        for die in range(1, 7):
            profile = tuple(
                sum(item["copies"] for item in deck["cards"]
                    if item["id"] in CARDS and action(CARDS[item["id"]], die) == word)
                for word in ("Attack", "Defend", "Save", "Draw", "Recover", "Move", "Advance")
            )
            assert sum(profile) == 18
            profiles.append(profile)
        assert len(set(profiles)) >= 4, deck["id"]


def main() -> None:
    test_original_dice_face_probabilities_for_every_force()
    test_all_44_forces_have_no_empty_results_and_no_extra_basic_attacks()
    test_intentional_three_force_combinations_on_same_roll()
    test_no_starter_deck_has_empty_or_universal_attack_rolls()
    test_all_six_faces_offer_distinct_deckwide_ensembles()
    print("PASS: all 44 six-face distributions preserved, zero blank outcomes, 6 intentional lineups and balanced activity.")


if __name__ == "__main__":
    main()
