from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from pathlib import Path

import markdown
if __package__:
    from .build_browser_runtime import ensure_browser_runtime
    from longwar.reference_decks import REFERENCE_DECK_PATHS
else:
    from build_browser_runtime import ensure_browser_runtime
    from longwar.reference_decks import REFERENCE_DECK_PATHS
from longwar.cards import load_card_file
from longwar.rules import GameRules

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
DIST = ROOT / "dist"
RULEBOOK = ROOT / "rules" / "rulebook.md"
CARDS = ROOT / "cards" / "cards.json"
REFERENCE_DECKS = REFERENCE_DECK_PATHS
BALANCE_HEALTH = ROOT / "artifacts" / "balance-health.json"
PUBLISHED_ARTIFACTS = ("lab-report.json", "balance-health.json")
PRINTABLE_PAGES = {
    "cards.html",
    "playtest-kit.html",
    "rulebook.html",
    "playmat.html",
    "tokens.html",
}


def print_build_version() -> str:
    """Exact revision printed on every physical playtest artifact."""
    github_sha = os.environ.get("GITHUB_SHA", "").strip().lower()
    if re.fullmatch(r"[0-9a-f]{7,40}", github_sha):
        return github_sha[:8]

    # Local builds still get a stable version that changes with printable
    # rules/cards/layout inputs, rather than an ambiguous "dev" label.
    inputs = [
        RULEBOOK,
        CARDS,
        ROOT / "src" / "longwar" / "rules.py",
        WEB / "print-cards.css",
        WEB / "print-cards.js",
        WEB / "rules.css",
        WEB / "style.css",
        WEB / "tokens.css",
        WEB / "playtest-kit.js",
        WEB / "cards.js",
        WEB / "playmat.html",
        WEB / "tokens.html",
        WEB / "assets" / "rulebook-battlefield.svg",
        *REFERENCE_DECKS,
    ]
    digest = hashlib.sha256()
    for path in sorted(inputs):
        digest.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return "local-" + digest.hexdigest()[:8]


def stamp_print_version(version: str) -> None:
    """Add machine-readable and visible print revision markers."""
    meta = f'<meta name="lw-build-version" content="{version}">'
    stamp = (
        '<div class="print-version" aria-hidden="true">'
        f'TLW print v{version}</div>'
    )
    for page in DIST.rglob("*.html"):
        source = page.read_text(encoding="utf-8")
        source = source.replace("{{PRINT_VERSION}}", version)
        if 'name="lw-build-version"' not in source:
            source = source.replace("</head>", f"  {meta}\n</head>")
        # The rulebook owns its version footer inside each explicit print page.
        # A fixed trailing DOM stamp can itself create an extra blank page.
        if (
            page.name in PRINTABLE_PAGES
            and page.name != "rulebook.html"
            and 'class="print-version"' not in source
        ):
            source = source.replace("</body>", f"  {stamp}\n</body>")
        page.write_text(source, encoding="utf-8")



def version_static_assets() -> str:
    inputs = [
        path
        for path in DIST.rglob("*")
        if path.is_file()
        and (
            path.suffix in {".js", ".mjs", ".css", ".whl"}
            or path.relative_to(DIST).as_posix()
            in {"data/cards.json", "data/reference-decks.json"}
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
        for module in ("browser-engine.mjs", "remote-peer.mjs"):
            source = source.replace(
                f'"./{module}"',
                f'"./{module}?v={version}"',
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


def render_rule_tokens(source: str, rules: GameRules) -> str:
    recovery = [
        rules.command_recovery_for_battle(battle)
        for battle in range(1, 6)
    ]
    values = {
        key.upper(): value
        for key, value in rules.as_dict().items()
    }
    # Short aliases keep authored reference copy readable while canonical
    # GameRules field names remain the actual source of truth.
    values.update(
        {
            "COLLAPSE_THRESHOLD": rules.command_collapse_threshold,
            "RECOVERY_START": rules.command_recovery_start,
            "RECOVERY_DECREMENT": rules.command_recovery_decrement,
            "RECOVERY_FLOOR": rules.command_recovery_floor,
            "RECOVERY_SERIES": ", ".join(
                f"+{value}" for value in recovery
            ) + "…",
            "RECOVERY_SERIES_PLAIN": ", ".join(
                str(value) for value in recovery
            ) + "...",
        }
    )
    rendered = source
    for key, value in values.items():
        rendered = rendered.replace("{{" + key + "}}", str(value))
    unresolved = sorted(set(re.findall(r"{{([A-Z0-9_]+)}}", rendered)))
    if unresolved:
        raise ValueError(
            "Unknown rule-reference tokens: " + ", ".join(unresolved)
        )
    return rendered


def main() -> None:
    card_data = load_card_file(CARDS)
    runtime = ensure_browser_runtime()
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(WEB, DIST)
    shutil.copytree(runtime, DIST / "runtime")

    playmat = DIST / "playmat.html"
    playmat.write_text(
        render_rule_tokens(
            playmat.read_text(encoding="utf-8"),
            GameRules.standard(),
        ),
        encoding="utf-8",
    )

    data_dir = DIST / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(CARDS, data_dir / "cards.json")

    known_cards = {card["id"] for card in card_data["cards"]}
    reference_decks = []
    for deck_path in REFERENCE_DECKS:
        deck = json.loads(deck_path.read_text(encoding="utf-8"))
        missing = sorted(set(deck["cards"]) - known_cards)
        if missing:
            raise ValueError(
                f"{deck_path.name} references unknown cards: {', '.join(missing)}"
            )
        reference_decks.append({"file": deck_path.name, **deck})
    (data_dir / "reference-decks.json").write_text(
        json.dumps({"decks": reference_decks}, indent=2) + "\n",
        encoding="utf-8",
    )

    artifacts_dir = ROOT / "artifacts"
    for filename in PUBLISHED_ARTIFACTS:
        artifact = artifacts_dir / filename
        if artifact.exists():
            shutil.copy2(artifact, data_dir / filename)

    rulebook_md = render_rule_tokens(
        RULEBOOK.read_text(encoding="utf-8"),
        GameRules.standard(),
    )
    rulebook_html = markdown.markdown(
        rulebook_md,
        extensions=["extra", "sane_lists", "attr_list", "md_in_html"],
    )
    rulebook_html = group_rulebook_sections(rulebook_html)
    template = (WEB / "rulebook.template.html").read_text(encoding="utf-8")
    rendered = template.replace("{{RULEBOOK}}", rulebook_html)
    (DIST / "rulebook.html").write_text(rendered, encoding="utf-8")
    (DIST / "rulebook.template.html").unlink(missing_ok=True)

    print_version = print_build_version()
    stamp_print_version(print_version)
    version = version_static_assets()
    balance = "with balance data" if BALANCE_HEALTH.exists() else "without balance data"
    print(
        f"Built Pages site with {len(card_data['cards'])} cards "
        f"({balance}), print version {print_version}, "
        f"asset version {version} at {DIST}"
    )


if __name__ == "__main__":
    main()
