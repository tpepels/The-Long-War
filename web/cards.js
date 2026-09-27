async function main() {
  const response = await fetch("data/cards.json");
  if (!response.ok) throw new Error("Could not load card data");
  const data = await response.json();
  const cards = data.cards;

  document.getElementById("card-count").textContent = cards.length + " cards";
  const root = document.getElementById("cards");
  root.innerHTML = cards.map((card) => window.PrintCards.markup(card)).join("");
  window.CardLayoutGuard?.schedule(root);
}

main().catch((error) => {
  document.getElementById("cards").textContent = error.message;
});
