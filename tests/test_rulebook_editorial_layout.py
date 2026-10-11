"""Check the current physical D6 handbook, web rendering, and PDF source.

The legacy Bond/Name editorial expectations are historical and are deliberately
not frozen into the new physical playtest rulebook.
"""
from pathlib import Path

import markdown

from tools.build_pages import enrich_rulebook_layout, group_rulebook_sections
from tools.build_rulebook_pdf import markdown_to_typst

ROOT = Path(__file__).resolve().parents[1]
PLAYER = ROOT / "rules" / "player-rulebook.md"
FULL = ROOT / "rules" / "rulebook.md"


def test_rulebook_is_readable_and_describes_new_physical_rules() -> None:
    player = PLAYER.read_text(encoding="utf-8")
    full = FULL.read_text(encoding="utf-8")
    assert len(player.split()) < len(full.split()) * 0.75
    assert len(full.split()) > 1400

    for rule in ("D6", "Frontline", "Middle", "Rear", "Assault",
                 "Hold", "Volley", "Raid", "Protect", "Rescue",
                 "Command", "24-card", "Battle VIII"):
        assert rule in player or rule in full, rule
    for obsolete in ("BECOMES NAMED", "Strength deficit",
                     "Shaken", "Depleted", "Named Formation"):
        assert obsolete not in player, obsolete


def test_rulebook_web_editorial_wrappers_keep_tables() -> None:
    raw = markdown.markdown(
        PLAYER.read_text(encoding="utf-8"),
        extensions=["extra", "sane_lists", "attr_list"],
    )
    decorated = enrich_rulebook_layout(group_rulebook_sections(raw))
    assert "<h1>" in decorated
    assert "Battle Plans" in decorated
    assert decorated.count("<table>") == raw.count("<table>")
    assert decorated.count("<table>") >= 1


def test_player_rulebook_pdf_includes_d6_and_plans() -> None:
    rendered = markdown_to_typst(PLAYER.read_text(encoding="utf-8"), "test")
    assert rendered.count("#columns(2, gutter: 7mm)[") == 1
    assert 'advanced-reference.html' in rendered
    assert "FIELD MANUAL" in rendered
    assert "Assault" in rendered
    assert "Volley" in rendered
    assert "Raid" in rendered
    assert "#table(columns:" in rendered
