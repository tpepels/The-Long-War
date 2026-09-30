function esc(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function shortDeckLabel(name, index) {
  const primary = String(name || "").split(" / ")[0].trim();
  return primary || "Deck " + (index + 1);
}

function chunk(items, size) {
  const chunks = [];
  for (let index = 0; index < items.length; index += size) {
    chunks.push(items.slice(index, index + size));
  }
  return chunks;
}

async function main() {
  const [cardsResponse, decksResponse] = await Promise.all([
    fetch("data/cards.json"),
    fetch("data/reference-decks.json"),
  ]);
  if (!cardsResponse.ok || !decksResponse.ok) {
    throw new Error("Could not load reference deck data");
  }

  const cardData = await cardsResponse.json();
  const deckData = await decksResponse.json();
  const decks = Array.isArray(deckData.decks) ? deckData.decks : [];
  if (!decks.length) throw new Error("No reference decks were published");

  const index = Object.fromEntries(cardData.cards.map((card) => [card.id, card]));
  for (const deck of decks) {
    const missing = deck.cards.filter((id) => !index[id]);
    if (missing.length) {
      throw new Error(deck.name + " contains unknown cards: " + missing.join(", "));
    }
  }

  const root = document.getElementById("playtest-decks");
  root.innerHTML = decks.map((deck, deckIndex) => {
    const label = shortDeckLabel(deck.name, deckIndex);
    const sheets = chunk(deck.cards, 9);
    return '<section class="print-deck" data-deck-file="' + esc(deck.file) + '">' +
      '<header class="deck-sheet-heading"><strong>The Long War · reference deck ' +
      (deckIndex + 1) + ' of ' + decks.length + '</strong>' +
      '<span>' + esc(deck.name) + ' · ' + deck.cards.length + ' cards</span></header>' +
      sheets.map((sheet, sheetIndex) =>
        '<div class="deck-card-grid card-sheet" data-sheet="' + (sheetIndex + 1) + '">' +
        sheet.map((id) => window.PrintCards.markup(index[id], label)).join("") +
        '</div>'
      ).join("") +
      '</section>';
  }).join("");

  const totalCards = decks.reduce((total, deck) => total + deck.cards.length, 0);
  document.getElementById("kit-count").textContent =
    decks.length + " reference decks · " + totalCards + " cards";
  window.CardLayoutGuard?.schedule(root);
}

main().catch((error) => {
  document.getElementById("playtest-decks").textContent = error.message;
});
