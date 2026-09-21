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

const TYPE_SYMBOLS = {
  subject: "◆",
  link: "⛓",
  name: "✦",
  stratagem: "⚑",
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
  return TYPE_LABELS[card.type] ?? titleCase(card.type);
}

function propertyValues(card) {
  const values = [];
  if (card.type === "subject" && card.role) values.push(titleCase(card.role));
  for (const value of card.classes || []) {
    if (value === "hero") continue;
    const label = titleCase(value);
    if (!values.includes(label)) values.push(label);
  }
  return values;
}

function propertyLabel(card) {
  const values = propertyValues(card);
  return values.length
    ? '<div class="card-properties">' +
      values.map((value) => "<em>" + esc(value) + "</em>").join("<span>·</span>") +
      "</div>"
    : "";
}

function themeClasses(card) {
  const classes = ["game-card", "card-" + card.type];
  if (card.hero) classes.push("card-hero");
  if (card.veiled) classes.push("card-veiled");
  if (card.role) classes.push("role-" + card.role);
  if (card.story_form) classes.push("story-" + card.story_form);
  for (const value of card.classes || []) classes.push("class-" + value);
  return classes.join(" ");
}

function cardInitials(title) {
  return String(title)
    .replace(/^(the|a|an)\s+/i, "")
    .split(/\s+/)
    .slice(0, 3)
    .map((word) => word[0] || "")
    .join("")
    .toUpperCase();
}

function cardSymbol(card) {
  if (card.type === "plot") return card.veiled ? "◐" : "⌁";
  if (card.hero) return "♛";
  return TYPE_SYMBOLS[card.type] || "•";
}

function artMarkup(card) {
  return '<div class="card-art" aria-hidden="true">' +
    '<span class="card-art-orbit"></span>' +
    '<span class="card-art-line line-a"></span>' +
    '<span class="card-art-line line-b"></span>' +
    '<b class="card-art-symbol">' + cardSymbol(card) + '</b>' +
    '<strong class="card-art-mark">' + esc(cardInitials(card.title)) + '</strong>' +
  "</div>";
}

function cardMarkup(card) {
  const strength = Number.isInteger(card.strength)
    ? '<div class="strength" aria-label="Strength ' + card.strength + '">' + card.strength + "</div>"
    : "";

  const unique = card.unique ? '<span class="unique"><em>Unique</em></span>' : "";

  return '<article class="' + themeClasses(card) + '" data-card-id="' + esc(card.id) + '">' +
    '<header class="card-header"><div class="card-heading">' +
      '<div class="card-type">' + esc(typeLabel(card)) + "</div>" +
      "<h2>" + esc(card.title) + "</h2>" +
      propertyLabel(card) +
    "</div>" + strength + "</header>" +
    artMarkup(card) +
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
  document.getElementById("cards").innerHTML = cards.map(cardMarkup).join("");
}

main().catch((error) => {
  document.getElementById("cards").textContent = error.message;
});
