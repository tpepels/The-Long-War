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
        "A round in The Long War is called a **Battle**.",
        "The battlefield is divided into four contested areas called **Fronts**.",
        "**Command** is the resource used to play cards and move established groups.",
        "Cards can contribute a number called **Strength**.",
        "A **Force** supplies the group's printed Strength.",
        "A **Bond** can connect to that Force.",
        "A **Name** gives the group its identity.",
        "Any stack containing a Force is a **formation**.",
        "A formation containing **Force + Bond + Name** is a **Named Formation**.",
        "A **Maneuver** is an operation that moves one of your Named Formations.",
        "To **Pass** is to spend 0 Command and use your operation without playing a card or Maneuvering.",
        "A **Narrative** represents something the war has made true beyond a single formation.",
        "A **Stratagem** is a public plan for the current Battle.",
        "that forced movement is called a **Retreat**.",
        "The check that can end the war is called **Command Collapse**.",
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
    assert 'href="rulebook.pdf?v={{PRINT_VERSION}}"' in template
    assert "window.print()" not in template
    assert "WeasyPrint" not in pyproject
    assert "pypdf" in pyproject


def test_simultaneous_command_collapse_uses_first_passer() -> None:
    source = text("rules/rulebook.md")
    assert (
        "If both players are at or below **{{COLLAPSE_THRESHOLD}} Command** "
        "with equal Command, the player who **Passed first** loses the war."
        in source
    )


def test_rulebook_uses_card_art_not_old_flow_diagrams() -> None:
    source = text("rules/rulebook.md")
    assert "rulebook-battle-flow.svg" not in source
    assert "rulebook-formation.jpg" in source
    assert "rulebook-maneuver.jpg" in source
    assert "rulebook-pass-flow.jpg" not in source
    assert "rulebook-retreat.jpg" in source


def test_pass_and_battle_end_order_match_canonical_rules() -> None:
    source = text("rules/rulebook.md")
    assert "It is permanent for the rest of the Battle" in source
    assert "Once the first active Pass exists, the Pass gate is open." in source
    assert "The first Pass does not start a countdown." in source
    assert (
        "Pass is no longer a normal voluntary choice while another legal "
        "operation is available."
        in source
    )
    assert (
        "If the war survives Battle resolution and Command Collapse, the "
        "player who **Passed first** starts the next Battle."
        in source
    )
    assert "both players have Passed at least once" in source
    assert "If you Pass again while your Pass is already active" not in source
    assert "Apply Command loss for unprotected Fronts lost, then check Command Collapse." in source
    assert "Do **not** clamp negative Command back to 0." in source
    assert "This reduces current Command; it does **not** reduce recovery a second time." in source


def test_print_builder_rasterizes_jpeg_art_for_pdf() -> None:
    builder = text("tools/build_rulebook_pdf.py")
    assert "from PIL import Image" not in builder
    assert "def _pdf_safe_image_path" in builder
    assert 'source.suffix.lower() not in {".jpg", ".jpeg"}' in builder
    assert 'shutil.which("ffmpeg")' in builder
    assert '"-frames:v"' in builder
    assert 'source.stem + "-print.png"' in builder



def test_rulebook_images_use_field_manual_visual_language() -> None:
    pages = text("tools/build_pages.py")
    pdf = text("tools/build_rulebook_pdf.py")
    css = text("web/rules.css")

    assert "def decorate_rulebook_images" in pages
    assert '"teaching-plate"' in pages
    assert '"tabletop-example"' in pages
    assert '"BATTLE PLATE"' in pages
    assert '"FIELD EXAMPLE"' in pages

    assert "TEACHING_PLATE_IMAGES" in pdf
    assert '"BATTLE PLATE" if teaching_plate else "FIELD EXAMPLE"' in pdf
    assert 'image_width = "100%" if teaching_plate else "94%"' in pdf

    assert "/* Illustrated field-manual figures */" in css
    assert ".rulebook-figure.teaching-plate" in css
    assert ".rulebook-figure.tabletop-example img" in css
