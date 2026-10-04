(() => {
"use strict";
const esc=value=>String(value??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;");
const H=()=>window.V2Heraldry;
const typeGlyph=type=>H()?.symbol(type)||"";
const classGlyph=name=>H()?.classification(name)||"";
const strengthGlyph=()=>H()?.strength()||"";
const timingGlyph=name=>H()?.timing(name)||"";

function costSeal(value){
  return '<span class="prototype-cost" aria-label="Command cost '+esc(value)+'"><svg viewBox="0 0 40 40" aria-hidden="true"><path d="M12 2H28L38 12V28L28 38H12L2 28V12Z"/><path class="seal-inner" d="M14 6H26L34 14V26L26 34H14L6 26V14Z"/></svg><b>'+esc(value)+'</b></span>';
}
function render(card,skin){
  const effect=card.effects?.[0]||null;
  const classes=(card.classes||[]).map(name=>'<span title="'+esc(name)+'">'+classGlyph(name)+'</span>').join("");
  const classline=(card.classes||[]).map(name=>'<span>'+classGlyph(name)+' '+esc(name[0].toUpperCase()+name.slice(1))+'</span>').join('<i>·</i>');
  const live='<span class="named-mark">'+typeGlyph("name")+'</span><b>NAMED</b><strong>+1</strong>';
  return '<article class="force-prototype skin-'+skin+'">'+
    '<header class="prototype-edge">'+
      '<div class="prototype-stat"><span class="force-mark">'+typeGlyph("force")+'</span><span class="strength-mark">'+strengthGlyph()+'</span><b>'+esc(card.strength)+'</b></div>'+
      '<div class="prototype-classes">'+classes+'</div>'+
      '<div class="prototype-live">'+live+'</div>'+
    '</header>'+
    '<div class="prototype-art" aria-hidden="true"></div>'+
    '<section class="prototype-copy">'+
      '<div class="prototype-title-row"><h3>'+esc(card.title)+'</h3><span class="prototype-type-mark">'+typeGlyph("force")+'</span></div>'+
      '<div class="prototype-classline">'+classline+'</div>'+
      '<div class="prototype-divider"></div>'+
      (effect?'<div class="prototype-rule"><span class="rule-icon">'+timingGlyph(effect.timing)+'</span><div><h4>WHILE NAMED</h4><p>'+esc(effect.text)+'</p></div></div>':'')+
      '<footer class="prototype-footer"><span class="prototype-id">F · '+esc(card.id)+'</span></footer>'+
      costSeal(card.command_cost)+
    '</section>'+
  '</article>';
}

async function main(){
  const response=await fetch("data/cards-v2-redesign.json",{cache:"no-cache"});
  if(!response.ok) throw new Error("Could not load V2 card data");
  const data=await response.json();
  const card=data.cards.find(card=>card.id==="the-kings-spears");
  if(!card) throw new Error("The King's Spears not found");
  for(const [id,skin] of [
    ["force-chronicle","chronicle"],
    ["force-banner","banner"],
    ["force-steel","steel"],
    ["force-land","land"],
    ["force-omen","omen"],
  ]){
    document.getElementById(id).innerHTML=render(card,skin);
  }
}
main().catch(error=>{
  document.querySelectorAll(".prototype-slot").forEach(node=>node.textContent=error.message||String(error));
});
})();