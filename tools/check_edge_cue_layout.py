"""Verify compact right-edge CHECK cues fit the 10.5 mm exposed strip in Chromium.

Uses the actual printed JSON, shared CSS, PNG glyph renderer and web fonts.
Unlike general legacy layout diagnostics, only checks the edited edge region.
"""
from __future__ import annotations

import html
import json
import re
import tempfile
from pathlib import Path

from check_card_layout import ROOT, browser_path, run_browser
from print_cards import load_print_cards


def main() -> None:
    browser = browser_path()
    if not browser:
        print("SKIP: no Chromium/Chrome executable for exposed-edge cue geometry")
        return

    cards = [
        card for card in load_print_cards()["cards"]
        if (
            any("edge_cue" in e for e in (
                card["modes"]["force"]["effects"] if card["type"] == "hero"
                else card.get("effects", [])
            ))
        )
    ]
    assert len(cards) == 34
    data = json.dumps(cards).replace("<", "\\u003c")
    css = (ROOT / "web" / "physical-cards.css").read_text(encoding="utf-8")
    scripts = "\n".join(
        "<script>" + (ROOT / "web" / name).read_text(encoding="utf-8") + "</script>"
        for name in ("card-symbols.js", "physical-cards.js")
    )
    page = f"""<!doctype html><html><head><meta charset="utf-8">
<base href="{(ROOT / 'web').as_uri()}/">
<meta name="lw-build-version" content="edge-cue-check">
<style>{css}</style></head><body>
<main id="physical-layout" class="cards"></main>
<div id="cue-layout-result"></div><script id="card-data" type="application/json">{data}</script>
{scripts}<script>
const cards=JSON.parse(document.getElementById("card-data").textContent);
const area=document.getElementById("physical-layout");
area.innerHTML=cards.map(c=>'<div class="card-wrap">'+window.PhysicalCards.cardArticle(c)+'</div>').join("");
window.addEventListener("load",async()=>{{
  await document.fonts.ready;
  const errors=[],mm=96/25.4,rect=el=>el.getBoundingClientRect();
  for(const card of area.querySelectorAll(".physical-card")){{
    const id=card.dataset.cardId,zone=card.querySelector(".edge-zone-right");
    const cues=[...zone.querySelectorAll(".edge-cue")];
    if(!cues.length){{errors.push(id+":no-cues");continue;}}
    const box=rect(zone);
    if(zone.scrollWidth>zone.clientWidth+1||zone.scrollHeight>zone.clientHeight+1)
      errors.push(id+":right-zone-overflow");
    for(const cue of cues){{
      const cueRect=rect(cue),label=cue.querySelector(".edge-cue-text");
      if(!label||!/^[A-Z/ ]{{1,16}}$/.test(label.textContent))
        errors.push(id+":invalid-cue-text");
      if(label&&label.textContent.includes("CHECK"))
        errors.push(id+":redundant-check-prefix");
      if(cueRect.left<box.left-1||cueRect.right>box.right+1||
         cueRect.top<box.top-1||cueRect.bottom>box.bottom+1)
        errors.push(id+":cue-outside-right-zone");
      const text=rect(label);
      if(text.right>box.right+1||text.bottom>box.bottom+1)
        errors.push(id+":text-clipped");
      if(text.height>12)errors.push(id+":multiline-cue");
      if(/[+\\d]/.test(label.textContent))errors.push(id+":contains-effect-numbers");
    }}
    if(rect(zone).bottom > rect(card).top + 10.5*mm+1)
      errors.push(id+":outside-exposed-strip");
  }}
  document.getElementById("cue-layout-result").textContent=errors.length?errors.join(";"):"PASS";
}});
</script></body></html>"""
    with tempfile.TemporaryDirectory(prefix="longwar-edge-cues-") as directory:
        path = Path(directory) / "edge-cues.html"
        path.write_text(page, encoding="utf-8")
        result = run_browser(browser, path)
    if result.returncode:
        raise SystemExit("Chromium error: " + result.stderr[-2000:])
    match = re.search(r'<div id="cue-layout-result">([^<]*)</div>', result.stdout)
    status = html.unescape(match.group(1)) if match else "browser check did not finish"
    if status != "PASS":
        raise SystemExit("FAIL: " + status[:4000])
    print("PASS: 34 printed card right-edge cues fit the exposed strip without wrapping")


if __name__ == "__main__":
    main()
