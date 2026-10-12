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
  const collide=(a,b,tolerance=0.65)=>a&&b&&
    Math.min(a.right,b.right)-Math.max(a.left,b.left)>tolerance&&
    Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>tolerance;
  for(const card of document.querySelectorAll(".paper-d6-layout")){{
    const id=card.dataset.cardId;
    const rules=card.querySelector(".rules");
    const footer=card.querySelector(".card-footer");
    const title=card.querySelector(".paper-card-head .paper-head-title");
    const header=card.querySelector(".paper-card-head");
    const stat=card.querySelector(".paper-head-force");
    const positions=card.querySelector(".paper-head-positions");
    const artwork=card.querySelector(".motif-field");
    const faces=[...card.querySelectorAll(".d6-number")];
    const rows=[...card.querySelectorAll(".d6-stanza")];
    const dice=card.querySelectorAll(".d6-die-icon");
    if(!header||!title||!stat||!positions)
      issues.push(id+":missing-standalone-title-header");
    if(card.querySelector(".card-identity,.edge-identity,.edge-live-group,.d6-roll-key,.d6-key-arrow"))
      issues.push(id+":legacy-exposure-or-repeated-roll-key");
    if(card.querySelectorAll(".card-title").length!==1)
      issues.push(id+":repeated-or-missing-title");
    if(dice.length!==1)
      issues.push(id+":expected-one-die-pictogram");
    if(!artwork||artwork.getBoundingClientRect().height<25*(96/25.4))
      issues.push(id+":artwork-too-short");
    if(title&&header&&title.getBoundingClientRect().bottom>header.getBoundingClientRect().bottom+0.5)
      issues.push(id+":title-overflows-top-band");
    if(title&&title.scrollHeight>title.clientHeight+1)
      issues.push(id+":top-title-clipped");
    const overlaps=(a,b,pad=.6)=>a&&b&&
      Math.min(a.right,b.right)-Math.max(a.left,b.left)>pad&&
      Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>pad;
    if(title&&stat&&overlaps(title.getBoundingClientRect(),stat.getBoundingClientRect()))
      issues.push(id+":title-overlaps-force");
    if(title&&positions&&overlaps(title.getBoundingClientRect(),positions.getBoundingClientRect()))
      issues.push(id+":title-overlaps-placement");
    if(header&&artwork&&header.getBoundingClientRect().bottom>artwork.getBoundingClientRect().top+.5)
      issues.push(id+":top-band-overlaps-artwork");
    if(header&&getComputedStyle(header).gridTemplateColumns.split(" ").length!==3)
      issues.push(id+":expected-three-part-title-band");
    if(faces.length!==6||rows.length!==4)
      issues.push(id+":missing-four-passages-or-six-faces");
    const printed=faces.map(face=>Number(face.textContent)).sort((a,b)=>a-b).join(",");
    if(printed!=="1,2,3,4,5,6")issues.push(id+":missing-or-duplicate-die");
    // Old rectangles, column headers and independently stacked action prose
    // are forbidden. Distinct typography must be one *flowing paragraph*.
    if(card.querySelector(".d6-guide,.d6-outcomes,.d6-result-row,.d6-stanza-heading,.d6-verse,.d6-action-icon"))
      issues.push(id+":old-tabular-card-layout");
    let lastCopy=null;
    for(const row of rows){{
      const key=row.dataset.outcomeKey;
      const copy=row.querySelector(".d6-copy");
      const action=row.querySelector(".d6-action-word");
      const detail=row.querySelector(".d6-detail");
      const numerals=row.querySelector(".d6-rolls");
      const values=row.querySelector(".d6-roll-values");
      if(!values||row.querySelector(".d6-die-icon"))
        issues.push(id+":repeated-die-glyph-"+key);
      if(getComputedStyle(row,"::before").content!=="none" &&
         key!=="S")
        issues.push(id+":gratuitous-result-divider-"+key);
      const rowBox=row.getBoundingClientRect();
      const copyBox=copy?.getBoundingClientRect();
      const rollBox=numerals?.getBoundingClientRect();
      const represented=faces.filter(face=>face.closest(".d6-stanza")===row)
        .map(face=>Number(face.textContent));
      const expected=[...cards.find(c=>c.id===id).paper_d6.faces]
        .flatMap((letter,index)=>letter===key?[index+1]:[]);
      if(represented.join(",")!==expected.join(","))
        issues.push(id+":bad-die-assignment-"+key);
      if(!copy||!action||!numerals){{issues.push(id+":missing-passage-"+key);continue;}}
      if(parseFloat(getComputedStyle(copy).fontSize)<10.8)
        issues.push(id+":body-too-small-"+key);
      if(parseFloat(getComputedStyle(action).fontSize)<9.4)
        issues.push(id+":action-too-small-"+key);
      if(getComputedStyle(row).display==="grid")
        issues.push(id+":not-editorial-"+key);
      if(copy.scrollHeight>copy.clientHeight+2||copy.scrollWidth>copy.clientWidth+2)
        issues.push(id+":prose-overflow-"+key);
      if(copyBox.top<rowBox.top-0.5||copyBox.bottom>rowBox.bottom+0.5)
        issues.push(id+":prose-exceeds-own-passage-"+key);
      if(rollBox.left<rowBox.left-1||rollBox.right>copyBox.left-0.2)
        issues.push(id+":dice-overlap-prose-"+key);
      if(rollBox.top<rowBox.top-1||rollBox.bottom>rowBox.bottom+1)
        issues.push(id+":dice-overlap-neighbour-"+key);
      if(numerals.scrollWidth>numerals.clientWidth+2)
        issues.push(id+":dice-overflow-"+key);
      if(lastCopy&&collide(lastCopy,copyBox))
        issues.push(id+":neighbour-passages-collide-"+key);
      lastCopy=copyBox;
      // Verify actual text glyph line rectangles, not merely containing
      // DIVs. Long Specials can collide despite scrollHeight looking fine.
      for(const textSpan of [action,detail].filter(Boolean)){{
        const range=document.createRange();
        range.selectNodeContents(textSpan);
        for(const box of range.getClientRects()){{
          if(box.top<rowBox.top-1||box.bottom>rowBox.bottom+1)
            issues.push(id+":ink-outside-passage-"+key);
        }}
      }}
    }}
    if(rules.scrollHeight>rules.clientHeight+2)
      issues.push(id+":rules-clip");
    if(footer&&rules.getBoundingClientRect().bottom>footer.getBoundingClientRect().top+0.5)
      issues.push(id+":rules-overlap-footer");
    if(title&&title.getBoundingClientRect().bottom>artwork.getBoundingClientRect().top+0.5)
      issues.push(id+":name-extends-over-artwork");
    // Standalone D6 title is intentionally ABOVE the artwork.
    if(artwork&&title&&title.getBoundingClientRect().bottom>artwork.getBoundingClientRect().top+0.5)
      issues.push(id+":top-title-overlaps-artwork");
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
    print("PASS: 44 standalone paper cards: title in top band, one die cue, four unboxed results, correct D6 mappings and no collisions")


if __name__ == "__main__":
    main()
