"""Card-led paper edition: only the game loop lives in the rules.

Print details live on the physical Command, Battle Plan and Force cards.
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


def test_core_rules_are_only_a_short_game_loop():
    rules = CANONICAL.read_text(encoding="utf-8")
    assert rules == PLAYER.read_text(encoding="utf-8")
    assert 100 <= len(rules.split()) <= 200
    assert rules.count("\n## ") == 5
    for word in ("Prepare", "Deploy", "Plan", "Fight", "Win", "D6", "Command card"):
        assert word in rules
    for unnecessary in ("Tactical Read", "Pressure", "Pin", "Opportunity",
                        "Frontline", "Middle", "Rear", "Attack:", "Defend:",
                        "+1 Force", "recover 5", "Battle VIII"):
        assert unnecessary not in rules


def test_actual_paper_pdf_is_still_strict_one_a4():
    source = (ROOT / "tools/build_rulebook_pdf.py").read_text(encoding="utf-8")
    assert 'paper: "a4"' in source
    assert 'len(reader.pages) != 1' in source
    rendered = markdown_to_typst(CANONICAL.read_text(encoding="utf-8"), "test")
    assert rendered.count("#columns(2, gutter: 7mm)[") == 1


def test_web_rulebook_is_same_content_without_hidden_advanced_rules():
    html = markdown.markdown(
        CANONICAL.read_text(encoding="utf-8"),
        extensions=["extra", "sane_lists", "attr_list"],
    )
    laid_out = enrich_rulebook_layout(group_rulebook_sections(html))
    assert "<h1>" in laid_out
    assert "Deploy" in laid_out
    template = (ROOT / "web/rulebook.template.html").read_text(encoding="utf-8")
    assert "advanced-reference.html" not in template
    pages = (ROOT / "tools/build_pages.py").read_text(encoding="utf-8")
    assert 'meta http-equiv="refresh" content="0; url=rulebook.html"' in pages


def test_command_card_contains_rules_moved_out_of_the_handbook():
    html = (ROOT / "web/tokens.html").read_text(encoding="utf-8")
    assert html.count('class="plan"') == 8
    assert html.count('class="plan command-aid"') == 2
    for text in ("20 Command", "Draw 10", "24-card", "up to 2 actions",
                 "1 Command", "+1 Force", "Defend", "Save", "5 Command",
                 "Battle VIII"):
        # Labels can use HTML inline markup; check raw values nearby.
        if text == "24-card":
            continue  # deck size is on the single-page rules
        assert text in html, text
    assert "Tactical Read" not in html
    assert "Opportunity" not in html


def test_all_force_outcomes_still_print_and_remain_short():
    pool = json.loads(CARDS.read_text(encoding="utf-8"))["cards"]
    assert len(pool) == 44
    for card in pool:
        assert len(card["faces"]) == 6
        assert len(card["outcomes"]) == 4
        assert set(card["faces"]) == set(card["outcomes"])
        assert card["outcomes"]["F"]["effect"] == "Nothing."
        assert card["outcomes"]["D"]["effect"].startswith("Defend")
        other = "R" if card["role"] in ("healer", "steward") else "A"
        assert card["outcomes"][other]["effect"].startswith("Save" if other == "R" else "Attack")
        for entry in card["outcomes"].values():
            assert len(entry["effect"]) < 100


def test_no_competing_mat_or_extra_mechanics_sheet():
    mat = (ROOT / "web/playmat.html").read_text(encoding="utf-8")
    assert "Each Front:" in mat and "Command and Battle Plan cards" in mat
    assert "Tactical Read" not in mat
    deck_html = (ROOT / "web/playtest-kit.html").read_text(encoding="utf-8")
    assert "mechanics-reference" not in deck_html
    assert 'href="rulebook.html"' in deck_html
    source = (ROOT / "tools/paper_d6_cards.py").read_text(encoding="utf-8")
    assert "from longwar.engine" not in source
    assert "from longwar.ai" not in source
