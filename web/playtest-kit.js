function esc(value){
  return String(value??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;");
}
function chunk(items,size){
  const chunks=[];
  for(let index=0;index<items.length;index+=size)chunks.push(items.slice(index,index+size));
  return chunks;
}
function expandDeck(deck){
  return (deck.cards||[]).flatMap(entry=>Array.from({length:Number(entry.copies)||0},()=>entry.id));
}
function scheduleInspect(root){
  const run=()=>window.V2Cards?.inspect(root);
  requestAnimationFrame(run);
  if(document.fonts?.ready)document.fonts.ready.then(run);
}
async function main(){
  const [cardsResponse,decksResponse]=await Promise.all([
    fetch("data/cards-v2-redesign.json",{cache:"no-cache"}),
    fetch("data/v2-playtest-decks.json",{cache:"no-cache"}),
  ]);
  if(!cardsResponse.ok||!decksResponse.ok)throw new Error("Could not load current playtest card data");
  const cards=(await cardsResponse.json()).cards||[];
  const decks=(await decksResponse.json()).decks||[];
  if(!decks.length)throw new Error("No V2 playtest decks were published");
  const index=new Map(cards.map(card=>[card.id,card]));
  const root=document.getElementById("playtest-decks");
  root.innerHTML=decks.map((deck,deckIndex)=>{
    const expanded=expandDeck(deck);
    const missing=[...new Set(expanded.filter(id=>!index.has(id)))];
    if(missing.length)throw new Error(deck.title+" contains unknown cards: "+missing.join(", "));
    return '<section class="print-deck" data-deck-id="'+esc(deck.id)+'">'+
      '<header class="deck-sheet-heading"><strong>The Long War · playtest deck '+(deckIndex+1)+' of '+decks.length+'</strong>'+
      '<span>'+esc(deck.title)+' · '+expanded.length+' cards · '+esc(deck.playstyle||"Exploratory")+'</span></header>'+
      chunk(expanded,8).map((sheet,sheetIndex)=>
        '<div class="deck-card-grid print-sheet" data-sheet="'+(sheetIndex+1)+'">'+
        sheet.map(id=>window.V2Cards.cardArticle(index.get(id),"print-card deck-card")).join("")+
        '</div>'
      ).join("")+
      '</section>';
  }).join("");
  const total=decks.reduce((sum,deck)=>sum+expandDeck(deck).length,0);
  document.getElementById("kit-count").textContent=decks.length+" playtest decks · "+total+" cards";
  scheduleInspect(root);
}
main().catch(error=>{document.getElementById("playtest-decks").textContent=error.message});
