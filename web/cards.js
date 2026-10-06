function chunk(items,size){
  const chunks=[];
  for(let index=0;index<items.length;index+=size)chunks.push(items.slice(index,index+size));
  return chunks;
}
function scheduleInspect(root){
  const run=()=>window.V2Cards?.inspect(root);
  requestAnimationFrame(run);
  if(document.fonts?.ready)document.fonts.ready.then(run);
}
async function main(){
  const response=await fetch("data/cards.json",{cache:"no-cache"});
  if(!response.ok)throw new Error("Could not load current card data");
  const cards=(await response.json()).cards||[];
  document.getElementById("card-count").textContent=cards.length+" current cards";
  const root=document.getElementById("print-catalogue");
  root.innerHTML=chunk(cards,8).map((sheet,index)=>
    '<section class="print-sheet card-sheet" data-sheet="'+(index+1)+'">'+
    sheet.map(card=>window.V2Cards.cardArticle(card,"print-card")).join("")+
    '</section>'
  ).join("");
  scheduleInspect(root);
}
main().catch(error=>{document.getElementById("print-catalogue").textContent=error.message});
