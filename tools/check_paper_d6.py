"""Static integrity gate for the experimental physical D6 game.

This is not an alternate game engine and does not simulate combat.
Run: python tools/check_paper_d6.py
"""
from __future__ import annotations

import json
from pathlib import Path

from paper_d6_cards import PAPER_D6, PAPER_D6_DECKS, load_paper_d6_cards, load_paper_d6_decks
from print_cards import CANONICAL

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    executable_before = CANONICAL.read_bytes()
    raw = json.loads(PAPER_D6.read_text(encoding="utf-8"))
    printed = load_paper_d6_cards()
    decks = load_paper_d6_decks(printed)
    assert len(raw["cards"]) == len(printed["cards"]) == 44
    assert len({entry["id"] for entry in raw["cards"]}) == 44
    assert printed["print_only"] is True and printed["rules_model"] == "force-only-d6-army-wide-battle-plans"
    assert {c["type"] for c in printed["cards"]} == {"force", "hero"}
    assert sum(c["type"] == "force" for c in printed["cards"]) == 33
    assert sum(c["type"] == "hero" for c in printed["cards"]) == 11
    assert len(decks["decks"]) == 3
    assert decks["deck_size"] == 24
    assert all(sum(e["copies"] for e in deck["cards"]) == 24 for deck in decks["decks"])
    assert all("design_rules" not in c and "modes" not in c for c in printed["cards"])
    assert all(c["effects"] == [] and c["rule_blocks"] == [] for c in printed["cards"])
    assert all(not any(word in str(c["paper_d6"]).lower() for word in
                   ("bond", "named", "stratagem", "narrative", "exhausted"))
               for c in printed["cards"])
    assert all(len(c["paper_d6"]["faces"]) == 6 and
               len(c["paper_d6"]["outcomes"]) == 4 and
               set(c["paper_d6"]["faces"]) == set(c["paper_d6"]["outcomes"])
               for c in printed["cards"])
    assert all(1 <= c["paper_d6"]["force"] <= 6 and
               0 <= c["command_cost"] <= 20
               for c in printed["cards"])
    assert all(not c.get("hero_name_command_cost") for c in printed["cards"])

    # Preserve representative original die-face mappings through the simplification.
    cards = {c["id"]: c["paper_d6"]["faces"] for c in printed["cards"]}
    expected = [
        ("the-red-shields", "S", 2),
        ("the-crow-archers", "A", 2),
        ("the-white-hands-of-elara", "S", 2),
        ("the-fifty-men", "A", 1),
        ("the-river-raiders", "A", 1),
        ("tovan-the-quartermaster", "D", 1),
    ]
    for name, face, die in expected:
        assert cards[name][die - 1] == face, (name, die, face)
    assert CANONICAL.read_bytes() == executable_before, "Engine card pool changed"

    physical = (ROOT / "rules" / "player-rulebook.md").read_text(encoding="utf-8")
    aid = (ROOT / "web" / "tokens.html").read_text(encoding="utf-8")
    assert "D6" in physical and "Command card" in physical
    for plan in ("Assault", "Hold", "Volley", "Raid"):
        assert plan in aid
    for core in ("Defend", "Save", "Attack", "20 Command", "5 Command"):
        assert core in aid
    print("Card-led paper D6: 44 Forces/Heroes, 4 Plans and Command aid per player, 3 legal decks.")


if __name__ == "__main__":
    main()
