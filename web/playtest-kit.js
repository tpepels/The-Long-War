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
  const classes = (card.classes || [])
    .filter((value) => value !== "hero" && value !== card.role)
    .map((value) => titleCase(value));
  const role = card.type === "subject" && card.role
    ? '<span class="card-role"><strong>' + esc(titleCase(card.role)) + '</strong><span>' +
      esc(window.CardRules.roleHint(card)) + '</span></span>'
    : "";
  const classMarkup = classes.length
    ? '<span class="card-classes">' + classes.map((value) => "<em>" + esc(value) + "</em>").join(" · ") + "</span>"
    : '<span class="card-classes">&nbsp;</span>';
  return '<div class="card-properties">' + role + classMarkup + "</div>";
}

function ruleMarkup(card) {
  return window.CardRules.markup(card, formatGameText, "<em>No special rules.</em>");
}

function cardMarkup(card, deckLabel) {
  const strength = Number.isInteger(card.strength)
    ? '<div class="strength" aria-label="Strength">' + card.strength + "</div>"
    : "";
  const unique = card.unique ? '<span class="unique"><em>Unique</em></span>' : "";
  return '<article class="game-card deck-card card-' + card.type +
    (card.veiled ? " card-veiled" : "") +
    (card.hero ? " card-hero" : "") + '" data-card-id="' + esc(card.id) + '">' +
    '<div class="card-meta"><span class="card-type">' + esc(typeLabel(card)) + '</span>' + strength + '</div>' +
    '<h2 class="card-title">' + esc(card.title) + '</h2>' +
    propertyLabel(card) +
    '<div class="card-rule">' + ruleMarkup(card) + '</div>' +
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
      '<header class="deck-sheet-heading"><strong>The Long War · v0.5</strong>' +
      '<span>' + label + ' · ' + deckData.name + ' · 30 cards</span></header>' +
      '<div class="deck-card-grid">' +
      deckData.cards.map((id) => cardMarkup(index[id], label)).join("") +
      '</div></section>'
  ).join("");
  document.getElementById("kit-count").textContent = "2 × 30-card reference decks";
  window.CardLayoutGuard?.schedule(document.getElementById("playtest-decks"));
}

main().catch((error) => {
  document.getElementById("playtest-decks").textContent = error.message;
});
