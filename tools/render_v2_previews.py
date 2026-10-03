from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]

def browser_path() -> str | None:
    return next((path for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser") if (path := shutil.which(name))), None)

CARDS = ROOT / "cards" / "v2" / "cards.json"
WEB = ROOT / "web"


def page(markup_js: str, width: int, height: int) -> str:
    cards = json.loads(CARDS.read_text(encoding="utf-8"))["cards"]
    payload = json.dumps(cards).replace("<", "\\u003c")
    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<base href="{WEB.as_uri()}/">
<link rel="stylesheet" href="cards-v2.css">
<style>
  html, body {{ margin: 0; width: {width}px; min-height: {height}px; overflow: hidden; background: #dedbd2; }}
  body {{ padding: 28px; }}
  .proof-title {{ margin: 0 0 18px; font: 600 30px/1 "LW Display", Georgia, serif; color: #29291f; }}
  .proof-subtitle {{ margin: -8px 0 24px; font: 12px/1.3 Arial, sans-serif; color: #5f6458; }}
  .proof-grid {{ display: grid; grid-template-columns: repeat(4, 68mm); gap: 26px 30px; align-items: start; justify-content: center; }}
  .proof-stack {{ width: 68mm; margin: 0; }}
  .proof-stack figcaption {{ min-height: 42px; margin-bottom: 8px; }}
  .proof-stack h3 {{ margin: 0; font: 600 21px/1 "LW Display", Georgia, serif; }}
  .proof-stack p {{ margin: 4px 0 0; font: 11px/1.25 Arial, sans-serif; color: #5c6156; }}
  .proof-card {{ width: 68mm; }}
  .proof-card .v2-card {{ box-shadow: 0 1.4mm 3mm #26271938; }}
</style>
</head>
<body>
<h1 class="proof-title" id="proof-title"></h1>
<p class="proof-subtitle" id="proof-subtitle"></p>
<main id="proof" class="proof-grid"></main>
<script src="v2-heraldry.js"></script>
<script src="v2-reminders.js"></script>
<script src="cards-v2.js"></script>
<script>
const cards = {payload};
{markup_js}
document.fonts.ready.then(() => document.documentElement.dataset.ready = "1");
</script>
</body>
</html>"""


def formation_markup() -> str:
    return r'''
document.getElementById("proof-title").textContent = "V2 formation stack proofs";
document.getElementById("proof-subtitle").textContent = "Actual 10.5 mm overlap - every live Force/Bond rule must remain visible.";
const cases = [
  ["force-alone", "Force alone", "Formation · Unbonded"],
  ["force-bond", "Force + Bond", "Bonded"],
  ["named", "Force + Bond + Name", "Named · also Bonded"],
  ["hero-name", "Hero as Name", "Named · Hero on top"],
];
document.getElementById("proof").innerHTML = cases.map(([id, title, state]) =>
  '<figure class="proof-stack"><figcaption><h3>' + title + '</h3><p>' + state + '</p></figcaption>' +
  window.V2Cards.stackMarkup(cards, id) + '</figure>'
).join("");
'''


def family_markup() -> str:
    return r'''
document.getElementById("proof-title").textContent = "V2 card families and text density";
document.getElementById("proof-subtitle").textContent = "Same physical component at short, medium and dense rules loads.";
const ids = [
  "the-fifty-men",
  "watched-the-skies-for",
  "corin-of-the-high-wall",
  "rovan-the-gatebreaker",
  "the-scouts-found-the-gap",
  "the-center-must-hold",
  "the-king-had-given-the-order",
  "serai-queen-of-crows",
];
document.getElementById("proof").innerHTML = ids.map(id => {
  const card = cards.find(c => c.id === id);
  return '<div class="proof-card">' + window.V2Cards.cardArticle(card) + '</div>';
}).join("");
'''


def screenshot(browser: str, html: Path, output: Path, width: int, height: int) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        browser,
        "--headless=new",
        "--no-sandbox",
        "--disable-gpu",
        "--hide-scrollbars",
        "--allow-file-access-from-files",
        f"--window-size={width},{height}",
        "--virtual-time-budget=2000",
        f"--screenshot={output}",
        html.as_uri(),
    ]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=45, check=False)
    if result.returncode != 0:
        command[1] = "--headless"
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=45, check=False)
    if result.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
        raise SystemExit("Could not render V2 preview:\n" + result.stderr[-4000:])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT / "web" / "art" / "v2" / "previews")
    parser.add_argument("--browser", type=Path)
    parser.add_argument("--require-browser", action="store_true")
    args = parser.parse_args()
    browser = str(args.browser.resolve()) if args.browser else browser_path()
    if not browser:
        if args.require_browser:
            raise SystemExit("Chrome/Chromium is required")
        print("SKIP: Chrome/Chromium is not installed")
        return

    output = args.output_dir.resolve()
    with tempfile.TemporaryDirectory(prefix="longwar-v2-preview-") as temp:
        temp = Path(temp)
        formation = temp / "formation.html"
        family = temp / "families.html"
        formation.write_text(page(formation_markup(), 1450, 760), encoding="utf-8")
        family.write_text(page(family_markup(), 1450, 980), encoding="utf-8")
        screenshot(browser, formation, output / "v2-formation-stacks.png", 1450, 760)
        screenshot(browser, family, output / "v2-card-families.png", 1450, 980)
    print(f"Rendered V2 previews to {output}")


if __name__ == "__main__":
    main()
