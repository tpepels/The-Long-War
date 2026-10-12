"""Verify both printable 12-card Order decks at actual 68 x 96 mm size."""
from __future__ import annotations

import html
import json
import re
import tempfile
from pathlib import Path
import shutil

from PIL import Image

from check_card_layout import ROOT, browser_path, run_browser

CHECK = r"""
window.addEventListener("load",()=>{
  const issues=[];
  const sheets=[...document.querySelectorAll("#order-print-pages .print-sheet")];
  const cards=[...document.querySelectorAll("#order-print-pages .order-card")];
  const hand=document.querySelectorAll("#order-hand .order-card");
  const gallery=document.querySelectorAll("#order-gallery .order-card");
  if(sheets.length!==3)issues.push("expected-three-print-sheets:"+sheets.length);
  if(cards.length!==24)issues.push("expected-24-orders:"+cards.length);
  if(hand.length!==3)issues.push("expected-three-hand-cards:"+hand.length);
  if(gallery.length!==4)issues.push("expected-four-distinct-orders:"+gallery.length);
  const mm=96/25.4;
  const inside=(a,b,pad=1)=>b.left>=a.left-pad&&b.right<=a.right+pad&&
    b.top>=a.top-pad&&b.bottom<=a.bottom+pad;
  for(let i=0;i<cards.length;i++){
    const card=cards[i];
    const name=card.dataset.order+":"+i;
    const rect=card.getBoundingClientRect();
    const sheet=card.closest(".print-sheet")?.getBoundingClientRect();
    const header=card.querySelector(".stack-edge.paper-card-head");
    const title=header?.querySelector(".paper-head-title");
    const art=card.querySelector(".motif-field");
    const artRect=art?.getBoundingClientRect();
    const rules=card.querySelector(".rules.order-rules");
    const effect=card.querySelector(".order-effect");
    const copy=card.querySelector(".order-text");
    const footer=card.querySelector(".card-footer");
    const expectedArt=card.dataset.order==="assault"?"all-banners-forward":
      card.dataset.order==="hold"?"no-step-back":
      card.dataset.order==="volley"?"a-volley-before-dawn":"the-line-wheeled";
    if(!card.classList.contains("physical-card")||
       !card.classList.contains("paper-order-layout")||
       !card.classList.contains("card-order"))
      issues.push(name+":not-shared-physical-card");
    if(!header||!title||!art||!rules||!copy||!footer)
      issues.push(name+":missing-shared-card-structure");
    if(Math.abs(rect.width-68*mm)>2||Math.abs(rect.height-96*mm)>2)
      issues.push(name+":incorrect-card-dimensions");
    if(sheet&&!inside(sheet,rect,1.1))issues.push(name+":outside-sheet");
    if(artRect&&artRect.height<28*mm)issues.push(name+":artwork-too-small");
    const shell=getComputedStyle(card,"::before").backgroundImage;
    const painting=art&&getComputedStyle(art,"::before").backgroundImage;
    const artFrame=art&&getComputedStyle(art,"::after").backgroundImage;
    if(!shell.includes("card-shell"))issues.push(name+":missing-force-card-shell");
    if(!painting||!painting.includes(expectedArt+".webp"))
      issues.push(name+":wrong-canonical-painting");
    if(!artFrame||!artFrame.includes("art-window"))
      issues.push(name+":missing-force-card-art-frame");
    if(card.querySelector(".order-illustration,.order-crest"))
      issues.push(name+":old-independent-order-design");
    if(copy){
      if(!getComputedStyle(copy).fontFamily.includes("LW Text"))
        issues.push(name+":different-than-force-font");
      if(parseFloat(getComputedStyle(copy).fontSize)<12)
        issues.push(name+":effect-too-small");
      if(copy.scrollHeight>copy.clientHeight+2||copy.scrollWidth>copy.clientWidth+2)
        issues.push(name+":effect-clipped");
    }
    if(title&&header){
      if(title.scrollHeight>title.clientHeight+2)
        issues.push(name+":title-clipped");
      if(title.getBoundingClientRect().bottom>header.getBoundingClientRect().bottom+.5)
        issues.push(name+":title-outside-header");
    }
    if(artRect&&header&&artRect.top<header.getBoundingClientRect().bottom-.5)
      issues.push(name+":header-overlaps-art");
    if(artRect&&rules&&rules.getBoundingClientRect().top<artRect.bottom-.5)
      issues.push(name+":rules-overlap-art");
    if(rules&&footer&&rules.getBoundingClientRect().bottom>footer.getBoundingClientRect().top+.5)
      issues.push(name+":rules-overlap-footer");
    if(copy&&rules&&copy.getBoundingClientRect().bottom>rules.getBoundingClientRect().bottom+.5)
      issues.push(name+":effect-outside-rules");
    if(card.scrollHeight>card.clientHeight+2)
      issues.push(name+":whole-card-overflow");
  }
  const inspector=window.PhysicalCards?.inspect(document)||[];
  for(const entry of inspector.filter(e=>e.id?.startsWith("order-")))
    issues.push(entry.id+":"+entry.problems.join(","));
  document.getElementById("order-layout-result").textContent=
    issues.length?issues.join(";"):"PASS";
});
"""


def main() -> None:
    browser = browser_path()
    if not browser:
        print("SKIP: Chromium is not available for Order print geometry")
        return
    data = json.loads((ROOT / "cards/paper-d6-orders.json").read_text())
    authored = (ROOT / "web/orders.html").read_text()
    css = (ROOT / "web/orders.css").read_text()
    shared_css = (ROOT / "web/physical-cards.css").read_text()
    # Layout uses the same shared artwork frame, font and renderer modules
    # as Force cards, not a second Order-specific painted-card template.
    css += """
    .print-pages{display:block!important}
    .print-sheet{height:194mm;width:278mm;margin:0;display:grid;
      grid-template-columns:repeat(4,68mm);
      grid-template-rows:repeat(2,96mm);gap:2mm}
    """
    authored = authored.replace(
        '<link rel="stylesheet" href="physical-cards.css">',
        "<style>" + shared_css + "</style>",
    ).replace(
        '<link rel="stylesheet" href="orders.css">',
        "<style>" + css + "</style>",
    )
    data_literal = json.dumps(data).replace("<", "\\u003c")
    scripts = (
        '<script>window.fetch=async()=>({ok:true,json:async()=>('
        + data_literal + ')});</script>'
        + '<script>' + (ROOT / "web/card-symbols.js").read_text() + '</script>'
        + '<script>' + (ROOT / "web/physical-cards.js").read_text() + '</script>'
        + '<script>' + js + '</script>'
        + '<div id="order-layout-result"></div>'
        + '<script>' + CHECK + '</script>'
    )
    authored = authored.replace('<script src="card-symbols.js"></script>', "")
    authored = authored.replace('<script src="physical-cards.js"></script>', "")
    authored = authored.replace('<script src="orders.js"></script>', scripts)
    with tempfile.TemporaryDirectory(prefix="longwar-orders-") as folder:
        path = Path(folder) / "orders.html"
        # The published site uses optimised WebP illustrations, not PNG
        # originals. Make the exact same art paths available to headless
        # Chromium so the test fails if images are missing or undecodable.
        shutil.copytree(ROOT / "web/fonts", path.parent / "fonts")
        shutil.copytree(ROOT / "web/art/card-frame", path.parent / "art/card-frame")
        art_dir = path.parent / "art/cards-print"
        art_dir.mkdir(parents=True)
        for order in data["orders"]:
            art_id = order["art_id"]
            source = ROOT / "web/art/cards" / (art_id + ".png")
            if not source.is_file():
                raise SystemExit("Missing Order illustration source: " + str(source))
            with Image.open(source) as image:
                image = image.convert("RGB")
                image.thumbnail((960, 960), Image.Resampling.LANCZOS)
                image.save(art_dir / (art_id + ".webp"), "WEBP", quality=86)
        path.write_text(authored, encoding="utf-8")
        result = run_browser(browser, path, timeout_seconds=60)
    if result.returncode:
        raise SystemExit("Order print Chrome failed: " + result.stderr[-1200:])
    match = re.search(r'<div id="order-layout-result">([^<]*)</div>', result.stdout)
    status = html.unescape(match.group(1)) if match else "Order browser test did not finish"
    if status != "PASS":
        raise SystemExit("FAIL Order layout: " + status[:4500])
    print("PASS: two canonical 12-card Order decks fit three A4 sheets, with Force-family frames, typography, genuine illustrations and unclipped effects")


if __name__ == "__main__":
    main()
