"""Check the short player rulebook and its link to complete rulings.

Avoid freezing editable prose, mechanics or layout pixel counts in tests.
"""
from pathlib import Path

import markdown

from tools.build_pages import enrich_rulebook_layout, group_rulebook_sections
from tools.build_rulebook_pdf import markdown_to_typst

ROOT = Path(__file__).resolve().parents[1]
PLAYER = ROOT / "rules" / "player-rulebook.md"
FULL = ROOT / "rules" / "rulebook.md"


def test_rulebook_is_concise_but_reference_is_preserved() -> None:
    player = PLAYER.read_text(encoding="utf-8")
    full = FULL.read_text(encoding="utf-8")
    assert len(player.split()) < len(full.split()) * 0.55
    assert len(full.split()) > 5500
    assert "Simultaneous Stratagems" in full
    assert "Unusual Front exchanges" in full
    assert "Prepared layers and attachment rewards" in full

    for heading in ("The battlefield", "Your turn", "Playing cards",
                    "Maneuver", "Attacking", "Conditions", "Special cards",
                    "Command", "Passing", "Resolving a Battle", "Reference"):
        assert heading in player

    for rule in ("20 Command", "10 cards", "2 Actions", "1 Command",
                 "BECOMES NAMED", "Guarded", "Exhausted",
                 "Command Collapse", "34 cards", "Stratagem"):
        assert rule in player


def test_rulebook_web_editorial_wrappers() -> None:
    raw = markdown.markdown(
        PLAYER.read_text(encoding="utf-8"),
        extensions=["extra", "sane_lists", "attr_list"],
    )
    decorated = enrich_rulebook_layout(group_rulebook_sections(raw))
    for section_id, css_class in (
        ("learn", "war-timeline"),
        ("components", "component-checklist"),
        ("setup", "setup-steps"),
        ("turn", "action-menu"),
        ("conditions", "condition-list--afflictions"),
        ("passing", "closing-sequence"),
        ("scoring", "resolution-step"),
    ):
        assert f'id="{section_id}"' in decorated
        assert css_class in decorated
    assert 'class="condition-list condition-list--boons"' in decorated
    assert 'class="formation-anatomy"' in decorated
    assert decorated.count('class="resolution-step"') == 6
    assert decorated.count("<table>") == raw.count("<table>")


def test_player_rulebook_pdf_has_reference_link_and_core_tables() -> None:
    rendered = markdown_to_typst(PLAYER.read_text(encoding="utf-8"), "test")
    assert rendered.count("#columns(2, gutter: 7mm)[") == 1
    assert 'advanced-reference.html' in rendered
    assert "FIELD MANUAL" in rendered
    assert "FORMATION LAYERS" in rendered
    assert "LEGAL TARGET" in rendered
    assert "BECOMES NAMED" in rendered
    assert "RESULT" in rendered
    assert "#table(columns:" in rendered
    assert rendered.count('stroke: (left: 3pt + rgb(') >= 6
