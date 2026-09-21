const TYPE_LABELS = { subject: "Subject", link: "Link", name: "Name", plot: "Plot" };

function typeLabel(card) {
  if (card.type === "plot" && (card.keywords || []).includes("scheme")) return "Plot · Scheme";
  return TYPE_LABELS[card.type] ?? card.type;
}

function cardMarkup(card, deckLabel) {
  const strength = Number.isInteger(card.strength)
    ? '<div class="strength" aria-label="Strength">' + card.strength + '</div>'
    : "";
  const unique = card.unique ? '<span class="unique">Unique</span>' : "";
  return '<article class="game-card deck-card card-' + card.type + '">' +
    '<header class="card-header"><div><div class="card-type">' + typeLabel(card) +
    '</div><h2>' + card.title + '</h2></div>' + strength + '</header>' +
    '<div class="card-art" aria-hidden="true"><span>' + card.title + '</span></div>' +
    '<div class="card-rule"><p>' + (card.text || "&nbsp;") + '</p></div>' +
    '<footer class="card-footer"><span>' + unique + '</span><span>' + deckLabel + '</span></footer>' +
    '</article>';
}

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
      '<header class="deck-sheet-heading"><strong>The Long War · v0.1</strong>' +
      '<span>' + label + ' · ' + deckData.name + ' · 30 cards</span></header>' +
      '<div class="deck-card-grid">' +
      deckData.cards.map((id) => cardMarkup(index[id], label)).join("") +
      '</div></section>'
  ).join("");
  document.getElementById("kit-count").textContent = "2 × 30-card reference decks";
}

main().catch((error) => {
  document.getElementById("playtest-decks").textContent = error.message;
});
