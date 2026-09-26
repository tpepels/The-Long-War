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

const TYPE_LABELS = { force: "Force", bond: "Bond", name: "Name", story: "Story", stratagem: "Stratagem" };

const canonicalType = (card) => ({
  subject: "force",
  link: "bond",
  plot: "story",
}[card?.type] || card?.type);

const cssCardType = (card) => ({
  force: "subject",
  bond: "link",
  story: "plot",
}[canonicalType(card)] || canonicalType(card));

const titleCase = (value) =>
  String(value ?? "")
    .split(/[-_ ]+/)
    .filter(Boolean)
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(" ");

function typeLabel(card) {
  const type = canonicalType(card);
  if (type === "story") {
    const form = titleCase(card.story_form);
    const ongoing = card.ongoing ?? card.veiled ?? false;
    return form ? form + (ongoing ? " · Ongoing Story" : " · Story") : (ongoing ? "Ongoing Story" : "Story");
  }
  if (type === "force" && card.hero) return "Hero · Force / Name";
  return TYPE_LABELS[type] ?? type;
}



function cardMotif(card) {
  let hash = 0;
  for (const char of card.id) hash = ((hash * 33) ^ char.charCodeAt(0)) >>> 0;
  return " motif-" + (hash % 6);
}

function cardSymbol(card) {
  const type = canonicalType(card);
  if (type === "story") return (card.ongoing ?? card.veiled ?? false) ? "◐" : "⌁";
  return { force: "◆", bond: "⛓", name: "✦", stratagem: "⚑" }[type] || "•";
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
  const role = canonicalType(card) === "force" && card.role
    ? '<span class="card-role"><strong>' + esc(titleCase(card.role)) + '</strong></span>'
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
  const strength = card.hero
    ? '<div class="strength hero-dual-strength" aria-label="Force strength ' + card.strength + ', Name strength ' + card.hero_name_strength + '">' +
      '<span><small>F</small>' + card.strength + '</span><span><small>N</small>' + card.hero_name_strength + '</span></div>'
    : Number.isInteger(card.strength)
      ? '<div class="strength" aria-label="Strength">' + card.strength + "</div>"
      : "";
  const commandCost = Number.isInteger(card.command_cost)
    ? '<div class="command-cost" aria-label="Command cost">' + card.command_cost + "</div>"
    : "";
  const unique = card.unique ? '<span class="unique"><em>Unique</em></span>' : "";
  return '<article class="game-card deck-card card-' + cssCardType(card) +
    (card.veiled ? " card-veiled" : "") +
    (card.hero ? " card-hero" : "") + '" data-card-id="' + esc(card.id) + '">' +
    '<div class="card-meta"><span class="card-type">' + esc(typeLabel(card)) + '</span>' + commandCost + strength + '</div>' +
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
      '<header class="deck-sheet-heading"><strong>The Long War · v0.9</strong>' +
      '<span>' + label + ' · ' + deckData.name + ' · ' + deckData.cards.length + ' cards</span></header>' +
      '<div class="deck-card-grid">' +
      deckData.cards.map((id) => cardMarkup(index[id], label)).join("") +
      '</div></section>'
  ).join("");
  document.getElementById("kit-count").textContent =
    "2 × " + deckData.cards.length + "-card reference decks";
  window.CardLayoutGuard?.schedule(document.getElementById("playtest-decks"));
}

main().catch((error) => {
  document.getElementById("playtest-decks").textContent = error.message;
});
