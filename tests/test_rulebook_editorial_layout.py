"""The entire current physical game fits on one comfortably readable A4.

These tests check paper-only content; they never run the digital engine or AI.
"""
from pathlib import Path
import json

import markdown

from tools.build_pages import enrich_rulebook_layout, group_rulebook_sections
from tools.build_rulebook_pdf import markdown_to_typst

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "rules/rulebook.md"
PLAYER = ROOT / "rules/player-rulebook.md"
CARDS = ROOT / "cards/paper-d6.json"

REMOVED = ("Tactical Read", "Pressure", "Pin", "Opportunit",
           "counter bonus", "Reroll", "Exhausted", "wound counter")


def test_one_source_of_truth_and_readable_length():
    rules = CANONICAL.read_text(encoding="utf-8")
    assert rules == PLAYER.read_text(encoding="utf-8")
    assert 440 <= len(rules.split()) <= 680
    assert rules.count("\n## ") == 6
    assert "20 Command" in rules
    assert "24-card" in rules
    assert "eight Battles" in rules
    assert "more surviving Forces" in rules
    assert "one D6" in rules
    assert "5 Command" in rules
    for forbidden in REMOVED:
        assert forbidden.lower() not in rules.lower(), forbidden


def test_printable_rulebook_is_a4_and_strictly_one_page():
    source = (ROOT / "tools/build_rulebook_pdf.py").read_text(encoding="utf-8")
    assert 'paper: "a4"' in source
    assert 'len(reader.pages) != 1' in source
    rendered = markdown_to_typst(CANONICAL.read_text(encoding="utf-8"), "test")
    assert rendered.count("#columns(2, gutter: 7mm)[") == 1
    for name in ("Assault", "Hold", "Volley", "Raid"):
        assert name in rendered
    assert "#table(columns:" in rendered


def test_web_rules_dont_add_a_hidden_second_rulebook():
    html = markdown.markdown(
        CANONICAL.read_text(encoding="utf-8"),
        extensions=["extra", "sane_lists", "attr_list"],
    )
    laid_out = enrich_rulebook_layout(group_rulebook_sections(html))
    assert laid_out.count("<table>") == html.count("<table>") == 1
    template = (ROOT / "web/rulebook.template.html").read_text(encoding="utf-8")
    assert "Detailed physical rules" not in template
    assert "advanced-reference.html" not in template
    pages = (ROOT / "tools/build_pages.py").read_text(encoding="utf-8")
    assert 'meta http-equiv="refresh" content="0; url=rulebook.html"' in pages


def test_every_paper_card_uses_the_small_shared_vocabulary():
    pool = json.loads(CARDS.read_text(encoding="utf-8"))["cards"]
    assert len(pool) == 44
    for card in pool:
        assert len(card["faces"]) == 6
        assert len(card["outcomes"]) == 4
        assert set(card["faces"]) == set(card["outcomes"])
        outcomes = card["outcomes"]
        assert outcomes["F"] == {"title": "Nothing", "effect": "Nothing."}
        assert outcomes["D"]["effect"].startswith("Defend")
        third = "R" if card["role"] in ("healer", "steward") else "A"
        assert outcomes[third]["effect"].startswith("Save" if third == "R" else "Attack")
        assert outcomes["S"]["effect"].startswith(("Defend", "Save", "Attack"))
        for key, result in outcomes.items():
            assert result["title"] in {"Nothing", "Defend", "Attack", "Save", "Special"}
            assert len(result["effect"]) < 94, card["id"]
            for forbidden in ("Pressure", "Pin", "Tactical Read", "Opportunity", "Evade", "Protect", "Rescue", "Strike"):
                assert forbidden not in result["effect"], (card["id"], forbidden)


def test_printable_reference_agrees_with_one_page():
    for name in ("web/tokens.html", "web/playmat.html"):
        content = (ROOT / name).read_text(encoding="utf-8")
        for phrase in ("Assault", "Hold", "Volley", "Raid", "Attack", "Defend"):
            assert phrase in content, (name, phrase)
        for forbidden in ("Tactical Read", "Pressure", "Opportunity"):
            assert forbidden not in content, (name, forbidden)
    plans = (ROOT / "web/tokens.html").read_text(encoding="utf-8")
    assert plans.count('class="plan"') == 8

    # Cards print without another mechanics sheet or second set of rules.
    deck_html = (ROOT / "web/playtest-kit.html").read_text(encoding="utf-8")
    deck_js = (ROOT / "web/playtest-kit.js").read_text(encoding="utf-8")
    assert "include-mechanics" not in deck_html
    assert "mechanics-reference" not in deck_html
    assert "includeMechanics" not in deck_js
    assert 'href="rulebook.html"' in deck_html


def test_physical_only_no_runtime_edit():
    source = (ROOT / "tools/paper_d6_cards.py").read_text(encoding="utf-8")
    assert "from longwar.engine" not in source
    assert "from longwar.ai" not in source
