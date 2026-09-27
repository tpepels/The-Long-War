async function main() {
  const [cardsResponse, deckResponse] = await Promise.all([
    fetch("data/cards.json"),
    fetch("data/reference-deck.json"),
  ]);
  if (!cardsResponse.ok || !deckResponse.ok) throw new Error("Could not load playtest data");
  const cardData = await cardsResponse.json();
  const deckData = await deckResponse.json();
  const index = Object.fromEntries(cardData.cards.map((card) => [card.id, card]));
  const labels = ["Player 1", "Player 2"];

  document.getElementById("playtest-decks").innerHTML = labels.map((label) =>
    '<section class="print-deck">' +
      '<header class="deck-sheet-heading"><strong>The Long War · v0.9</strong>' +
      '<span>' + label + ' · ' + deckData.name + ' · ' + deckData.cards.length + ' cards</span></header>' +
      '<div class="deck-card-grid">' +
      deckData.cards.map((id) => window.PrintCards.markup(index[id], label)).join("") +
      '</div></section>'
  ).join("");
  document.getElementById("kit-count").textContent =
    "2 × " + deckData.cards.length + "-card reference decks";
  window.CardLayoutGuard?.schedule(document.getElementById("playtest-decks"));
}

main().catch((error) => {
  document.getElementById("playtest-decks").textContent = error.message;
});
