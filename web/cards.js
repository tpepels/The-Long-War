function chunk(items,size){
  const chunks=[];
  for(let index=0;index<items.length;index+=size)chunks.push(items.slice(index,index+size));
  return chunks;
}
async function preloadArt(ids){
  await Promise.all(ids.map(id=>new Promise(resolve=>{
    const image=new Image();
    image.onload=resolve;
    image.onerror=resolve;
    image.src="art/cards-print/"+encodeURIComponent(id)+".webp";
  })));
}
async function main(){
  const response=await fetch("data/cards.json",{cache:"no-cache"});
  if(!response.ok)throw new Error("Could not load current card data");
  const cards=(await response.json()).cards||[];
  const count=document.getElementById("card-count");
  const printButton=document.getElementById("print-catalogue-button");
  count.textContent=cards.length+" current cards · preparing print artwork…";
  const root=document.getElementById("print-catalogue");
  root.innerHTML=chunk(cards,8).map((sheet,index)=>
    '<section class="print-sheet card-sheet" data-sheet="'+(index+1)+'">'+
    sheet.map(card=>window.PhysicalCards.cardArticle(card,"print-card",{printArt:true})).join("")+
    '</section>'
  ).join("");
  await preloadArt(cards.map(card=>card.id));
  if(document.fonts?.ready)await document.fonts.ready;
  count.textContent=cards.length+" current cards · ready to print";
  if(printButton)printButton.disabled=false;
}
main().catch(error=>{
  document.getElementById("print-catalogue").textContent=error.message;
  const count=document.getElementById("card-count");
  if(count)count.textContent="Could not prepare cards";
});
