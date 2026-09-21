const worker = new Worker("play-worker.js", { type: "module" });
const pending = new Map();
let requestId = 0;
let cards = {};
let state = null;

const $ = (id) => document.getElementById(id);
const frontNames = ["Left", "Center", "Right"];

function esc(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function request(payload) {
  return new Promise((resolve, reject) => {
    const id = ++requestId;
    pending.set(id, { resolve, reject });
    worker.postMessage({ id, ...payload });
  });
}

worker.addEventListener("message", (event) => {
  if (event.data.type === "ready") {
    $("engine-status").textContent = "Rules engine ready";
    $("mode").disabled = false;
    $("seed").disabled = false;
    $("start-game").disabled = false;
    return;
  }
  if (event.data.type === "boot_error") {
    $("engine-status").textContent = "Rules engine failed to load";
    $("setup-note").textContent = event.data.error;
    return;
  }
  const entry = pending.get(event.data.id);
  if (!entry) return;
  pending.delete(event.data.id);
  if (event.data.ok) entry.resolve(event.data.result);
  else entry.reject(new Error(event.data.error));
});

function cardTitle(cardId) {
  if (!cardId) return "—";
  return cards[cardId]?.title ?? cardId;
}

function cardType(card) {
  if (card.type === "plot" && (card.keywords || []).includes("scheme")) return "Scheme";
  return card.type[0].toUpperCase() + card.type.slice(1);
}

function boardSlot(owner, front, rank) {
  return state.board[owner].find((slot) => slot.front === front && slot.rank === rank);
}

function renderSlot(owner, front, rank) {
  const slot = boardSlot(owner, front, rank);
  if (!slot?.subject) {
    return '<div class="digital-slot empty"><span>' +
      (rank === "front" ? "Frontline" : "Rear") + '</span></div>';
  }
  const legend = [slot.subject, slot.link, slot.name]
    .filter(Boolean)
    .map(cardTitle)
    .join(" — ");
  return '<div class="digital-slot occupied">' +
    '<span class="slot-rank">' + esc(slot.rank_name) + '</span>' +
    '<strong>' + esc(legend) + '</strong>' +
    '<span class="slot-strength">' + slot.strength + '</span>' +
    '</div>';
}

function renderScheme(owner, front) {
  const scheme = state.schemes[owner][front];
  if (!scheme) return '<div class="scheme-marker empty">No Scheme</div>';
  if (scheme.hidden) return '<div class="scheme-marker hidden">Face-down Scheme</div>';
  return '<div class="scheme-marker">' + esc(cardTitle(scheme.card_id)) +
    (scheme.revealed ? " · revealed" : "") + '</div>';
}

function renderBattlefield() {
  $("battlefield").innerHTML = frontNames.map((name, front) => {
    const p0 = state.front_strengths[0][front];
    const p1 = state.front_strengths[1][front];
    return '<section class="digital-front">' +
      '<header><strong>' + name + '</strong><span>P2 ' + p1 + ' · P1 ' + p0 + '</span></header>' +
      '<div class="front-side opponent-side">' +
        renderScheme(1, front) +
        renderSlot(1, front, "rear") +
        renderSlot(1, front, "front") +
      '</div>' +
      '<div class="battle-line">battle line</div>' +
      '<div class="front-side player-side">' +
        renderSlot(0, front, "front") +
        renderSlot(0, front, "rear") +
        renderScheme(0, front) +
      '</div>' +
    '</section>';
  }).join("");
}

function renderStrip() {
  const winnerText = state.winner == null ? "" : " · Player " + (state.winner + 1) + " wins";
  $("match-strip").innerHTML =
    '<strong>Battle ' + state.battle + '</strong>' +
    '<span>Player 1 victories: ' + state.players[0].victories + '</span>' +
    '<span>Player 2 victories: ' + state.players[1].victories + '</span>' +
    '<span>Turn: Player ' + (state.active_player + 1) + winnerText + '</span>' +
    '<span>Hands: ' + state.players[0].hand_count + ' / ' + state.players[1].hand_count + '</span>';
}

function renderPrivacy() {
  const gate = $("privacy-gate");
  if (!state.needs_reveal) {
    gate.hidden = true;
    return;
  }
  gate.hidden = false;
  gate.innerHTML =
    '<p>Pass the device to <strong>Player ' + (state.active_player + 1) + '</strong>.</p>' +
    '<button type="button" id="reveal-hand">Reveal Player ' + (state.active_player + 1) + ' hand</button>';
  $("reveal-hand").addEventListener("click", async () => {
    await runBusy(async () => {
      state = await request({ type: "view", viewer: state.active_player });
      render();
    });
  });
}

function actionButtonsFor(cardId) {
  return state.legal_actions.filter((action) => action.card_id === cardId);
}

function actionButton(action) {
  const reason = $("show-reasons").checked
    ? '<small>' + esc(action.reason) + '</small>'
    : "";
  return '<button type="button" class="legal-action" data-action-key="' +
    encodeURIComponent(action.key) + '">' +
    '<span>' + esc(action.label) + '</span>' + reason + '</button>';
}

function bindActionButtons() {
  document.querySelectorAll("[data-action-key]").forEach((button) => {
    button.addEventListener("click", async () => {
      const key = decodeURIComponent(button.dataset.actionKey);
      await runBusy(async () => {
        state = await request({ type: "act", key, viewer: state.viewer });
        render();
      });
    });
  });
}

function renderHand() {
  const hand = $("hand");
  const actions = $("turn-actions");
  if (state.viewer == null || state.phase === "complete") {
    hand.innerHTML = "";
    actions.innerHTML = "";
    return;
  }

  $("hand-title").textContent = "Player " + (state.viewer + 1) + " hand · " + state.hand.length + " cards";
  const grouped = new Map();
  for (const cardId of state.hand) grouped.set(cardId, (grouped.get(cardId) || 0) + 1);

  hand.innerHTML = [...grouped.entries()].map(([cardId, count]) => {
    const card = cards[cardId];
    const plays = actionButtonsFor(cardId);
    return '<article class="hand-card">' +
      '<header><span>' + esc(cardType(card)) + (count > 1 ? " ×" + count : "") + '</span>' +
      '<strong>' + esc(card.title) + '</strong>' +
      (Number.isInteger(card.strength) ? '<b>' + card.strength + '</b>' : "") +
      '</header>' +
      '<p>' + esc(card.text || "No rules text.") + '</p>' +
      '<div class="hand-card-actions">' +
      (plays.length ? plays.map(actionButton).join("") : '<span class="muted">No legal play right now.</span>') +
      '</div></article>';
  }).join("");

  const nonCardActions = state.legal_actions.filter((action) => !action.card_id);
  actions.innerHTML = nonCardActions.map(actionButton).join("");
  bindActionButtons();
}

function renderHistory() {
  $("history").innerHTML = state.log.map((line) => '<li>' + esc(line) + '</li>').join("");
}

function render() {
  $("game").hidden = false;
  renderStrip();
  renderPrivacy();
  renderBattlefield();
  renderHand();
  renderHistory();
  if (state.phase === "complete") {
    $("privacy-gate").hidden = false;
    $("privacy-gate").innerHTML = '<p><strong>Player ' + (state.winner + 1) + ' wins the match.</strong></p>';
  }
}

async function runBusy(fn) {
  $("engine-status").textContent = "Resolving…";
  document.querySelectorAll("button").forEach((button) => { button.disabled = true; });
  try {
    await fn();
    $("engine-status").textContent = "Rules engine ready";
  } catch (error) {
    $("engine-status").textContent = "Action failed";
    window.alert(error.message);
  } finally {
    document.querySelectorAll("button").forEach((button) => { button.disabled = false; });
  }
}

async function loadCards() {
  const response = await fetch("data/cards.json", { cache: "no-store" });
  if (!response.ok) throw new Error("Could not load card data");
  const data = await response.json();
  cards = Object.fromEntries(data.cards.map((card) => [card.id, card]));
}

$("new-game-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const mode = $("mode").value;
  const seed = Math.max(0, Math.min(2147483647, Number($("seed").value) || 0));
  await runBusy(async () => {
    state = await request({ type: "new_game", mode, seed });
    $("play-setup").hidden = true;
    render();
  });
});

$("restart").addEventListener("click", () => {
  state = null;
  $("game").hidden = true;
  $("play-setup").hidden = false;
});

$("show-reasons").addEventListener("change", () => {
  if (state) renderHand();
});

loadCards().catch((error) => {
  $("setup-note").textContent = error.message;
});
