from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def game_text(value: str) -> str:
    escaped = html.escape(value)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", escaped)
    return escaped


def rule_markup(card: dict, empty: str = "&nbsp;") -> str:
    blocks = card.get("rule_blocks", [])
    if not blocks:
        return f'<div class="rule-block rule-empty">{empty}</div>'
    return "".join(
        f'<div class="rule-block rule-{html.escape(block["kind"])}">'
        f'{game_text(block["text"])}</div>'
        for block in blocks
    )


def title_case(value: str) -> str:
    return " ".join(part.capitalize() for part in re.split(r"[-_ ]+", value) if part)


def properties(card: dict) -> list[str]:
    values: list[str] = []
    if card["type"] == "subject" and card.get("role"):
        values.append(title_case(card["role"]))
    for value in card.get("classes", []):
        if value == "hero":
            continue
        label = title_case(value)
        if label not in values:
            values.append(label)
    return values


def type_label(card: dict) -> str:
    if card["type"] == "link":
        return "Bond"
    if card["type"] == "plot":
        form = title_case(card.get("story_form", "Story"))
        return f"{form} · " + ("Veiled Story" if card.get("veiled") else "Story")
    if card["type"] == "subject" and card.get("hero"):
        return "Hero · Subject"
    return title_case(card["type"])


def classes(card: dict) -> str:
    values = [f"card-{card['type']}"]
    if card.get("veiled"):
        values.extend(["card-veiled", "card-scheme"])
    if card.get("hero"):
        values.append("card-hero")
    return " ".join(values)


def property_markup(card: dict, class_name: str) -> str:
    values = properties(card)
    content = " · ".join(f"<em>{html.escape(value)}</em>" for value in values) or "&nbsp;"
    return f'<div class="{class_name}">{content}</div>'


def play_card(card: dict) -> str:
    strength = (
        f'<span class="play-card-strength">{card["strength"]}</span>'
        if isinstance(card.get("strength"), int)
        else ""
    )
    return (
        f'<article class="play-card {classes(card)}" data-card-id="{html.escape(card["id"])}">'
        f'<div class="play-card-meta"><span>{html.escape(type_label(card))}</span></div>'
        f'<h3>{html.escape(card["title"])}</h3>'
        f'{property_markup(card, "play-card-properties")}'
        f'{strength}'
        f'<div class="play-card-art"><span class="play-card-symbol">◆</span><b>LW</b></div>'
        f'<div class="play-card-rules">{rule_markup(card, "<em>No special rules.</em>")}</div>'
        f'<footer>SELECT OR DRAG TO PLAY</footer>'
        f'</article>'
    )


def print_card(card: dict) -> str:
    strength = (
        f'<div class="strength">{card["strength"]}</div>'
        if isinstance(card.get("strength"), int)
        else ""
    )
    unique = '<span class="unique"><em>Unique</em></span>' if card.get("unique") else ""
    return (
        f'<article class="game-card {classes(card)}" data-card-id="{html.escape(card["id"])}">'
        f'<div class="card-meta"><span class="card-type">{html.escape(type_label(card))}</span>{strength}</div>'
        f'<h2 class="card-title">{html.escape(card["title"])}</h2>'
        f'{property_markup(card, "card-properties")}'
        f'<div class="card-art"><span class="card-art-sigil">◆</span>'
        f'<span class="card-art-name">{html.escape(card["title"])}</span></div>'
        f'<div class="card-rule">{rule_markup(card)}</div>'
        f'<footer class="card-footer">{unique}<span class="card-id">{html.escape(card["id"])}</span></footer>'
        f'</article>'
    )


def browser_path() -> str | None:
    return next(
        (
            path
            for name in (
                "google-chrome",
                "google-chrome-stable",
                "chromium",
                "chromium-browser",
            )
            if (path := shutil.which(name))
        ),
        None,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--require-browser",
        action="store_true",
        help="Fail instead of skipping when Chrome/Chromium is unavailable.",
    )
    args = parser.parse_args()

    browser = browser_path()
    if browser is None:
        if args.require_browser:
            raise SystemExit("Chrome/Chromium is required for card layout validation")
        print("SKIP: Chrome/Chromium is not installed")
        return

    cards = json.loads((ROOT / "cards" / "cards.json").read_text(encoding="utf-8"))["cards"]
    style = (ROOT / "web" / "style.css").read_text(encoding="utf-8")
    play_style = (ROOT / "web" / "play.css").read_text(encoding="utf-8")
    guard = (ROOT / "web" / "card-layout-guard.js").read_text(encoding="utf-8")

    document = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>{style}</style>
<style>{play_style}</style>
<style>
  html, body {{ width: auto !important; height: auto !important; min-height: 0 !important; overflow: visible !important; }}
  body {{ padding: 24px; }}
  .layout-test {{ display: flex; flex-wrap: wrap; gap: 24px; align-items: flex-start; }}
  .layout-test .play-card {{ margin-left: 0 !important; transform: none !important; }}
  .layout-test-print {{ display: grid; grid-template-columns: repeat(4, 68mm); gap: 4mm; margin-top: 24px; }}
  #layout-result {{ position: fixed; left: -9999px; }}
</style>
</head>
<body class="game-body">
<div id="layout-result"></div>
<section class="layout-test">
{''.join(play_card(card) for card in cards)}
</section>
<section class="layout-test-print">
{''.join(print_card(card) for card in cards)}
</section>
<script>{guard}</script>
<script>
window.addEventListener("load", () => {{
  const failures = window.CardLayoutGuard.check(document);
  document.documentElement.dataset.layoutCheck = failures.length ? "fail" : "pass";
  document.getElementById("layout-result").textContent = failures
    .map((entry) => (entry.card.dataset.cardId || "unknown") + ":" + entry.regions.join(","))
    .join(";");
}});
</script>
</body>
</html>"""

    with tempfile.TemporaryDirectory(prefix="longwar-layout-") as temp_dir:
        path = Path(temp_dir) / "card-layout.html"
        path.write_text(document, encoding="utf-8")
        command = [
            browser,
            "--headless=new",
            "--no-sandbox",
            "--disable-gpu",
            "--window-size=1920,1080",
            "--virtual-time-budget=1500",
            "--dump-dom",
            path.as_uri(),
        ]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode != 0 and "--headless=new" in command:
            command[1] = "--headless"
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

    if result.returncode != 0:
        raise SystemExit(
            "Headless browser failed during card layout validation:\n" +
            result.stderr[-4000:]
        )

    if 'data-layout-check="pass"' not in result.stdout:
        match = re.search(r'<div id="layout-result">([^<]*)</div>', result.stdout)
        details = html.unescape(match.group(1)) if match else "unknown layout failure"
        raise SystemExit(f"Card layout failure detected: {details}")

    print(f"PASS: {len(cards)} browser cards and {len(cards)} print cards fit fixed regions")


if __name__ == "__main__":
    main()
