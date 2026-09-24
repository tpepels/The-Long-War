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

function cardMarkup(card) {
  const strength = Number.isInteger(card.strength)
    ? '<div class="strength" aria-label="Strength">' + card.strength + "</div>"
    : "";
  const commandCost = Number.isInteger(card.command_cost)
    ? '<div class="command-cost" aria-label="Command cost">' + card.command_cost + "</div>"
    : "";
  const unique = card.unique ? '<span class="unique"><em>Unique</em></span>' : "";

  return '<article class="game-card card-' + card.type +
    (card.veiled ? " card-veiled" : "") +
    (card.hero ? " card-hero" : "") + '" data-card-id="' + esc(card.id) + '">' +
    '<div class="card-meta"><span class="card-type">' + esc(typeLabel(card)) + "</span>" + commandCost + strength + "</div>" +
    '<h2 class="card-title">' + esc(card.title) + "</h2>" +
    propertyLabel(card) +
    '<div class="card-rule">' + ruleMarkup(card) + "</div>" +
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
