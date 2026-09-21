function esc(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function formatGameText(value) {
  return esc(value)
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>");
}

const TYPE_LABELS = { subject: "Subject", link: "Bond", name: "Name", stratagem: "Stratagem" };

const titleCase = (value) =>
  String(value ?? "")
    .split(/[-_ ]+/)
    .filter(Boolean)
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(" ");

function typeLabel(card) {
  if (card.type === "plot") {
    const form = titleCase(card.story_form);
    return card.veiled ? form + " · Veiled Story" : form + " · Story";
  }
  if (card.type === "subject" && card.hero) return "Hero · Subject";
  return TYPE_LABELS[card.type] ?? card.type;
}


function cardDensity(card) {
  const length = String(card.text || "").replace(/\*\*/g, "").replace(/\*/g, "").length;
  if (length >= 220) return " card-density-max";
  if (length >= 160) return " card-density-dense";
  if (length >= 120) return " card-density-medium";
  return "";
}

function cardMotif(card) {
  let hash = 0;
  for (const char of card.id) hash = ((hash * 33) ^ char.charCodeAt(0)) >>> 0;
  return " motif-" + (hash % 6);
}

function cardSymbol(card) {
  if (card.type === "plot") return card.veiled ? "◐" : "⌁";
  return { subject: "◆", link: "⛓", name: "✦", stratagem: "⚑" }[card.type] || "•";
}

function cardArtMarkup(card) {
  return '<div class="card-art ' + cardMotif(card) + '" aria-hidden="true">' +
    '<span class="card-art-sigil">' + cardSymbol(card) + '</span>' +
    '<span class="card-art-name">' + esc(card.title) + '</span>' +
    '<span class="card-art-mark"></span>' +
  '</div>';
}

function propertyLabel(card) {
  const values = [];
  if (card.type === "subject" && card.role) values.push(titleCase(card.role));
  for (const value of card.classes || []) {
    if (value === "hero") continue;
    const label = titleCase(value);
    if (!values.includes(label)) values.push(label);
  }
  return values.length
    ? '<div class="card-properties">' +
      values.map((value) => "<em>" + esc(value) + "</em>").join(" · ") +
      "</div>"
    : "";
}

function cardMarkup(card, deckLabel) {
  const strength = Number.isInteger(card.strength)
    ? '<div class="strength" aria-label="Strength">' + card.strength + "</div>"
    : "";
  const unique = card.unique ? '<span class="unique"><em>Unique</em></span>' : "";
  return '<article class="game-card deck-card card-' + card.type +
    (card.veiled ? " card-veiled" : "") +
    (card.hero ? " card-hero" : "") + cardDensity(card) + '">' +
    '<header class="card-header"><div><div class="card-type">' + esc(typeLabel(card)) +
    '</div><h2>' + esc(card.title) + '</h2>' + propertyLabel(card) + '</div>' + strength + '</header>' +
    cardArtMarkup(card) +
    '<div class="card-rule"><p>' + (card.text ? formatGameText(card.text) : "&nbsp;") + '</p></div>' +
    '<footer class="card-footer"><span>' + unique + '</span><span>' + esc(deckLabel) + '</span></footer>' +
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
      '<header class="deck-sheet-heading"><strong>The Long War · v0.4</strong>' +
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
