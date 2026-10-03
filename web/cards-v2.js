(() => {
"use strict";
const scriptURL=document.currentScript?.src||"";
const VERSION=(()=>{try{return new URL(scriptURL,window.location.href).searchParams.get("v")||"dev"}catch(_){return"dev"}})();
const esc=v=>String(v??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;");
const titleCase=v=>String(v??"").split(/[-_ ]+/).filter(Boolean).map(p=>p[0].toUpperCase()+p.slice(1)).join(" ");
const TYPE={force:"Force",bond:"Bond",name:"Name",hero:"Hero",tactic:"Tactic",stratagem:"Stratagem",narrative:"Narrative"};
const LABEL={play:"PLAY",once_per_battle:"1/BATTLE",bonded:"BONDED",while_named:"WHILE NAMED",becomes_named:"BECOMES NAMED",action:"ACTION",trigger:"TRIGGER",continuous:"CONTINUOUS",hidden:"HIDDEN"};
function modeEffects(card,mode){const v=card?.modes?.[mode];return Array.isArray(v?.effects)?v.effects:[]}
function effects(card){return card?.type==="hero"?[...modeEffects(card,"force"),...modeEffects(card,"name")]:Array.isArray(card?.effects)?card.effects:[]}
function symbol(type){const s={
force:'<svg viewBox="0 0 24 24"><path d="M5 3h14v7c0 5-3 8.6-7 11-4-2.4-7-6-7-11z"/><path d="M8 7h8M12 5v10"/></svg>',
bond:'<svg viewBox="0 0 24 24"><path d="M8.4 8.3l-2.1 2.1a4 4 0 005.7 5.7l2.1-2.1"/><path d="M15.6 15.7l2.1-2.1a4 4 0 00-5.7-5.7L9.9 10"/><path d="M9 15l6-6"/></svg>',
name:'<svg viewBox="0 0 24 24"><path d="M6 21V3"/><path d="M7 4h11l-3 4 3 4H7"/></svg>',
hero:'<svg viewBox="0 0 24 24"><path d="M12 2l2.7 6.4 6.8.6-5.2 4.5 1.6 6.7-5.9-3.5-5.9 3.5 1.6-6.7L2.5 9l6.8-.6z"/></svg>',
tactic:'<svg viewBox="0 0 24 24"><path d="M13 2L5 14h6l-1 8 9-13h-6z"/></svg>',
stratagem:'<svg viewBox="0 0 24 24"><path d="M2 12s4-6 10-6 10 6 10 6-4 6-10 6S2 12 2 12z"/><circle cx="12" cy="12" r="2.5"/></svg>',
narrative:'<svg viewBox="0 0 24 24"><path d="M5 4h11a3 3 0 013 3v13H8a3 3 0 01-3-3z"/><path d="M8 4v16M11 8h5M11 12h5"/></svg>'};return s[type]||s.force}
function statMarkup(c){
 if(c.type==="hero")return '<span class="stat-cluster"><span class="stat-crest stat-force"><small>F</small><b>'+esc(c.force_strength)+'</b></span><span class="stat-crest stat-name"><small>N</small><b>+'+esc(c.name_strength_modifier)+'</b></span></span>';
 if(c.type==="force")return '<span class="stat-cluster"><span class="stat-crest stat-force"><b>'+esc(c.strength)+'</b></span></span>';
 if(c.type==="bond"||c.type==="name"){const n=Number(c.strength_modifier||0);return '<span class="stat-cluster"><span class="stat-crest stat-mod"><b>'+(n>=0?"+":"")+esc(n)+'</b></span></span>'}
 return '<span class="stat-cluster"></span>';
}
function liveReminder(c){const es=c.type==="hero"?modeEffects(c,"force"):(c.effects||[]);return es.filter(e=>["once_per_battle","bonded","while_named"].includes(e.timing)&&e.exposed).map(e=>'<em>'+esc(LABEL[e.timing]||e.timing)+'</em>'+esc(e.exposed.replace(/^(1\/B|BONDED|NAMED)\s*·?\s*/i,""))).join("<br>")}
function classes(c){return(c.classes?.length?c.classes:(c.references||[])).map(titleCase).join(" · ")}
function memoryNote(e){const m=new Set(e.memory||[]),out=[];if(m.has("used_marker"))out.push("mark used");if(m.has("effect_marker"))out.push("effect marker");if(m.has("suppression_marker"))out.push("suppression marker");if(m.has("front_marker"))out.push("Front marker");return out.join(" · ")}
function block(e){const note=memoryNote(e),limit=e.limit==="once_per_battle"?'<span class="effect-limit">once per Battle</span>':"";return '<div class="effect-block"><div class="effect-head"><span class="effect-label">'+esc(LABEL[e.timing]||e.timing)+'</span>'+limit+'</div><div class="effect-text">'+esc(e.text)+'</div>'+(note?'<div class="effect-note">'+esc(note)+'</div>':"")+'</div>'}
function rules(c){
 if(c.type==="hero")return '<div class="mode-heading">As Force</div>'+modeEffects(c,"force").map(block).join("")+'<div class="mode-heading name-mode">As Name</div>'+modeEffects(c,"name").map(block).join("");
 const es=effects(c);return(c.type==="stratagem"?'<span class="hidden-ribbon">Played face-down</span>':"")+(es.length?es.map(block).join(""):'<div class="empty-rules">No special rules.</div>');
}
function motif(c){let h=0;for(const ch of c.id)h=((h*33)^ch.charCodeAt(0))>>>0;return h%6}
function density(c){const n=(c.title||"").length+effects(c).reduce((s,e)=>s+(e.text||"").length,0);return n>370?" card-very-dense":n>245?" card-dense":""}
function titleDensity(c){const n=(c.title||"").length;return n>33?" title-very-long":n>25?" title-long":""}
function cardArticle(c,extra=""){
 const live=liveReminder(c),cls=classes(c),m=motif(c);
 return '<article class="v2-card card-'+esc(c.type)+density(c)+titleDensity(c)+(extra?" "+extra:"")+'" data-card-id="'+esc(c.id)+'">'+
 '<div class="stack-edge"><span class="type-sigil">'+symbol(c.type)+'</span>'+statMarkup(c)+'<div class="edge-meta"><div class="edge-type">'+esc(TYPE[c.type]||c.type)+(c.unique?" · Unique":"")+'</div><div class="edge-classes">'+esc(cls)+'</div></div><div class="edge-live">'+(c.placement?'<em>'+esc(c.placement.toUpperCase())+' ONLY</em>':"")+live+'</div></div>'+
 '<div class="card-body"><h3 class="card-title">'+esc(c.title)+'</h3><div class="card-byline">'+esc(cls)+'</div><div class="motif-field motif-'+m+'"><span class="motif-sigil">'+symbol(c.type)+'</span><span class="motif-word">'+esc(TYPE[c.type]||c.type)+'</span></div><div class="rules">'+rules(c)+'</div></div>'+
 '<footer class="card-footer"><span class="footer-id">'+esc(c.id)+'</span><span class="cost-gem" aria-label="Command cost '+esc(c.command_cost)+'">'+esc(c.command_cost)+'</span></footer></article>';
}
function cardMarkup(c,extra="",copies=0){return '<div class="card-wrap">'+(copies>1?'<span class="copy-chip">×'+copies+'</span>':"")+cardArticle(c,extra)+'</div>'}
function norm(c){return[c.title,c.type,...(c.classes||[]),...(c.references||[]),...(c.design_tags||[]),c.text].join(" ").toLowerCase()}
function deckMap(deck){return new Map((deck?.cards||[]).map(x=>[x.id,x.copies]))}
function render(cards,decks){
 const type=document.getElementById("type-filter").value,cl=document.getElementById("class-filter").value,mech=document.getElementById("mechanic-filter").value,deckId=document.getElementById("deck-filter").value,q=document.getElementById("search").value.trim().toLowerCase(),deck=decks.find(d=>d.id===deckId),copies=deckMap(deck);
 const filtered=cards.filter(c=>(type==="all"||c.type===type)&&(cl==="all"||(c.classes||[]).includes(cl)||(c.references||[]).includes(cl))&&(mech==="all"||(c.design_tags||[]).includes(mech))&&(deckId==="all"||copies.has(c.id))&&(!q||norm(c).includes(q)));
 document.getElementById("count").textContent=filtered.length+" / "+cards.length;
 document.getElementById("cards").innerHTML=filtered.map(c=>cardMarkup(c,"",copies.get(c.id)||0)).join("");
}
function fillFilters(cards,decks){
 const classes=[...new Set(cards.flatMap(c=>[...(c.classes||[]),...(c.references||[])]))].sort(),tags=[...new Set(cards.flatMap(c=>c.design_tags||[]))].sort();
 document.getElementById("class-filter").innerHTML='<option value="all">All classes</option>'+classes.map(x=>'<option value="'+esc(x)+'">'+esc(titleCase(x))+'</option>').join("");
 document.getElementById("mechanic-filter").innerHTML='<option value="all">All mechanics</option>'+tags.map(x=>'<option value="'+esc(x)+'">'+esc(titleCase(x))+'</option>').join("");
 document.getElementById("deck-filter").innerHTML='<option value="all">All cards</option>'+decks.map(d=>'<option value="'+esc(d.id)+'">'+esc(d.title)+'</option>').join("");
}
function renderStack(cards){const ids=["the-ash-bowmen","watched-the-skies-for","corin-of-the-high-wall"],extra=["stack-force","stack-bond","stack-name"];document.getElementById("stack-demo").innerHTML=ids.map((id,i)=>{const c=cards.find(x=>x.id===id);return c?cardArticle(c,extra[i]):""}).join("")}
async function main(){
 const [cr,dr]=await Promise.all([fetch("data/cards-v2-redesign.json?v="+encodeURIComponent(VERSION),{cache:"no-cache"}),fetch("data/v2-playtest-decks.json?v="+encodeURIComponent(VERSION),{cache:"no-cache"})]);
 if(!cr.ok)throw new Error("Could not load V2 card data");if(!dr.ok)throw new Error("Could not load V2 playtest decks");
 const cards=(await cr.json()).cards||[],decks=(await dr.json()).decks||[];fillFilters(cards,decks);renderStack(cards);render(cards,decks);
 for(const id of["type-filter","class-filter","mechanic-filter","deck-filter"])document.getElementById(id).addEventListener("change",()=>render(cards,decks));
 document.getElementById("search").addEventListener("input",()=>render(cards,decks));
}
main().catch(err=>{document.getElementById("cards").textContent=err.message});
})();