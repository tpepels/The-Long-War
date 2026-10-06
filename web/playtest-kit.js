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
    fetch("data/cards.json",{cache:"no-cache"}),
    fetch("data/v2-playtest-decks.json",{cache:"no-cache"}),
  ]);
  if(!cardsResponse.ok||!decksResponse.ok)throw new Error("Could not load current playtest card data");
  const cardData=await cardsResponse.json();
  const cards=cardData.cards||[];
  const decks=(await decksResponse.json()).decks||[];
  const vocabulary=cardData.position_vocabulary||{};
  const timing=cardData.timing_vocabulary||{};
  const reference=document.getElementById("mechanics-reference");
  if(reference){
    const rows=[
      ["MOVE",vocabulary.move],
      ["MOVE UP TO N",vocabulary.move_multiple],
      ["SWAP",vocabulary.swap],
      ["MOVES / MOVED",vocabulary.movement_event],
      ["DIRECTLY AHEAD",vocabulary.directly_ahead],
      ["DIRECTLY BEHIND",vocabulary.directly_behind],
      ["ROW RESTRICTIONS",vocabulary.row_restriction],
      ["SUPPORT +N",vocabulary.support],
      ["SUPPLY",vocabulary.supply],
      ["OUTMATCHED",vocabulary.outmatched],
      ["RESERVE +N",vocabulary.reserve],
      ["PRESS +N",vocabulary.press],
      ["SUPPLY RAID",vocabulary.supply_raid],
      ["STEAL COMMAND",vocabulary.steal_command],
      ["TIRELESS",vocabulary.tireless],
      ["EXHAUSTION",vocabulary.exhaustion],
      ["EXHAUSTED",timing.exhausted],
      ["STACKING",vocabulary.stacking],
      ["COMMAND MODIFIERS",vocabulary.command_modifiers],
      ["TAX MARKERS",vocabulary.tax_markers],
      ["-STRENGTH MARKER",vocabulary.strength_marker],
      ["TEMPORARY NEGATIVE",vocabulary.temporary_negative_marker],
    ].filter(([,value])=>value);
    reference.innerHTML='<h1>Card mechanics quick reference</h1><div class="mechanics-grid">'+
      rows.map(([term,value])=>'<div><dt>'+esc(term)+'</dt><dd>'+esc(value)+'</dd></div>').join("")+
      '</div>';
  }
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
