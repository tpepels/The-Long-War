"""Static tabletop gate for short, role-led battles (physical cards only).

Not an executable game simulation or proof of play balance.
Run: python tools/check_tactical_battlefeel.py
"""
from __future__ import annotations

from collections import Counter
import json

from print_cards import ROOT, load_print_cards

ROLES = ROOT / "cards/tactical-force-roles.json"
SHORT = ROOT / "rules/player-rulebook.md"
REFERENCE = ROOT / "rules/rulebook.md"
COMBAT = ROOT / "cards/combat-reference.md"
ROLE_SET = {"line", "guard", "archer", "rider", "skirmisher", "raider",
            "command", "support", "scout"}
MODIFIED = {
    "the-grey-riders", "the-damar", "the-vardai", "the-iron-boars",
    "the-unnamed-host", "seven-black-ships", "the-river-raiders",
    "the-black-company",
}


def formation_strength(base: int, bond: int = 0, name: int = 0,
                       shaken: bool = False, depleted: bool = False,
                       exhausted: bool = False, flanked: bool = False) -> int:
    return max(0, base + bond + name - 2 * int(shaken)
               - int(depleted) - int(exhausted) - int(flanked))


def can_incursion(attacker: int, defender: int | None, *,
                  front: bool = True, rear_target: bool = True,
                  depleted: bool = False, attack_unused: bool = True) -> bool:
    return (front and rear_target and not depleted and attack_unused
            and (defender is None or attacker > defender))


def run() -> None:
    printed = load_print_cards()
    cards = {c["id"]: c for c in printed["cards"]}
    roles = json.loads(ROLES.read_text(encoding="utf-8"))
    assert roles["schema_version"] == 1
    assert "design-only" in roles["scope"]
    force_ids = {cid for cid, c in cards.items() if c["type"] == "force"}
    assert len(cards) == 131 and len(force_ids) == 33
    seen = set()
    for role in roles["roles"]:
        cid = role["id"]
        assert cid not in seen and cid in force_ids, cid
        seen.add(cid)
        assert role["role"] in ROLE_SET, (cid, role)
        assert len(role["purpose"]) >= 32, cid
    assert seen == force_ids and len(roles["roles"]) == 33
    assert Counter(c["type"] for c in printed["cards"])["force"] == 33

    # Pure threshold/arithmetic examples exercise the proposed tabletop choice,
    # including the fact that combat bonuses and negative markers matter.
    assert not can_incursion(4, 5)
    assert can_incursion(4, formation_strength(5, shaken=True))
    assert can_incursion(4, 3)
    assert not can_incursion(4, 4)  # ties hold
    assert can_incursion(1, None)
    assert not can_incursion(4, None, front=False)
    assert not can_incursion(4, None, rear_target=False)
    assert not can_incursion(4, None, depleted=True)
    assert not can_incursion(4, None, attack_unused=False)
    assert can_incursion(formation_strength(3, bond=1, name=1),
                         formation_strength(6, flanked=True, shaken=True))
    assert not can_incursion(formation_strength(3, exhausted=True), 3)

    manual = SHORT.read_text(encoding="utf-8")
    detailed = REFERENCE.read_text(encoding="utf-8")
    quick = COMBAT.read_text(encoding="utf-8")
    for text in (manual, detailed, quick):
        assert "Incursion" in text, "Missing basic Raider check"
        assert "Archer" in text and "Shake" in text
        assert any(phrase in text for phrase in ("one Force", "one of your Forces", "one of their Forces")), "Defeat exhaustion must be one chosen Force"
        assert "every unprotected Force" not in text
        assert "all unprotected Forces" not in text
    assert "| **Archer** | Opposing Rear in same Front | Shake |" in manual
    assert "| **Archer** | Opposing Rear Force in the same Front | Shake it |" in detailed
    assert "one new Exhaustion token" in manual
    assert "if its current Strength is greater than" in manual
    assert "strictly greater" in detailed
    assert "A tie holds the line" in manual
    assert "Only a **card effect**" in manual
    assert "once per Battle" in detailed

    def text(card_id: str) -> str:
        return " ".join(e["text"] for e in cards[card_id]["effects"])

    assert set(MODIFIED) <= force_ids
    assert all(len(e["text"]) <= 190 for cid in MODIFIED
               for e in cards[cid]["effects"]), "Card text is too long"
    assert all(0 <= cards[cid]["command_cost"] <= 5 for cid in MODIFIED)
    for cid in ("seven-black-ships", "the-river-raiders"):
        assert "basic Raider Attack" in text(cid), cid
        assert "Frontline here is empty" not in text(cid), cid
    assert "Shaken" in text("the-iron-boars")
    assert "Shaken" in text("the-unnamed-host")
    assert "Depleted" in text("the-unnamed-host")
    assert "opponent loses" not in text("the-unnamed-host")
    assert "Shaken" in text("the-black-company")
    assert "without another Action" in text("the-grey-riders")
    assert "unused basic Rider Attack" in text("the-grey-riders")
    assert len(cards["the-grey-riders"]["effects"]) == 1
    vardai = cards["the-vardai"]["effects"]
    assert len(vardai) == 1 and vardai[0]["timing"] == "action"
    assert vardai[0].get("limit") == "once_per_battle"
    assert "Pay 1 Command" in vardai[0]["text"]
    assert "unused basic Rider Attack" in vardai[0]["text"]
    assert "newly legal" in text("the-damar")
    assert "without another Action" in text("the-damar")

    # Conditions and abilities are printed exceptions, not global rules.
    assert "after every Maneuver" not in manual and "after any Maneuver" not in manual
    assert printed["print_edge_cue_count"] == 32
    print("PASS: 131 printed identities; 33 design-only Force roles; "
          "Archer Shake, single-Force defeat Exhaustion, 9 local Incursion "
          "threshold/legality examples, 8 focused card effects, "
          "and card-granted combined Actions.")
    print("LIMIT: these are static contracts and examples, not AI or human match results.")


if __name__ == "__main__":
    run()
