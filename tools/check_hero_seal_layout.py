"""Browser regression focused on the 11 printed Hero cost seals.

Avoids unrelated legacy full-catalogue layout warnings; checks the actual
printed JS and CSS in headless Chromium, including PNG icon dimensions.
"""
from __future__ import annotations

import html
import json
import re
import sys
import tempfile
from pathlib import Path

from check_card_layout import ROOT, browser_path, run_browser
from print_cards import load_print_cards


def main() -> None:
    browser = browser_path()
    if not browser:
        print("SKIP: no Chromium/Chrome executable for Hero seal geometry")
        return

    heroes = [c for c in load_print_cards()["cards"] if c["type"] == "hero"]
    assert len(heroes) == 11
    data = json.dumps(heroes).replace("<", "\\u003c")
    css = (ROOT / "web" / "physical-cards.css").read_text(encoding="utf-8")
    scripts = "\n".join(
        "<script>" + (ROOT / "web" / name).read_text(encoding="utf-8") + "</script>"
        for name in ("card-symbols.js", "physical-cards.js")
    )
    page = f"""<!doctype html><html><head><meta charset="utf-8">
<base href="{(ROOT / 'web').as_uri()}/">
<meta name="lw-build-version" content="hero-price-check">
<style>{css}</style></head><body>
<main id="physical-layout" class="cards"></main>
<div id="hero-layout-result"></div><script id="card-data" type="application/json">{data}</script>
{scripts}<script>
const cards=JSON.parse(document.getElementById("card-data").textContent);
const area=document.getElementById("physical-layout");
area.innerHTML=cards.map(c=>'<div class="card-wrap">'+window.PhysicalCards.cardArticle(c)+'</div>').join("");
window.addEventListener("load",async()=>{{
  await document.fonts.ready;
  const fails=[],rect=el=>el.getBoundingClientRect();
  const inside=(outer,inner,pad=1)=>
    inner.left>=outer.left+pad && inner.right<=outer.right-pad &&
    inner.top>=outer.top+pad && inner.bottom<=outer.bottom-pad;
  for(const card of area.querySelectorAll(".card-hero")){{
    const id=card.dataset.cardId;
    const seal=card.querySelector(".cost-gem-hero");
    const parts=[...card.querySelectorAll(".hero-cost-part")];
    if(!seal||parts.length!==2){{fails.push(id+":missing-seal-parts");continue;}}
    const bound=rect(seal);
    for(const part of parts){{
      if(!inside(bound,rect(part)))fails.push(id+":price-outside-seal");
      const number=part.querySelector("b");
      if(!number){{fails.push(id+":missing-number");continue;}}
      if(part.querySelector("img,svg,.hero-cost-symbol"))
        fails.push(id+":redundant-cost-icon");
      const range=document.createRange();range.selectNodeContents(number);
      const ink=rect(range);
      if(!inside(bound,ink))
        fails.push(id+":number-outside-seal"+JSON.stringify({{
          top:Math.round(ink.top-bound.top),
          bottom:Math.round(bound.bottom-ink.bottom),
          left:Math.round(ink.left-bound.left),
          right:Math.round(bound.right-ink.right)
        }}));
      if(Math.abs((ink.left+ink.right)/2-(bound.left+bound.right)/2)>1)
        fails.push(id+":number-off-centre");
      if(parseFloat(getComputedStyle(number).fontSize)<4*96/25.4)
        fails.push(id+":number-too-small");
    }}
    const a=rect(parts[0].querySelector("b")),b=rect(parts[1].querySelector("b"));
    if(a.bottom>b.top-1)fails.push(id+":numbers-overlap-or-out-of-order");
    if(card.querySelector(".hero-rule-mode .effect-timing-icon,.hero-rule-mode .mode-heading img,.hero-rule-mode .mode-heading svg"))
      fails.push(id+":redundant-heading-icon");
    for(const effect of card.querySelectorAll(".hero-rule-mode .effect-block")){{
      if(effect.querySelectorAll(".inline-card-ref").length>2)
        fails.push(id+":excess-inline-referents");
    }}
  }}
  document.getElementById("hero-layout-result").textContent=fails.length?fails.join(";"):"PASS";
}});
</script></body></html>"""

    with tempfile.TemporaryDirectory(prefix="longwar-hero-price-layout-") as directory:
        path = Path(directory) / "hero-seals.html"
        path.write_text(page, encoding="utf-8")
        result = run_browser(browser, path)
    if result.returncode:
        raise SystemExit(f"Headless browser error:\n{result.stderr[-2000:]}")
    match = re.search(r'<div id="hero-layout-result">([^<]*)</div>', result.stdout)
    status = html.unescape(match.group(1)) if match else "browser check did not complete"
    if status != "PASS":
        raise SystemExit("FAIL: " + status[:3000])
    print("PASS: 11 Hero seals contain large centred Force(top)/Name(bottom) costs with no role icons")


if __name__ == "__main__":
    main()
