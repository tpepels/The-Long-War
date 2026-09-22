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

const TYPE_LABELS = {
  subject: "Subject",
  link: "Bond",
  name: "Name",
  stratagem: "Stratagem",
};

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

function cardMarkup(card) {
  const strength = Number.isInteger(card.strength)
    ? '<div class="strength" aria-label="Strength">' + card.strength + "</div>"
    : "";
  const unique = card.unique ? '<span class="unique"><em>Unique</em></span>' : "";

  return '<article class="game-card card-' + card.type +
    (card.veiled ? " card-veiled" : "") +
    (card.hero ? " card-hero" : "") + '">' +
    '<header class="card-header"><div>' +
      '<div class="card-type">' + esc(typeLabel(card)) + "</div>" +
      "<h2>" + esc(card.title) + "</h2>" +
      propertyLabel(card) +
    "</div>" + strength + "</header>" +
    cardArtMarkup(card) +
    '<div class="card-rule"><p>' + (card.text ? formatGameText(card.text) : "&nbsp;") + "</p></div>" +
    '<footer class="card-footer">' + unique + '<span class="card-id">' + esc(card.id) + "</span></footer>" +
    "</article>";
}

async function main() {
  const response = await fetch("data/cards.json");
  if (!response.ok) throw new Error("Could not load card data");
  const data = await response.json();
  const cards = data.cards;

  document.getElementById("card-count").textContent = cards.length + " cards";
  const root = document.getElementById("cards");
  root.innerHTML = cards.map(cardMarkup).join("");
  window.CardLayoutGuard?.schedule(root);
}

main().catch((error) => {
  document.getElementById("cards").textContent = error.message;
});
