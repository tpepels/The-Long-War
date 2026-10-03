(() => {
"use strict";
const TYPE_LABELS={force:"Force",bond:"Bond",name:"Name",hero:"Hero",tactic:"Tactic",stratagem:"Stratagem",narrative:"Narrative"};
const LABELS={play:"PLAY",once_per_battle:"1/BATTLE",named:"NAMED",action:"ACTION",trigger:"TRIGGER",resolution:"RESOLUTION",continuous:"CONTINUOUS",hidden:"HIDDEN"};
const esc=v=>String(v??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;");
const titleCase=v=>String(v??"").split(/[-_ ]+/).filter(Boolean).map(p=>p[0].toUpperCase()+p.slice(1)).join(" ");
function symbol(type){
  const s={
    force:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 3h14v7c0 5-3 8.6-7 11-4-2.4-7-6-7-11z"/><path d="M8 7h8M12 5v10"/></svg>',
    bond:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8.4 8.3l-2.1 2.1a4 4 0 005.7 5.7l2.1-2.1"/><path d="M15.6 15.7l2.1-2.1a4 4 0 00-5.7-5.7L9.9 10"/><path d="M9 15l6-6"/></svg>',
    name:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 21V3"/><path d="M7 4h11l-3 4 3 4H7"/></svg>',
    hero:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2l2.7 6.4 6.8.6-5.2 4.5 1.6 6.7-5.9-3.5-5.9 3.5 1.6-6.7L2.5 9l6.8-.6z"/></svg>',
    tactic:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M13 2L5 14h6l-1 8 9-13h-6z"/></svg>',
    stratagem:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s4-6 10-6 10 6 10 6-4 6-10 6S2 12 2 12z"/><circle cx="12" cy="12" r="2.5"/></svg>',
    narrative:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 4h11a3 3 0 013 3v13H8a3 3 0 01-3-3z"/><path d="M8 4v16M11 8h5M11 12h5"/></svg>'
  }; return s[type]||s.force;
}
function allEffects(card){
  if(card.type==="hero") return [...card.modes.force.effects,...card.modes.name.effects];
  return card.effects||[];
}
function strength(card){
  if(card.type==="hero") return '<span class="stack-stat compact">F '+esc(card.force_strength)+'<br>N +'+esc(card.name_strength_modifier)+'</span>';
  if(card.type==="force") return '<span class="stack-stat">'+esc(card.strength)+'</span>';
  if(card.type==="bond"||card.type==="name") return '<span class="stack-stat">'+(card.strength_modifier>=0?"+":"")+esc(card.strength_modifier)+'</span>';
  return '<span class="stack-stat compact">'+esc(TYPE_LABELS[card.type][0])+'</span>';
}
function topReminder(card){
  if(card.type==="hero"){
    return (card.modes.force.effects||[]).filter(e=>e.exposed).map(e=>e.exposed).join(" · ");
  }
  return (card.effects||[]).filter(e=>e.exposed).map(e=>e.exposed).join(" · ");
}
function classes(card){
  const values=card.classes?.length?card.classes:(card.references||[]);
  return values.map(titleCase).join(" · ");
}
function memoryText(memory){
  const m=new Set(memory||[]); const out=[];
  if(m.has("used_marker")) out.push("mark used");
  if(m.has("effect_marker")) out.push("effect marker");
  if(m.has("suppression_marker")) out.push("suppression marker");
  if(m.has("front_marker")) out.push("Front marker");
  return out.join(" · ");
}
function block(e){
  const mem=memoryText(e.memory);
  const limit=e.limit==="once_per_battle"?'<span class="effect-limit">once per Battle</span>':"";
  return '<div class="effect-block"><div class="effect-head"><span class="effect-label">'+esc(LABELS[e.timing]||e.timing)+'</span>'+limit+'</div><div class="effect-text">'+esc(e.text)+'</div>'+(mem?'<div class="effect-memory">'+esc(mem)+'</div>':"")+'</div>';
}
function rules(card){
  if(card.type==="hero"){
    return '<div class="mode-heading">As Force</div>'+card.modes.force.effects.map(block).join("")+
      '<div class="mode-heading name-mode">As Name</div>'+card.modes.name.effects.map(block).join("");
  }
  if(card.type==="stratagem"){
    return '<div class="hidden-band">Played face-down</div>'+(card.effects||[]).map(block).join("");
  }
  if(!(card.effects||[]).length) return '<div class="empty-rules">No special rules.</div>';
  return card.effects.map(block).join("");
}
function watermark(type){return {force:"F",bond:"B",name:"N",hero:"H",tactic:"T",stratagem:"S",narrative:"N"}[type]||""}
function cardMarkup(card,extra=""){
  const long=String(card.title||"").length>26?" long-title":"";
  const placement=card.placement?'<span class="placement">'+esc(card.placement.toUpperCase())+' ONLY</span>':"";
  const reminder=topReminder(card);
  const sub=card.type==="bond"?titleCase(card.bond_kind||"Bond"):classes(card);
  return '<article class="v2-card card-'+esc(card.type)+long+(extra?" "+extra:"")+'" data-card-id="'+esc(card.id)+'">'+
    '<div class="exposed-strip"><span class="type-symbol">'+symbol(card.type)+'</span>'+strength(card)+
    '<div class="strip-mid"><div class="strip-type">'+esc(TYPE_LABELS[card.type])+(card.unique?" · Unique":"")+'</div><div class="strip-classes">'+esc(classes(card))+'</div></div>'+
    '<div class="strip-right">'+placement+(reminder?'<span class="strip-reminder">'+esc(reminder)+'</span>':"")+'</div></div>'+
    '<div class="card-face" data-watermark="'+esc(watermark(card.type))+'"><h3 class="card-title">'+esc(card.title)+'</h3>'+
    (sub?'<div class="card-subline">'+esc(sub)+'</div>':"")+'<div class="effect-list">'+rules(card)+'</div></div>'+
    '<footer class="card-footer"><div class="footer-meta">'+esc(card.id)+'</div><span class="command-label">Command</span><span class="command-badge">'+esc(card.command_cost)+'</span></footer></article>';
}
function normalize(card){return [card.title,card.type,...(card.classes||[]),...(card.references||[]),card.text].join(" ").toLowerCase()}
function render(cards){
  const type=document.getElementById("type-filter").value,q=document.getElementById("search").value.trim().toLowerCase();
  const filtered=cards.filter(c=>(type==="all"||c.type===type)&&(!q||normalize(c).includes(q)));
  document.getElementById("count").textContent=filtered.length+" / "+cards.length;
  document.getElementById("cards").innerHTML=filtered.map(c=>'<div class="card-wrap">'+cardMarkup(c)+'</div>').join("");
}
function renderStack(cards){
  const ids=["the-crow-archers","guarded","iria"];
  const sel=ids.map(id=>cards.find(c=>c.id===id)).filter(Boolean);
  document.getElementById("stack-demo").innerHTML=sel.map((c,i)=>cardMarkup(c,["stack-force","stack-bond","stack-name"][i])).join("");
}
async function main(){
  const response=await fetch("data/cards-v2-redesign.json"); if(!response.ok) throw new Error("Could not load V2 card data");
  const data=await response.json(),cards=data.cards||[];
  renderStack(cards); render(cards);
  document.getElementById("type-filter").addEventListener("change",()=>render(cards));
  document.getElementById("search").addEventListener("input",()=>render(cards));
}
main().catch(err=>{document.getElementById("cards").textContent=err.message});
})();