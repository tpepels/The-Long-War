(() => {
"use strict";
const scriptURL=typeof document==="undefined"?"":document.currentScript?.src||"";
const VERSION=(()=>{try{return new URL(scriptURL,window.location.href).searchParams.get("v")||"dev"}catch(_){return"dev"}})();
const PRINT_VERSION=typeof document==="undefined"||typeof document.querySelector!=="function"?"dev":document.querySelector('meta[name="lw-build-version"]')?.getAttribute("content")||"dev";
const esc=value=>String(value??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;");
const titleCase=value=>String(value??"").split(/[-_ ]+/).filter(Boolean).map(part=>part[0].toUpperCase()+part.slice(1)).join(" ");
const TYPE={force:"Force",bond:"Bond",name:"Name",hero:"Hero",tactic:"Tactic",order:"Order",stratagem:"Stratagem",narrative:"Narrative"};
const LABEL={play:"PLAY",action:"ACTION",reaction:"REACTION",bonded:"BONDED",while_named:"WHILE NAMED",becomes_named:"BECOMES NAMED",trigger:"TRIGGER",continuous:"CONTINUOUS",hidden:"REVEAL",front:"FRONT",middle:"MIDDLE",rear:"REAR",exhausted:"EXHAUSTED",tireless:"TIRELESS",mobile:"MOBILE"};
const LIVE=new Set(["action","reaction","bonded","while_named","continuous","front","middle","rear","exhausted","tireless","mobile"]);
const RULE_TERMS=[
  "Named Formation","Bonded Formation","Unbonded Formation","Formation",
  "Force","Bond","Name","Hero","Tactic","Order","Stratagem","Narrative",
  "Command","Strength","Action","Reaction","Battle","Front","Maneuver","Pass","Support","Supply","Outmatched","Reserve","Press","Steal","Tireless","Mobile","Unnamed","Exhausted","Exhaustion","Exhaustion token",
  "Front row","Middle row","Rear row","Tax marker","temporary negative marker",
  "prepared Bond","prepared Name"
];
const CLASSIFICATION_TERMS=[
  "Human","Archer","Builder","Captain","Guard","Healer","Heir","King","Raider",
  "Rider","Scout","Seer","Ship","Skirmisher","Spearman","Steward","Stronghold","Veteran"
];
const REFERENT_TERMS=[
  ...CLASSIFICATION_TERMS,
  "discard pile","deck","hand","card","marker","turn"
];
const pluralize=term=>term.endsWith("s")?term:term+"s";
const RULE_TERM_SET=new Set(RULE_TERMS.flatMap(term=>[term,pluralize(term)]).map(term=>term.toLowerCase()));
const REFERENT_TERM_SET=new Set(REFERENT_TERMS.flatMap(term=>[term,pluralize(term)]).map(term=>term.toLowerCase()));
const CLASSIFICATION_TERM_MAP=new Map(CLASSIFICATION_TERMS.flatMap(term=>[
  [term.toLowerCase(),term.toLowerCase()],
  [pluralize(term).toLowerCase(),term.toLowerCase()]
]));
const EMPHASIS_TERMS=[...new Set([...RULE_TERM_SET,...REFERENT_TERM_SET])]
  .sort((a,b)=>b.length-a.length)
  .map(term=>term.replace(/[.*+?^$()|[\]\\{}]/g,match=>"\\\\"+match));
const EMPHASIS_RE=new RegExp("\\b("+EMPHASIS_TERMS.join("|")+")\\b","gi");
function formatRuleText(value,options={}){
  const source=String(value??"");
  const inlineClassIcons=Boolean(options.inlineClassIcons);
  let html="",cursor=0;
  for(const match of source.matchAll(EMPHASIS_RE)){
    const index=match.index??0,token=match[0],key=token.toLowerCase();
    html+=esc(source.slice(cursor,index));
    const className=CLASSIFICATION_TERM_MAP.get(key);
    if(inlineClassIcons&&className){
      const icon=classGlyph(className)
        .replace(/<title>.*?<\/title>/,"")
        .replace("<svg ","<svg aria-hidden=\"true\" focusable=\"false\" ");
      html+='<span class="inline-class-ref" title="'+esc(titleCase(className))+'">'+icon+'<span>'+esc(token)+'</span></span>';
    } else if(RULE_TERM_SET.has(key))html+='<strong class="rule-term">'+esc(token)+'</strong>';
    else html+='<em class="rule-referent">'+esc(token)+'</em>';
    cursor=index+token.length;
  }
  return html+esc(source.slice(cursor));
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
function classificationLine(card){
  const own=card.classes||[];
  const refs=card.type==="tactic"?[]:(card.references||[]);
  const values=own.length?own:refs;
  const typeItem='<span class="class-body-item class-type-item">'+typeGlyph(card.type)+'<span>'+esc(TYPE[card.type]||titleCase(card.type))+'</span></span>';
  const classItems=values.map(name=>'<span class="class-body-item">'+classGlyph(name)+'<span>'+esc(titleCase(name))+'</span></span>');
  const suffix=classItems.length?'<span class="class-separator">·</span>'+(own.length?"":'<span class="class-line-prefix">Involves</span>')+classItems.join('<span class="class-separator">·</span>'):"";
  return '<div class="class-line">'+typeItem+suffix+'</div>';
}
function liveEffects(card){if(card.type==="hero")return modeEffects(card,"force").filter(e=>LIVE.has(e.timing));return["force","bond"].includes(card.type)?(card.effects||[]).filter(e=>LIVE.has(e.timing)):[]}
function exposedText(effect){return String(effect.exposed||effect.text||"").replace(/^ACTION\s+1\/B\s*·\s*/i,"").replace(/^REACTION\s+1\/B\s*·\s*/i,"").replace(/^BONDED\s*·\s*/i,"").replace(/^NAMED\s*·\s*/i,"").trim()}
function liveMarkup(effect){
  const limited=effect.limit==="once_per_battle";
  const reminder=exposedText(effect);
  const timing=LABEL[effect.timing]||effect.timing;
  const redundant=effect.timing==="continuous"||reminder.toUpperCase().startsWith(timing);
  return '<span class="edge-mechanic" data-timing="'+esc(effect.timing)+'" data-reminder-has-timing="'+redundant+'" aria-label="'+esc(timing+(limited?" once per Battle":"")+": "+effect.text)+'"><span class="edge-timing-word">'+esc(timing)+'</span>'+(limited?'<span class="use-socket" title="Once per Battle: cover after use" aria-hidden="true"></span>':"")+'<span class="edge-live-text">'+esc(reminder)+'</span></span>';
}
function placementMarkup(card){
  const rows=Array.isArray(card.allowed_rows)?card.allowed_rows:(card.placement?[card.placement]:[]);
  if(!rows.length)return"";
  const label=rows.map(titleCase).join(" / ")+" only";
  return '<span class="edge-placement" title="'+esc(label)+'">'+rowGlyph(rows)+'</span>';
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
    add("tireless","This Force may Maneuver while Exhausted; all other Maneuver requirements still apply.");
  }

  if(/\bMOBILE\b/.test(text)){
    add("mobile","This Force may Maneuver while Unnamed; all other Maneuver requirements still apply.");
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
  const kind=["bonded","while_named","continuous","front","middle","rear","exhausted","tireless","mobile"].includes(effect.timing)?"state":["becomes_named","trigger","reaction","hidden"].includes(effect.timing)?"event":"operation";
  const reminder=mechanicReminder(effect);
  return '<section class="effect-block timing-'+kind+'"><div class="effect-head"><span class="effect-timing-icon" aria-hidden="true">'+effectTimingGlyph(effect.timing)+'</span><span class="effect-label">'+esc(LABEL[effect.timing]||effect.timing)+'</span>'+(effect.limit==="once_per_battle"?'<span class="effect-use"><span class="use-socket"></span><em>once per Battle</em></span>':"")+'</div> <div class="effect-text">'+formatRuleText(effect.text,options)+'</div>'+(reminder?'<div class="effect-reminder">'+formatRuleText(reminder)+'</div>':"")+'</section>';
}
function heroModeHeading(mode){
  return '<h4 class="mode-heading"><span class="mode-heading-core">'+typeGlyph(mode)+'<span>'+esc(titleCase(mode))+'</span></span></h4>';
}
function rules(card){
  if(card.type==="hero")return '<section class="hero-rule-mode" data-mode="force">'+heroModeHeading("force")+modeEffects(card,"force").map(effectBlock).join("")+'</section><section class="hero-rule-mode" data-mode="name">'+heroModeHeading("name")+modeEffects(card,"name").map(effectBlock).join("")+'</section>';
  return effects(card).map(effect=>effectBlock(effect,{inlineClassIcons:card.type==="tactic"})).join("");
}
function statusLine(card){const bits=[];if(card.duration==="this_battle"&&card.type!=="narrative")bits.push("This Battle");return bits.join(" · ")}
function costSeal(card){return '<span class="cost-gem" aria-label="Command cost '+esc(card.command_cost)+'"><b>'+esc(card.command_cost)+'</b></span>'}
function densityClass(card){
  const es=effects(card),chars=es.reduce((n,e)=>n+(e.text||"").length+mechanicReminder(e).length,0);
  if(card.type==="hero"){
    if(chars>180||(es.length>=3&&chars>120))return " very-dense";
    if(es.length>=3||chars>100)return " dense";
  }
  return chars>250?" very-dense":chars>170||es.length>1?" dense":chars<95?" sparse":"";
}
function artFocus(value,fallback){
  const text=String(value??"").trim();
  if(/^\d+(?:\.\d+)?%$/.test(text)&&parseFloat(text)<=100)return text;
  return fallback;
}
function artStyle(card,options={}){
  const x=artFocus(card.art_focus_x,"50%");
  const y=artFocus(card.art_focus_y,"50%");
  const artBase=options.printArt?"art/cards-print/":"art/cards/";
  const artExt=options.printArt?".webp":".png";
  const artURL=artBase+esc(card.id)+artExt+"?v="+encodeURIComponent(VERSION);
  return ' style="--card-art:url('+artURL+');--art-x:'+esc(x)+';--art-y:'+esc(y)+'"';
}
function cardArticle(card,extra="",options={}){
  const density=densityClass(card),titleDensity=card.title.length>=32?" title-very-long":card.title.length>=25?" title-long":"",heroMode=options.heroMode==="name"?"name":"force";
  const footerMark=typeGlyph(card.type);
  return '<article class="physical-card card-'+esc(card.type)+density+titleDensity+(extra?" "+esc(extra):"")+'" data-card-id="'+esc(card.id)+'"'+(card.type==="hero"?' data-hero-mode="'+heroMode+'"':"")+artStyle(card,options)+'>'+(isFormationCard(card)?stackEdge(card):eventCrown(card))+'<div class="card-body"><div class="motif-field" aria-hidden="true"></div><div class="card-identity"><h3 class="card-title">'+esc(card.title)+'</h3></div><div class="rules">'+rules(card)+'</div></div><footer class="card-footer">'+(card.unique?'<span class="footer-unique">Unique</span>':"")+classificationLine(card)+'<span class="footer-mark">'+footerMark+'</span><span class="footer-version">v'+esc(PRINT_VERSION)+'</span><span class="footer-id">'+esc(card.id)+'</span>'+costSeal(card)+'</footer></article>';
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
  card.classList.toggle("layout-overflow",problems.length>0);if(problems.length)failures.push({id:card.dataset.cardId,problems:[...new Set(problems)]});
 });return failures;
}
window.PhysicalCards={cardArticle,stackMarkup,inspect};
})();
