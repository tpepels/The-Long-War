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
    if card["type"] == "narrative":
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
    """Exercise the browser play-card surface; physical print uses V2Cards."""
    if browser_markup is None:
        raise ValueError("Legacy print renderer was removed; use check_v2_layout for physical cards")
    styles = "\n".join(
        "<style>" + (ROOT / "web" / name).read_text(encoding="utf-8") + "</style>"
        for name in ("style.css", "play.css")
    )
    scripts = "\n".join(
        "<script>" + (ROOT / "web" / name).read_text(encoding="utf-8") + "</script>"
        for name in ("card-rules.js", "card-layout-guard.js")
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


def v2_layout_document(cards: list[dict], stacks: bool = False) -> str:
    """Measure the same V2 physical renderer used by the catalogue and stacks."""
    card_data = json.dumps(cards).replace("<", "\\u003c")
    page_source = (ROOT / "web" / "cards-v2.html").read_text(encoding="utf-8")
    source_names = [source.split("?", 1)[0] for source in re.findall(
        r'<script\b[^>]*\bsrc=["\']([^"\']+)["\']', page_source,
    )]
    scripts = "\n".join(
        "<script>" + (ROOT / "web" / name).read_text(encoding="utf-8") + "</script>"
        for name in source_names
    )
    css = (ROOT / "web" / "cards-v2.css").read_text(encoding="utf-8")
    render = (
        'root.innerHTML = ["force-alone", "force-bond", "force-name", "named", "hero-force", "hero-name"]'
        '.map(name => window.V2Cards.stackMarkup(cards, name)).join("");'
        if stacks else
        'root.innerHTML = cards.map(card => \'<div class="card-wrap">\' + window.V2Cards.cardArticle(card) + "</div>").join("");'
    )
    checks = r"""
const mm = 96 / 25.4;
const issues = [];
const fail = (card, reason) => issues.push((card?.dataset.cardId || "stacks") + ":" + reason);
const rect = element => element.getBoundingClientRect();
function inside(outer, inner, tolerance = 1.5) {
  return inner.left >= outer.left - tolerance && inner.top >= outer.top - tolerance &&
    inner.right <= outer.right + tolerance && inner.bottom <= outer.bottom + tolerance;
}
function visible(element) {
  const style = getComputedStyle(element);
  return style.display !== "none" && style.visibility !== "hidden" && Number(style.opacity) > 0;
}
const anchors = new Map();
function sameAnchor(card, label, values) {
  if (!anchors.has(label)) anchors.set(label, values);
  else if (values.some((value, index) => Math.abs(value - anchors.get(label)[index]) > 1))
    fail(card, "unaligned-" + label);
}
const textContext = document.createElement("canvas").getContext("2d");
function textInk(element) {
  // A Range includes the font's unused ascender/descender space. Canvas ink
  // metrics distinguish actual clipping from harmless tight line boxes.
  const range = document.createRange();
  range.selectNodeContents(element);
  const box = range.getBoundingClientRect(), style = getComputedStyle(element);
  // Computed font shorthand is empty for lining-nums in Chromium.
  textContext.font = [style.fontStyle, style.fontWeight, style.fontSize, style.fontFamily].join(" ");
  textContext.letterSpacing = style.letterSpacing;
  const metrics = textContext.measureText(element.textContent);
  const ascent = style.fontVariantNumeric.includes("lining-nums")
    ? Math.max(metrics.actualBoundingBoxAscent, textContext.measureText("H").actualBoundingBoxAscent)
    : metrics.actualBoundingBoxAscent;
  const baseline = box.top + metrics.fontBoundingBoxAscent;
  return {
    left: box.left - metrics.actualBoundingBoxLeft,
    right: Math.max(box.right, box.left + metrics.actualBoundingBoxRight),
    top: baseline - ascent,
    bottom: baseline + metrics.actualBoundingBoxDescent,
    baseline,
  };
}
const articles = [...document.querySelectorAll(".v2-card")];
if (!articles.length) issues.push("No V2 physical cards rendered");
if (!STACKS && articles.length !== cards.length) issues.push("Wrong catalogue card count");
for (const card of articles) {
  const bounds = rect(card);
  if (Math.abs(bounds.width - 68 * mm) > 1 || Math.abs(bounds.height - 96 * mm) > 1) fail(card, "physical-size");
  const formationCard = card.matches(".card-force, .card-bond, .card-name, .card-hero");
  const edge = card.querySelector(".stack-edge");
  if (formationCard) {
    if (!edge) {
      fail(card, "missing-stack-edge");
    } else {
      if (Math.abs(rect(edge).bottom - bounds.top - 10.5 * mm) > 1) fail(card, "edge-height");
      const headerStats = [...edge.querySelectorAll(".strength-mark, .hero-stat")];
      const first = headerStats[0];
      if (!first) fail(card, "missing-header-strength");
      else sameAnchor(card, "first-strength", [rect(first).left - bounds.left, rect(first).top - bounds.top]);
      const identity = edge.querySelector(".edge-identity");
      if (identity) sameAnchor(card, "classification-row-center", [rect(identity).top - bounds.top + rect(identity).height / 2]);
      const live = edge.querySelector(".edge-live-group");
      if (live) sameAnchor(card, "live-row-center", [rect(live).top - bounds.top + rect(live).height / 2]);
      if (edge.querySelector(".edge-heading, .edge-reminders")) fail(card, "stack-edge-not-single-row");
      for (const stat of headerStats) {
        const numeral = stat.querySelector("b");
        if (!numeral) { fail(card, "missing-header-stat-numeral"); continue; }
        if (!visible(stat) || !visible(numeral)) fail(card, "header-stat-hidden");
        const ink = textInk(numeral);
        if (!inside(rect(edge), ink, 1)) fail(card, "header-stat-text-outside");
        if (parseFloat(getComputedStyle(numeral).fontSize) < 3.8 * mm - .1) fail(card, "header-stat-font-shrunk");
        sameAnchor(card, "header-stat-baseline", [ink.baseline - bounds.top]);
      }
      const placement = edge.querySelector(".edge-placement");
      if (placement && (!visible(placement) || !inside(rect(edge), rect(placement), 1))) fail(card, "row-restriction-outside");
      for (const element of edge.querySelectorAll(".edge-identity, .edge-live-group")) {
        const label = element.classList.contains("edge-live-group") ? "edge-live-group" : "edge-identity";
        if (!visible(element) || !inside(rect(edge), rect(element))) fail(card, label + "-outside");
        if (element.scrollHeight > element.clientHeight + 1 || element.scrollWidth > element.clientWidth + 1)
          fail(card, label + "-overflow");
      }
    }
  } else {
    const crown = card.querySelector(".event-crown");
    if (!crown) fail(card, "missing-event-crown");
    else if (!visible(crown) || !inside(bounds, rect(crown))) fail(card, "event-crown-outside");
  }
  for (const selector of [".card-title", ".rules", ".card-footer", ".cost-gem"]) {
    const element = card.querySelector(selector);
    if (!element) { fail(card, "missing-" + selector.slice(1)); continue; }
    if (!visible(element)) fail(card, selector.slice(1) + "-hidden");
    if (!inside(bounds, rect(element))) fail(card, selector.slice(1) + "-outside");
    if (element.scrollHeight > element.clientHeight + 1 || element.scrollWidth > element.clientWidth + 1)
      fail(card, selector.slice(1) + "-overflow");
  }
  const art = card.querySelector(".motif-field"), rules = card.querySelector(".rules"), footer = card.querySelector(".card-footer");
  if (art && rules && rect(rules).top < rect(art).bottom - 1) fail(card, "art-rules-overlap");
  if (art && art.querySelector("svg, img")) fail(card, "art-overlay");
  if (rules && footer && rect(rules).bottom > rect(footer).top + 1.5) fail(card, "rules-footer-overlap");
  const cost = card.querySelector(".cost-gem");
  if (cost) sameAnchor(card, "command-anchor", [bounds.right - rect(cost).right, bounds.bottom - rect(cost).bottom]);
  if (footer && cost && (!footer.contains(cost) || rect(cost).bottom > rect(footer).bottom + 1 || rect(cost).bottom < rect(footer).top))
    fail(card, "cost-not-anchored-to-footer");
  if (cost) for (const text of card.querySelectorAll(".effect-text")) {
    const a = rect(cost), b = rect(text);
    if (a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top) fail(card, "rules-cost-overlap");
  }
}
if (STACKS) {
  const expected = {
    "force-bond": ["force", "bond"], "force-name": ["force", "name"],
    "named": ["force", "bond", "name"], "hero-force": ["hero", "bond", "name"],
    "hero-name": ["force", "bond", "hero"],
  };
  const byId = new Map(cards.map(card => [card.id, card]));
  for (const [name, types] of Object.entries(expected)) {
    const stack = document.querySelector('.stack-demo[data-stack-case="' + name + '"]');
    if (!stack) { issues.push(name + ":missing-stack"); continue; }
    const wrappers = [...stack.querySelectorAll(".stack-card")];
    const layers = wrappers.map(layer => layer.matches(".v2-card") ? layer : layer.querySelector(".v2-card"));
    if (layers.some(layer => !layer)) { issues.push(name + ":missing-physical-card"); continue; }
    const actual = layers.map(card => byId.get(card.dataset.cardId)?.type);
    if (JSON.stringify(actual) !== JSON.stringify(types)) issues.push(name + ":wrong-stack-composition");
    for (let index = 0; index < layers.length; index++) {
      const card = layers[index], body = card.querySelector(".card-body");
      if (Number(wrappers[index].dataset.stackLayer) !== index) fail(card, "wrong-stack-layer");
      if (!body || !visible(body) || rect(body).height < 20 * mm) fail(card, "stack-body-hidden");
      if (Math.abs(rect(card).top - rect(layers[0]).top - index * 10.5 * mm) > 1) fail(card, "wrong-stack-offset");
      if (index + 1 < layers.length && rect(card.querySelector(".stack-edge")).bottom > rect(layers[index + 1]).top + 1)
        fail(card, "buried-edge-covered");
      if (byId.get(card.dataset.cardId)?.type === "hero" && card.dataset.heroMode !== (name === "hero-name" ? "name" : "force"))
        fail(card, "wrong-hero-mode");
    }
  }
}
for (const font of document.fonts) if (font.status === "error") issues.push("Font failed to load: " + font.family);
document.documentElement.dataset.layoutCheck = issues.length ? "fail" : "pass";
document.getElementById("layout-result").textContent = issues.join(";");
""".replace("STACKS", "true" if stacks else "false")
    return f"""<!doctype html><html><head><meta charset="utf-8">
<base href="{(ROOT / 'web').as_uri()}/"><title>The Long War — V2 physical cards</title>
<meta name="lw-build-version" content="layout-check">
<style>{css}</style><style>#layout-result {{ position:fixed; left:-9999px; }} @media print {{ #layout-result {{ display:none; }} }}</style>
</head><body><div id="layout-result"></div><main id="v2-layout" class="{'stack-examples' if stacks else 'cards'}"></main>
<script id="card-data" type="application/json">{card_data}</script>
{scripts}<script>
const cards = JSON.parse(document.getElementById("card-data").textContent);
const root = document.getElementById("v2-layout");
{render}
window.addEventListener("load", async () => {{ await document.fonts.ready; {checks} }});
</script><div class="print-version" aria-hidden="true">TLW print vlayout-check</div></body></html>"""


def check_v2_layout(browser: str, pdf_path: Path | None = None) -> None:
    cards = json.loads((ROOT / "cards" / "v2" / "cards.json").read_text(encoding="utf-8"))["cards"]
    probe = {
        "id": "oversized-reminder-probe", "title": "Oversized reminder probe", "type": "force",
        "strength": 0, "command_cost": 0, "classes": ["human"],
        "effects": [{"timing": "action", "limit": "once_per_battle",
                     "text": "Choose another friendly formation in this Front. " * 30,
                     "exposed": "ACTION 1/B · incomplete hint"}],
    }
    numeric_probe = {
        "id": "numeric-range-probe", "title": "Ariadne of the Twenty Standards", "type": "hero",
        "force_strength": 12, "name_strength_modifier": -2, "command_cost": 20,
        "classes": ["human", "king", "veteran"], "unique": True,
        "modes": {"force": {"effects": []}, "name": {"effects": []}},
    }
    if pdf_path is not None:
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
    for label, document, expect_overflow in (
        ("v2-catalogue", v2_layout_document(cards), False),
        ("v2-stacks", v2_layout_document(cards, stacks=True), False),
        ("v2-numeric-range", v2_layout_document([numeric_probe]), False),
        ("v2-overflow-probe", v2_layout_document([probe]), True),
    ):
        with tempfile.TemporaryDirectory(prefix="longwar-layout-" + label + "-") as temp_dir:
            path = Path(temp_dir) / (label + ".html")
            path.write_text(document, encoding="utf-8")
            result = run_browser(browser, path, pdf_path if label == "v2-catalogue" else None)
        if result.returncode != 0:
            raise SystemExit(f"Headless browser failed during {label}:\n" + result.stderr[-4000:])
        match = re.search(r'<div id="layout-result">([^<]*)</div>', result.stdout)
        details = html.unescape(match.group(1)) if match else "validation did not complete"
        if expect_overflow:
            if 'data-layout-check="fail"' not in result.stdout or "oversized-reminder-probe:edge-live" not in details:
                raise SystemExit("V2 oversized reminder was not flagged: " + details)
        elif 'data-layout-check="pass"' not in result.stdout:
            raise SystemExit(f"{label} card layout failure detected: {details}")
    if pdf_path is not None:
        if not pdf_path.is_file() or not pdf_path.stat().st_size:
            raise SystemExit(f"Browser did not create the requested PDF: {pdf_path}")
        if extractor := shutil.which("pdftotext"):
            extracted = subprocess.run(
                [extractor, "-layout", str(pdf_path), "-"], capture_output=True,
                text=True, timeout=30, check=False,
            )
            if extracted.returncode:
                raise SystemExit("Could not inspect exported V2 PDF: " + extracted.stderr)
            pages = extracted.stdout.split("\f")
            if not pages[-1].strip():
                pages.pop()
            expected_pages = (len(cards) + 7) // 8
            if len(pages) != expected_pages:
                raise SystemExit(f"V2 PDF must have {expected_pages} eight-card sheets; found {len(pages)} pages")
            blank_pages = [str(index) for index, page in enumerate(pages, 1) if not page.strip()]
            if blank_pages:
                raise SystemExit("V2 PDF contains blank pages: " + ", ".join(blank_pages))
            unstamped_pages = [str(index) for index, page in enumerate(pages, 1)
                               if "TLW print vlayout-check" not in re.sub(r"\s+", " ", page)]
            if unstamped_pages:
                raise SystemExit("V2 PDF is missing the print version on pages: " + ", ".join(unstamped_pages))
            missing = [card["id"] for card in cards if not re.search(
                r"(?<![a-z0-9-])" + re.escape(card["id"]) + r"(?![a-z0-9-])", extracted.stdout,
            )]
            if missing:
                raise SystemExit("V2 PDF is missing card IDs: " + ", ".join(missing))
        else:
            raise SystemExit("pdftotext is required to verify V2 PDF pagination and card coverage")
        print(f"PDF: {pdf_path}")
    print(f"PASS: {len(cards)} V2 physical cards, six formation stacks, numeric-range stress, and oversized-reminder detection")


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
        "--surface", choices=("all", "print", "browser", "v2"), default="all",
        help="Card surface to validate (print and v2 both use the shared V2 physical renderer).",
    )
    args = parser.parse_args()
    if args.pdf and args.surface == "browser":
        parser.error("--pdf requires --surface print, all, or v2")

    browser = str(args.browser.expanduser().resolve()) if args.browser else browser_path()
    if browser is None:
        if args.require_browser or args.pdf:
            raise SystemExit("Chrome/Chromium is required for card layout validation")
        print("SKIP: Chrome/Chromium is not installed")
        return
    if args.browser and not Path(browser).is_file():
        raise SystemExit(f"Browser executable does not exist: {browser}")
    pdf_path = args.pdf.expanduser().resolve() if args.pdf else None
    if args.surface in ("print", "v2"):
        check_v2_layout(browser, pdf_path)
        return

    cards = json.loads((ROOT / "cards" / "cards.json").read_text(encoding="utf-8"))["cards"]
    batch_size = 8
    cases: list[tuple[str, list[dict], str | None]] = [
        (
            "browser-rotated", cards[:batch_size],
            '<section class="layout-test layout-test-rotated">'
            + "".join(play_card(card) for card in cards[:batch_size]) + "</section>",
        )
    ]
    for start in range(0, len(cards), batch_size):
        batch = cards[start : start + batch_size]
        number = start // batch_size + 1
        cases.append((
            f"browser-{number}", batch, '<section class="layout-test">' +
            "".join(play_card(card) for card in batch) + "</section>",
        ))

    for label, batch, markup in cases:
        with tempfile.TemporaryDirectory(prefix=f"longwar-layout-{label}-") as temp_dir:
            path = Path(temp_dir) / f"card-layout-{label}.html"
            path.write_text(layout_document(batch, markup), encoding="utf-8")
            result = run_browser(browser, path)
        if result.returncode != 0:
            raise SystemExit(
                f"Headless browser failed during {label} card layout validation:\n" +
                result.stderr[-4000:]
            )
        if 'data-layout-check="pass"' not in result.stdout:
            match = re.search(r'<div id="layout-result">([^<]*)</div>', result.stdout)
            details = html.unescape(match.group(1)) if match else "unknown layout failure"
            raise SystemExit(f"{label.title()} card layout failure detected: {details}")

    print(f"PASS: {len(cards)} browser play cards fit their fixed regions")
    if args.surface == "all":
        check_v2_layout(browser, pdf_path)



if __name__ == "__main__":
    main()
