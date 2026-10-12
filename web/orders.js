"use strict";
// Canonical drawable Order cards, shared by the live print sheets and on-page hand.
// Illustrations are from retired paper card identities. The print site
// publishes optimized versions through build_print_art().
// The Force catalogue and Order print sheets use one physical-card renderer.
const byId=id=>document.getElementById(id);
const state={cards:[],copies:3,pile:[],hand:[],used:[],selected:null,battles:0};
function cardHTML(card,{choice=false}={}){
  return window.PhysicalCards.orderArticle(card,{
    selectable:choice,
    selected:choice&&state.selected===card.uid,
    uid:card.uid
  });
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
    :"Battle "+state.battles+" completed. "+state.hand.length+" Orders in hand; "+state.pile.length+" undrawn.";
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
    if(data.status!=="canonical-paper-only"||data.orders.length!==4||
       !data.orders.every(card=>card.art_id && /^[a-z0-9-]+$/.test(card.art_id)))
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
