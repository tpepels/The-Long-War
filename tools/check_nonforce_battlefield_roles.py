"""Audit dynamic battlefield jobs of every non-Force physical card.

Static printed-text contracts, not a tabletop or native-engine simulation.
Run: python tools/check_nonforce_battlefield_roles.py
"""
from __future__ import annotations

from collections import Counter
import json

from print_cards import ROOT, load_print_cards

AUDIT = ROOT / "cards/nonforce-battlefield-audit.json"
REVISED = {
    "kept-pace-with", "rallied-behind", "carried-messages-for",
    "watched-the-skies-for", "iria", "lysa-the-listener", "elian",
    "they-returned-with-names", "the-lines-held", "the-center-must-hold",
    "the-flank-was-refused", "they-knew-the-ground",
    "the-raiders-came-home-loaded", "send-a-runner",
    "kael-the-roadless", "rovan-the-gatebreaker",
    "neris-the-ferryman", "serai-queen-of-crows",
}
FAMILIES = {
    "bond": 24, "name": 20, "hero": 11, "tactic": 14,
    "stratagem": 11, "narrative": 12, "order": 6,
}
ROLES = {
    "intrigue", "attack", "disruption", "maneuver",
    "defence", "formation", "strength", "logistics",
}


def effects(card: dict) -> list[dict]:
    if card["type"] == "hero":
        return [
            *card["modes"]["force"]["effects"],
            *card["modes"]["name"]["effects"],
        ]
    return card["effects"]


def content(card: dict) -> str:
    return " ".join(e["text"] for e in effects(card))


def has(cards: dict, cid: str, *pieces: str) -> bool:
    value = content(cards[cid])
    return all(p in value for p in pieces)


def run() -> None:
    printed = load_print_cards()
    catalogue = {card["id"]: card for card in printed["cards"]}
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    rows = audit["rows"]
    assert len(catalogue) == 131
    assert audit["schema_version"] == 1 and audit["reviewed"] == 98

    nonforce = {cid: card for cid, card in catalogue.items()
                if card["type"] != "force"}
    assert Counter(c["type"] for c in nonforce.values()) == FAMILIES
    assert len(rows) == len(nonforce) == 98
    assert {r["id"] for r in rows} == set(nonforce)
    assert len({r["id"] for r in rows}) == len(rows)
    assert {r["id"] for r in rows if r["decision"] == "revised"} == REVISED
    assert Counter(r["decision"] for r in rows) == {
        "keep": 62, "watch": 18, "revised": 18,
    }

    for row in rows:
        cid = row["id"]
        card = nonforce[cid]
        assert row["title"] == card["title"]
        assert row["type"] == card["type"]
        assert row["role"] in ROLES
        assert row["reason"] and len(row["reason"]) > 25
        assert row["effect_length_max"] == max(
            len(effect["text"]) for effect in effects(card)
        ), (cid, "audit is stale")
        # Actual 63x88 mm cards have limited rule space; the revised
        # effects must be concise, not prose about multiple new phases.
        if row["decision"] == "revised":
            assert all(0 < len(e["text"]) <= 160
                       for e in effects(card)), (cid, content(card))

    for cid in ("kept-pace-with", "rallied-behind",
                "carried-messages-for"):
        assert "Move" in content(catalogue[cid]), cid
    assert has(catalogue, "watched-the-skies-for",
               "Stratagem", "Draw 1 card")
    assert has(catalogue, "iria", "Stratagem", "Move")
    assert has(catalogue, "lysa-the-listener", "opponent's hand", "Guarded")
    assert has(catalogue, "elian", "Pay 1 Command", "unused basic Attack",
               "without another Action")
    assert has(catalogue, "they-returned-with-names", "Named Formation",
               "Shaken", "Name text")
    for cid in ("the-lines-held", "the-center-must-hold",
                "the-flank-was-refused"):
        assert len(effects(catalogue[cid])) == 1
        assert effects(catalogue[cid])[0]["timing"] == "hidden"
        assert has(catalogue, cid, "At resolution", "Move", "+2 Strength")
    assert len(effects(catalogue["they-knew-the-ground"])) == 1
    assert has(catalogue, "they-knew-the-ground", "Move", "Seer", "Guarded")
    assert len(effects(catalogue["the-raiders-came-home-loaded"])) == 1
    assert has(catalogue, "the-raiders-came-home-loaded",
               "up to two", "Raider", "Skirmisher", "adjacent legal position")
    assert has(catalogue, "send-a-runner", "Scout in Rear",
               "Move", "Draw 1 card")

    # Hero price and mode timings remain untouched. New exceptions live on
    # their printed Force/Name panel and never grant a second Attack use.
    assert has(catalogue, "kael-the-roadless", "Stratagem", "Move")
    assert has(catalogue, "rovan-the-gatebreaker",
               "stronger", "opposing Frontline", "Shaken", "Move")
    assert has(catalogue, "neris-the-ferryman",
               "unused basic Rider Attack", "without another Action")
    assert has(catalogue, "serai-queen-of-crows",
               "Pay 1 Command", "Move one friendly Archer")
    for cid in ("elian", "neris-the-ferryman"):
        assert "unused basic" in content(catalogue[cid])
    assert printed["print_only"] is True
    print("PASS: all 98 non-Force printed identities mapped to battlefield roles")
    print("  18 concise revisions, 62 deliberately retained, "
          "18 opportunities flagged for real tabletop checks")
    print("  Tactical improvements live on cards; core player rules unchanged")
    print("LIMIT: no evidence of actual activation rates, win rates or comeback balance")


if __name__ == "__main__":
    run()
