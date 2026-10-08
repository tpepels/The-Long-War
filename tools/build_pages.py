from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import markdown
from PIL import Image

if __package__:
    from .build_browser_runtime import ensure_browser_runtime
    from longwar.reference_decks import REFERENCE_DECK_PATHS
else:
    from build_browser_runtime import ensure_browser_runtime
    from longwar.reference_decks import REFERENCE_DECK_PATHS
from longwar.cards import load_card_file
if __package__:
    from .print_cards import load_print_cards
else:
    from print_cards import load_print_cards
from longwar.decks import (
    MINIMUM_DECK_SIZE,
    MINIMUM_FORCE_COUNT,
    MINIMUM_PRINTED_NAME_COUNT,
    NON_UNIQUE_COPY_LIMIT,
    UNIQUE_COPY_LIMIT,
)
from longwar.rules import GameRules

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
DIST = ROOT / "dist"
RULEBOOK = ROOT / "rules" / "rulebook.md"
CARDS = ROOT / "cards" / "cards.json"
PLAYTEST_DECKS = ROOT / "cards" / "playtest-decks.json"
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
# These files belong only to the native-runtime Webgame, not inspection Pages.
WEBGAME_RUNTIME_SCRIPTS = ("play.js", "browser-engine.mjs", "remote-peer.mjs")
PRINT_ART_MAX_PX = 960
PRINT_ART_QUALITY = 86
CARD_FRAME_MAX_PX = {
    "card-shell": 1134,
    "art-window": 744,
    "title-divider": 640,
    "command-seal": 160,
}


def print_build_version() -> str:
    """Exact revision printed on every physical playtest artifact."""
    github_sha = os.environ.get("GITHUB_SHA", "").strip().lower()
    if re.fullmatch(r"[0-9a-f]{7,40}", github_sha):
        return github_sha[:8]

    # A clean local checkout prints the same Git revision as CI. If the
    # checkout is dirty, say so explicitly rather than stamping changed
    # physical artifacts as an unchanged commit.
    try:
        git_sha = subprocess.check_output(
            ["git", "rev-parse", "--short=8", "HEAD"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip().lower()
        if re.fullmatch(r"[0-9a-f]{8}", git_sha):
            dirty = bool(
                subprocess.check_output(
                    ["git", "status", "--porcelain", "--untracked-files=normal"],
                    cwd=ROOT,
                    text=True,
                    stderr=subprocess.DEVNULL,
                ).strip()
            )
            return git_sha + ("-dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        pass

    # Source archives without Git metadata still get a deterministic,
    # unmistakably non-commit identifier.
    inputs = [
        RULEBOOK,
        CARDS,
        ROOT / "cards" / "print-overrides.json",
        PLAYTEST_DECKS,
        ROOT / "src" / "longwar" / "rules.py",
        WEB / "physical-cards.css",
        WEB / "physical-cards.js",
        WEB / "card-symbols.js",
        WEB / "rules.css",
        WEB / "style.css",
        WEB / "tokens.css",
        WEB / "playtest-kit.js",
        WEB / "cards.js",
        WEB / "site-nav.template.html",
        WEB / "playmat.html",
        WEB / "tokens.html",
        *(WEB / "art" / "card-frame" / (name + ".png") for name in CARD_FRAME_MAX_PX),
        *REFERENCE_DECKS,
    ]
    digest = hashlib.sha256()
    for path in sorted(inputs):
        digest.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return "local-" + digest.hexdigest()[:8]


def build_print_art() -> None:
    """Generate compact card art and lossless shared frames from source PNGs."""
    source_dir = WEB / "art" / "cards"
    target_dir = DIST / "art" / "cards-print"
    target_dir.mkdir(parents=True, exist_ok=True)

    cards = load_card_file(CARDS)["cards"]
    art_ids = sorted({card.get("art_id", card["id"]) for card in cards})
    for art_id in art_ids:
        source = source_dir / (art_id + ".png")
        if not source.is_file():
            raise ValueError(f"Missing canonical card artwork: {source}")
        target = target_dir / (art_id + ".webp")
        with Image.open(source) as image:
            image = image.convert("RGB")
            image.thumbnail(
                (PRINT_ART_MAX_PX, PRINT_ART_MAX_PX),
                Image.Resampling.LANCZOS,
            )
            image.save(
                target,
                "WEBP",
                quality=PRINT_ART_QUALITY,
                method=6,
            )

    frame_dir = DIST / "art" / "card-frame"
    frame_dir.mkdir(parents=True, exist_ok=True)
    css_path = DIST / "physical-cards.css"
    css = css_path.read_text(encoding="utf-8")
    for name, max_px in CARD_FRAME_MAX_PX.items():
        source = WEB / "art" / "card-frame" / (name + ".png")
        if not source.is_file():
            raise ValueError(f"Missing shared card frame artwork: {source}")
        with Image.open(source) as image:
            image = image.convert("RGBA")
            image.thumbnail((max_px, max_px), Image.Resampling.LANCZOS)
            image.save(frame_dir / (name + ".webp"), "WEBP", lossless=True, method=6)
        css = re.sub(
            r'(url\(\s*[\"\']?art/card-frame/' + re.escape(name) + r')\.png([\"\']?\s*\))',
            r"\1.webp\2",
            css,
        )
    css_path.write_text(css, encoding="utf-8")


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


def render_site_navigation() -> None:
    """Expand the six public links at build time, preserving page styling."""
    links = (WEB / "site-nav.template.html").read_text(encoding="utf-8")
    for page in DIST.glob("*.html"):
        source = page.read_text(encoding="utf-8")
        if "<!-- SITE_NAV -->" not in source:
            continue
        navigation = links
        if page.name == "index.html":
            navigation = navigation.replace('<a href="play.html"', '<a class="button" href="play.html"')
            navigation = navigation.replace('<a href=', '<a class="button secondary" href=')
        else:
            navigation = re.sub(
                r'<a href="' + re.escape(page.name) + r'">([^<]+)</a>',
                r'<span aria-current="page">\1</span>',
                navigation,
            )
        page.write_text(source.replace("<!-- SITE_NAV -->", navigation.rstrip()), encoding="utf-8")



def version_static_assets() -> str:
    inputs = [
        path
        for path in DIST.rglob("*")
        if path.is_file()
        and (
            path.suffix in {".js", ".mjs", ".css", ".whl"}
            or (path.parent == DIST / "art" / "card-frame" and path.suffix == ".webp")
            or path.relative_to(DIST).as_posix()
            in {"data/cards.json", "data/print-cards.json", "data/playtest-decks.json", "data/reference-decks.json"}
        )
    ]
    digest = hashlib.sha256()
    for path in sorted(inputs):
        digest.update(path.relative_to(DIST).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    version = digest.hexdigest()[:12]

    frame_names = "|".join(re.escape(name) for name in CARD_FRAME_MAX_PX)
    frame_pattern = re.compile(
        r'(?P<prefix>url\(\s*[\"\']?)(?P<path>art/card-frame/(?:'
        + frame_names + r')\.webp)(?P<suffix>[\"\']?\s*\))'
    )
    for css in DIST.rglob("*.css"):
        source = css.read_text(encoding="utf-8")
        source = frame_pattern.sub(
            lambda match: f'{match["prefix"]}{match["path"]}?v={version}{match["suffix"]}',
            source,
        )
        css.write_text(source, encoding="utf-8")

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
        r'(?P<attr>src|href)="(?P<path>(?!https?://)[^"#?]+\.(?:js|mjs|css))(?:\?v=[^"&#]*)?"'
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



def enrich_rulebook_layout(rendered: str) -> str:
    """Add semantic, layout-only groupings around existing player-facing rules.

    Keep the authoritative language in rules/rulebook.md: these wrappers style
    the same lists, steps, and tables instead of maintaining a second ruleset.
    """
    def add_list_class(body: str, tag: str, class_name: str) -> str:
        return body.replace(f"<{tag}>", f'<{tag} class="{class_name}">', 1)

    pattern = re.compile(
        r'(<section class="rule-section">)(<h2\\b[^>]*id="([^"]+)"[^>]*>.*?</h2>)'
        r'(.*?)(</section>)',
        re.DOTALL,
    )

    def decorate_section(match: re.Match[str]) -> str:
        _, heading, section_id, body, _ = match.groups()
        class_name = f"rule-section rule-section--{section_id}"
        if section_id == "learn":
            body = add_list_class(body, "ul", "war-timeline")
        elif section_id == "components":
            body = add_list_class(body, "ul", "component-checklist")
        elif section_id == "setup":
            body = add_list_class(body, "ol", "setup-steps")
        elif section_id == "turn":
            body = add_list_class(body, "ul", "action-menu")
        elif section_id == "conditions":
            body = add_list_class(body, "ul", "condition-list condition-list--afflictions")
            body = body.replace("<ul>", '<ul class="condition-list condition-list--boons">', 1)
        elif section_id == "passing":
            body = add_list_class(body, "ol", "closing-sequence")
        elif section_id == "scoring":
            # Each heading and its explanation form a single resolution step.
            body = re.sub(
                r'(<h3\\b[^>]*>.*?</h3>)(.*?)(?=<h3\\b|\\Z)',
                lambda step: (
                    '<div class="resolution-step">' + step.group(1)
                    + step.group(2) + "</div>"
                ),
                body,
                flags=re.DOTALL,
            )
        elif section_id == "battlefield":
            # A visual aid only: the layers and order come from the adjacent prose.
            anatomy = (
                '<figure class="formation-anatomy" aria-label="Formation layers">'
                '<figcaption>One position · up to three layers</figcaption>'
                '<div class="formation-layers">'
                '<span><b>Name</b><small>Top · identity</small></span>'
                '<span><b>Bond</b><small>Middle · attachment</small></span>'
                '<span><b>Force</b><small>Base · Strength</small></span>'
                '</div><p>Force + Bond + Name = <strong>Named Formation</strong></p>'
                '</figure>'
            )
            body += anatomy
        elif section_id == "stories":
            body = re.sub(
                r'<p>(<strong>(?:Tactics|Narrative|Stratagem|Heroes)</strong>)',
                r'<p class="card-kind-note">\\1',
                body,
            )
        elif section_id == "command":
            body = body.replace("<p>", '<p class="command-primer">', 1)
        return f'<section class="{class_name}">' + heading + body + "</section>"

    rendered = pattern.sub(decorate_section, rendered)

    # Tables stay semantically intact; their container allows horizontal scroll
    # on small screens without crushing multi-column reference text.
    rendered = rendered.replace(
        "<table>", '<div class="rule-table-scroll" tabindex="0" '
        'role="region" aria-label="Rules table"><table>'
    ).replace("</table>", "</table></div>")

    # Keep quick facts subordinate to the introduction, not a duplicate rules
    # section. The explanations and legal exceptions remain in the body text.
    facts = (
        '<aside class="rulebook-fast-facts" aria-label="At a glance">'
        '<div><b>20</b><span>Starting Command</span></div>'
        '<div><b>2</b><span>Actions per normal turn, up to</span></div>'
        '<div><b>4</b><span>Fronts by Battle III</span></div>'
        '<div><b>3</b><span>Formation layers, maximum</span></div>'
        '</aside>'
    )
    rendered = rendered.replace(
        '<section class="rule-section rule-section--learn">',
        facts + '<section class="rule-section rule-section--learn">',
        1,
    )
    return rendered


def render_rule_tokens(source: str, rules: GameRules) -> str:
    recovery = [
        rules.command_recovery_for_battle(battle)
        for battle in range(1, 6)
    ]
    effective_recovery = [
        max(
            rules.command_recovery_floor,
            rules.command_recovery_for_battle(battle),
        )
        for battle in range(1, 7)
    ]
    values = {
        key.upper(): value
        for key, value in rules.as_dict().items()
    }
    # Short aliases keep authored reference copy readable while canonical
    # GameRules field names remain the actual source of truth.
    values.update(
        {
            "MINIMUM_DECK_SIZE": MINIMUM_DECK_SIZE,
            "MINIMUM_FORCE_COUNT": MINIMUM_FORCE_COUNT,
            "MINIMUM_PRINTED_NAME_COUNT": MINIMUM_PRINTED_NAME_COUNT,
            "NON_UNIQUE_COPY_LIMIT": NON_UNIQUE_COPY_LIMIT,
            "UNIQUE_COPY_LIMIT": UNIQUE_COPY_LIMIT,
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
            "EFFECTIVE_RECOVERY_SERIES_PLAIN": ", ".join(
                str(value) for value in effective_recovery
            ) + "...",
            "RECOVERY_BATTLE_3": rules.command_recovery_for_battle(3),
            "RECOVERY_BATTLE_3_LOSE_2": max(
                rules.command_recovery_floor,
                rules.command_recovery_for_battle(3) - 2,
            ),
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


def copy_web_sources(*, inspection_only: bool) -> None:
    """Copy public site assets, excluding orphaned Webgame scripts in inspection builds.

    Source web/ still includes the complete Webgame for future engine work.
    Without its page and runtime, its scripts must not appear in dist/: static
    integrity checks correctly flag their absent DOM targets and dependencies.
    """
    ignored = ["art", "site-nav.template.html"]
    if inspection_only:
        ignored.extend(WEBGAME_RUNTIME_SCRIPTS)
    shutil.copytree(WEB, DIST, ignore=shutil.ignore_patterns(*ignored))


def main() -> None:
    card_data = load_card_file(CARDS)
    inspection_only = os.environ.get("TLW_PAGES_INSPECTION_ONLY") == "1"
    runtime = None if inspection_only else ensure_browser_runtime()
    if DIST.exists():
        shutil.rmtree(DIST)
    # Canonical PNGs are authoring inputs. Generate only optimized derivatives
    # for Pages; never copy the originals into disposable deployment output.
    copy_web_sources(inspection_only=inspection_only)
    if runtime is not None:
        shutil.copytree(runtime, DIST / "runtime")
    else:
        # The webgame needs the native WASM runtime, which is not yet compatible
        # with the evolving physical card pool. Publish inspectable pages anyway.
        (DIST / "play.html").write_text(
            '<!doctype html><html lang="en"><meta charset="utf-8">'
            '<title>Webgame unavailable during card playtest</title>'
            '<style>body{font:1.15rem/1.6 system-ui;max-width:45rem;margin:4rem auto;padding:1rem}</style>'
            '<h1>Webgame temporarily unavailable</h1>'
            '<p>The physical cards, decks, rules and print references remain available '
            'for inspection while the game engine is updated.</p>'
            '<p><a href="cards.html">Inspect cards</a> · '
            '<a href="rulebook.html">Read rules</a> · '
            '<a href="playtest-kit.html">Print decks</a></p></html>',
            encoding="utf-8",
        )
    # Only publish the selected, print-ready PNG sizes used by card-symbols.js.
    # Full-resolution icon sources remain in the repository for editing.
    source_icons = WEB / "art" / "icons" / "sizes" / "128"
    if not source_icons.is_dir():
        raise FileNotFoundError(f"Missing PNG icon candidates: {source_icons}")
    shutil.copytree(source_icons, DIST / "art" / "icons" / "sizes" / "128")
    build_print_art()

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
    (data_dir / "print-cards.json").write_text(
        json.dumps(load_print_cards(card_data), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    shutil.copy2(PLAYTEST_DECKS, data_dir / "playtest-decks.json")

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
        extensions=["extra", "sane_lists", "attr_list"],
    )
    rulebook_html = group_rulebook_sections(rulebook_html)
    rulebook_html = enrich_rulebook_layout(rulebook_html)
    template = (WEB / "rulebook.template.html").read_text(encoding="utf-8")
    rendered = template.replace("{{RULEBOOK}}", rulebook_html)
    (DIST / "rulebook.html").write_text(rendered, encoding="utf-8")
    (DIST / "rulebook.template.html").unlink(missing_ok=True)

    render_site_navigation()
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
