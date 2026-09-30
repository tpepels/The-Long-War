function chunk(items, size) {
  const chunks = [];
  for (let index = 0; index < items.length; index += size) {
    chunks.push(items.slice(index, index + size));
  }
  return chunks;
}

async function main() {
  const response = await fetch("data/cards.json");
  if (!response.ok) throw new Error("Could not load card data");
  const data = await response.json();
  const cards = data.cards;

  document.getElementById("card-count").textContent = cards.length + " cards";
  const root = document.getElementById("cards");
  root.innerHTML = chunk(cards, 9).map((sheet, sheetIndex) =>
    '<section class="card-sheet" data-sheet="' + (sheetIndex + 1) + '">' +
    sheet.map((card) => window.PrintCards.markup(card)).join("") +
    '</section>'
  ).join("");
  window.CardLayoutGuard?.schedule(root);
}

main().catch((error) => {
  document.getElementById("cards").textContent = error.message;
});
