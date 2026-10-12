"""Check the *optional* drawable Order prototype.

This check deliberately does not amend or assert the published paper game's
rulebook, whose Battle Plans are still a reusable menu.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    data = json.loads((ROOT / "cards/paper-d6-orders-prototype.json").read_text())
    assert data["status"] == "design-prototype-not-canonical"
    assert data["schema_version"] == 1
    assert data["deck_size_per_player"] == 12
    assert data["copies_per_order"] == 3
    assert data["starting_order_hand"] == 3
    assert data["orders_played_per_battle"] == 1
    assert data["replenish_orders_after_battle"] == 1
    assert data["discard_after_battle"] is True

    orders = data["orders"]
    assert len(orders) == 4
    assert {order["id"] for order in orders} == {"assault", "hold", "volley", "raid"}
    assert len(orders) * data["copies_per_order"] == data["deck_size_per_player"]
    assert all(order["title"] and order["effect"] and order["timing"]
               and order["symbol"] for order in orders)

    # These are precisely the existing tactical effects, repackaged as draw
    # cards, not new or secretly altered physical game mechanics.
    canonical = (ROOT / "web/tokens.html").read_text()
    lead = {"assault": "After combat, ", "hold": "Before rolling, ",
            "volley": "", "raid": "Before rolling, "}
    for order in orders:
        effect = order["effect"]
        canonical_text = (lead[order["id"]] + effect[0].lower() + effect[1:]
                          if lead[order["id"]] else effect)
        assert canonical_text in canonical, order["id"]

    markup = (ROOT / "web/orders-prototype.html").read_text()
    js = (ROOT / "web/orders-prototype.js").read_text()
    css = (ROOT / "web/orders-prototype.css").read_text()
    source = (ROOT / "tools/build_pages.py").read_text()

    assert "not yet the published rules" in markup
    assert "data/orders-prototype.json" in js
    assert "orders-prototype.json" in source
    assert 'Array.from({length:3}' in js
    assert 'id="order-hand"' in markup
    assert "function playSelected()" in js
    assert "68mm" in css and "96mm" in css
    assert "repeat(4,68mm)" in css and "repeat(2,96mm)" in css
    assert '@page{size:A4 landscape' in css

    # No canonical rules nor deck composition needs to change to preview this.
    rules = (ROOT / "rules/rulebook.md").read_text()
    assert "a **Command card**" in rules
    assert "four **Battle Plans**" in rules

    print("PASS: experimental 12-card drawable Order deck, unchanged effects, print format and hand simulator.")


if __name__ == "__main__":
    main()
