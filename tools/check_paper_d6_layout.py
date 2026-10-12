"""Check that all 44 experimental D6 cards actually fit the physical renderer.

Run: python tools/check_paper_d6_layout.py
"""
from __future__ import annotations

import html
import json
import re
import tempfile
from pathlib import Path

from check_card_layout import ROOT, browser_path, run_browser
from paper_d6_cards import load_paper_d6_cards


def main() -> None:
    browser = browser_path()
    if not browser:
        print("SKIP: no Chromium/Chrome for D6 paper card geometry")
        return

    cards = load_paper_d6_cards()["cards"]
    data = json.dumps(cards).replace("<", "\\u003c")
    css = (ROOT / "web" / "physical-cards.css").read_text(encoding="utf-8")
    scripts = "\n".join(
        "<script>" + (ROOT / "web" / name).read_text(encoding="utf-8") + "</script>"
        for name in ("card-symbols.js", "physical-cards.js")
    )
    page = f"""<!doctype html><html><head><meta charset="utf-8">
<base href="{(ROOT / 'web').as_uri()}/">
<meta name="lw-build-version" content="d6-layout-test">
<style>{css}</style></head><body>
<main id="physical-layout" class="cards"></main>
<div id="d6-layout-result"></div><script id="card-data" type="application/json">{data}</script>
{scripts}<script>
const cards=JSON.parse(document.getElementById("card-data").textContent);
document.getElementById("physical-layout").innerHTML=cards.map(c=>
  '<div class="card-wrap">'+window.PhysicalCards.cardArticle(c)+'</div>').join("");
window.addEventListener("load",async()=>{{
  await document.fonts.ready;
  const failures=window.PhysicalCards.inspect(document);
  const issues=failures.map(c=>c.id+":"+c.problems.join(","));
  for(const card of document.querySelectorAll(".paper-d6-layout")){{
    const id=card.dataset.cardId;
    const rules=card.querySelector(".rules");
    const faces=[...card.querySelectorAll(".d6-number")];
    const rows=[...card.querySelectorAll(".d6-stanza")];
    const artwork=card.querySelector(".motif-field");
    if(!artwork||artwork.getBoundingClientRect().height<25*(96/25.4))
      issues.push(id+":artwork-shrunk-for-rules");
    for(const effect of card.querySelectorAll(".d6-verse")){{
      const size=parseFloat(getComputedStyle(effect).fontSize);
      if(size<11.35)issues.push(id+":text-too-small-"+size.toFixed(2));
      if(effect.getBoundingClientRect().width<39*(96/25.4))
        issues.push(id+":text-column-too-narrow");
    }}
    if(faces.length!==6||rows.length!==4)issues.push(id+":missing-editorial-stanzas");
    if(card.querySelector(".d6-guide,.d6-outcomes,.d6-result-row,.d6-number[data-chip]"))
      issues.push(id+":legacy-table-layout");
    const printed=faces.map(face=>Number(face.textContent));
    if(printed.join(",")!=="1,2,3,4,5,6" &&
       [...printed].sort((a,b)=>a-b).join(",")!=="1,2,3,4,5,6")
      issues.push(id+":die-values-missing-or-repeated");
    if(card.querySelectorAll(".d6-face-row,.d6-outcome,.d6-face").length)
      issues.push(id+":legacy-two-step-die-lookup");
    for(const row of rows){{
      const key=row.dataset.outcomeKey;
      const represented=faces.filter(face=>face.closest(".d6-stanza")===row)
        .map(face=>Number(face.textContent));
      const expected=[...cards.find(c=>c.id===id).paper_d6.faces]
        .flatMap((letter,index)=>letter===key?[index+1]:[]);
      if(represented.join(",")!==expected.join(","))
        issues.push(id+":incorrect-roll-mapping-"+key);
      const effect=row.querySelector(".d6-verse");
      const heading=row.querySelector(".d6-stanza-heading");
      const rect=row.getBoundingClientRect();
      for(const [name,part] of [["row",row],["effect",effect]]){{
        if(part&&(part.scrollHeight>part.clientHeight+2||part.scrollWidth>part.clientWidth+2))
          issues.push(id+":clipped-"+name+"-"+key+"-"+(part.scrollHeight-part.clientHeight));
      }}
      // SVG/large serif numerals can legitimately extend beyond their inline
      // line boxes. Measure the prose's actual bounds rather than treating
      // intrinsic scrollHeight on these un-clipped spans as content clipping.
      if(heading&&heading.getBoundingClientRect().top<rect.top-1)
        issues.push(id+":heading-overlaps-previous-"+key);
      if(effect&&effect.getBoundingClientRect().bottom>rect.bottom+1)
        issues.push(id+":effect-overlaps-next-"+key);
    }}
    if(rules.scrollHeight>rules.clientHeight+2)issues.push(id+":outcomes-clipped");
    for(const row of rows){{
      const design=getComputedStyle(row);
      if(design.display==="grid"||parseFloat(design.borderTopWidth)>0.5)
        issues.push(id+":still-looks-like-a-table");
    }}
    const footer=card.querySelector(".card-footer");
    if(rules.getBoundingClientRect().bottom>footer.getBoundingClientRect().top+1)
      issues.push(id+":rules-overlap-footer");
  }}
  document.getElementById("d6-layout-result").textContent=issues.length?issues.join(";"):"PASS";
}});
</script></body></html>"""
    with tempfile.TemporaryDirectory(prefix="longwar-paper-d6-") as directory:
        path = Path(directory) / "d6-cards.html"
        path.write_text(page, encoding="utf-8")
        result = run_browser(browser, path)
    if result.returncode:
        raise SystemExit("Headless D6 browser error: " + result.stderr[-1600:])
    match = re.search(r'<div id="d6-layout-result">([^<]*)</div>', result.stdout)
    status = html.unescape(match.group(1)) if match else "D6 layout test did not finish"
    if status != "PASS":
        raise SystemExit("FAIL D6 paper layout: " + status[:4000])
    print("PASS: 44 D6 cards: editorial stanzas, full art window, accessible text, six correct faces, no clipping")


if __name__ == "__main__":
    main()
