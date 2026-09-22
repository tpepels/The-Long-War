from __future__ import annotations

import argparse
import html
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEWPORTS = [(1920, 1080), (1440, 900), (1366, 768), (1024, 768)]


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


def board_card(title: str = "The Red Shields") -> str:
    return (
        '<div class="board-legend">'
        '<div class="board-card board-card-subject card-subject">'
        '<div class="board-card-face">'
        '<span class="board-card-type">Subject</span>'
        f'<strong>{title}</strong>'
        '<div class="play-card-art compact"><span class="play-card-symbol">◆</span><b>RS</b></div>'
        '<span class="board-card-strength">5</span>'
        '</div></div><span class="slot-strength">5</span></div>'
    )


def slot(front: int, rank: str) -> str:
    return (
        f'<div class="digital-slot occupied" data-board-front="{front}" data-board-rank="{rank}">'
        f'<span class="slot-rank">{rank}</span>{board_card()}</div>'
    )


def rank_row(rank: str, label: str) -> str:
    return (
        f'<div class="rank-row rank-{rank}"><span class="rank-label">{label}</span>'
        + "".join(slot(front, rank) for front in range(3))
        + "</div>"
    )


def scheme_row() -> str:
    marker = '<div class="scheme-marker hidden"><span>Veiled</span><b>face-down</b></div>'
    return '<div class="scheme-row"><span class="rank-label">Veiled</span>' + marker * 3 + "</div>"


def full_card(index: int) -> str:
    titles = [
        "The Children of the Salt Road",
        "Sera, Mother of White Hands",
        "Mara, Queen of Cinders",
        "Avaros, the Bronze King",
    ]
    title = titles[index % len(titles)]
    return (
        f'<article class="play-card card-subject" style="--fan-rot:0deg;--fan-y:0px" data-card-id="fixture-{index}">'
        '<div class="play-card-meta"><span>Subject</span></div>'
        f'<h3>{title}</h3>'
        '<div class="play-card-properties"><em>Swordsman</em> · <em>Human</em></div>'
        '<span class="play-card-strength">5</span>'
        '<div class="play-card-art"><span class="play-card-symbol">◆</span><b>LW</b></div>'
        '<div class="play-card-rules">'
        '<div class="rule-block rule-property"><em>Frontline only.</em></div>'
        '<div class="rule-block rule-trigger"><strong>When you play a Bond here:</strong> gain +1 Strength.</div>'
        '<div class="rule-block rule-continuous"><strong>While this is here:</strong> adjacent Subjects get +1 Strength.</div>'
        '</div>'
        '<footer>SELECT OR DRAG TO PLAY</footer>'
        '</article>'
    )


def fixture(style: str, play_style: str) -> str:
    fronts = "".join(
        f'<div class="front-banner"><span>{name}</span><b><i>5</i><em>—</em><i>5</i></b><small>Tied</small></div>'
        for name in ("Left", "Center", "Right")
    )
    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>{style}</style>
<style>{play_style}</style>
</head>
<body class="game-body">
<div class="game-chrome">
  <header class="game-masthead">
    <a class="game-mark"><span>THE</span><strong>LONG WAR</strong></a>
    <span class="engine-lamp">Game ready</span>
    <nav><a>Rules</a><button>New match</button></nav>
  </header>
  <main class="play-client">
    <section class="play-game">
      <section class="tabletop-shell">
        <div class="campaign-hud"><div class="match-strip">
          <div class="score-player active"><span>P2</span><span class="victory-pips"><i></i><i></i></span></div>
          <div class="battle-medallion"><small>Battle</small><strong>II</strong></div>
          <div class="turn-marker">Turn · Player 1</div>
          <div class="score-player"><span>P1</span><span class="victory-pips"><i class="won"></i><i></i></span></div>
        </div></div>
        <section class="opponent-rack">
          <div class="rack-player"><span>OPPONENT</span><strong>Player 2</strong></div>
          <div class="opponent-hand">{'<span class="card-back"></span>' * 9}</div>
          <div class="rack-piles"><div class="rack-pile"><span>Deck</span><b>17</b></div><div class="rack-pile"><span>Discard</span><b>Remembered</b></div></div>
        </section>
        <section class="war-table">
          <div class="table-surface-mark">LEFT · CENTER · RIGHT</div>
          <div class="orders-ribbon"><div><small>YOUR TURN</small><strong>Choose a card</strong><span>Select a card. Legal positions will highlight.</span></div></div>
          <div class="choice-tray" hidden></div>
          <div class="digital-battlefield">
            <div class="battlefield-table">
              <div class="battle-stratagem-zone opponent"><span>Opponent Stratagem</span><div class="stratagem-marker hidden"><span>Stratagem</span><b>face-down</b></div></div>
              <div class="front-banner-row"><span></span>{fronts}</div>
              <div class="army-side opponent-army">{scheme_row()}{rank_row("rear", "Rear")}{rank_row("front", "Frontline")}</div>
              <div class="battle-line-wide"><span>THE BATTLE LINE</span></div>
              <div class="army-side player-army">{rank_row("front", "Frontline")}{rank_row("rear", "Rear")}{scheme_row()}</div>
              <div class="battle-stratagem-zone player"><span>Your Stratagem</span><div class="stratagem-marker"><span>The Storm Broke</span><b>revealed</b></div></div>
            </div>
          </div>
        </section>
        <section class="hand-dock">
          <header>
            <div class="hand-heading"><span>YOUR HAND</span><h2>Player 1 hand · 12 cards</h2></div>
            <div class="rack-piles player-piles"><div class="rack-pile"><span>Deck</span><b>16</b></div></div>
            <div class="hand-controls"><button class="pass-button">Pass</button></div>
          </header>
          <div class="digital-hand">{''.join(full_card(i) for i in range(12))}</div>
          <div class="turn-actions"></div>
        </section>
      </section>
      <aside class="game-tools"><details><summary>Piles</summary></details><details><summary>Log</summary></details></aside>
    </section>
  </main>
</div>
<div id="layout-result"></div>
<script>
window.addEventListener("load", () => {{
  const failures = [];
  const epsilon = 2;
  const root = document.documentElement;
  const body = document.body;

  function fail(name) {{ if (!failures.includes(name)) failures.push(name); }}
  function pageOverflow(element, name) {{
    if (element.scrollWidth > window.innerWidth + epsilon) fail(name + "-horizontal");
    if (element.scrollHeight > window.innerHeight + epsilon) fail(name + "-vertical");
  }}
  function contained(outer, inner, name) {{
    const a = outer.getBoundingClientRect();
    const b = inner.getBoundingClientRect();
    if (b.left < a.left - epsilon || b.right > a.right + epsilon ||
        b.top < a.top - epsilon || b.bottom > a.bottom + epsilon) fail(name);
  }}

  pageOverflow(root, "root-scroll");
  pageOverflow(body, "body-scroll");
  if (getComputedStyle(body).overflowX !== "hidden" || getComputedStyle(body).overflowY !== "hidden") fail("body-overflow-style");

  const shell = document.querySelector(".tabletop-shell");
  const viewport = {{left: 0, top: 0, right: window.innerWidth, bottom: window.innerHeight}};
  const shellRect = shell.getBoundingClientRect();
  if (shellRect.left < -epsilon || shellRect.right > viewport.right + epsilon ||
      shellRect.top < -epsilon || shellRect.bottom > viewport.bottom + epsilon) fail("shell-outside-viewport");

  contained(shell, document.querySelector(".war-table"), "table-outside-scene");
  contained(shell, document.querySelector(".hand-dock"), "hand-dock-outside-scene");

  const hand = document.querySelector(".digital-hand");
  document.querySelectorAll(".digital-hand > .play-card").forEach((card, index) => {{
    contained(hand, card, "hand-card-" + index + "-clipped");
  }});

  const board = document.querySelector(".digital-battlefield");
  const boardRect = board.getBoundingClientRect();
  if (boardRect.width < 1 || boardRect.height < 1) fail("battlefield-collapsed");
  if (boardRect.height < shellRect.height * 0.45) fail("battlefield-too-small");

  document.querySelectorAll(".board-card").forEach((card, index) => {{
    const rect = card.getBoundingClientRect();
    if (rect.width < 50 || rect.height < 68) fail("board-card-" + index + "-too-small");
  }});

  document.documentElement.dataset.gameLayout = failures.length ? "fail" : "pass";
  document.getElementById("layout-result").textContent = failures.join(",");
}});
</script>
</body>
</html>"""


def run_viewport(browser: str, document: str, width: int, height: int) -> str | None:
    with tempfile.TemporaryDirectory(prefix="longwar-game-layout-") as temp_dir:
        path = Path(temp_dir) / "game-layout.html"
        path.write_text(document, encoding="utf-8")
        command = [
            browser,
            "--headless=new",
            "--no-sandbox",
            "--disable-gpu",
            f"--window-size={width},{height}",
            "--force-device-scale-factor=1",
            "--virtual-time-budget=1000",
            "--dump-dom",
            path.as_uri(),
        ]
        result = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
        if result.returncode != 0:
            command[1] = "--headless"
            result = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)

    if result.returncode != 0:
        return "browser-error: " + result.stderr[-1200:]
    if 'data-game-layout="pass"' in result.stdout:
        return None
    match = re.search(r'<div id="layout-result">([^<]*)</div>', result.stdout)
    return html.unescape(match.group(1)) if match else "unknown-layout-failure"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-browser", action="store_true")
    args = parser.parse_args()

    browser = browser_path()
    if browser is None:
        if args.require_browser:
            raise SystemExit("Chrome/Chromium is required for game layout validation")
        print("SKIP: Chrome/Chromium is not installed")
        return

    style = (ROOT / "web" / "style.css").read_text(encoding="utf-8")
    play_style = (ROOT / "web" / "play.css").read_text(encoding="utf-8")
    document = fixture(style, play_style)

    failed = []
    for width, height in VIEWPORTS:
        error = run_viewport(browser, document, width, height)
        if error:
            failed.append(f"{width}x{height}: {error}")

    if failed:
        raise SystemExit("Game layout failure:\n" + "\n".join(failed))

    print("PASS: game scene fits " + ", ".join(f"{w}x{h}" for w, h in VIEWPORTS))


if __name__ == "__main__":
    main()
