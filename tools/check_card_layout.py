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


def rule_markup(card: dict, empty: str = "<em>No special rules.</em>") -> str:
    blocks = card.get("rule_blocks", [])
    if not blocks:
        return (
            '<div class="rule-block rule-empty"><span class="rule-text">'
            + empty
            + "</span></div>"
        )
    return "".join(
        f'<div class="rule-block rule-{html.escape(block["kind"])}">'
        f'<span class="rule-label">{html.escape(block.get("label", "EFFECT"))}</span>'
        f'<span class="rule-text">{game_text(block["text"])}</span></div>'
        for block in blocks
    )


def title_case(value: str) -> str:
    return " ".join(part.capitalize() for part in re.split(r"[-_ ]+", value) if part)


def type_label(card: dict) -> str:
    if card["type"] == "bond":
        return "Bond"
    if card["type"] == "story":
        form = title_case(card.get("narrative_form", ""))
        label = "Ongoing Narrative" if card.get("ongoing") else "Narrative"
        return f"{form} · {label}" if form else label
    if card["type"] == "force" and card.get("hero"):
        return "Hero · Force / Name"
    return title_case(card["type"])


def classes(card: dict) -> str:
    values = [f"card-{card['type']}"]
    if card.get("hero"):
        values.append("card-hero")
    return " ".join(values)


def property_markup(card: dict, class_name: str) -> str:
    class_prefix = "play-card" if class_name.startswith("play-") else "card"
    role_markup = ""
    if card["type"] == "force" and card.get("role"):
        role = title_case(card["role"])
        role_markup = (
            f'<span class="{class_prefix}-role"><strong>{html.escape(role)}</strong>'
            "</span>"
        )
    values = [
        title_case(value)
        for value in card.get("classes", [])
        if value != "hero" and value != card.get("role")
    ]
    classes_markup = " · ".join(
        f"<em>{html.escape(value)}</em>" for value in values
    ) or "&nbsp;"
    return (
        f'<div class="{class_name}">{role_markup}'
        f'<span class="{class_prefix}-classes">{classes_markup}</span></div>'
    )


def play_card(card: dict) -> str:
    strength = (
        (
            '<span class="play-card-strength hero-dual-strength">'
            f'<span><small>F</small>{card["strength"]}</span>'
            f'<span><small>N</small>{card["hero_name_strength"]}</span>'
            '</span>'
        )
        if card.get("hero")
        else (
            f'<span class="play-card-strength">{card["strength"]}</span>'
            if isinstance(card.get("strength"), int)
            else ""
        )
    )
    command = (
        f'<span class="play-command-cost" aria-label="Command cost">C {card["command_cost"]}</span>'
        if isinstance(card.get("command_cost"), int) else ""
    )
    return (
        f'<article class="play-card {classes(card)}" data-card-id="{html.escape(card["id"])}">'
        f'<div class="play-card-meta"><span>{html.escape(type_label(card))}</span><span class="play-card-meta-badges">{command}</span></div>'
        f'<h3>{html.escape(card["title"])}</h3>'
        f'{property_markup(card, "play-card-properties")}'
        f'{strength}'
        f'<div class="play-card-rules">{rule_markup(card, "<em>No special rules.</em>")}</div>'
        f'<footer>SELECT OR INSPECT</footer>'
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


def layout_document(cards: list[dict], browser_markup: str | None = None) -> str:
    """Exercise the shipped print renderer and CSS, including catalogue printing."""
    style_files = ("style.css", "play.css") if browser_markup is not None else ("print-cards.css",)
    styles = "\n".join(
        "<style>" + (ROOT / "web" / name).read_text(encoding="utf-8") + "</style>"
        for name in style_files
    )
    scripts = "\n".join(
        "<script>" + (ROOT / "web" / name).read_text(encoding="utf-8") + "</script>"
        for name in ("card-rules.js", "print-cards.js", "card-layout-guard.js")
    )
    # A card's text must not terminate the inline JSON script element.
    card_data = json.dumps(cards).replace("<", "\\u003c")
    markup = browser_markup if browser_markup is not None else '<main id="cards" class="card-sheets"></main>'
    render = "" if browser_markup is not None else """
const cards = JSON.parse(document.getElementById("card-data").textContent);
document.getElementById("cards").innerHTML = cards.map(card => window.PrintCards.markup(card)).join("");
"""
    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<base href="{(ROOT / 'web').as_uri()}/">
<title>The Long War — print catalogue</title>
{styles}
<style>
  html, body {{ width: auto !important; height: auto !important; min-height: 0 !important; overflow: visible !important; }}
  body {{ margin: 0; padding: 24px; }}
  .layout-test {{ display: flex; flex-wrap: wrap; gap: 24px; align-items: flex-start; }}
  .layout-test .play-card {{ margin-left: 0 !important; transform: none !important; }}
  .layout-test-rotated .play-card {{ transform: rotate(4deg) !important; }}
  #layout-result {{ position: fixed; left: -9999px; }}
  @media print {{ body {{ padding: 0; }} #layout-result {{ display: none; }} }}
</style>
</head>
<body class="{'game-body' if browser_markup is not None else ''}">
<div id="layout-result"></div>
{markup}
<script id="card-data" type="application/json">{card_data}</script>
{scripts}
<script>
{render}
window.addEventListener("load", async () => {{
  await document.fonts.ready;
  const failures = window.CardLayoutGuard.check(document);
  const count = document.querySelectorAll(".game-card, .play-card").length;
  const details = failures
    .map((entry) => (entry.card.dataset.cardId || "unknown") + ":" + entry.regions.join(","));
  for (const font of document.fonts) {{
    if (font.status === "error") details.push("Font failed to load: " + font.family);
  }}
  if (count !== {len(cards)}) details.push("Expected {len(cards)} cards, rendered " + count);
  document.documentElement.dataset.layoutCheck = details.length ? "fail" : "pass";
  document.getElementById("layout-result").textContent = details.join(";");
}});
</script>
</body>
</html>"""


def run_browser(browser: str, path: Path, pdf: Path | None = None) -> subprocess.CompletedProcess[str]:
    command = [
        browser,
        "--headless=new",
        "--no-sandbox",
        "--disable-gpu",
        "--allow-file-access-from-files",
        "--window-size=1920,1080",
        "--virtual-time-budget=1500",
        "--dump-dom",
    ]
    if pdf is not None:
        command.extend([f"--print-to-pdf={pdf}", "--no-pdf-header-footer"])
    command.append(path.as_uri())
    result = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
    if result.returncode != 0:
        command[1] = "--headless"
        result = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--require-browser",
        action="store_true",
        help="Fail instead of skipping when Chrome/Chromium is unavailable.",
    )
    parser.add_argument("--browser", type=Path, help="Path to a Chrome/Chromium executable.")
    parser.add_argument("--pdf", type=Path, help="Also export the full print catalogue to this PDF path.")
    parser.add_argument(
        "--surface", choices=("all", "print", "browser"), default="all",
        help="Card surface to validate (default: all).",
    )
    args = parser.parse_args()
    if args.pdf and args.surface == "browser":
        parser.error("--pdf requires --surface print or all")

    browser = str(args.browser.expanduser().resolve()) if args.browser else browser_path()
    if browser is None:
        if args.require_browser or args.pdf:
            raise SystemExit("Chrome/Chromium is required for card layout validation")
        print("SKIP: Chrome/Chromium is not installed")
        return
    if args.browser and not Path(browser).is_file():
        raise SystemExit(f"Browser executable does not exist: {browser}")

    cards = json.loads((ROOT / "cards" / "cards.json").read_text(encoding="utf-8"))["cards"]
    batch_size = 8
    cases: list[tuple[str, list[dict], str | None]] = []
    if args.surface in ("all", "browser"):
        cases.append((
            "browser-rotated", cards[:batch_size],
            '<section class="layout-test layout-test-rotated">'
            + "".join(play_card(card) for card in cards[:batch_size]) + "</section>",
        ))
    for start in range(0, len(cards), batch_size):
        batch = cards[start : start + batch_size]
        number = start // batch_size + 1
        if args.surface in ("all", "browser"):
            cases.append((
                f"browser-{number}", batch, '<section class="layout-test">' +
                "".join(play_card(card) for card in batch) + "</section>",
            ))
        if args.surface in ("all", "print"):
            cases.append((f"print-{number}", batch, None))
    pdf_path = args.pdf.expanduser().resolve() if args.pdf else None
    if pdf_path is not None:
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        cases.append(("print-catalogue", cards, None))

    for label, batch, markup in cases:
        with tempfile.TemporaryDirectory(prefix=f"longwar-layout-{label}-") as temp_dir:
            path = Path(temp_dir) / f"card-layout-{label}.html"
            path.write_text(layout_document(batch, markup), encoding="utf-8")
            result = run_browser(browser, path, pdf_path if label == "print-catalogue" else None)

        if result.returncode != 0:
            raise SystemExit(
                f"Headless browser failed during {label} card layout validation:\n" +
                result.stderr[-4000:]
            )
        if 'data-layout-check="pass"' not in result.stdout:
            match = re.search(r'<div id="layout-result">([^<]*)</div>', result.stdout)
            details = html.unescape(match.group(1)) if match else "unknown layout failure"
            raise SystemExit(f"{label.title()} card layout failure detected: {details}")

    surfaces = "browser and print" if args.surface == "all" else args.surface
    print(f"PASS: {len(cards)} cards fit their regions on {surfaces} surfaces")
    if pdf_path is not None:
        if not pdf_path.is_file() or pdf_path.stat().st_size == 0:
            raise SystemExit(f"Browser did not create the requested PDF: {pdf_path}")
        print(f"PDF: {pdf_path}")


if __name__ == "__main__":
    main()
