"""Integrity checks for the canonical, separately drawable paper Order deck.

The tactical effects are unchanged from the older reusable Battle Plans;
only their economy and draw/commit/discard interaction have changed.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "cards/paper-d6-orders.json"
EXPECTED = {
    "assault": (
        "After combat",
        "Advance one surviving Force one empty rank forward in each Front.",
    ),
    "hold": (
        "Before rolling",
        "Withdraw one Force one empty rank per Front. "
        "Your Defend results can protect any ally in their Front.",
    ),
    "volley": (
        "During combat",
        "Your Archers may Attack any enemy in their Front, including Middle and Rear.",
    ),
    "raid": (
        "Before rolling and during combat",
        "Move one Raider, Rider or Skirmisher per Front to an empty "
        "same-rank space in an adjacent open Front. They may Attack enemy "
        "Middle or Rear."
    ),
}


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert data["status"] == "canonical-paper-only"
    assert data["deck_size_per_player"] == 12
    assert data["copies_per_order"] == 3
    assert data["starting_order_hand"] == 3
    assert data["orders_played_per_battle"] == 1
    assert data["replenish_orders_after_battle"] == 1
    assert data["discard_after_battle"]
    assert len(data["orders"]) * data["copies_per_order"] == 12
    assert {order["id"] for order in data["orders"]} == set(EXPECTED)
    for order in data["orders"]:
        assert (order["timing"], order["effect"]) == EXPECTED[order["id"]]

    rulebook = (ROOT / "rules/rulebook.md").read_text(encoding="utf-8")
    assert "12-card Order deck" in rulebook
    assert "3 Orders" in rulebook
    assert "one Order from their hand" in rulebook
    assert "discard your played Order" in rulebook
    assert "Command card" not in rulebook and "Battle Plan" not in rulebook

    html = (ROOT / "web/orders.html").read_text(encoding="utf-8")
    script = (ROOT / "web/orders.js").read_text(encoding="utf-8")
    css = (ROOT / "web/orders.css").read_text(encoding="utf-8")
    build = (ROOT / "tools/build_pages.py").read_text(encoding="utf-8")
    assert "not yet the published rules" not in html
    assert "orders.css" in html and "orders.js" in html
    assert "data/orders.json" in script
    assert "orders-prototype.json" not in script
    assert "function playSelected()" in script and "function drawNewHand()" in script
    assert "state.copies=data.copies_per_order" in script
    assert "const twoPlayers=[...pool(),...pool()" in script
    assert "68mm" in css and "96mm" in css
    assert "repeat(4,68mm)" in css and "repeat(2,96mm)" in css
    assert '@page{size:A4 landscape' in css
    assert 'ROOT / "cards/paper-d6-orders.json"' in build
    assert 'data_dir / "orders.json"' in build

    assert "tokens.html" not in (ROOT / "web/playtest-kit.html").read_text()
    assert "orders.html" in (ROOT / "web/site-nav.template.html").read_text()
    assert "force-only-d6-drawable-orders" in (ROOT / "tools/paper_d6_cards.py").read_text()
    assert not (ROOT / "cards/paper-d6-orders-prototype.json").exists()

    print("PASS: canonical 12-card drawable Orders per player; four unchanged tactical effects; 3-card hand, one commit and replenishment each Battle.")


if __name__ == "__main__":
    main()
