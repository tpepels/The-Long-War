const TYPE_LABELS = {
  subject: "Subject",
  link: "Link",
  name: "Name",
  plot: "Plot",
};

function cardMarkup(card) {
  const strength = Number.isInteger(card.strength)
    ? `<div class="strength" aria-label="Strength">${card.strength}</div>`
    : "";

  const unique = card.unique ? '<span class="unique">Unique</span>' : "";

  return `
    <article class="game-card card-${card.type}">
      <header class="card-header">
        <div>
          <div class="card-type">${TYPE_LABELS[card.type] ?? card.type}</div>
          <h2>${card.title}</h2>
        </div>
        ${strength}
      </header>
      <div class="card-art" aria-hidden="true">
        <span>${card.title}</span>
      </div>
      <div class="card-rule">
        <p>${card.text || "&nbsp;"}</p>
      </div>
      <footer class="card-footer">
        ${unique}
        <span class="card-id">${card.id}</span>
      </footer>
    </article>
  `;
}

async function main() {
  const response = await fetch("data/cards.json");
  if (!response.ok) throw new Error("Could not load card data");
  const data = await response.json();
  const cards = data.cards;

  document.getElementById("card-count").textContent = `${cards.length} cards`;
  document.getElementById("cards").innerHTML = cards.map(cardMarkup).join("");
}

main().catch((error) => {
  document.getElementById("cards").textContent = error.message;
});
