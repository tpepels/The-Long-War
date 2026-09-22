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


def title_case(value: str) -> str:
    return " ".join(part.capitalize() for part in re.split(r"[-_ ]+", value) if part)


def properties(card: dict) -> str:
    values: list[str] = []
    if card["type"] == "subject" and card.get("role"):
        values.append(title_case(card["role"]))
    for value in card.get("classes", []):
        if value == "hero":
            continue
        label = title_case(value)
        if label not in values:
            values.append(label)
    return " · ".join(values)


def type_label(card: dict) -> str:
    if card["type"] == "link":
        return "Bond"
    if card["type"] == "plot":
        form = title_case(card.get("story_form", "Story"))
        return ("Veiled " if card.get("veiled") else "") + form + " Story"
    return title_case(card["type"])


def classes(card: dict) -> str:
    values = [f"card-{card['type']}"]
    if card.get("veiled"):
        values.append("card-veiled")
        values.append("card-scheme")
    if card.get("hero"):
        values.append("card-hero")
    return " ".join(values)


def play_card(card: dict) -> str:
    prop = properties(card) or "&nbsp;"
    strength = (
        f'<span class="play-card-strength">{card["strength"]}</span>'
        if isinstance(card.get("strength"), int)
        else ""
    )
    return (
        f'<article class="play-card {classes(card)}" data-card-id="{html.escape(card["id"])}">'
        f'<div class="play-card-meta"><span>{html.escape(type_label(card))}</span></div>'
        f'<h3>{html.escape(card["title"])}</h3>'
        f'<div class="play-card-properties">{html.escape(prop) if prop != "&nbsp;" else prop}</div>'
        f'{strength}'
        f'<div class="play-card-art"><span class="play-card-symbol">◆</span><b>LW</b></div>'
        f'<div class="play-card-rules">{game_text(card.get("text", "")) or "<em>No special rules.</em>"}</div>'
        f'<footer>SELECT OR DRAG TO PLAY</footer>'
        f'</article>'
    )


def print_card(card: dict) -> str:
    prop = properties(card)
    property_markup = (
        '<div class="card-properties">' +
        " · ".join(f"<em>{html.escape(value.strip())}</em>" for value in prop.split(" · ")) +
        "</div>"
        if prop
        else ""
    )
    strength = (
        f'<div class="strength">{card["strength"]}</div>'
        if isinstance(card.get("strength"), int)
        else ""
    )
    unique = '<span class="unique"><em>Unique</em></span>' if card.get("unique") else ""
    return (
        f'<article class="game-card {classes(card)}" data-card-id="{html.escape(card["id"])}">'
        f'<header class="card-header"><div>'
        f'<div class="card-type">{html.escape(type_label(card))}</div>'
        f'<h2>{html.escape(card["title"])}</h2>{property_markup}'
        f'</div>{strength}</header>'
        f'<div class="card-art"><span class="card-art-symbol">◆</span></div>'
        f'<div class="card-rule"><p>{game_text(card.get("text", "")) or "&nbsp;"}</p></div>'
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
  body {{ padding: 24px; }}
  .layout-test {{ display: flex; flex-wrap: wrap; gap: 24px; align-items: flex-start; }}
  .layout-test .play-card {{ margin-left: 0 !important; transform: none !important; }}
  .layout-test-print {{ display: grid; grid-template-columns: repeat(4, 68mm); gap: 4mm; }}
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
        details = html.unescape(match.group(1)) if match else "unknown overflow"
        raise SystemExit(f"Card text overflow detected: {details}")

    print(f"PASS: {len(cards)} browser cards and {len(cards)} print cards fit fixed regions")


if __name__ == "__main__":
    main()
