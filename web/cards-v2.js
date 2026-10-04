(() => {
"use strict";
const scriptURL=typeof document==="undefined"?"":document.currentScript?.src||"";
const VERSION=(()=>{try{return new URL(scriptURL,window.location.href).searchParams.get("v")||"dev"}catch(_){return"dev"}})();
const esc=value=>String(value??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;");
const titleCase=value=>String(value??"").split(/[-_ ]+/).filter(Boolean).map(part=>part[0].toUpperCase()+part.slice(1)).join(" ");
const TYPE={force:"Force",bond:"Bond",name:"Name",hero:"Hero",tactic:"Tactic",stratagem:"Stratagem",narrative:"Narrative"};
const LABEL={play:"PLAY",action:"ACTION",reaction:"REACTION",bonded:"BONDED",while_named:"WHILE NAMED",becomes_named:"BECOMES NAMED",trigger:"TRIGGER",continuous:"CONTINUOUS",hidden:"REVEAL"};
const LIVE=new Set(["action","reaction","bonded","while_named"]);
const H=()=>window.V2Heraldry;
const signed=value=>(Number(value)>=0?"+":"")+String(value??0);
const modeEffects=(card,mode)=>card?.modes?.[mode]?.effects||[];
const effects=card=>card.type==="hero"?[...modeEffects(card,"force"),...modeEffects(card,"name")]:(card.effects||[]);
const typeGlyph=type=>H()?.symbol(type)||"";
const classGlyph=name=>H()?.classification(name)||"";
const timingGlyph=name=>H()?.timing(name)||"";
const utilityGlyph=name=>H()?.utility(name)||"";
const strengthGlyph=()=>H()?.strength()||"";
const rowGlyph=name=>H()?.row(name)||"";
const commandGlyph=(value="")=>H()?.command(value)||"";
const isFormationCard=card=>["force","bond","name","hero"].includes(card.type);

function statGroup(card){
  if(card.type==="hero")return '<div class="hero-stats" aria-label="Hero Force '+esc(card.force_strength)+', Name '+esc(signed(card.name_strength_modifier))+'"><span class="hero-stat hero-force-stat">'+typeGlyph("force")+'<b>'+esc(card.force_strength)+'</b></span><span class="hero-stat hero-name-stat">'+typeGlyph("name")+'<b>'+esc(signed(card.name_strength_modifier))+'</b></span></div>';
  const value=card.type==="force"?card.strength:["bond","name"].includes(card.type)?signed(card.strength_modifier):"";
  return '<div class="edge-stats" aria-label="'+esc(TYPE[card.type]||card.type)+' Strength '+esc(value)+'"><span class="type-mark">'+typeGlyph(card.type)+'</span><span class="strength-mark">'+strengthGlyph()+'<b>'+esc(value)+'</b></span></div>';
}
function classificationIcons(card){return(card.classes||[]).map(name=>'<span class="class-sigil" data-class="'+esc(name)+'" data-group="'+esc(H()?.group(name)||"role")+'" title="'+esc(titleCase(name))+'">'+classGlyph(name)+'</span>').join("")}
function classificationLine(card){
  const own=card.classes||[],refs=card.references||[],values=own.length?own:refs;if(!values.length)return"";
  return '<div class="class-line">'+(own.length?"":'<span class="class-line-prefix">Involves</span>')+values.map(name=>'<span class="class-body-item">'+classGlyph(name)+'<span>'+esc(titleCase(name))+'</span></span>').join('<span class="class-separator">·</span>')+'</div>';
}
function liveEffects(card){if(card.type==="hero")return modeEffects(card,"force").filter(e=>LIVE.has(e.timing));return["force","bond"].includes(card.type)?(card.effects||[]).filter(e=>LIVE.has(e.timing)):[]}
function exposedText(effect){return String(effect.exposed||effect.text||"").replace(/^ACTION\s+1\/B\s*·\s*/i,"").replace(/^REACTION\s+1\/B\s*·\s*/i,"").replace(/^BONDED\s*·\s*/i,"").replace(/^NAMED\s*·\s*/i,"").trim()}
function token(icon,label="",extra=""){return '<span class="edge-token '+extra+'" title="'+esc(label||icon)+'">'+utilityGlyph(icon)+(label?'<b>'+esc(label)+'</b>':"")+'</span>'}
function classToken(name){return '<span class="edge-token edge-class-token" title="'+esc(titleCase(name))+'">'+classGlyph(name)+'</span>'}
function typeToken(name){return '<span class="edge-token edge-type-token" title="'+esc(titleCase(name))+'">'+typeGlyph(name)+'</span>'}
function strengthToken(value=""){return '<span class="edge-token edge-strength-token" title="Strength '+esc(value)+'">'+strengthGlyph()+(value?'<b>'+esc(value)+'</b>':"")+'</span>'}
function commandToken(value=""){return '<span class="edge-token edge-command-token" title="Command '+esc(value)+'">'+commandGlyph(value)+'</span>'}
function rowToken(name){return '<span class="edge-token edge-row-token" title="'+esc(titleCase(name))+' row">'+rowGlyph(name)+'</span>'}
function effectTokens(effect){
  const p=exposedText(effect).toUpperCase();if(!p)return"";
  const patterns=[
    [/^CAPTAIN\/SCOUT CYCLE$/,()=>classToken("captain")+classToken("scout")+token("cycle")],
    [/^RIDER\/SCOUT CYCLE$/,()=>classToken("rider")+classToken("scout")+token("cycle")],
    [/^LOOK AT STRATAGEM$/,()=>token("eye")+typeToken("stratagem")],
    [/^MOVE (\d)(?: · FRONT \+(\d))?$/,m=>token("move",m[1])+(m[2]?rowToken("front")+strengthToken("+"+m[2]):"")],
    [/^SUPPRESS BOND STR$/,()=>token("suppress")+typeToken("bond")+strengthToken()],
    [/^LOCK NAME ACTION$/,()=>typeToken("name")+token("lock")+token("action")],
    [/^PREVENT MARKER$/,()=>token("shield")+token("marker")],
    [/^IGNORE TACTIC$/,()=>token("shield")+typeToken("tactic")],
    [/^PRESS PREPARED$/,()=>token("target")+token("prepared")],
    [/^PREVENT -STR$/,()=>token("shield")+strengthToken("-")],
    [/^PROTECT NAME$/,()=>token("shield")+typeToken("name")],
    [/^TAX NEXT BOND$/,()=>commandToken("+1")+typeToken("bond")],
    [/^TAX NEXT CARD$/,()=>commandToken("+1")+token("card")],
    [/^GUARD ALLY$/,()=>token("shield")+token("ally")],
    [/^CLEAR ALLY$/,()=>token("clear")+token("ally")],
    [/^RAID \+1 COMMAND$/,()=>classToken("raider")+commandToken("+1")],
    [/^RAID LOOK 2$/,()=>classToken("raider")+token("eye")+token("hand","2")],
    [/^ENEMY -1$/,()=>token("enemy")+strengthToken("-1")],
    [/^ARCHER\/SCOUT · \+1$/,()=>classToken("archer")+classToken("scout")+strengthToken("+1")],
    [/^CAPTAIN\/KING · \+1$/,()=>classToken("captain")+classToken("king")+strengthToken("+1")],
    [/^GUARD\/SPEAR · \+1$/,()=>classToken("guard")+classToken("spearman")+strengthToken("+1")],
    [/^BONDS HERE -1$/,()=>typeToken("bond")+commandToken("-1")],
    [/^NAME -1$/,()=>typeToken("name")+commandToken("-1")],
    [/^TACTICS HERE -1$/,()=>typeToken("tactic")+commandToken("-1")],
    [/^WITH ARCHER \+1$/,()=>classToken("archer")+strengthToken("+1")],
    [/^FRONT\/MIDDLE \+1$/,()=>rowToken("front")+rowToken("middle")+strengthToken("+1")],
    [/^FRONT \+1$/,()=>rowToken("front")+strengthToken("+1")],
    [/^REAR \+1$/,()=>rowToken("rear")+strengthToken("+1")],
    [/^\+(\d)$/,m=>strengthToken("+"+m[1])]
  ];
  for(const [re,render] of patterns){const m=p.match(re);if(m)return render(m)}
  return '<span class="edge-fallback">'+esc(p)+'</span>';
}
function liveMarkup(effect){
  const limited=effect.limit==="once_per_battle";
  return '<span class="edge-mechanic" aria-label="'+esc((LABEL[effect.timing]||effect.timing)+(limited?" once per Battle":"")+": "+effect.text)+'"><span class="edge-timing" title="'+esc(LABEL[effect.timing]||effect.timing)+'">'+timingGlyph(effect.timing)+'</span>'+(limited?'<span class="use-socket" title="Once per Battle: cover after use" aria-hidden="true"></span>':"")+'<span class="edge-effect-tokens">'+effectTokens(effect)+'</span></span>';
}
function stackEdge(card){
  return '<header class="stack-edge" data-edge-layout="single-row">'+statGroup(card)+'<div class="edge-identity" aria-label="'+esc((card.classes||[]).map(titleCase).join(", "))+'">'+classificationIcons(card)+'</div><div class="edge-live-group">'+(card.placement?'<span class="edge-placement" title="'+esc(titleCase(card.placement))+' only">'+rowGlyph(card.placement)+'<span class="placement-lock">'+utilityGlyph("lock")+'</span></span>':"")+liveEffects(card).map(liveMarkup).join("")+'</div></header>';
}
function eventCrown(card){return '<header class="event-crown"><span class="event-sigil">'+typeGlyph(card.type)+'</span><span class="event-family">'+esc(TYPE[card.type])+'</span><span class="event-rule"></span></header>'}
function effectBlock(effect){
  const kind=["bonded","while_named","continuous"].includes(effect.timing)?"state":["becomes_named","trigger","reaction","hidden"].includes(effect.timing)?"event":"operation";
  return '<section class="effect-block timing-'+kind+'"><div class="effect-head"><span class="effect-timing-icon" aria-hidden="true">'+timingGlyph(effect.timing)+'</span><span class="effect-label">'+esc(LABEL[effect.timing]||effect.timing)+'</span>'+(effect.limit==="once_per_battle"?'<span class="effect-use"><span class="use-socket"></span><em>once per Battle</em></span>':"")+'</div><div class="effect-text">'+esc(effect.text)+'</div></section>';
}
function rules(card){
  if(card.type==="hero")return '<section class="hero-rule-mode" data-mode="force"><h4 class="mode-heading">'+typeGlyph("force")+'As Force</h4>'+modeEffects(card,"force").map(effectBlock).join("")+'</section><section class="hero-rule-mode" data-mode="name"><h4 class="mode-heading">'+typeGlyph("name")+'As Name</h4>'+modeEffects(card,"name").map(effectBlock).join("")+'</section>';
  return effects(card).length?effects(card).map(effectBlock).join(""):'<p class="empty-rules">No special rules.</p>';
}
function statusLine(card){const bits=[];if(card.type==="stratagem")bits.push("Played face-down");if(card.duration==="this_battle")bits.push("This Battle");return bits.join(" · ")}
function costSeal(card){return '<span class="cost-gem" aria-label="Command cost '+esc(card.command_cost)+'">'+commandGlyph(card.command_cost)+'</span>'}
function cardArticle(card,extra="",options={}){
  const count=effects(card).reduce((n,e)=>n+(e.text||"").length,0),density=count>250?" very-dense":count>170?" dense":count<95?" sparse":"",heroMode=options.heroMode==="name"?"name":"force",status=statusLine(card);
  return '<article class="v2-card card-'+esc(card.type)+density+(extra?" "+esc(extra):"")+'" data-card-id="'+esc(card.id)+'"'+(card.type==="hero"?' data-hero-mode="'+heroMode+'"':"")+'>'+(isFormationCard(card)?stackEdge(card):eventCrown(card))+'<div class="card-body"><h3 class="card-title">'+esc(card.title)+'</h3>'+classificationLine(card)+(status?'<p class="card-byline">'+esc(status)+'</p>':"")+'<div class="motif-field" aria-hidden="true"></div><div class="rules">'+rules(card)+'</div></div><footer class="card-footer"><span class="footer-mark">'+(card.unique?"Unique":"")+'</span><span class="footer-id">'+esc(card.id)+'</span>'+costSeal(card)+'</footer></article>';
}
const STACK_CASES={
 "force-alone":{title:"Force alone",state:"Formation · Unbonded",ids:["the-crow-archers"]},
 "force-bond":{title:"Force + Bond",state:"Bonded",ids:["the-crow-archers","watched-the-skies-for"]},
 "force-name":{title:"Force + Name",state:"Formation · not Named",ids:["the-red-shields","corin-of-the-high-wall"]},
 named:{title:"Force + Bond + Name",state:"Named · also Bonded",ids:["the-ash-bowmen","watched-the-skies-for","corin-of-the-high-wall"]},
 "hero-force":{title:"Hero as Force",state:"Named · also Bonded",ids:["serai-queen-of-crows","followed","namar"],heroMode:"force"},
 "hero-name":{title:"Hero as Name",state:"Named · also Bonded",ids:["the-house-of-reed","carried-messages-for","alda-keeper-of-the-ford"],heroMode:"name"}
};
function stackMarkup(cards,caseName){const entry=STACK_CASES[caseName];if(!entry)return"";return '<div class="stack-demo" data-stack-case="'+esc(caseName)+'" data-layers="'+entry.ids.length+'">'+entry.ids.map((id,index)=>{const card=cards.find(c=>c.id===id);return card?'<div class="stack-card" data-stack-layer="'+index+'">'+cardArticle(card,"",{heroMode:entry.heroMode})+'</div>':""}).join("")+'</div>'}
function renderStacks(cards){const target=document.getElementById("stack-tests");if(target)target.innerHTML=Object.entries(STACK_CASES).map(([key,entry])=>'<figure class="stack-case"><figcaption><h3>'+esc(entry.title)+'</h3><p>'+esc(entry.state)+'</p></figcaption>'+stackMarkup(cards,key)+'</figure>').join("")}
function renderLegend(){
  const target=document.getElementById("symbol-key");if(!target)return;
  const groups=[["Kind",["human","ship","stronghold"]],["Role",["archer","guard","scout","rider","skirmisher","raider","healer","spearman","steward","builder","seer"]],["Rank",["king","captain","veteran","heir"]]];
  target.innerHTML='<div class="legend-core"><span>'+typeGlyph("force")+'Force</span><span>'+typeGlyph("bond")+'Bond</span><span>'+typeGlyph("name")+'Name</span><span>'+strengthGlyph()+'Strength</span><span>'+commandGlyph("")+'Command</span><span>'+timingGlyph("action")+'Action</span><span>'+timingGlyph("reaction")+'Reaction</span><span class="legend-socket"><i class="use-socket"></i>once / Battle</span></div>'+groups.map(([label,names])=>'<div class="legend-group"><b>'+label+'</b>'+names.map(name=>'<span>'+classGlyph(name)+'<em>'+esc(titleCase(name))+'</em></span>').join("")+'</div>').join("");
}
function norm(card){return[card.title,card.type,...(card.classes||[]),...(card.references||[]),...(card.design_tags||[]),card.text].join(" ").toLowerCase()}
function render(cards,decks){
 const value=id=>document.getElementById(id).value,deck=decks.find(d=>d.id===value("deck-filter")),copies=new Map((deck?.cards||[]).map(c=>[c.id,c.copies])),query=value("search").trim().toLowerCase();
 const filtered=cards.filter(card=>
  (value("type-filter")==="all"||card.type===value("type-filter")) &&
  (value("class-filter")==="all"||[...(card.classes||[]),...(card.references||[])].includes(value("class-filter"))) &&
  (value("mechanic-filter")==="all"||(card.design_tags||[]).includes(value("mechanic-filter"))) &&
  (!deck||copies.has(card.id)) &&
  (!query||norm(card).includes(query))
 );
 document.getElementById("count").textContent=filtered.length+" / "+cards.length+" designs";
 document.getElementById("cards").innerHTML=filtered.map(card=>'<div class="card-wrap">'+cardArticle(card)+(copies.has(card.id)?'<span class="copy-chip">'+copies.get(card.id)+' in deck</span>':"")+'</div>').join("");
 scheduleCheck();
}
function inspect(root=document){
 const failures=[],mm=96/25.4;
 root.querySelectorAll(".v2-card").forEach(card=>{
  const box=card.getBoundingClientRect();if(!box.width||!box.height)return;
  const problems=[],edge=card.querySelector(".stack-edge");
  for(const node of card.querySelectorAll(".stack-edge,.edge-identity,.edge-live-group,.card-title,.motif-field,.rules,.card-footer"))if(node.scrollWidth>node.clientWidth+1||node.scrollHeight>node.clientHeight+1)problems.push((node.classList[0]||"node")+"-overflow");
  if(edge)for(const node of edge.querySelectorAll(".edge-stats,.hero-stats,.edge-identity,.edge-live-group"))if(node.getBoundingClientRect().bottom>box.top+10.5*mm+.5)problems.push("covered-edge");
  const art=card.querySelector(".motif-field"),rules=card.querySelector(".rules"),footer=card.querySelector(".card-footer");
  if(art&&rules&&rules.getBoundingClientRect().top<art.getBoundingClientRect().bottom-.5)problems.push("art-rules-overlap");
  if(rules&&footer&&rules.getBoundingClientRect().bottom>footer.getBoundingClientRect().top+.5)problems.push("rules-footer-overlap");
  if(art?.querySelector("svg,img"))problems.push("art-overlay");
  card.classList.toggle("layout-overflow",problems.length>0);if(problems.length)failures.push({id:card.dataset.cardId,problems:[...new Set(problems)]});
 });return failures;
}
function scheduleCheck(){const status=document.getElementById("layout-status");requestAnimationFrame(()=>requestAnimationFrame(()=>{const failures=inspect();if(failures.length){status.hidden=false;status.textContent="Layout check: "+failures.length+" rendering(s) need attention: "+failures.slice(0,8).map(f=>f.id+" ("+f.problems.join(", ")+")").join("; ")+(failures.length>8?" …":"")}else{status.hidden=true;status.textContent=""}window.V2CardLabLastCheck=failures}))}
async function main(){
 const [cardsResponse,decksResponse]=await Promise.all([fetch("data/cards-v2-redesign.json?v="+encodeURIComponent(VERSION),{cache:"no-cache"}),fetch("data/v2-playtest-decks.json?v="+encodeURIComponent(VERSION),{cache:"no-cache"})]);
 if(!cardsResponse.ok)throw new Error("Could not load V2 card data");if(!decksResponse.ok)throw new Error("Could not load V2 playtest decks");
 const cards=(await cardsResponse.json()).cards||[],decks=(await decksResponse.json()).decks||[];
 const classNames=[...new Set(cards.flatMap(card=>[...(card.classes||[]),...(card.references||[])]))].sort();
 document.getElementById("class-filter").innerHTML='<option value="all">All classes</option>'+classNames.map(name=>'<option value="'+esc(name)+'">'+esc(titleCase(name))+'</option>').join("");
 const mechanics=[...new Set(cards.flatMap(card=>card.design_tags||[]))].sort();
 document.getElementById("mechanic-filter").innerHTML='<option value="all">All mechanics</option>'+mechanics.map(name=>'<option value="'+esc(name)+'">'+esc(titleCase(name))+'</option>').join("");
 document.getElementById("deck-filter").innerHTML='<option value="all">All cards</option>'+decks.map(deck=>'<option value="'+esc(deck.id)+'">'+esc(deck.title)+'</option>').join("");
 renderLegend();renderStacks(cards);render(cards,decks);
 ["type-filter","class-filter","mechanic-filter","deck-filter"].forEach(id=>document.getElementById(id).addEventListener("change",()=>render(cards,decks)));
 document.getElementById("search").addEventListener("input",()=>render(cards,decks));
 document.getElementById("stack-toggle").addEventListener("click",event=>{const lab=document.getElementById("stack-lab"),hidden=!lab.hidden;lab.hidden=hidden;event.currentTarget.setAttribute("aria-expanded",String(!hidden))});
 document.getElementById("print-cards").addEventListener("click",()=>window.print());
 window.V2CardLab={cards,decks,inspect,cardArticle,stackMarkup};
}
window.V2Cards={cardArticle,stackMarkup,inspect};
if(typeof document!=="undefined"&&document.getElementById("cards"))main().catch(error=>{const target=document.getElementById("cards");if(target)target.innerHTML='<p class="lab-error">'+esc(error?.message||error)+'</p>'});
})();