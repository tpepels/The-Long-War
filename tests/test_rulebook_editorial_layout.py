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
    assert "#table(" in typst
    assert "Gather these things" in typst
    assert "Command" in typst
