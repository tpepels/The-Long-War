(() => {
"use strict";
const scriptURL=typeof document==="undefined"?"":document.currentScript?.src||"";
const VERSION=(()=>{try{return new URL(scriptURL,window.location.href).searchParams.get("v")||"dev"}catch(_){return"dev"}})();
const PRINT_VERSION=typeof document==="undefined"||typeof document.querySelector!=="function"?"dev":document.querySelector('meta[name="lw-build-version"]')?.getAttribute("content")||"dev";
const esc=value=>String(value??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;");
const titleCase=value=>String(value??"").split(/[-_ ]+/).filter(Boolean).map(part=>part[0].toUpperCase()+part.slice(1)).join(" ");
const TYPE={force:"Force",bond:"Bond",name:"Name",hero:"Hero",tactic:"Tactic",order:"Order",stratagem:"Stratagem",narrative:"Narrative"};
const LABEL={play:"PLAY",attack:"ATTACK",action:"ACTION",reaction:"REACTION",bonded:"BONDED",while_named:"WHILE NAMED",becomes_named:"BECOMES NAMED",trigger:"TRIGGER",continuous:"CONTINUOUS",hidden:"REVEAL",front:"FRONT",middle:"MIDDLE",rear:"REAR",exhausted:"EXHAUSTED",tireless:"TIRELESS",mobile:"MOBILE"};
const LIVE=new Set(["action","attack","reaction","bonded","while_named","continuous","front","middle","rear","exhausted","tireless","mobile"]);
// Card rules are ordinary prose. Inline pictograms only help the reader
// identify OTHER cards by their card family or named classification.
// Structural icons live in the exposed edge, classifications and Command
// seal, not in rule prose or timing/role headings.
//
// One icon per distinct referent, at most two per effect. Outcomes (Strength,
// Command, markers, Shaken, Guarded), actions, locations and card timings are
// written as words, without emoji/rebus-style icon repetition.
const INLINE_CARD_TYPES=["Force","Bond","Name","Hero","Tactic","Order","Stratagem","Narrative"];
const INLINE_CLASSES=[
  "Human","Ship","Stronghold","Archer","Guard","Scout","Rider",
  "Skirmisher","Raider","Healer","Steward","Seer","King","Captain",
  "Builder","Veteran","Heir","Spearman"
];
const MAX_REFERENT_ICONS=2;
const REFERENTS=new Map();
for(const term of INLINE_CARD_TYPES){
  REFERENTS.set(term.toLowerCase(),{symbol:term.toLowerCase(),kind:"type"});
  REFERENTS.set((term+"s").toLowerCase(),{symbol:term.toLowerCase(),kind:"type"});
}
for(const term of INLINE_CLASSES){
  REFERENTS.set(term.toLowerCase(),{symbol:term.toLowerCase(),kind:"class"});
  REFERENTS.set((term+"s").toLowerCase(),{symbol:term.toLowerCase(),kind:"class"});
}
const REFERENT_RE=new RegExp("\\b("+[...REFERENTS.keys()].sort((a,b)=>b.length-a.length).join("|")+")\\b","gi");
function accessibleInlineGlyph(markup){
  return String(markup||"")
    .replace(/<title>.*?<\/title>/g,"")
    .replace(/\srole="img"/g,"")
    .replace(/\saria-label="[^"]*"/g,"")
    .replace(/\s(?:alt|title)="[^"]*"/g,"")
    .replace(/<(svg|img)\b/,'<$1 aria-hidden="true" focusable="false"');
}
function formatRuleText(value,{icons=true}={}){
  const source=String(value??"");
  if(!icons)return esc(source);
  let result="",cursor=0,used=new Set();
  for(const match of source.matchAll(REFERENT_RE)){
    const index=match.index??0,token=match[0];
    const info=REFERENTS.get(token.toLowerCase());
    if(!info||used.size>=MAX_REFERENT_ICONS||used.has(info.symbol))continue;
    // "This Force" and "this Name" describe the current layer, not a
    // separate card being referenced by an effect.
    if(/\b(?:this|its|that)\s*$/i.test(source.slice(Math.max(0,index-14),index)))continue;
    const markup=info.kind==="type"?typeGlyph(info.symbol):classGlyph(info.symbol);
    result+=esc(source.slice(cursor,index));
    result+='<span class="inline-rule-ref inline-card-ref" title="'+esc(token)+'">'+accessibleInlineGlyph(markup)+
      '<span class="rule-term">'+esc(token)+'</span></span>';
    used.add(info.symbol);
    cursor=index+token.length;
  }
  return result+esc(source.slice(cursor));
}
const H=()=>window.CardSymbols;
const signed=value=>(Number(value)>=0?"+":"")+String(value??0);
const modeEffects=(card,mode)=>card?.modes?.[mode]?.effects||[];
const effects=card=>card.type==="hero"?[...modeEffects(card,"force"),...modeEffects(card,"name")]:(card.effects||[]);
const typeGlyph=type=>H()?.symbol(type)||"";
const classGlyph=name=>H()?.classification(name)||"";
const timingGlyph=name=>H()?.timing(name)||"";
const utilityGlyph=name=>H()?.utility(name)||"";
const rowGlyph=name=>H()?.row(name)||"";
const effectTimingGlyph=name=>["front","middle","rear"].includes(name)?rowGlyph(name):["tireless","mobile"].includes(name)?utilityGlyph("move"):name==="exhausted"?utilityGlyph("marker"):timingGlyph(name);
const isFormationCard=card=>["force","bond","name","hero"].includes(card.type);

function statGroup(card){
  if(card.type==="hero")return '<div class="hero-stats" aria-label="Hero Force '+esc(card.force_strength)+', Name '+esc(signed(card.name_strength_modifier))+'"><span class="hero-stat hero-force-stat">'+typeGlyph("force")+'<b>'+esc(card.force_strength)+'</b></span><span class="hero-stat hero-name-stat">'+typeGlyph("name")+'<b>'+esc(signed(card.name_strength_modifier))+'</b></span></div>';
  const value=card.type==="force"?card.strength:["bond","name"].includes(card.type)?signed(card.strength_modifier):"";
  return '<div class="edge-stats" aria-label="'+esc(TYPE[card.type]||card.type)+' Strength '+esc(value)+'"><span class="type-mark">'+typeGlyph(card.type)+'</span><span class="strength-mark"><b>'+esc(value)+'</b></span></div>';
}
function classificationIcons(card){return(card.classes||[]).map(name=>'<span class="class-sigil" data-class="'+esc(name)+'" data-group="'+esc(H()?.group(name)||"role")+'" title="'+esc(titleCase(name))+'">'+classGlyph(name)+'</span>').join("")}
function decorativeGlyph(html){
  return String(html||"")
    .replace(/<title>.*?<\/title>/g,"")
    .replace(/ role="img"/g,' aria-hidden="true" focusable="false"')
    .replace(/ aria-label="[^"]*"/g,"");
}
function classificationLine(card){
  // Only classifications the card actually has belong in its footer.
  // "references" are engine metadata, never an "Involves" display row.
  const own=card.classes||[];
  const typeItem='<span class="class-body-item class-type-item">'+decorativeGlyph(typeGlyph(card.type))+'<span>'+esc(TYPE[card.type]||titleCase(card.type))+'</span></span>';
  const classItems=own.map(name=>'<span class="class-body-item">'+decorativeGlyph(classGlyph(name))+'<span>'+esc(titleCase(name))+'</span></span>');
  const suffix=classItems.length?'<span class="class-separator">·</span>'+classItems.join('<span class="class-separator">·</span>'):"";
  return '<div class="class-line">'+typeItem+suffix+'</div>';
}
function liveEffects(card){
  const effects=card.type==="hero"?modeEffects(card,"force"):["force","bond"].includes(card.type)?(card.effects||[]):[];
  const result=[];
  for(const effect of effects.filter(e=>LIVE.has(e.timing))){
    // A card with two permissions in the same phase needs one prompt,
    // not two identical instructions to check the rule text.
    const shared=effect.edge_cue&&!effect.limit&&result.find(e=>e.edge_cue===effect.edge_cue&&!e.limit);
    if(shared){shared.text+=" / "+effect.text;continue;}
    result.push({...effect});
  }
  return result;
}
function exposedText(effect){return String(effect.exposed||effect.text||"").replace(/^ACTION\s+1\/B\s*·\s*/i,"").replace(/^REACTION\s+1\/B\s*·\s*/i,"").replace(/^BONDED\s*·\s*/i,"").replace(/^NAMED\s*·\s*/i,"").trim()}
function liveMarkup(effect){
  const limited=effect.limit==="once_per_battle";
  const timing=LABEL[effect.timing]||effect.timing;
  // The exposed strip is a visual index to the card's rules. Do not repeat
  // outcomes, costs or a miniature version of the effect here.
  if(effect.edge_cue){
    return '<span class="edge-mechanic edge-cue" data-timing="'+esc(effect.timing)+'" title="'+esc(effect.text)+'" aria-label="'+esc("Check rule on "+effect.edge_cue.toLowerCase()+(limited?" (once per Battle)":"")+": "+effect.text)+'">'+
      '<span class="edge-cue-text">'+esc(effect.edge_cue)+'</span>'+
      (limited?'<span class="use-socket" title="Once per Battle: cover after use" aria-hidden="true"></span>':"")+'</span>';
  }
  const reminder=exposedText(effect);
  const redundant=effect.timing==="continuous"||reminder.toUpperCase().startsWith(timing);
  return '<span class="edge-mechanic" data-timing="'+esc(effect.timing)+'" data-reminder-has-timing="'+redundant+'" aria-label="'+esc(timing+(limited?" once per Battle":"")+": "+effect.text)+'"><span class="edge-timing-word">'+esc(timing)+'</span>'+(limited?'<span class="use-socket" title="Once per Battle: cover after use" aria-hidden="true"></span>':"")+'<span class="edge-live-text">'+esc(reminder)+'</span></span>';
}
function placementRows(card){
  return Array.isArray(card.allowed_rows)?card.allowed_rows:(card.placement?[card.placement]:[]);
}
const placementName=row=>row==="front"?"Frontline":titleCase(row);
function placementMarkup(card){
  const rows=placementRows(card);
  if(!rows.length)return"";
  const label=rows.map(placementName).join(" / ")+" only";
  return '<span class="edge-placement" title="'+esc(label)+'">'+rowGlyph(rows)+'</span>';
}
function placementRuleText(card){
  const rows=placementRows(card);
  if(!rows.length)return"";
  const labels=rows.map(placementName);
  const joined=labels.length===1?labels[0]:labels.slice(0,-1).join(", ")+" or "+labels.at(-1);
  return "This Force may only occupy the "+joined+" row"+(labels.length>1?"s":"")+".";
}
function placementRuleBlock(card){
  const rows=placementRows(card),text=placementRuleText(card);
  if(!text)return"";
  return '<section class="placement-rule"><div class="effect-head"><span class="placement-rule-label">PLACEMENT</span></div><div class="placement-rule-text">'+formatRuleText(text,{icons:false})+'</div></section>';
}
function stackEdge(card){
  const reminders=liveEffects(card);
  return '<header class="stack-edge" data-edge-layout="three-zone">'+
    '<div class="edge-zone edge-zone-left">'+statGroup(card)+'</div>'+
    '<div class="edge-zone edge-zone-middle edge-identity" aria-label="'+esc((card.classes||[]).map(titleCase).join(", "))+'">'+classificationIcons(card)+placementMarkup(card)+'</div>'+
    '<div class="edge-zone edge-zone-right edge-live-group">'+reminders.map(liveMarkup).join("")+'</div>'+
  '</header>';
}
function eventCrown(card){
  return '<header class="event-crown" data-edge-layout="three-zone">'+
    '<div class="edge-zone edge-zone-left"><span class="event-sigil">'+typeGlyph(card.type)+'</span></div>'+
    '<div class="edge-zone edge-zone-middle"><span class="event-family">'+esc(TYPE[card.type])+'</span></div>'+
    '<div class="edge-zone edge-zone-right"><span class="event-status">'+esc(statusLine(card))+'</span></div>'+
  '</header>';
}
function mechanicReminder(effect){
  const text=String(effect?.text||"");
  const notes=[];
  const add=(key,note)=>{if(!notes.some(item=>item.key===key))notes.push({key,note})};
  let match;

  match=text.match(/\bSUPPORT\s+\+(\d+)\b/i);
  if(match)add("support","The friendly Formation directly ahead gets +"+match[1]+" Strength.");

  if(/\bSUPPLY\b/i.test(text)){
    add("supply","Bonds played onto the friendly Formation directly ahead cost 1 less Command (minimum 0); Names cost 1 less (minimum 1).");
  }

  match=text.match(/\bRESERVE\s+\+(\d+)\b/i);
  if(match)add("reserve","This Formation gets +"+match[1]+" Strength while the friendly Formation directly ahead is OUTMATCHED (the opposing Formation in the same rank has greater current Strength).");

  match=text.match(/\bPRESS\s+\+(\d+)\b/i);
  if(match)add("press","This Formation gets +"+match[1]+" Strength while at least one opposing Force in this Front is Exhausted.");

  match=text.match(/\bSTEAL\s+(\d+)\s+COMMAND\b/i);
  if(match)add("steal","The opponent loses up to "+match[1]+" Command, never below 1; regain exactly the amount lost.");

  if(/\bTIRELESS\b/.test(text)){
    add("tireless","TIRELESS means that Force may Maneuver while Exhausted; all other Maneuver requirements still apply.");
  }

  if(/\bMOBILE\b/.test(text)){
    add("mobile","MOBILE means that Force may Maneuver while Unnamed; all other Maneuver requirements still apply.");
  }

  if(/\bMOVE\s+\d+\b/.test(text)){
    add("move","MOVE is a card effect: move orthogonally to an adjacent legal empty position; it costs no Maneuver Command and ignores Named/Exhaustion requirements.");
  }

  if(/\bSWAP\b/.test(text)){
    add("swap","SWAP exchanges the complete contents of the two specified friendly positions; it costs no Maneuver Command and Exhaustion does not stop it.");
  }

  return notes.map(item=>item.note).join(" ");
}
function effectBlock(effect,options={}){
  const kind=["attack","bonded","while_named","continuous","front","middle","rear","exhausted","tireless","mobile"].includes(effect.timing)?"state":["becomes_named","trigger","reaction","hidden"].includes(effect.timing)?"event":"operation";
  const reminder=mechanicReminder(effect);
  return '<section class="effect-block timing-'+kind+'"><div class="effect-head"><span class="effect-label">'+esc(LABEL[effect.timing]||effect.timing)+'</span>'+(effect.limit==="once_per_battle"?'<span class="effect-use"><span class="use-socket"></span><em>once per Battle</em></span>':"")+'</div> <div class="effect-text">'+formatRuleText(effect.text)+'</div>'+(reminder?'<div class="effect-reminder">'+formatRuleText(reminder,{icons:false})+'</div>':"")+'</section>';
}
function heroModeHeading(mode){
  // The Command seal contains the two vertically stacked mode prices.
  // Upper = Force, lower = Name; details appear in the rulebook.
  return '<h4 class="mode-heading"><span class="mode-heading-core"><span>'+esc(titleCase(mode))+'</span></span></h4>';
}
function rules(card){
  const placement=placementRuleBlock(card);
  if(card.type==="hero")return placement+'<section class="hero-rule-mode" data-mode="force">'+heroModeHeading("force")+modeEffects(card,"force").map(effectBlock).join("")+'</section><section class="hero-rule-mode" data-mode="name">'+heroModeHeading("name")+modeEffects(card,"name").map(effectBlock).join("")+'</section>';
  return placement+effects(card).map(effect=>effectBlock(effect)).join("");
}
function statusLine(card){const bits=[];if(card.duration==="this_battle"&&card.type!=="narrative")bits.push("This Battle");return bits.join(" · ")}
function costSeal(card){
  if(card.type==="hero"){
    const f=card.hero_force_command_cost,n=card.hero_name_command_cost;
    // Numerals share the ordinary card seal's centre; no mode icons.
    return '<span class="cost-gem cost-gem-hero" aria-label="Hero Command: top '+esc(f)+' Force, bottom '+esc(n)+' Name">'+
      '<span class="hero-cost-stack" aria-hidden="true">'+
        '<span class="hero-cost-part hero-cost-force"><b>'+esc(f)+'</b></span>'+
        '<span class="hero-cost-part hero-cost-name"><b>'+esc(n)+'</b></span>'+
      '</span></span>';
  }
  return '<span class="cost-gem" aria-label="Command cost '+esc(card.command_cost)+'"><b>'+esc(card.command_cost)+'</b></span>';
}

function densityClass(card){
  const es=effects(card),placement=placementRuleText(card);
  const chars=placement.length+es.reduce((n,e)=>n+(e.text||"").length+mechanicReminder(e).length,0);
  const blocks=es.length+(placement?1:0);
  if(card.type==="hero"){
    if(chars>180||(blocks>=3&&chars>120))return " very-dense";
    if(blocks>=3||chars>100)return " dense";
  }
  return chars>250?" very-dense":chars>170||blocks>1?" dense":chars<95?" sparse":"";
}
function artFocus(value,fallback){
  const text=String(value??"").trim();
  if(/^\d+(?:\.\d+)?%$/.test(text)&&parseFloat(text)<=100)return text;
  return fallback;
}
function cardArtURL(id,printArt=false){
  const base=printArt?"art/cards-print/":"art/cards/";
  const ext=printArt?".webp":".png";
  return base+encodeURIComponent(String(id))+ext+"?v="+encodeURIComponent(VERSION);
}
function artStyle(card,options={}){
  const x=artFocus(card.art_focus_x,"50%");
  // Preserve the top of every illustration; the bottom may be cropped by cover.
  const y=artFocus(card.art_focus_y,"0%");
  const artURL=cardArtURL(card.art_id||card.id,Boolean(options.printArt));
  return ' style="--card-art:url('+artURL+');--art-x:'+esc(x)+';--art-y:'+esc(y)+'"';
}
function cardArticle(card,extra="",options={}){
  const density=densityClass(card),titleDensity=card.title.length>=32?" title-very-long":card.title.length>=25?" title-long":"",heroMode=options.heroMode==="name"?"name":"force";
  const footerMark=typeGlyph(card.type);
  return '<article class="physical-card card-'+esc(card.type)+density+titleDensity+(extra?" "+esc(extra):"")+'" data-card-id="'+esc(card.id)+'"'+(card.type==="hero"?' data-hero-mode="'+heroMode+'"':"")+artStyle(card,options)+'>'+(isFormationCard(card)?stackEdge(card):eventCrown(card))+'<div class="card-body"><div class="motif-field" aria-hidden="true"></div><div class="card-identity"><h3 class="card-title">'+esc(card.title)+'</h3></div><div class="rules">'+rules(card)+'</div></div><footer class="card-footer">'+(card.unique?'<span class="footer-unique">Unique</span>':"")+classificationLine(card)+'<span class="footer-mark">'+footerMark+'</span><span class="footer-version">v'+esc(PRINT_VERSION)+'</span><span class="footer-id">'+esc(card.id)+'</span>'+costSeal(card)+'</footer></article>';
}
const STACK_CASES={
 "force-alone":{title:"Force alone",state:"Formation · Unbonded",ids:["the-crow-archers"]},
 "force-bond":{title:"Force + Bond",state:"Bonded",ids:["the-crow-archers","had-been-ordered-forward"]},
 "force-name":{title:"Force + Name",state:"Formation · not Named",ids:["the-red-shields","corin-of-the-high-wall"]},
 named:{title:"Force + Bond + Name",state:"Named · also Bonded",ids:["the-old-guard","blocked-the-road-for","mara"]},
 "hero-force":{title:"Hero as Force",state:"Named · also Bonded",ids:["serai-queen-of-crows","followed","namar"],heroMode:"force"},
 "hero-name":{title:"Hero as Name",state:"Named · also Bonded",ids:["the-house-of-reed","carried-messages-for","alda-keeper-of-the-ford"],heroMode:"name"}
};
function stackMarkup(cards,caseName){const entry=STACK_CASES[caseName];if(!entry)return"";return '<div class="stack-demo" data-stack-case="'+esc(caseName)+'" data-layers="'+entry.ids.length+'">'+entry.ids.map((id,index)=>{const card=cards.find(c=>c.id===id);return card?'<div class="stack-card" data-stack-layer="'+index+'">'+cardArticle(card,"",{heroMode:entry.heroMode})+'</div>':""}).join("")+'</div>'}
function inspect(root=document){
 const failures=[],mm=96/25.4;
 root.querySelectorAll(".physical-card").forEach(card=>{
  const box=card.getBoundingClientRect();if(!box.width||!box.height)return;
  const problems=[],edge=card.querySelector(".stack-edge");
  for(const node of card.querySelectorAll(".stack-edge,.edge-identity,.edge-live-group,.card-title,.motif-field,.rules,.card-footer"))if(node.scrollWidth>node.clientWidth+1||node.scrollHeight>node.clientHeight+1)problems.push((node.classList[0]||"node")+"-overflow");
  if(edge)for(const node of edge.querySelectorAll(".edge-stats,.hero-stats,.edge-identity,.edge-live-group"))if(node.getBoundingClientRect().bottom>box.top+10.5*mm+.5)problems.push("covered-edge");
  const art=card.querySelector(".motif-field"),rules=card.querySelector(".rules"),footer=card.querySelector(".card-footer");
  if(art&&rules&&rules.getBoundingClientRect().top<art.getBoundingClientRect().bottom-.5)problems.push("art-rules-overlap");
  if(rules&&footer&&rules.getBoundingClientRect().bottom>footer.getBoundingClientRect().top+.5)problems.push("rules-footer-overlap");
  if(art?.querySelector("svg,img"))problems.push("art-overlay");
  // Inspect actual numeral boxes after CSS positioning adjustments.
  const seal=card.querySelector(".cost-gem-hero");
  if(seal){
    const bound=seal.getBoundingClientRect();
    const parts=[...seal.querySelectorAll(".hero-cost-part")];
    const pairBounds=parts.map(part=>{
      const ink=[...part.querySelectorAll("b")].map(node=>node.getBoundingClientRect());
      for(const rect of ink){
        if(rect.left<bound.left+1||rect.right>bound.right-1||
           rect.top<bound.top+1||rect.bottom>bound.bottom-1)
          problems.push("hero-price-outside-seal");
      }
      return {
        left:Math.min(...ink.map(r=>r.left)),
        right:Math.max(...ink.map(r=>r.right)),
        top:Math.min(...ink.map(r=>r.top)),
        bottom:Math.max(...ink.map(r=>r.bottom))
      };
    });
    if(pairBounds.length===2){
      const [a,b]=pairBounds;
      if(Math.min(a.right,b.right)>Math.max(a.left,b.left)+1&&
         Math.min(a.bottom,b.bottom)>Math.max(a.top,b.top)+1)
        problems.push("hero-price-overlap");
    }
  }
  card.classList.toggle("layout-overflow",problems.length>0);if(problems.length)failures.push({id:card.dataset.cardId,problems:[...new Set(problems)]});
 });return failures;
}
window.PhysicalCards={cardArticle,stackMarkup,inspect,cardArtURL};
})();
