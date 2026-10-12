"""Verify both printable 12-card Order decks at actual 68 x 96 mm size."""
from __future__ import annotations

import html
import json
import re
import tempfile
from pathlib import Path

from check_card_layout import ROOT, browser_path, run_browser

CHECK = r"""
window.addEventListener("load",async()=>{
  await document.fonts.ready;
  await Promise.resolve();
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
    const art=card.querySelector(".order-art")?.getBoundingClientRect();
    const effect=card.querySelector(".order-effect");
    const effectRect=effect?.getBoundingClientRect();
    const copy=card.querySelector(".order-text");
    const footer=card.querySelector(".order-footer")?.getBoundingClientRect();
    if(Math.abs(rect.width-68*mm)>2||Math.abs(rect.height-96*mm)>2)
      issues.push(name+":incorrect-card-dimensions");
    if(sheet&&!inside(sheet,rect,1.1))issues.push(name+":outside-sheet");
    if(!art||art.height<35*mm)issues.push(name+":missing-large-artwork");
    if(!copy||!effect||!footer)issues.push(name+":missing-effect");
    else {
      if(effectRect.bottom>footer.top+1)issues.push(name+":effect-overlaps-footer");
      if(copy.scrollHeight>copy.clientHeight+2||copy.scrollWidth>copy.clientWidth+2)
        issues.push(name+":effect-clipped");
      if(copy.getBoundingClientRect().bottom>effectRect.bottom+.5)
        issues.push(name+":text-outside-effect-region");
      if(parseFloat(getComputedStyle(copy).fontSize)<11.5)
        issues.push(name+":font-too-small");
      if(card.scrollHeight>card.clientHeight+2)
        issues.push(name+":whole-card-overflow");
    }
  }
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
    js = (ROOT / "web/orders.js").read_text()
    css += """
    .print-pages{display:block!important}
    .print-sheet{height:194mm;width:278mm;margin:0;display:grid;
      grid-template-columns:repeat(4,68mm);
      grid-template-rows:repeat(2,96mm);gap:2mm}
    """
    authored = authored.replace(
        '<link rel="stylesheet" href="orders.css">',
        "<style>" + css + "</style>",
    )
    data_literal = json.dumps(data).replace("<", "\\u003c")
    scripts = (
        '<script>window.fetch=async()=>({ok:true,json:async()=>('
        + data_literal + ')});</script>'
        + '<script>' + js + '</script>'
        + '<div id="order-layout-result"></div>'
        + '<script>' + CHECK + '</script>'
    )
    authored = authored.replace('<script src="orders.js"></script>', scripts)
    with tempfile.TemporaryDirectory(prefix="longwar-orders-") as folder:
        path = Path(folder) / "orders.html"
        path.write_text(authored, encoding="utf-8")
        result = run_browser(browser, path, timeout_seconds=60)
    if result.returncode:
        raise SystemExit("Order print Chrome failed: " + result.stderr[-1200:])
    match = re.search(r'<div id="order-layout-result">([^<]*)</div>', result.stdout)
    status = html.unescape(match.group(1)) if match else "Order browser test did not finish"
    if status != "PASS":
        raise SystemExit("FAIL Order layout: " + status[:4500])
    print("PASS: two canonical 12-card Order decks fit three A4 sheets, with readable art and unclipped effects")


if __name__ == "__main__":
    main()
