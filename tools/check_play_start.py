from __future__ import annotations

import argparse
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

if __package__:
    from .check_game_layout import browser_window_size
else:
    from check_game_layout import browser_window_size

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


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


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-browser", action="store_true")
    parser.add_argument("--viewport", default="1440x900", help="Desktop width x height.")
    parser.add_argument("--reduced-motion", action="store_true")
    args = parser.parse_args()
    try:
        width, height = (int(value) for value in args.viewport.split("x"))
    except ValueError:
        parser.error("--viewport must be WIDTHxHEIGHT")

    browser = browser_path()
    if browser is None:
        if args.require_browser:
            raise SystemExit("Chrome/Chromium is required for play-start validation")
        print("SKIP: Chrome/Chromium is not installed")
        return

    if not (DIST / "play.html").exists():
        subprocess.run(
            [sys.executable, str(ROOT / "tools" / "build_pages.py")],
            cwd=ROOT,
            check=True,
        )

    source = (DIST / "play.html").read_text(encoding="utf-8")
    smoke = r"""
<script>
(() => {
  const root = document.documentElement;
  root.dataset.playSmoke = "waiting";
  let stage = "start";
  let ticks = 0;
  let beforeHistory = 0;
  let humanHistory = 0;
  let targetClicked = false;
  let beforeHand = 0;
  let beforeCommand = 0;
  let cycleCost = 0;
  const expectedReducedMotion = REDUCED_MOTION_EXPECTED;

  function fail(detail) {
    root.dataset.playSmoke = "fail";
    root.dataset.playSmokeDetail = String(detail || "unknown");
    clearInterval(timer);
  }

  function historyCount() {
    return document.querySelectorAll("#history li").length;
  }

  const timer = setInterval(() => {
    ticks += 1;
    if (ticks > 280) {
      fail(
        stage + ": " +
        (document.getElementById("interaction-hint")?.textContent ||
         document.getElementById("setup-note")?.textContent ||
         document.getElementById("engine-status")?.textContent ||
         "timeout")
      );
      return;
    }

    if (document.body.classList.contains("is-busy")) return;

    if (stage === "start") {
      const start = document.getElementById("start-game");
      const form = document.getElementById("new-game-form");
      if (!start || !form || start.disabled) return;
      document.getElementById("mode").value = "computer";
      document.getElementById("seed").value = "1701";
      root.dataset.playSmoke = "submitted";
      form.requestSubmit();
      stage = "mulligan";
      return;
    }

    if (stage === "mulligan") {
      const setup = document.getElementById("play-setup");
      const game = document.getElementById("game");
      const confirm = document.getElementById("confirm-mulligan");
      if (!confirm) return;
      if (!setup?.hidden || getComputedStyle(setup).display !== "none") {
        fail("start overlay remains visible after match start");
        return;
      }
      if (game?.hidden || getComputedStyle(game).display === "none") {
        fail("game scene is still hidden after match start");
        return;
      }
      if (document.querySelectorAll("#hand .play-card").length !== 10) {
        fail("mulligan did not render ten cards");
        return;
      }
      const openingCard = document.querySelector("#hand [data-mulligan-index]");
      openingCard.focus();
      openingCard.dispatchEvent(new KeyboardEvent("keydown", { key: "i", bubbles: true }));
      const openingInspector = document.getElementById("card-inspector");
      if (!openingInspector || openingInspector.hidden) {
        fail("opening card keyboard inspection did not open");
        return;
      }
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
      confirm.click();
      stage = "menu";
      return;
    }

    if (stage === "menu") {
      if (JSON.parse(window.render_game_to_text()).needs_ai) return;
      document.querySelector('[data-open-drawer="menu"]')?.click();
      const drawer = document.getElementById("game-drawer");
      if (!drawer || drawer.hidden || getComputedStyle(drawer).display === "none") {
        fail("game menu did not open");
        return;
      }
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
      if (!drawer.hidden && getComputedStyle(drawer).display !== "none") {
        fail("Escape did not close game menu");
        return;
      }
      if (expectedReducedMotion && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
        fail("reduced-motion preference was not applied");
        return;
      }
      stage = "cancel";
      return;
    }

    if (stage === "cancel") {
      const card = document.querySelector("#hand .play-card.playable.card-subject[data-hand-card]");
      if (!card) return;
      card.click();
      if (!document.querySelector(".digital-slot.targetable")) {
        fail("card selection did not activate legal targets");
        return;
      }
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
      if (document.querySelector(".digital-slot.targetable")) {
        fail("Escape did not cancel legal targeting");
        return;
      }
      stage = "select";
      return;
    }

    if (stage === "select") {
      const card =
        document.querySelector("#hand .play-card.playable.card-subject[data-hand-card]") ||
        document.querySelector("#hand .play-card.playable[data-hand-card]");
      if (!card) return;
      beforeHistory = historyCount();
      card.click();
      stage = "target";
      return;
    }

    if (stage === "target") {
      if (historyCount() > beforeHistory) {
        const banner = document.getElementById("action-banner");
        if (!banner || banner.hidden || !banner.classList.contains("show")) {
          fail("human action did not produce a visible action banner");
          return;
        }
        humanHistory = historyCount();
        stage = "inspect";
        return;
      }

      const choice = document.querySelector("#choice-tray:not([hidden]) button");
      if (choice) {
        choice.click();
        stage = "verify";
        return;
      }

      const target = document.querySelector(
        ".digital-slot.targetable, .story-marker.targetable"
      );
      if (!target) return;
      target.click();
      targetClicked = true;
      return;
    }

    if (stage === "verify") {
      if (historyCount() > beforeHistory) {
        const banner = document.getElementById("action-banner");
        if (!banner || banner.hidden || !banner.classList.contains("show")) {
          fail("human action did not produce a visible action banner");
          return;
        }
        humanHistory = historyCount();
        stage = "inspect";
        return;
      }
      const choice = document.querySelector("#choice-tray:not([hidden]) button");
      if (choice) choice.click();
      return;
    }

    if (stage === "inspect") {
      const publicCard =
        document.querySelector(".opponent-army [data-inspect-card]") ||
        document.querySelector("#battlefield [data-inspect-card]");
      if (!publicCard) return;
      publicCard.click();
      const inspector = document.getElementById("card-inspector");
      if (!inspector || inspector.hidden || getComputedStyle(inspector).display === "none") {
        fail("public battlefield card did not open inspector");
        return;
      }
      if (!document.querySelector("#card-inspector-card .play-card")) {
        fail("inspector did not render the full card");
        return;
      }
      document.getElementById("card-inspector-close")?.click();
      stage = "wait-ai";
      return;
    }

    if (stage === "wait-ai") {
      if (historyCount() <= humanHistory) return;
      const banner = document.getElementById("action-banner");
      const kicker = document.getElementById("action-banner-kicker")?.textContent || "";
      if (!banner || banner.hidden || !banner.classList.contains("show")) {
        fail("opponent action was not shown before returning control");
        return;
      }
      if (!kicker.includes("OPPONENT")) {
        fail("delayed action banner did not identify the opponent");
        return;
      }
      stage = "verify-standard";
      return;
    }

    if (stage === "verify-standard") {
      const snapshot = JSON.parse(window.render_game_to_text());
      if (snapshot.needs_ai) return;
      if (snapshot.legal_actions.some((action) => action.kind === "Draw" || action.kind === "Cycle")) {
        fail("standard game exposed Draw or Cycle as an operation");
        return;
      }
      const cycle = document.getElementById("cycle-button");
      if (cycle && !cycle.hidden && getComputedStyle(cycle).display !== "none") {
        fail("Cycle control was visible in the standard game");
        return;
      }
      if (document.documentElement.scrollWidth > innerWidth + 2 || document.documentElement.scrollHeight > innerHeight + 2) {
        fail("normal gameplay produced page scrollbars");
        return;
      }
      root.dataset.playSmoke = "pass";
      root.dataset.playSmokeDetail = "menu, keyboard cancellation, human action, full inspection, paced AI, and standard Force controls passed";
      clearInterval(timer);
      return;
    }

    if (targetClicked && historyCount() > beforeHistory) {
      const banner = document.getElementById("action-banner");
      if (!banner || banner.hidden || !banner.classList.contains("show")) {
        fail("human action did not produce a visible action banner");
        return;
      }
      humanHistory = historyCount();
      stage = "inspect";
      return;
    }
  }, 40);
})();
</script>
"""
    smoke = smoke.replace("REDUCED_MOTION_EXPECTED", "true" if args.reduced_motion else "false")
    page = source.replace("</body>", smoke + "\n</body>")

    with tempfile.TemporaryDirectory(prefix="longwar-play-smoke-") as tmp:
        smoke_path = DIST / "play-smoke.html"
        smoke_path.write_text(page, encoding="utf-8")
        port = free_port()
        server = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "http.server",
                str(port),
                "--bind",
                "127.0.0.1",
                "--directory",
                str(DIST),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            deadline = time.time() + 5
            url = f"http://127.0.0.1:{port}/play-smoke.html"
            while True:
                try:
                    urllib.request.urlopen(url, timeout=1).close()
                    break
                except Exception:
                    if time.time() >= deadline:
                        raise SystemExit("Local play-test server did not start")
                    time.sleep(0.05)

            result = subprocess.run(
                [
                    browser,
                    "--headless=new",
                    "--no-sandbox",
                    "--disable-gpu",
                    browser_window_size(browser, width, height),
                    "--force-device-scale-factor=1",
                    *(["--force-prefers-reduced-motion"] if args.reduced_motion else []),
                    "--virtual-time-budget=12000",
                    "--dump-dom",
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=35,
                check=False,
            )
        finally:
            server.terminate()
            try:
                server.wait(timeout=3)
            except subprocess.TimeoutExpired:
                server.kill()
            smoke_path.unlink(missing_ok=True)

    if result.returncode != 0:
        raise SystemExit("Headless browser failed during play-start validation:\n" + result.stderr[-3000:])
    if 'data-play-smoke="pass"' not in result.stdout:
        marker = 'data-play-smoke-detail="'
        detail = "unknown"
        if marker in result.stdout:
            detail = result.stdout.split(marker, 1)[1].split('"', 1)[0]
        raise SystemExit(f"Start-a-match browser smoke failed: {detail}")

    print(f"PASS: {width}x{height} real browser menu, keyboard targeting/cancellation, action, inspector, paced AI and standard Force controls" + (" with reduced motion" if args.reduced_motion else ""))


if __name__ == "__main__":
    main()
