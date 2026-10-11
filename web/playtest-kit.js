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
  const results=await Promise.all(unique.map(id=>new Promise(resolve=>{
    const image=new Image();
    image.onload=()=>resolve({id,ok:true});
    image.onerror=()=>resolve({id,ok:false});
    image.src=window.PhysicalCards.cardArtURL(id,true);
  })));
  const missing=results.filter(result=>!result.ok).map(result=>result.id);
  if(missing.length)throw new Error("Print artwork failed to load for "+missing.join(", ")+". Reload the page before printing.");
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
      ["WIN / BOARD","Control a Front with more surviving Forces (0–3 per player); equal headcounts are contested. Defeated Forces leave permanently. Collapse at 0 Command before recovery."],
      ["TURNS","Four Fronts: 2+3 open first, then 1 at Battle II, 4 at Battle III. Pass before drawing, or draw 1 and take up to two Actions: deploy, Maneuver for 1 Command, or discard 2 to draw 1."],
      ["PLANS","After the two closing turns, reveal one secret army-wide Assault / Hold / Volley / Raid Plan each. Plans set which enemy ranks are eligible and when Forces move; they never alter dice or Force."],
      ["ASSAULT","Normal Strikes target the foremost occupied enemy rank. After casualties, advance one surviving unpinned Force one empty rank forward per Front."],
      ["HOLD","Withdraw one Force one empty rank backward per Front before rolling. Strikes target foremost. Protect can cover any friendly Force in its own Front."],
      ["VOLLEY","An Archer can Strike any occupied enemy rank in its Front; other Strikes target foremost."],
      ["RAID","Move one Raider/Rider/Skirmisher sideways to an empty same-rank position in an adjacent active Front before rolling. These roles may Strike Middle or Rear if occupied, otherwise foremost."],
      ["ROLL / TARGET","Each player rolls one D6 per occupied Front; every Force there reads its own face. Declare all legal Strike targets together; players freely choose from the Plan's eligible enemies. Printed fixed-target Specials take precedence."],
      ["COORDINATE","After cancelling attacks: each uncancelled damaging Strike gains +1 effective Force per OTHER uncancelled damaging Strike on that same target. An effective Force GREATER than the defender defeats; equality stalemates unless that Special permits equality."],
      ["PRESSURE / PIN","An individually nonlethal Strike may instead become Pressure at declaration; after Evade, it suppresses the target's entire rolled Protect/Rescue or Pins it. Pressure never adds to damage. Uncancelled failed damaging Strikes also Pin: no post-combat movement this Battle."],
      ["PROTECT / EVADE","Evade cancels every incoming damaging Strike or Pressure against itself. Protect cancels one incoming damaging Strike for an eligible target unless printed otherwise. Allocate Protect after targets and Pressure are known."],
      ["RESCUE","After lethal checks, each Rescue prevents a permitted Force's ENTIRE defeat, even against several attacking Strikes. A rescued target was not destroyed."],
      ["COMBAT TIMING","Reveal Plans → move → roll → declare Strike/Pressure targets → Evade → Pressure → Protect → coordinated lethality & Pin → Rescue → discard casualties → printed advances → Assault advances → territory."],
      ["COMMAND","Lose 1 Command per enemy-controlled Front; check Collapse before recovery. Recover 8 if behind in controlled Fronts, 6 if ahead, 7 each if tied; cap 20. Draw back to 10."],
      ["LIMITS","Only printed Specials may reach an adjacent Front. No markers persist for Pressure/Pin. No Bonds, Names, Tactics, Orders, Stratagems or Narratives; Heroes play as Forces (one per Battle)."],
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
        '<aside><strong>Key combinations</strong><ul class="deck-combo-list">'+
        (deck.combo_notes||[]).slice(0,2).map(note=>'<li>'+esc(note)+'</li>').join("")+
        '</ul><details class="deck-combo-question"><summary>More combos and playtest question</summary><ul class="deck-combo-list">'+
        (deck.combo_notes||[]).slice(2).map(note=>'<li>'+esc(note)+'</li>').join("")+
        '</ul><p>'+esc(deck.hypothesis||"")+'</p></details></aside></div>'+
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
      try{
        await preloadArt(selectedArtIds);
        if(document.fonts?.ready)await document.fonts.ready;
        if(generation!==renderGeneration)return;
        printButton.disabled=false;
        summary.textContent=selectionSummary(chosenDecks,false);
      }catch(error){
        if(generation!==renderGeneration)return;
        printButton.disabled=true;
        summary.textContent=error.message;
      }
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
