(() => {
"use strict";
const ids=["the-kings-spears","the-red-shields","the-house-of-reed","the-grey-riders","the-lantern-scouts","the-salt-road-fleet","the-serekh","the-aradai","the-iron-boars","the-white-hands-of-elara"];
async function main(){
  const response=await fetch("data/cards-v2-redesign.json",{cache:"no-cache"});
  if(!response.ok) throw new Error("Could not load V2 card data");
  const cards=(await response.json()).cards||[];
  const byId=new Map(cards.map(card=>[card.id,card]));
  const primary=byId.get("the-kings-spears");
  if(!primary) throw new Error("The King's Spears not found");
  document.getElementById("hero-proof").innerHTML=window.V2Cards.cardArticle(primary);
  document.getElementById("force-proof-grid").innerHTML=ids.filter(id=>id!=="the-kings-spears").map(id=>{
    const card=byId.get(id);
    return card?window.V2Cards.cardArticle(card):"";
  }).join("");
}
main().catch(error=>{document.getElementById("hero-proof").textContent=error.message||String(error)});
})();