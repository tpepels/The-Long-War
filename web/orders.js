"use strict";
// Canonical printable Order deck plus a separate interactive hand rehearsal.
const ART={
  blade:'<path d="M13 58L51 18l9-5-5 9-38 40zM15 59l-7 8m0-23 20 20M8 44l10 10"/><path d="M24 46l15 15"/>',
  shield:'<path d="M35 11L58 19v19c0 19-11 30-23 37C23 68 12 57 12 38V19z"/><path d="M35 19v45M20 39h30"/>',
  arrows:'<path d="M7 59L62 13m-16-1 16 1-1 16M11 68l56-46m-16-1 16 1-1 16"/><path d="M13 52l16 16m-15-30 16 16"/>',
  horse:'<path d="M17 65c4-9 5-20 6-31l-8-9 15-14 13 8-3 10 17 5-5 11-16-1c2 10 7 15 15 22"/><path d="M21 48l17 3M30 20l4 4M10 69h51"/>'
};
const esc=v=>String(v??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;");
const byId=id=>document.getElementById(id);
const state={cards:[],copies:3,pile:[],hand:[],used:[],selected:null,battles:0};
function cardHTML(card,{choice=false}={}){
  const n=choice?' role="button" tabindex="0" aria-pressed="'+(state.selected===card.uid)+'"':"";
  return '<article class="order-card" data-order="'+esc(card.id)+'" data-instance="'+esc(card.uid)+'"'+n+'>'+
    '<header class="order-header"><span class="order-family">ORDER</span><h3>'+esc(card.title)+'</h3><span class="order-crest" aria-hidden="true">✧</span></header>'+
    '<div class="order-art" aria-hidden="true"><svg viewBox="0 0 76 80">'+ART[card.symbol]+'</svg></div>'+
    '<section class="order-effect"><p class="order-timing">'+esc(card.timing)+'</p><p class="order-text">'+esc(card.effect)+'</p></section>'+
    '<footer class="order-footer"><span>The Long War</span></footer></article>';
}
function pool(){
  return state.cards.flatMap(card=>Array.from({length:state.copies},(_,n)=>({...card,uid:card.id+"-"+n})));
}
function shuffled(items){
  const a=[...items];
  for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]]}
  return a;
}
function draw(){
  if(!state.pile.length && state.used.length){state.pile=shuffled(state.used);state.used=[]}
  const card=state.pile.shift();
  if(card)state.hand.push(card);
}
function drawNewHand(){
  state.pile=shuffled(pool());state.hand=[];state.used=[];state.selected=null;state.battles=0;
  for(let n=0;n<3;n++)draw();
  renderHand();
}
function renderHand(){
  byId("order-hand").innerHTML=state.hand.map(c=>cardHTML(c,{choice:true})).join("");
  byId("hand-status").textContent=state.battles===0
    ?"Choose one of three Orders. It will be revealed to your opponent before the D6 rolls."
    :"Battle "+state.battles+" completed in this hand rehearsal. "+state.hand.length+" Orders in hand; "+state.pile.length+" undrawn.";
  byId("play-order").disabled=!state.selected;
}
function choose(uid){
  const chosen=state.hand.find(x=>x.uid===uid);
  if(!chosen)return;
  state.selected=state.selected===uid?null:uid;
  renderHand();
}
function playSelected(){
  if(!state.selected)return;
  const i=state.hand.findIndex(c=>c.uid===state.selected);
  if(i<0)return;
  const [card]=state.hand.splice(i,1);state.used.push(card);
  state.selected=null;state.battles+=1;
  draw();
  renderHand();
  byId("hand-status").textContent="Played "+card.title+". Discarded it and drew one replacement. Choose your next Battle Order.";
}
function printDeck(){
  const sheets=[];
  // 12 cards for each player: three of every available Order.
  const twoPlayers=[...pool(),...pool().map(c=>({...c,uid:"opponent-"+c.uid}))];
  for(let index=0;index<twoPlayers.length;index+=8)
    sheets.push('<section class="print-sheet">'+twoPlayers.slice(index,index+8).map(c=>cardHTML(c)).join("")+'</section>');
  byId("order-print-pages").innerHTML=sheets.join("");
}
async function init(){
  try{
    const response=await fetch("data/orders.json");
    if(!response.ok)throw new Error("Card data was not published");
    const data=await response.json();
    if(data.status!=="canonical-paper-only"||data.orders.length!==4)
      throw new Error("Unexpected Order deck data");
    state.cards=data.orders;
    state.copies=data.copies_per_order;
    byId("order-gallery").innerHTML=data.orders.map((card,i)=>cardHTML({...card,uid:"gallery-"+i})).join("");
    printDeck();drawNewHand();
    byId("print-orders").disabled=false;byId("reset-hand").disabled=false;
  }catch(e){
    byId("hand-status").textContent="Order deck could not load: "+e.message;
  }
}
byId("order-hand").addEventListener("click",e=>{const item=e.target.closest(".order-card");if(item)choose(item.dataset.instance)});
byId("order-hand").addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){const item=e.target.closest(".order-card");if(item){e.preventDefault();choose(item.dataset.instance)}}});
byId("reset-hand").addEventListener("click",drawNewHand);
byId("play-order").addEventListener("click",playSelected);
byId("print-orders").addEventListener("click",()=>window.print());
init();
