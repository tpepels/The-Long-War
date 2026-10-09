"""Smoke checks for the rulebook's source-driven editorial wrappers.

Avoid testing precise text, columns or colours: those are intentionally
iterated during playtesting, while the wrappers should remain semantic.
"""
import markdown

from tools.build_pages import enrich_rulebook_layout, group_rulebook_sections
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_editorial_wrappers_reuse_actual_rules_content() -> None:
    md = (ROOT / "rules" / "rulebook.md").read_text(encoding="utf-8")
    raw = markdown.markdown(md, extensions=["extra", "sane_lists", "attr_list"])
    grouped = group_rulebook_sections(raw)
    decorated = enrich_rulebook_layout(grouped)

    for section_id, css_name in [
        ("learn", "war-timeline"),
        ("components", "component-checklist"),
        ("setup", "setup-steps"),
        ("turn", "action-menu"),
        ("conditions", "condition-list--afflictions"),
        ("passing", "closing-sequence"),
        ("scoring", "resolution-step"),
    ]:
        assert f'id="{section_id}"' in decorated
        assert css_name in decorated

    assert 'class="condition-list condition-list--boons"' in decorated
    assert 'class="formation-anatomy"' in decorated
    assert 'class="rulebook-fast-facts"' in decorated
    assert decorated.count('class="resolution-step"') == 6
    assert decorated.count('<div class="rule-table-scroll"') == raw.count("<table>")
    assert decorated.count('<table>') == raw.count("<table>")
    assert "Force + Bond + Name" in decorated


def test_print_rulebook_handles_lists_quotes_and_tables() -> None:
    from tools.build_rulebook_pdf import markdown_to_typst
    md = (ROOT / "rules" / "rulebook.md").read_text(encoding="utf-8")
    typst = markdown_to_typst(md, "test")
    assert "STARTING COMMAND" in typst
    assert "Strength example:" in typst
    assert "LEGAL TARGET:" in typst
    assert "BASIC ATTACK RESULT:" in typst
    assert "Gather these things" in typst
    assert "Command" in typst

def test_print_rulebook_uses_player_handbook_layout() -> None:
    """The print handbook uses columns with intentional full-width breaks."""
    from tools.build_rulebook_pdf import markdown_to_typst

    md = (ROOT / "rules" / "rulebook.md").read_text(encoding="utf-8")
    rendered = markdown_to_typst(md, "test")
    # Keep ONE continuous two-column region. Reopening columns after panels
    # forces page/column breaks and creates half-empty trailing pages.
    assert rendered.count("#columns(2, gutter: 7mm)[") == 1
    assert "Use these position terms literally:" in rendered
    assert "After checking Guarded, follow this cleanup order:" in rendered
    assert "PRINTED LABEL" in rendered
    assert "RESULT" in rendered
    assert "#table(columns:" in rendered
    assert "FIELD MANUAL" in rendered
    assert "FORMATION LAYERS" in rendered
    assert rendered.count("CLOSING TURN") >= 3
    assert rendered.count("ACTION ") >= 5
    assert rendered.count('stroke: (left: 3pt + rgb(') >= 6
    assert "The shape of the war" in rendered
    assert "Strength example:" in rendered
    # Key technical reference entries must survive print-only compaction.
    for term in ("BECOMES NAMED", "HIDDEN / REVEAL", "Bond discarded",
                 "Force moves", "Frontline", "Command Collapse"):
        assert term in rendered
