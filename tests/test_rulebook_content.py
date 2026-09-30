from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_rulebook_opening_is_jargon_free() -> None:
    source = text("rules/rulebook.md")
    opening = source.split("## ", 1)[0]

    # Page-one orientation must work before the reader knows any canonical
    # vocabulary. Those terms are introduced deliberately in the next section.
    jargon = (
        "Battle",
        "Front",
        "Frontline",
        "Rear",
        "Strength",
        "Force",
        "Bond",
        "Name",
        "formation",
        "Command",
        "Maneuver",
        "Pass",
        "Retreat",
        "Narrative",
        "Stratagem",
        "Hero",
        "Unique",
    )
    for term in jargon:
        assert re.search(rf"\b{re.escape(term)}s?\b", opening, re.IGNORECASE) is None


def test_core_terms_are_explicitly_introduced_before_rules_depend_on_them() -> None:
    source = text("rules/rulebook.md")

    expected_introductions = (
        "A round of the game is called a **Battle**.",
        "Each of the four contested areas is called a **Front**.",
        "The resource you spend to play cards and move established groups is called **Command**.",
        "A **Force** gives a position its body.",
        "A **Bond** is attached to a Force",
        "A **Name** gives that group an identity.",
        "A **formation** is a Force together with any Bond and/or Name",
        "A **Named Formation** is a complete formation",
        "A **Maneuver** is an operation that moves one of your Named Formations.",
        "To **Pass** is to spend 0 Command and take no other operation.",
        "A **Narrative** is a card that represents something the war has made true",
        "A **Stratagem** is a public plan for the current Battle.",
        "That movement is called a **Retreat**.",
        "**Command Collapse** is the check that can end the war.",
    )
    for sentence in expected_introductions:
        assert sentence in source


def test_print_rulebook_uses_typst_not_browser_pagination() -> None:
    builder = text("tools/build_rulebook_pdf.py")
    workflow = text(".github/workflows/pages.yml")
    template = text("web/rulebook.template.html")
    pyproject = text("pyproject.toml")

    assert "typst compile" not in builder  # command is assembled safely as argv
    assert '"compile"' in builder
    assert "#columns(2, gutter: 9mm)[" in builder
    assert "TLW print v" in builder
    assert "PdfReader" in builder
    assert "blank or nearly blank" in builder

    assert "typst-community/setup-typst@v5" in workflow
    assert "typst-version: 0.15.1" in workflow
    assert 'href="rulebook.pdf"' in template
    assert "window.print()" not in template
    assert "WeasyPrint" not in pyproject
    assert "pypdf" in pyproject
