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
    args = parser.parse_args()

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
  let targetClicked = false;

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
    if (ticks > 220) {
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
      document.getElementById("mode").value = "heuristic";
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
      confirm.click();
      stage = "select";
      return;
    }

    if (stage === "select") {
      const card = document.querySelector("#hand .play-card.playable[data-hand-card]");
      if (!card) return;
      beforeHistory = historyCount();
      card.click();
      stage = "target";
      return;
    }

    if (stage === "target") {
      if (historyCount() > beforeHistory) {
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
        ".digital-slot.targetable, .scheme-marker.targetable"
      );
      if (!target) return;
      target.click();
      targetClicked = true;
      return;
    }

    if (stage === "verify") {
      if (historyCount() > beforeHistory) {
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
      root.dataset.playSmoke = "pass";
      root.dataset.playSmokeDetail = "card action and public-card inspection completed";
      clearInterval(timer);
      return;
    }

    if (targetClicked && historyCount() > beforeHistory) {
      stage = "inspect";
      return;
    }
  }, 40);
})();
</script>
"""
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
                    "--window-size=1440,900",
                    "--virtual-time-budget=9000",
                    "--dump-dom",
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=20,
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

    print("PASS: real browser starts the match, completes a board action, and opens a public battlefield card at readable size")


if __name__ == "__main__":
    main()
