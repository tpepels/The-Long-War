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
      const symbol=part.querySelector(".hero-cost-symbol img,.hero-cost-symbol svg");
      const number=part.querySelector("b");
      if(!symbol||!number){{fails.push(id+":missing-icon-or-number");continue;}}
      if(!inside(bound,rect(symbol)))fails.push(id+":icon-outside-seal");
      const range=document.createRange();range.selectNodeContents(number);
      if(!inside(bound,rect(range)))fails.push(id+":number-outside-seal");
    }}
    const a=rect(parts[0]),b=rect(parts[1]);
    if(Math.min(a.right,b.right)>Math.max(a.left,b.left)+1 &&
       Math.min(a.bottom,b.bottom)>Math.max(a.top,b.top)+1)
       fails.push(id+":prices-overlap");
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
    print("PASS: 11 actual Hero seals keep both icon/price pairs inside; no role or timing icons in rules")


if __name__ == "__main__":
    main()
