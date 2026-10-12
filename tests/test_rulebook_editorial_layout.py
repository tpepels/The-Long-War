"""Card-led physical game: separate drawable Orders, not reusable Plan aids."""
from pathlib import Path
import json

import markdown

from tools.build_pages import enrich_rulebook_layout, group_rulebook_sections
from tools.build_rulebook_pdf import markdown_to_typst

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "rules/rulebook.md"
PLAYER = ROOT / "rules/player-rulebook.md"
CARDS = ROOT / "cards/paper-d6.json"
ORDERS = ROOT / "cards/paper-d6-orders.json"


def test_rules_are_one_short_self_contained_game_loop():
    rules = CANONICAL.read_text(encoding="utf-8")
    assert rules == PLAYER.read_text(encoding="utf-8")
    assert 180 <= len(rules.split()) <= 290
    assert rules.count("\n## ") == 5
    for term in ("Prepare", "Deploy", "Order", "Fight", "Continue", "D6",
                 "24-card Force deck", "12-card Order deck", "3 Orders",
                 "Pass", "one Order from their hand", "5 Command", "Battle VIII"):
        assert term in rules, term
    for forbidden in ("Command card", "Battle Plan", "Tactical Read",
                      "Pressure", "Pin", "Opportunity"):
        assert forbidden not in rules


def test_rulebook_prints_on_one_readable_a4_page():
    source = (ROOT / "tools/build_rulebook_pdf.py").read_text(encoding="utf-8")
    assert 'paper: "a4"' in source
    assert "len(reader.pages) != 1" in source
    rendered = markdown_to_typst(CANONICAL.read_text(encoding="utf-8"), "test")
    assert "#columns(1, gutter: 7mm)[" in rendered
    assert "#set text(size: 11.5pt" in rendered


def test_web_rules_have_no_hidden_advanced_chapters():
    html = markdown.markdown(
        CANONICAL.read_text(encoding="utf-8"),
        extensions=["extra", "sane_lists", "attr_list"],
    )
    laid_out = enrich_rulebook_layout(group_rulebook_sections(html))
    assert "Deploy" in laid_out and "Order" in laid_out
    template = (ROOT / "web/rulebook.template.html").read_text(encoding="utf-8")
    assert "advanced-reference.html" not in template
    build = (ROOT / "tools/build_pages.py").read_text(encoding="utf-8")
    assert 'meta http-equiv="refresh" content="0; url=rulebook.html"' in build


def test_drawable_orders_replace_the_reference_cards():
    orders = json.loads(ORDERS.read_text(encoding="utf-8"))
    assert orders["status"] == "canonical-paper-only"
    assert orders["deck_size_per_player"] == 12
    assert orders["copies_per_order"] == 3
    assert orders["starting_order_hand"] == 3
    assert orders["orders_played_per_battle"] == 1
    assert orders["replenish_orders_after_battle"] == 1
    assert orders["discard_after_battle"]
    assert {o["id"] for o in orders["orders"]} == {"assault", "hold", "volley", "raid"}
    assert len(orders["orders"]) * orders["copies_per_order"] == 12

    html = (ROOT / "web/orders.html").read_text(encoding="utf-8")
    css = (ROOT / "web/orders.css").read_text(encoding="utf-8")
    js = (ROOT / "web/orders.js").read_text(encoding="utf-8")
    assert "12-card Order deck" in html
    assert "no Command card" in html
    assert "data/orders.json" in js
    assert 'function playSelected()' in js
    assert 'length:state.copies' in js
    assert "68mm" in css and "96mm" in css
    assert "repeat(4,68mm)" in css and "repeat(2,96mm)" in css
    assert '@page{size:A4 landscape' in css
    assert "orders.json" in (ROOT / "tools/build_pages.py").read_text(encoding="utf-8")

    for path in ("web/tokens.html", "web/orders-prototype.html"):
        source = (ROOT / path).read_text(encoding="utf-8")
        assert 'url=orders.html' in source
        assert "command-aid" not in source
    assert not (ROOT / "cards/paper-d6-orders-prototype.json").exists()


def test_force_cards_are_unchanged_and_short():
    pool = json.loads(CARDS.read_text(encoding="utf-8"))["cards"]
    assert len(pool) == 44
    for card in pool:
        assert len(card["faces"]) == 6
        assert len(card["outcomes"]) == 4
        assert set(card["faces"]) == set(card["outcomes"])
        assert card["outcomes"]["F"]["effect"] == "Nothing."
        assert card["outcomes"]["D"]["effect"].startswith("Defend")
        third = "R" if card["role"] in ("healer", "steward") else "A"
        assert card["outcomes"][third]["effect"].startswith("Save" if third == "R" else "Attack")
        for effect in card["outcomes"].values():
            assert len(effect["effect"]) < 100


def test_no_competing_extra_mechanics_sheet_or_runtime_mutation():
    mat = (ROOT / "web/playmat.html").read_text(encoding="utf-8")
    assert "short rules" in mat and "drawn Orders" in mat
    assert "Tactical Read" not in mat
    kit = (ROOT / "web/playtest-kit.html").read_text(encoding="utf-8")
    assert "mechanics-reference" not in kit
    assert 'href="orders.html"' in kit
    source = (ROOT / "tools/paper_d6_cards.py").read_text(encoding="utf-8")
    assert "force-only-d6-drawable-orders" in source
    assert "from longwar.engine" not in source
    assert "from longwar.ai" not in source
