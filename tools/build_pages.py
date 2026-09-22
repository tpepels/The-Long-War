from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
DIST = ROOT / "dist"
RULEBOOK = ROOT / "rules" / "rulebook.md"
CARDS = ROOT / "cards" / "cards.json"
REFERENCE_DECK = ROOT / "decks" / "reference.json"
BALANCE_HEALTH = ROOT / "artifacts" / "balance-health.json"


def version_static_assets() -> str:
    inputs = [
        path
        for path in DIST.rglob("*")
        if path.is_file()
        and (
            path.suffix in {".js", ".mjs", ".css"}
            or path.relative_to(DIST).as_posix()
            in {"data/cards.json", "data/reference-deck.json"}
        )
    ]
    digest = hashlib.sha256()
    for path in sorted(inputs):
        digest.update(path.relative_to(DIST).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    version = digest.hexdigest()[:12]

    play_js = DIST / "play.js"
    if play_js.exists():
        source = play_js.read_text(encoding="utf-8")
        source = source.replace(
            '"./browser-engine.mjs"',
            f'"./browser-engine.mjs?v={version}"',
        )
        play_js.write_text(source, encoding="utf-8")

    asset_pattern = re.compile(
        r'(?P<attr>src|href)="(?P<path>(?!https?://)[^"#?]+\.(?:js|mjs|css))"'
    )
    for page in DIST.rglob("*.html"):
        source = page.read_text(encoding="utf-8")
        source = asset_pattern.sub(
            lambda match: (
                f'{match.group("attr")}="{match.group("path")}?v={version}"'
            ),
            source,
        )
        page.write_text(source, encoding="utf-8")
    return version


def group_rulebook_sections(rendered: str) -> str:
    """Wrap each H2 section so short rules sections do not split awkwardly across columns."""
    pattern = re.compile(
        r'(<h2\b[^>]*>.*?</h2>)(.*?)(?=(?:<h2\b|<div class="rulebook-kicker"|$))',
        re.DOTALL,
    )
    return pattern.sub(
        lambda match: '<section class="rule-section">' + match.group(1) + match.group(2) + '</section>',
        rendered,
    )


def main() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(WEB, DIST)

    data_dir = DIST / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(CARDS, data_dir / "cards.json")
    shutil.copy2(REFERENCE_DECK, data_dir / "reference-deck.json")

    if BALANCE_HEALTH.exists():
        shutil.copy2(BALANCE_HEALTH, data_dir / "balance-health.json")

    artifacts_dir = ROOT / "artifacts"
    if artifacts_dir.exists():
        for artifact in artifacts_dir.glob("*.json"):
            shutil.copy2(artifact, data_dir / artifact.name)

    rulebook_md = RULEBOOK.read_text(encoding="utf-8")
    rulebook_html = markdown.markdown(
        rulebook_md,
        extensions=["extra", "sane_lists", "attr_list", "md_in_html"],
    )
    rulebook_html = group_rulebook_sections(rulebook_html)

    template = (WEB / "rulebook.template.html").read_text(encoding="utf-8")
    rendered = template.replace("{{RULEBOOK}}", rulebook_html)
    (DIST / "rulebook.html").write_text(rendered, encoding="utf-8")
    (DIST / "rulebook.template.html").unlink(missing_ok=True)

    version = version_static_assets()
    card_data = json.loads(CARDS.read_text(encoding="utf-8"))
    balance = "with balance data" if BALANCE_HEALTH.exists() else "without balance data"
    print(
        f"Built Pages site with {len(card_data['cards'])} cards "
        f"({balance}), asset version {version} at {DIST}"
    )


if __name__ == "__main__":
    main()
