from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_rulebook_opens_with_plain_game_shape_before_detail() -> None:
    source = text("rules/rulebook.md")
    opening = source.split("## The shape of the war", 1)[0]

    assert "two-player card game" in opening
    assert "series of Battles" in opening
    assert "battlefield that grows" in opening
    assert "Cards you commit to the field stay there" in opening
    assert "remaining Command" in opening
    assert "The war ends when one side can no longer sustain it" in opening


def test_current_core_rules_are_introduced_explicitly() -> None:
    source = text("rules/rulebook.md")

    expected = (
        "The battlefield contains four contested areas called **Fronts**",
        "**Battle I:** only the two middle Fronts are active.",
        "Each player begins with **20 Command**.",
        "Forces provide **Strength**.",
        "Any stack containing a Force is a **formation**.",
        "A formation containing **Force + Bond + Name** is a **Named Formation**.",
        "A **Maneuver** is an Action that moves one of your Named Formations.",
        "As one Action, you may:",
        "**Pass is a turn, not an Action.**",
        "A **Narrative** represents something that has become true beyond a single formation.",
        "A **Stratagem** is a hidden plan for the current Battle.",
        "A **Hero** is a Unique card that may be played either as a Force or as a Name.",
    )
    for phrase in expected:
        assert phrase in source


def test_print_rulebook_uses_typst_not_browser_pagination() -> None:
    builder = text("tools/build_rulebook_pdf.py")
    workflow = text(".github/workflows/pages.yml")
    template = text("web/rulebook.template.html")
    pyproject = text("pyproject.toml")

    assert "typst compile" not in builder
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


def test_simultaneous_command_collapse_uses_the_battle_passer() -> None:
    source = text("rules/rulebook.md")
    assert (
        "If both players are at 0 or less with the same Command total, "
        "the player who **Passed in that Battle** loses."
        in source
    )


def test_pass_and_battle_end_order_match_playtest_rules() -> None:
    source = text("rules/rulebook.md")

    assert "You may Pass only if, after drawing for the turn, you have **no legal Action at all**." in source
    assert "The opponent takes one full turn: draw 1 card, then take up to 2 Actions." in source
    assert "The player who Passed takes one full turn: draw 1 card, then take up to 2 Actions." in source
    assert "The Battle ends immediately." in source
    assert "player who **did not Pass** starts the next Battle" in source

    assert "You may end your turn after zero, one, or two Actions." in source
    assert "Ending your turn voluntarily is **not Pass**" in source
    assert "if no legal Action remains after your draw, you must **Pass**" in source
    assert "having no legal Action simply ends that closing turn" in source

    assert "Winning or losing a Front does **not** move, Retreat, or discard any battlefield cards." in source
    assert "Battle resolution by itself never causes any of these removals." in source
    assert "Check for Command Collapse before anyone recovers Command." in source


def test_growing_fronts_and_deck_rules_are_canonical_in_rulebook() -> None:
    source = text("rules/rulebook.md")

    assert "**Battle I:** only the two middle Fronts are active." in source
    assert "**Battle II:** the left outer Front becomes active." in source
    assert "**Battle III:** the right outer Front becomes active." in source
    assert "An inactive Front is not part of the battlefield yet." in source
    assert "Every Front has three positions on each player's side:" in source
    assert "the **Middle/Support** between the front and rear;" in source
    assert "**Directly in front of:** the next position toward the Frontline" in source
    assert "**Directly behind:** the next position toward the Rear" in source

    assert "at least **34 cards**" in source
    assert "at most **4 copies** of any non-Unique title" in source
    assert "at most **1 copy** of any Unique title" in source
    assert "There is no required minimum number of Forces or printed Names." in source


def test_hidden_stratagem_and_split_hero_limits_are_explicit() -> None:
    source = text("rules/rulebook.md")

    assert "places the card **face-down** in your Stratagem area" in source
    assert "identity of a face-down Stratagem is hidden" in source
    assert "that choice is public" in source
    assert "at most **1 as a Force**" in source
    assert "at most **1 as a Name**" in source


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
