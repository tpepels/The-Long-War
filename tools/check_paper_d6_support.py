"""New physical War deck types: persistent Holdings and immediate Tactics."""
from __future__ import annotations

import html
import json
import re
import tempfile
from pathlib import Path

from paper_d6_cards import load_paper_d6_war_cards, load_paper_d6_decks
from check_card_layout import ROOT, browser_path, run_browser

SUPPORT = ROOT / "cards/paper-d6-support.json"


def check_data():
    data = json.loads(SUPPORT.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert data["status"] == "canonical-paper-only"
    assert data["deck_size"] == 24 and data["min_forces_per_deck"] == 16
    assert set(data["types"]) == {"holding", "tactic"}
    assert data["types"]["holding"]["counts_as_force"] is False
    assert data["types"]["tactic"]["counts_as_force"] is False
    assert len(data["cards"]) == 12
    assert len({c["id"] for c in data["cards"]}) == 12
    assert len({c["art_id"] for c in data["cards"]}) == 12
    assert {c["type"] for c in data["cards"]} == {"holding", "tactic"}
    for kind in ("holding", "tactic"):
        assert sum(c["type"] == kind for c in data["cards"]) == 6
    for c in data["cards"]:
        assert 1 <= c["command_cost"] <= 4
        assert 15 <= len(c["effect"]) <= 105, c["id"]
        assert "Nothing" not in c["effect"]
        assert (ROOT / "web/art/cards" / (c["art_id"] + ".png")).is_file(), c["id"]
    assert len({c["id"] for c in data["cards"]}) == 12
    war = load_paper_d6_war_cards()
    assert len(war["cards"]) == 56
    assert len({c["id"] for c in war["cards"]}) == 56
    assert sum("paper_d6" in c for c in war["cards"]) == 44
    assert sum("paper_support" in c for c in war["cards"]) == 12

    decks = load_paper_d6_decks(war)["decks"]
    by_id = {c["id"]: c for c in war["cards"]}
    assert len(decks) == 3
    for deck in decks:
        counts = {"force": 0, "holding": 0, "tactic": 0}
        for entry in deck["cards"]:
            kind = by_id[entry["id"]]["type"]
            if kind == "hero":
                kind = "force"
            counts[kind] += entry["copies"]
        assert counts == {"force": 18, "holding": 3, "tactic": 3}, (deck["id"], counts)
    rules = (ROOT / "rules/rulebook.md").read_text(encoding="utf-8")
    assert "24-card War deck" in rules
    assert "Holding" in rules and "Tactic" in rules
    assert "at least 16 Forces" in rules
    assert "maximum one of yours per Front" in rules
    assert "Holdings occupy no Force position" in rules
    return [card for card in war["cards"] if "paper_support" in card]


CHECK = r"""
window.addEventListener("load",()=>{
  const issues=[];
  const cards=[...document.querySelectorAll(".paper-support-layout")];
  if(cards.length!==12)issues.push("not-twelve-cards");
  const mm=96/25.4;
  for(const c of cards){
    const id=c.dataset.cardId,box=c.getBoundingClientRect();
    const title=c.querySelector(".paper-head-title");
    const head=c.querySelector(".paper-card-head");
    const art=c.querySelector(".motif-field");
    const rules=c.querySelector(".support-rules");
    const timing=c.querySelector(".support-timing");
    const text=c.querySelector(".support-effect");
    const seal=c.querySelector(".cost-gem");
    const footer=c.querySelector(".support-footer");
    if(!title||!head||!art||!rules||!timing||!text||!seal||!footer)
      issues.push(id+":missing-component");
    if(Math.abs(box.width-68*mm)>2||Math.abs(box.height-96*mm)>2)
      issues.push(id+":bad-dimensions");
    if(head&&art&&head.getBoundingClientRect().bottom>art.getBoundingClientRect().top+.5)
      issues.push(id+":header-art-overlap");
    if(art&&rules&&rules.getBoundingClientRect().top<art.getBoundingClientRect().bottom-.5)
      issues.push(id+":art-rules-overlap");
    if(rules&&footer&&rules.getBoundingClientRect().bottom>footer.getBoundingClientRect().top+.5)
      issues.push(id+":rules-footer-overlap");
    if(text&&text.scrollHeight>text.clientHeight+2)issues.push(id+":text-clipped");
    if(title&&title.scrollHeight>title.clientHeight+2)issues.push(id+":title-clipped");
    if(rules&&rules.scrollHeight>rules.clientHeight+2)issues.push(id+":rules-clipped");
    if(text&&rules&&text.getBoundingClientRect().bottom>rules.getBoundingClientRect().bottom+.5)
      issues.push(id+":text-outside-rules");
    if(!getComputedStyle(c,"::before").backgroundImage.includes("card-shell"))
      issues.push(id+":not-force-family-shell");
    if(!getComputedStyle(art,"::after").backgroundImage.includes("art-window"))
      issues.push(id+":not-force-family-frame");
    if(!getComputedStyle(art,"::before").backgroundImage.includes("cards-print"))
      issues.push(id+":no-retired-illustration");
    if(c.classList.contains("card-holding")&&!timing.textContent.includes("STAYS"))
      issues.push(id+":permanent-not-obvious");
    if(c.classList.contains("card-tactic")&&!timing.textContent.includes("DISCARD"))
      issues.push(id+":immediate-not-obvious");
  }
  const failures=window.PhysicalCards.inspect(document);
  issues.push(...failures.map(f=>f.id+":"+f.problems.join(",")));
  document.getElementById("support-test-result").textContent=issues.length?issues.join(";"):"PASS";
});
"""


def check_layout(cards):
    browser = browser_path()
    if not browser:
        print("SKIP: Chrome not installed for support-card layout")
        return
    css = (ROOT / "web/physical-cards.css").read_text(encoding="utf-8")
    scripts = "\n".join(
        "<script>" + (ROOT / "web" / name).read_text(encoding="utf-8") + "</script>"
        for name in ("card-symbols.js", "physical-cards.js")
    )
    payload = json.dumps(cards).replace("<", "\\u003c")
    page = f"""<!doctype html><html><head><meta charset="utf-8">
<base href="{(ROOT / 'web').as_uri()}/">
<meta name="lw-build-version" content="support-layout-test">
<style>{css}</style></head><body>
<main id="cards" class="cards"></main><div id="support-test-result"></div>
<script type="application/json" id="support-data">{payload}</script>
{scripts}<script>
const source=JSON.parse(document.getElementById("support-data").textContent);
document.getElementById("cards").innerHTML=source.map(card=>
  '<div class="card-wrap">'+window.PhysicalCards.cardArticle(card,"",{printArt:true})+'</div>').join("");
{CHECK}
</script></body></html>"""
    with tempfile.TemporaryDirectory(prefix="longwar-support-") as folder:
        path = Path(folder) / "support-layout.html"
        path.write_text(page, encoding="utf-8")
        result = run_browser(browser, path, timeout_seconds=60)
    if result.returncode:
        raise SystemExit("Chrome support card layout failed: "+result.stderr[-1000:])
    match = re.search(r'<div id="support-test-result">([^<]*)</div>', result.stdout)
    status = html.unescape(match.group(1)) if match else "Browser never completed"
    if status != "PASS":
        raise SystemExit("FAIL support layout: "+status[:5000])
    print("PASS: all 12 Holding/Tactic cards share Force shell and frame; no clipped rules")


def main():
    cards = check_data()
    print("PASS: 44 Forces + 6 persistent Holdings + 6 immediate Tactics; all sample War decks legal")
    check_layout(cards)


if __name__ == "__main__":
    main()
