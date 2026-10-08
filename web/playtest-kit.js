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
async function preloadArt(ids){
  const unique=[...new Set(ids)];
  await Promise.all(unique.map(id=>new Promise(resolve=>{
    const image=new Image();
    image.onload=resolve;
    image.onerror=resolve;
    image.src="art/cards-print/"+encodeURIComponent(id)+".webp";
  })));
}
async function main(){
  const [cardsResponse,decksResponse]=await Promise.all([
    fetch("data/print-cards.json",{cache:"no-cache"}),
    fetch("data/playtest-decks.json",{cache:"no-cache"}),
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
  let renderGeneration=0;
  let readyPromise=Promise.resolve();

  if(reference){
    const rows=[
      ["TURN / PASS","Before drawing, either Pass (whole turn, no draw) or draw 1 and take up to 2 Actions: play, ACTION, Maneuver, Attack, Cycle. After Pass: opponent full turn, passer full turn, resolve."],
      ["STRENGTH","Force plus Bond and Name modifiers plus effects, minimum 0 per formation. Sum across all 3 ranks in each Front. Attached Name classifications combine with Force classes."],
      ["STACKING","Force below Bond below Name, exposing the buried 10.5 mm strips. PLAY resolves when played; BECOMES NAMED can retrigger after rebuilding."],
      ["PREPARED","Moving into compatible prepared Bond/Name layers attaches them; a duplicate layer makes the move illegal. Prepared PLAY effects never replay."],
      ["MANEUVER","One Action and 1 Command; Named formation moves one orthogonally adjacent active position, or swaps with another friendly formation. Exhausted cannot initiate unless exempt."],
      ["MOVE","Card effects move a formation into an adjacent active empty or compatible prepared position, with no Maneuver cost or Named requirement. Respect legal rows."],
      ["ATTACK","One Action per Force per Battle; Force and attached Name class types combine. No damage; Depleted cannot Attack. ATTACK text modifies an existing Attack."],
      ["ARCHER","Exhaust opposing Rear Force in same Front; Middle Guard screens unless Shaken or Depleted."],
      ["SKIRMISHER","Shake opposing Middle Force in same Front."],
      ["RAIDER","Deplete opposing Middle or Rear Force if its opposing Frontline is empty."],
      ["RIDER","Shake opposing flanked Frontline Force in adjacent active Front."],
      ["FLANKING","Enemy Frontline in an adjacent active Front without a matching friendly Frontline there: flanked Force has −1 Strength while exposed (no marker)."],
      ["EXHAUSTED","Cannot initiate Maneuver; can still Attack and contribute Strength. Old Exhaustion clears at Battle end; defeated Forces get new Exhaustion for next Battle."],
      ["SHAKEN / DEPLETED","Shaken: −2 Strength and no Guard screening. Depleted: no Attack or printed ACTION ability; no Guard screening."],
      ["BOONS","Guarded blocks next affliction, including lost-Front Exhaustion; Inspired prevents Shaken; Empowered bypasses Archer screening for next Attack."],
      ["NARRATIVE","Up to 4 face-up per player; all last through the current Battle, then discard."],
      ["STRATAGEM","Publicly assign an active Front; identity hidden. Optional reveal on eligible trigger. One simultaneous pre-comparison reveal window, no second window for newly created ties."],
      ["RESOLUTION","Compare Fronts, apply Battle-end effects and Command losses; check Collapse before recovery. Guarded protects defeat, then clear temporary effects and apply new lost-Front Exhaustion."],
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

  function selectedDecks(){
    return decks.filter(deck=>selected.has(deck.id));
  }

  function renderSelectedDecks(chosenDecks){
    root.innerHTML=chosenDecks.map((deck,deckIndex)=>{
      const expanded=expandedByDeck.get(deck.id);
      return '<section class="print-deck" data-deck-id="'+esc(deck.id)+'">'+
        '<header class="deck-sheet-heading"><strong>The Long War · playtest deck '+(deckIndex+1)+' of '+chosenDecks.length+'</strong>'+
        '<span>'+esc(deck.title)+' · '+expanded.length+' cards</span></header>'+
        '<div class="deck-screen-summary"><div><p class="deck-print-kicker">PLAYTEST DECK</p><h2>'+esc(deck.title)+'</h2><p>'+esc(deck.playstyle||"")+'</p></div>'+
        '<aside><strong>What this deck tests</strong><p>'+esc(deck.hypothesis||"")+'</p></aside></div>'+
        chunk(expanded,8).map((sheet,sheetIndex)=>
          '<div class="deck-card-grid print-sheet" data-sheet="'+(sheetIndex+1)+'">'+
          sheet.map(id=>window.PhysicalCards.cardArticle(index.get(id),"print-card deck-card",{printArt:true})).join("")+
          '</div>'
        ).join("")+
        '</section>';
    }).join("");
  }

  function selectionSummary(chosenDecks,loading=false){
    if(!chosenDecks.length)return "Select at least one deck to print.";
    const cardsToPrint=chosenDecks.reduce((sum,deck)=>sum+expandedByDeck.get(deck.id).length,0);
    const sheets=chosenDecks.reduce((sum,deck)=>sum+Math.ceil(expandedByDeck.get(deck.id).length/8),0);
    const extra=includeMechanics.checked?1:0;
    return chosenDecks.length+" deck"+(chosenDecks.length===1?"":"s")+" selected · "+cardsToPrint+" cards · "+sheets+" card sheets"+
      (extra?" + 1 mechanics sheet":"")+(loading?" · loading print artwork…":" · ready to print");
  }

  function updatePicker(){
    document.querySelectorAll(".deck-choice").forEach(label=>{
      const input=label.querySelector("input");
      const id=input.value;
      label.classList.toggle("is-selected",selected.has(id));
      input.checked=selected.has(id);
    });
  }

  async function applySelection(){
    const generation=++renderGeneration;
    const chosenDecks=selectedDecks();
    updatePicker();
    if(reference)reference.classList.toggle("print-excluded",!includeMechanics.checked);

    document.getElementById("kit-count").textContent=chosenDecks.length
      ? chosenDecks.length+" of "+decks.length+" decks selected"
      : decks.length+" playtest decks";

    renderSelectedDecks(chosenDecks);
    printButton.disabled=true;
    summary.textContent=selectionSummary(chosenDecks,chosenDecks.length>0);

    if(!chosenDecks.length)return;

    const selectedIds=chosenDecks.flatMap(deck=>expandedByDeck.get(deck.id));
    const selectedArtIds=selectedIds.map(id=>index.get(id)?.art_id||id);
    readyPromise=(async()=>{
      await preloadArt(selectedArtIds);
      if(document.fonts?.ready)await document.fonts.ready;
      if(generation!==renderGeneration)return;
      printButton.disabled=false;
      summary.textContent=selectionSummary(chosenDecks,false);
    })();
    await readyPromise;
  }

  picker.addEventListener("change",event=>{
    const input=event.target.closest('input[type="checkbox"]');
    if(!input)return;
    if(input.checked)selected.add(input.value);else selected.delete(input.value);
    applySelection();
  });
  includeMechanics.addEventListener("change",()=>{
    if(reference)reference.classList.toggle("print-excluded",!includeMechanics.checked);
    summary.textContent=selectionSummary(selectedDecks(),printButton.disabled);
  });
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
  printButton.addEventListener("click",async()=>{
    printButton.disabled=true;
    await readyPromise;
    printButton.disabled=false;
    window.print();
  });

  await applySelection();
}
main().catch(error=>{
  const root=document.getElementById("playtest-decks");
  if(root)root.textContent=error.message;
  const summary=document.getElementById("print-summary");
  if(summary)summary.textContent=error.message;
});
