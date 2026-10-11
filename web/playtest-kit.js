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
      [
            "WIN / BOARD",
            "Control a Front with more surviving Forces (0–3 per player); rank has no control bonus. Defeated Forces leave permanently. Collapse at 0 Command before recovery."
      ],
      [
            "TURNS",
            "Fronts 2+3 first, then 1 in Battle II and 4 in Battle III. Pass before draw, or draw 1 and take up to 2 Actions: Deploy, Maneuver for 1 Command, Cycle 2 cards to draw 1."
      ],
      [
            "PLANS",
            "Choose one secret army-wide Assault/Hold/Volley/Raid; reveal before dice. Plans set eligible targets and movement, never Force or D6."
      ],
      [
            "COUNTER CYCLE",
            "Hold counters Assault; Assault counters Volley; Volley counters Raid; Raid counters Hold. Assault/Raid and Hold/Volley are neutral; mirrors have no counter."
      ],
      [
            "TACTICAL READ",
            "Countering plan: ONE Read per occupied Front after dice. Choose rolled Strike (no fixed printed rank): target ANY opposing rank and ignore ONE Protect; OR choose rolled Protect to cancel ONE extra damaging Strike against an already eligible friend. No Read on Rescue or Falter."
      ],
      [
            "ROLE POSITIONS",
            "Frontline Guard rolling Protect can cover any ally in its Front. Middle/Rear Archer gains Volley targeting. Frontline/Middle Raider/Rider/Skirmisher gains Raid deep targeting. Rear Healer/Steward can Rescue any ally in same Front."
      ],
      [
            "ASSAULT",
            "Ordinary Strikes target foremost; unconditional one optional post-combat forward rank step per Front. Not an extra movement if an Opportunity is earned."
      ],
      [
            "HOLD",
            "Withdraw one Force a rank before dice; Protect can cover any ally in its Front. Post-combat step only after an Opportunity."
      ],
      [
            "VOLLEY",
            "Middle/Rear Archer can target any enemy rank; others target foremost. Post-combat step only after Opportunity."
      ],
      [
            "RAID",
            "Mobile Force may move sideways into originally empty same-rank adjacent active Front before dice; mobile in Frontline/Middle may Strike enemy Middle/Rear. Step only after Opportunity."
      ],
      [
            "OPPORTUNITY",
            "After combat earn one if you discarded enemy with a damaging Strike, cancelled a damaging Strike via Protect/Evade, or saved a Force via Rescue. Optional forward move into empty legal rank. ONE post-combat move per player per Front, including Special advances; no moved-twice or Pinned Force."
      ],
      [
            "ROLL / TARGET",
            "Each player rolls one D6 per occupied Front; all their Forces use their own face. Declare Strikes and Pressure simultaneously. Fixed-target Specials override Plan and role reach."
      ],
      [
            "COORDINATE",
            "Each uncancelled damaging Strike gains +1 effective Force per OTHER uncancelled Strike at the same target. Greater Force defeats, equality stalemates absent a printed Special."
      ],
      [
            "PRESSURE / PIN",
            "Weak Strike may become Pressure instead of damage: suppress the target's rolled Protect/Rescue or Pin it. No coordination bonus. Failed uncancelled damaging Strikes Pin, preventing post-combat movement this Battle only."
      ],
      [
            "PROTECT / EVADE / RESCUE",
            "Evade cancels all attacks and Pressure against self. Protect cancels one damaging Strike unless printed otherwise. Rescue prevents the ENTIRE defeat of one permitted Force."
      ],
      [
            "COMBAT TIMING",
            "Reveal Plans → pre-combat move → roll → declare targets/Read/Pressure → Evade → Pressure → Protect/Read → coordination, lethal and Pin → Rescue → discard casualties → Special then Plan/Opportunity move → control."
      ],
      [
            "COMMAND",
            "Lose 1 Command per enemy-controlled Front, check Collapse, recover 8 when behind, 6 when ahead, 7 if tied; cap 20. Refill to 10."
      ],
      [
            "LIMITS",
            "Only printed Specials cross Fronts. Tactical Read/Opportunity/Pin have no markers. Bonds, Names, Tactics, Orders, Stratagems, Narratives suspended; Heroes are Force-only."
      ]
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
