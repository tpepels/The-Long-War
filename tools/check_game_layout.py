"""Render native presentation snapshots through the real desktop client.

Only the browser transport is replaced in the temporary fixture. The production
HTML, CSS, card renderer, interaction renderer and layout code are unchanged.
"""
from __future__ import annotations

import argparse
import copy
from functools import lru_cache
import html
import json
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from urllib.parse import quote
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEWPORTS = [(1280, 720), (1366, 768), (1440, 900), (1920, 1080)]
SCENARIOS = ("battle", "targeting", "inspector", "ai", "choose-first", "complete", "mulligan", "drawer")


def browser_path() -> str | None:
    return next((path for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")
                 if (path := shutil.which(name))), None)


@lru_cache(maxsize=None)
def browser_vertical_inset(browser: str) -> int:
    # New Chrome headless reserves browser chrome inside --window-size. Measure
    # it so "1280x720" means the document viewport, not the outer window.
    probe = "data:text/html," + quote('<script>document.write("viewport-height:" + innerHeight)</script>')
    result = subprocess.run([browser, "--headless=new", "--no-sandbox", "--disable-gpu",
                             "--force-device-scale-factor=1", "--window-size=1000,900", "--dump-dom", probe],
                            capture_output=True, text=True, timeout=20, check=True)
    match = re.search(r"<body>viewport-height:(\d+)", result.stdout)
    if not match:
        raise RuntimeError("Could not measure the headless browser viewport")
    return 900 - int(match.group(1))


def browser_window_size(browser: str, width: int, height: int) -> str:
    return f"--window-size={width},{height + browser_vertical_inset(browser)}"


def presentation_snapshots() -> dict[str, dict]:
    """Use canonical visibility/strength/action encoding for crowded QA states."""
    from longwar.game.engine import all_positions
    from longwar.game.model import Phase, SchemeState, StratagemState
    from longwar.web_api import PlaySession

    card_json = (ROOT / "cards/cards.json").read_text(encoding="utf-8")
    deck_json = (ROOT / "decks/reference.json").read_text(encoding="utf-8")
    cards = json.loads(card_json)["cards"]
    by_type = {kind: sorted((card for card in cards if card["type"] == kind),
                           key=lambda card: len(card["title"]), reverse=True)
               for kind in ("subject", "link", "name", "stratagem")}
    veiled = next(card["id"] for card in cards if card.get("veiled"))
    session = PlaySession(card_json, deck_json, "heuristic", 1701, paced_ai=True)
    opening = session.snapshot(0)
    session.mulligan([], 0)
    session.state.active_player = 0
    session.opening_player = None  # No opening announcement over the layout cases.
    for owner in range(2):
        for index, position in enumerate(all_positions()):
            slot = session.state.slot(owner, position)
            slot.subject = by_type["subject"][index % len(by_type["subject"])]["id"]
            slot.link = by_type["link"][index % len(by_type["link"])]["id"]
            slot.name = by_type["name"][index % len(by_type["name"])]["id"]
        session.state.schemes[owner] = [SchemeState(veiled) for _ in range(3)]
        session.state.stratagems[owner] = StratagemState(
            by_type["stratagem"][owner]["id"],
            revealed=True,
        )
    session.state.players[0].hand = [card["id"] for card in sorted(cards, key=lambda card: len(card["title"]), reverse=True)[:18]]
    session.state.players[1].hand = [card["id"] for card in cards[:18]]
    session.state.players[0].discard = [by_type["subject"][0]["id"]]
    session.state.players[1].discard = [by_type["name"][0]["id"]]
    crowded = session.snapshot(0)
    cases = {name: copy.deepcopy(crowded) for name in ("battle", "inspector", "drawer")}
    # One free Subject destination exercises legal-target highlighting using an
    # action encoded by the real engine, with the rest of the formations full.
    session.state.board[0][0][1].subject = None
    session.state.players[0].hand.append(by_type["subject"][0]["id"])
    cases["targeting"] = session.snapshot(0)
    session.state.active_player = 1
    cases["ai"] = session.snapshot(0)
    session.state.active_player = 0
    session.state.battle = 2
    session.state.phase = Phase.CHOOSE_FIRST
    session.state.chooser = 0
    session.state.players[0].victories = 1
    cases["choose-first"] = session.snapshot(0)
    session.state.phase = Phase.COMPLETE
    session.state.winner = 0
    session.state.players[0].victories = 2
    cases["complete"] = session.snapshot(0)
    cases["mulligan"] = opening
    return cases


TRANSPORT = """
const scenario = new URL(location.href).searchParams.get("scenario") || "battle";
const snapshots = await (await fetch("./qa-snapshots.json")).json();
export async function initializeBrowserEngine() {}
export class BrowserSession {
  snapshot() { return structuredClone(snapshots[scenario]); }
  view() { return this.snapshot(); }
  act() { return this.snapshot(); }
  mulligan() { return this.snapshot(); }
  aiStep() { return this.snapshot(); }
  destroy() {}
}
"""

CHECK_SCRIPT = r"""
<script>
(() => {
  const scenario = new URL(location.href).searchParams.get("scenario") || "battle";
  const failures = [];
  const epsilon = 2;
  const $ = (id) => document.getElementById(id);
  const fail = (name) => { if (!failures.includes(name)) failures.push(name); };
  window.addEventListener("error", (event) => fail("script-error:" + event.message));
  window.addEventListener("unhandledrejection", (event) => fail("script-rejection:" + event.reason));
  const rect = (element) => element.getBoundingClientRect();
  const visible = (element) => element && !element.hidden && rect(element).width > 0 && rect(element).height > 0;
  function withinViewport(element, name) {
    const box = rect(element);
    if (box.left < -epsilon || box.right > innerWidth + epsilon ||
        box.top < -epsilon || box.bottom > innerHeight + epsilon) fail(name);
  }
  function essential(element, name) {
    if (!visible(element)) return fail(name + "-hidden");
    withinViewport(element, name + "-clipped");
  }
  async function run() {
    for (let attempt = 0; attempt < 100; attempt++) {
      if ($("start-game") && !$('start-game').disabled) break;
      await new Promise((resolve) => setTimeout(resolve, 20));
    }
    $("new-game-form").requestSubmit();
    await new Promise((resolve) => setTimeout(resolve, 120));
    const stableZones = [...document.querySelectorAll(".opponent-rack, .hand-dock, .campaign-hud, #battlefield")].map((element) => [element, rect(element)]);
    if (scenario === "targeting") {
      const card = document.querySelector("#hand .play-card.playable.card-subject");
      if (!card) fail("targeting-card-unavailable");
      else card.click();
      if (!document.querySelector(".digital-slot.targetable")) fail("targeting-highlight-missing");
      essential($("cancel-selection"), "cancel-selection");
    }
    if (scenario === "inspector") {
      document.querySelector(".board-card[data-inspect-card]")?.click();
      essential($("card-inspector"), "inspector");
      const card = document.querySelector("#card-inspector-card .play-card");
      if (!card) fail("inspector-card-missing");
      else essential(card, "inspector-card");
      essential($("card-inspector-close"), "inspector-close");
    }
    if (scenario === "battle") {
      document.querySelector("#hand [data-hand-card]")?.click();
      const cycle = $("cycle-button");
      if (cycle && !cycle.hidden && getComputedStyle(cycle).display !== "none") {
        fail("standard-cycle-control-visible");
      }
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    }
    if (scenario === "drawer") {
      document.querySelector('[data-open-drawer="piles"]')?.click();
      essential($("game-drawer"), "game-drawer");
    }
    await new Promise((resolve) => setTimeout(resolve, 180));
    const root = document.documentElement;
    for (const [element, before] of stableZones) {
      const after = rect(element);
      if (["left", "top", "width", "height"].some((key) => Math.abs(before[key] - after[key]) > epsilon)) fail("interaction-moved-" + (element.id || element.className));
    }
    for (const [element, name] of [[root, "root-scroll"], [document.body, "body-scroll"]]) {
      if (element.scrollWidth > innerWidth + epsilon) fail(name + "-horizontal");
      if (element.scrollHeight > innerHeight + epsilon) fail(name + "-vertical");
    }
    const shell = document.querySelector(".tabletop-shell");
    essential(shell, "shell-outside-viewport");
    essential(document.querySelector(".opponent-rack"), "opponent-rack");
    essential(document.querySelector(".hand-dock"), "hand-dock");
    essential($("match-strip"), "battle-hud");
    if (document.querySelectorAll(".command-counter").length !== 2) fail("public-command-counters-missing");
    if (scenario !== "mulligan") {
      essential($("battlefield"), "battlefield");
      if (rect($("battlefield")).height < innerHeight * .38) fail("battlefield-too-small");
      if (document.querySelectorAll(".digital-slot").length !== 12) fail("formation-positions-missing");
      if (!document.querySelector(".scheme-marker.hidden")) fail("hidden-scheme-zone-missing");
      if (!document.querySelector(".stratagem-marker:not(.hidden)")) fail("public-stratagem-zone-missing");
      document.querySelectorAll(".scheme-marker.hidden:not(.known) [data-inspect-card]").forEach(() => fail("hidden-card-inspectable"));
    }
    document.querySelectorAll("#hand > .play-card").forEach((card, index) => {
      withinViewport(card, "hand-card-" + index + "-clipped");
      if (card.tabIndex < 0) fail("hand-card-" + index + "-keyboard-inaccessible");
    });
    if (scenario === "battle") {
      if (document.querySelectorAll("#hand > .play-card").length < 18) fail("large-hand-fixture-incomplete");
      if (!document.querySelector("#player-piles .command-counter")) fail("command-status-missing");
      const cycle = document.getElementById("cycle-button");
      if (cycle && !cycle.hidden && getComputedStyle(cycle).display !== "none") fail("standard-cycle-control-visible");
    }
    document.querySelectorAll(".board-card strong").forEach((title, index) => {
      if (title.scrollHeight > title.clientHeight + epsilon || title.scrollWidth > title.clientWidth + epsilon) fail("board-title-" + index + "-clipped");
    });
    if (scenario === "ai") {
      essential($("interaction-title"), "ai-turn-prompt");
      if (!$("interaction-hint").textContent.includes("Thinking")) fail("ai-thinking-state-missing");
    }
    if (scenario === "choose-first" && !document.querySelector("[data-choice-first]")) fail("choose-first-missing");
    if (scenario === "mulligan") essential($("confirm-mulligan"), "mulligan-confirm");
    if (scenario === "complete") {
      essential($("match-result"), "match-result");
      essential($("play-again"), "match-result-restart");
    }
    const guard = window.CardLayoutGuard?.check(document) || [];
    if (guard.length) fail("card-content-overflow:" + guard.map((item) => item.card.dataset.cardId + ":" + item.regions.join(",")).join(";"));
    root.dataset.gameLayout = failures.length ? "fail" : "pass";
    root.dataset.gameViewport = innerWidth + "x" + innerHeight;
    root.dataset.gameLayoutScenario = scenario;
    const output = document.createElement("output");
    output.id = "layout-result";
    output.hidden = true;
    output.textContent = failures.join("|");
    document.body.append(output);
  }
  window.addEventListener("load", run);
})();
</script>
"""


def prepare_fixture(directory: Path) -> None:
    shutil.copytree(ROOT / "web", directory, dirs_exist_ok=True)
    (directory / "data").mkdir(exist_ok=True)
    shutil.copy2(ROOT / "cards/cards.json", directory / "data/cards.json")
    shutil.copy2(ROOT / "decks/reference.json", directory / "data/reference-deck.json")
    (directory / "qa-snapshots.json").write_text(json.dumps(presentation_snapshots()), encoding="utf-8")
    (directory / "qa-engine.mjs").write_text(TRANSPORT, encoding="utf-8")
    play = (directory / "play.js").read_text(encoding="utf-8")
    play = play.replace('from "./browser-engine.mjs"', 'from "./qa-engine.mjs"', 1)
    (directory / "play.js").write_text(play, encoding="utf-8")
    page = (directory / "play.html").read_text(encoding="utf-8")
    (directory / "play.html").write_text(page.replace("</body>", CHECK_SCRIPT + "\n</body>"), encoding="utf-8")


PLAYWRIGHT_CAPTURE = r"""
const config = JSON.parse(process.argv[2]);
const { chromium } = await import(config.module);
const browser = await chromium.launch({ executablePath: config.browser, args: ["--no-sandbox"] });
try {
  const page = await browser.newPage({ viewport: { width: config.width, height: config.height } });
  await page.goto(config.url);
  await page.waitForFunction(() => document.documentElement.dataset.gameLayout, null, { timeout: 10000 });
  // Real pointer/focus checks are important for the exposed ends of a large fan.
  if (new URL(config.url).searchParams.get("scenario") === "battle") {
    const hand = page.locator("#hand > .play-card");
    const count = await hand.count();
    for (const index of [0, count - 1]) {
      const card = hand.nth(index);
      const box = await card.boundingBox();
      const point = { x: index === 0 ? box.x + 12 : box.x + box.width - 12, y: box.y + box.height * .4 };
      const reachable = await card.evaluate((element, point) => element.contains(document.elementFromPoint(point.x, point.y)), point);
      if (!reachable) await page.evaluate((index) => {
        document.documentElement.dataset.gameLayout = "fail";
        document.getElementById("layout-result").textContent += "|hand-card-" + index + "-pointer-inaccessible";
      }, index);
      await page.mouse.move(point.x, point.y);
      await page.waitForTimeout(250);
      await card.focus();
      await page.waitForTimeout(250);
      await card.evaluate((element, index) => {
        const box = element.getBoundingClientRect();
        if (box.left < -2 || box.top < -2 || box.right > innerWidth + 2 || box.bottom > innerHeight + 2) {
          document.documentElement.dataset.gameLayout = "fail";
          document.getElementById("layout-result").textContent += "|hand-card-" + index + "-focus-clipped";
        }
        element.blur();
      }, index);
      await page.mouse.move(0, 0);
      await page.waitForTimeout(250);
    }
  }
  await page.screenshot({ path: config.screenshot });
  process.stdout.write(await page.content());
} finally { await browser.close(); }
"""


def run_viewport(browser: str, url: str, width: int, height: int, screenshot: Path | None = None, playwright_module: Path | None = None) -> str | None:
    if screenshot:
        config = {"module": playwright_module.resolve().as_uri(), "browser": browser,
                  "url": url, "width": width, "height": height, "screenshot": str(screenshot.resolve())}
        result = subprocess.run(["node", "--input-type=module", "-", json.dumps(config)], input=PLAYWRIGHT_CAPTURE,
                                capture_output=True, text=True, timeout=30, check=False)
    else:
        command = [browser, "--headless=new", "--no-sandbox", "--disable-gpu", browser_window_size(browser, width, height),
                   "--force-device-scale-factor=1", "--virtual-time-budget=1500", "--dump-dom"]
        result = subprocess.run([*command, url], capture_output=True, text=True, timeout=30, check=False)
    if result.returncode != 0:
        return "browser-error: " + result.stderr[-1200:]
    if 'data-game-layout="pass"' in result.stdout:
        if f'data-game-viewport="{width}x{height}"' not in result.stdout:
            return "incorrect-browser-viewport"
        return None
    match = re.search(r'<output id="layout-result"[^>]*>([^<]*)</output>', result.stdout)
    return html.unescape(match.group(1)) if match else "fixture-not-ready"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-browser", action="store_true")
    parser.add_argument("--screenshots", type=Path, help="Save each viewport/state screenshot to this artifact directory.")
    parser.add_argument("--playwright-module", type=Path, help="Path to installed playwright/index.mjs; required for exact screenshots and pointer QA.")
    args = parser.parse_args()
    if args.screenshots and (not args.playwright_module or not args.playwright_module.is_file()):
        parser.error("--screenshots requires --playwright-module pointing to playwright/index.mjs")
    browser = browser_path()
    if browser is None:
        if args.require_browser:
            raise SystemExit("Chrome/Chromium is required for game layout validation")
        print("SKIP: Chrome/Chromium is not installed")
        return
    if args.screenshots:
        args.screenshots.mkdir(parents=True, exist_ok=True)
    failures = []
    with tempfile.TemporaryDirectory(prefix="longwar-game-layout-") as temporary:
        directory = Path(temporary)
        prepare_fixture(directory)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = int(sock.getsockname()[1])
        server = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1", "--directory", str(directory)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            url = f"http://127.0.0.1:{port}/play.html"
            for attempt in range(100):
                try:
                    urllib.request.urlopen(url, timeout=1).close()
                    break
                except OSError:
                    time.sleep(.02)
            for width, height in VIEWPORTS:
                for scenario in SCENARIOS:
                    name = f"{width}x{height}-{scenario}"
                    screenshot = args.screenshots / f"{name}.png" if args.screenshots else None
                    error = run_viewport(browser, url + "?scenario=" + scenario, width, height, screenshot, args.playwright_module)
                    if error:
                        failures.append(name + ": " + error)
        finally:
            server.terminate()
            try:
                server.wait(timeout=3)
            except subprocess.TimeoutExpired:
                server.kill()
    if failures:
        raise SystemExit("Game layout failure:\n" + "\n".join(failures))
    print(f"PASS: {len(SCENARIOS)} actual-client states fit " + ", ".join(f"{w}x{h}" for w, h in VIEWPORTS))


if __name__ == "__main__":
    main()
