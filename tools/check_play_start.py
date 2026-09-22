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
  let submitted = false;
  let ticks = 0;
  const timer = setInterval(() => {
    ticks += 1;
    const start = document.getElementById("start-game");
    const form = document.getElementById("new-game-form");
    const game = document.getElementById("game");
    const setup = document.getElementById("play-setup");
    if (!submitted && start && form && !start.disabled) {
      submitted = true;
      root.dataset.playSmoke = "submitted";
      form.requestSubmit();
    }
    if (
      submitted &&
      game &&
      setup &&
      !game.hidden &&
      setup.hidden &&
      document.querySelectorAll("#hand .play-card").length > 0
    ) {
      root.dataset.playSmoke = "pass";
      clearInterval(timer);
      return;
    }
    if (ticks > 100) {
      root.dataset.playSmoke = "fail";
      root.dataset.playSmokeDetail =
        document.getElementById("setup-note")?.textContent ||
        document.getElementById("engine-status")?.textContent ||
        "unknown";
      clearInterval(timer);
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
                    "--virtual-time-budget=5000",
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

    print("PASS: Begin Battle I opens a rendered mulligan in the real browser page")


if __name__ == "__main__":
    main()
