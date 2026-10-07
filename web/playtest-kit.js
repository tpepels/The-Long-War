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
  if(!cardsResponse.ok||!decksResponse.ok)throw new Error("Could not load current playtest data");

  const cardData=await cardsResponse.json();
  const cards=cardData.cards||[];
  const decks=(await decksResponse.json()).decks||[];
  if(!decks.length)throw new Error("No playtest decks were published");

  const index=new Map(cards.map(card=>[card.id,card]));
  const vocabulary=cardData.position_vocabulary||{};
  const timing=cardData.timing_vocabulary||{};
  const reference=document.getElementById("mechanics-reference");
  const picker=document.getElementById("deck-picker");
  const root=document.getElementById("playtest-decks");
  const includeMechanics=document.getElementById("include-mechanics");
  const printButton=document.getElementById("print-selected");
  const summary=document.getElementById("print-summary");
  const selected=new Set(decks.slice(0,2).map(deck=>deck.id));

  if(reference){
    const rows=[
      ["MOVE",vocabulary.move],
      ["MOVE UP TO N",vocabulary.move_multiple],
      ["SWAP",vocabulary.swap],
      ["MOVES / MOVED",vocabulary.movement_event],
      ["MOBILE",vocabulary.mobile],
      ["TIRELESS",vocabulary.tireless],
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

  const expandedByDeck=new Map();
  for(const deck of decks){
    const expanded=expandDeck(deck);
    const missing=[...new Set(expanded.filter(id=>!index.has(id)))];
    if(missing.length)throw new Error(deck.title+" contains unknown cards: "+missing.join(", "));
    expandedByDeck.set(deck.id,expanded);
  }

  picker.innerHTML=decks.map((deck,indexNumber)=>{
    const expanded=expandedByDeck.get(deck.id);
    const sheets=Math.ceil(expanded.length/8);
    return '<label class="deck-choice" data-deck-id="'+esc(deck.id)+'">'+
      '<input type="checkbox" value="'+esc(deck.id)+'"'+(selected.has(deck.id)?" checked":"")+'>'+
      '<span class="deck-choice-number">'+String(indexNumber+1).padStart(2,"0")+'</span>'+
      '<span class="deck-choice-copy"><strong>'+esc(deck.title)+'</strong><small>'+esc(deck.playstyle||"Exploratory")+'</small></span>'+
      '<span class="deck-choice-meta">'+expanded.length+' cards<br>'+sheets+' sheets</span>'+
      '</label>';
  }).join("");

  root.innerHTML=decks.map((deck,deckIndex)=>{
    const expanded=expandedByDeck.get(deck.id);
    return '<section class="print-deck" data-deck-id="'+esc(deck.id)+'">'+
      '<header class="deck-sheet-heading"><strong>The Long War · playtest deck '+(deckIndex+1)+' of '+decks.length+'</strong>'+
      '<span>'+esc(deck.title)+' · '+expanded.length+' cards</span></header>'+
      '<div class="deck-screen-summary"><div><p class="deck-print-kicker">PLAYTEST DECK '+(deckIndex+1)+'</p><h2>'+esc(deck.title)+'</h2><p>'+esc(deck.playstyle||"")+'</p></div>'+
      '<aside><strong>What this deck tests</strong><p>'+esc(deck.hypothesis||"")+'</p></aside></div>'+
      chunk(expanded,8).map((sheet,sheetIndex)=>
        '<div class="deck-card-grid print-sheet" data-sheet="'+(sheetIndex+1)+'">'+
        sheet.map(id=>window.V2Cards.cardArticle(index.get(id),"print-card deck-card")).join("")+
        '</div>'
      ).join("")+
      '</section>';
  }).join("");

  function applySelection(){
    document.querySelectorAll(".deck-choice").forEach(label=>{
      const input=label.querySelector("input");
      const id=input.value;
      label.classList.toggle("is-selected",selected.has(id));
      input.checked=selected.has(id);
    });
    document.querySelectorAll(".print-deck").forEach(section=>{
      const chosen=selected.has(section.dataset.deckId);
      section.classList.toggle("screen-excluded",!chosen);
      section.classList.toggle("print-excluded",!chosen);
    });
    if(reference)reference.classList.toggle("print-excluded",!includeMechanics.checked);

    const chosenDecks=decks.filter(deck=>selected.has(deck.id));
    const cardsToPrint=chosenDecks.reduce((sum,deck)=>sum+expandedByDeck.get(deck.id).length,0);
    const sheets=chosenDecks.reduce((sum,deck)=>sum+Math.ceil(expandedByDeck.get(deck.id).length/8),0);
    const extra=includeMechanics.checked?1:0;
    summary.textContent=chosenDecks.length
      ? chosenDecks.length+" deck"+(chosenDecks.length===1?"":"s")+" selected · "+cardsToPrint+" cards · "+sheets+" card sheets"+(extra?" + 1 mechanics sheet":"")
      : "Select at least one deck to print.";
    document.getElementById("kit-count").textContent=chosenDecks.length
      ? chosenDecks.length+" of "+decks.length+" decks selected"
      : decks.length+" playtest decks";
    printButton.disabled=chosenDecks.length===0;
  }

  picker.addEventListener("change",event=>{
    const input=event.target.closest('input[type="checkbox"]');
    if(!input)return;
    if(input.checked)selected.add(input.value);else selected.delete(input.value);
    applySelection();
  });
  includeMechanics.addEventListener("change",applySelection);
  document.getElementById("select-first-two").addEventListener("click",()=>{
    selected.clear();
    decks.slice(0,2).forEach(deck=>selected.add(deck.id));
    applySelection();
  });
  document.getElementById("select-all-decks").addEventListener("click",()=>{
    selected.clear();
    decks.forEach(deck=>selected.add(deck.id));
    applySelection();
  });
  printButton.addEventListener("click",()=>{
    applySelection();
    window.print();
  });
  window.addEventListener("beforeprint",applySelection);

  applySelection();
  scheduleInspect(root);
}
main().catch(error=>{
  const root=document.getElementById("playtest-decks");
  if(root)root.textContent=error.message;
  const summary=document.getElementById("print-summary");
  if(summary)summary.textContent=error.message;
});
