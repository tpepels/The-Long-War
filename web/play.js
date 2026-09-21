const worker = new Worker("play-worker.js", { type: "module" });
const pending = new Map();
let requestId = 0;
let cards = {};
let state = null;
let selectedCardId = null;
let stagedPlotSource = null;
let choiceActions = [];
let mulliganSelection = new Set();

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

function currentViewer() {
  if (!state) return 0;
  return state.viewer == null ? state.active_player : state.viewer;
}

function opponentOf(player) {
  return 1 - player;
}

function boardSlot(owner, front, rank) {
  return state.board[owner].find((slot) => slot.front === front && slot.rank === rank);
}

function locEquals(a, owner, front, rank) {
  return !!a && a.player === owner && a.front === front && a.rank === rank;
}

function posEquals(a, front, rank) {
  return !!a && a.front === front && a.rank === rank;
}

function selectedActions() {
  if (!state || !selectedCardId) return [];
  return state.legal_actions.filter((action) => action.card_id === selectedCardId);
}

function actionForPass() {
  if (!state || state.phase === "mulligan") return null;
  return state.legal_actions.find((action) => action.kind === "Pass") || null;
}

function targetActionsForSlot(owner, front, rank) {
  const actions = selectedActions();
  const matches = [];
  for (const action of actions) {
    if (["PlaySubject", "PlayLink", "PlayName"].includes(action.kind)) {
      if (owner === currentViewer() && posEquals(action.position, front, rank)) matches.push(action);
      continue;
    }
    if (action.kind !== "PlayPlot") continue;
    if (action.targets.length === 1) {
      if (locEquals(action.targets[0], owner, front, rank)) matches.push(action);
      continue;
    }
    if (action.targets.length === 2) {
      if (!stagedPlotSource) {
        if (locEquals(action.targets[0], owner, front, rank)) matches.push(action);
      } else if (
        locEquals(action.targets[0], stagedPlotSource.player, stagedPlotSource.front, stagedPlotSource.rank) &&
        locEquals(action.targets[1], owner, front, rank)
      ) {
        matches.push(action);
      }
    }
  }
  return matches;
}

function targetActionsForFront(front) {
  return selectedActions().filter((action) => action.kind === "PlayScheme" && action.front === front);
}

function cardTooltip(cardId) {
  const card = cards[cardId];
  if (!card) return "";
  return [card.title, card.text || ""].filter(Boolean).join(" — ");
}

function component(cardId, cls) {
  if (!cardId) return "";
  return '<span class="legend-component ' + cls + '" title="' + esc(cardTooltip(cardId)) + '">' +
    esc(cardTitle(cardId)) + "</span>";
}

function renderSlot(owner, front, rank) {
  const slot = boardSlot(owner, front, rank);
  const targetable = targetActionsForSlot(owner, front, rank).length > 0;
  const classes = ["digital-slot", slot?.subject ? "occupied" : "empty"];
  if (targetable) classes.push("targetable");
  if (stagedPlotSource && locEquals(stagedPlotSource, owner, front, rank)) classes.push("staged-source");

  const attrs =
    'data-board-owner="' + owner + '" data-board-front="' + front + '" data-board-rank="' + rank + '"';

  if (!slot?.subject) {
    return '<div class="' + classes.join(" ") + '" ' + attrs + '><span>' +
      (rank === "front" ? "Frontline" : "Rear") + "</span></div>";
  }

  return '<div class="' + classes.join(" ") + '" ' + attrs + ">" +
    '<span class="slot-rank">' + esc(slot.rank_name) + "</span>" +
    '<div class="legend-stack">' +
      component(slot.subject, "subject") +
      component(slot.link, "link") +
      component(slot.name, "name") +
    "</div>" +
    '<span class="slot-strength">' + slot.strength + "</span>" +
  "</div>";
}

function renderScheme(owner, front) {
  const scheme = state.schemes[owner][front];
  const targetable = owner === currentViewer() && targetActionsForFront(front).length > 0;
  const classes = ["scheme-marker"];
  if (targetable) classes.push("targetable");
  if (!scheme) classes.push("empty");
  if (scheme?.hidden) classes.push("hidden");
  const attrs = 'data-scheme-owner="' + owner + '" data-scheme-front="' + front + '"';
  if (!scheme) return '<div class="' + classes.join(" ") + '" ' + attrs + ">Scheme space</div>";
  if (scheme.hidden) return '<div class="' + classes.join(" ") + '" ' + attrs + ">Face-down Scheme</div>";
  return '<div class="' + classes.join(" ") + '" ' + attrs + ">" +
    esc(cardTitle(scheme.card_id)) + (scheme.revealed ? " · revealed" : "") + "</div>";
}

function controlClass(front, viewer) {
  const owner = state.front_control[front];
  if (owner == null) return "front-tied";
  return owner === viewer ? "front-winning" : "front-losing";
}

function renderBattlefield() {
  if (state.phase === "mulligan") {
    $("battlefield").innerHTML =
      '<div class="mulligan-placeholder"><strong>Opening mulligan</strong><span>The battlefield stays hidden until both opening hands are settled.</span></div>';
    return;
  }
  const bottom = currentViewer();
  const top = opponentOf(bottom);
  $("battlefield").innerHTML = frontNames.map((name, front) => {
    const p0 = state.front_strengths[0][front];
    const p1 = state.front_strengths[1][front];
    const topScore = top === 0 ? p0 : p1;
    const bottomScore = bottom === 0 ? p0 : p1;
    return '<section class="digital-front ' + controlClass(front, bottom) + '" data-front="' + front + '">' +
      "<header><div><strong>" + name + "</strong><small>" +
      (state.front_control[front] == null ? "Tied" : state.front_control[front] === bottom ? "You control" : "Opponent controls") +
      "</small></div><span>P" + (top + 1) + " " + topScore + " · P" + (bottom + 1) + " " + bottomScore + "</span></header>" +
      '<div class="front-side opponent-side"><div class="side-label">Player ' + (top + 1) + "</div>" +
        renderScheme(top, front) + renderSlot(top, front, "rear") + renderSlot(top, front, "front") +
      "</div>" +
      '<div class="battle-line">battle line</div>' +
      '<div class="front-side player-side"><div class="side-label">Player ' + (bottom + 1) + "</div>" +
        renderSlot(bottom, front, "front") + renderSlot(bottom, front, "rear") + renderScheme(bottom, front) +
      "</div></section>";
  }).join("");
  bindBoardTargets();
}

function renderStrip() {
  if (state.phase === "mulligan") {
    $("match-strip").innerHTML =
      "<strong>Opening mulligan</strong>" +
      "<span>Player " + (state.active_player + 1) + "</span>" +
      "<span>Select up to 2 cards to return</span>";
    $("pass-button").hidden = true;
    return;
  }
  const winnerText = state.winner == null ? "" : " · Player " + (state.winner + 1) + " wins";
  $("match-strip").innerHTML =
    "<strong>Battle " + state.battle + "</strong>" +
    "<span>P1 victories " + state.players[0].victories + "/2</span>" +
    "<span>P2 victories " + state.players[1].victories + "/2</span>" +
    "<span>Turn · Player " + (state.active_player + 1) + winnerText + "</span>" +
    "<span>Hands " + state.players[0].hand_count + " / " + state.players[1].hand_count + "</span>";

  const pass = actionForPass();
  const button = $("pass-button");
  button.hidden = !pass || state.viewer == null;
  button.disabled = !pass || state.viewer == null;
  button.classList.toggle("danger-pass", !!pass && state.players[opponentOf(currentViewer())].passed);
  button.textContent = state.players[opponentOf(currentViewer())].passed ? "Pass · score Battle" : "Pass";
}

function renderPrivacy() {
  const gate = $("privacy-gate");
  if (!state.needs_reveal) {
    gate.hidden = true;
    return;
  }
  gate.hidden = false;
  clearSelection();
  const opening = state.phase === "mulligan";
  gate.innerHTML =
    "<p>Pass the device to <strong>Player " + (state.active_player + 1) + "</strong>" +
    (opening ? " for the opening mulligan." : ".") + "</p>" +
    '<button type="button" id="reveal-hand">Reveal Player ' + (state.active_player + 1) +
    (opening ? " opening hand" : " hand") + "</button>";
  $("reveal-hand").addEventListener("click", async () => {
    await runBusy(async () => {
      state = await request({ type: "view", viewer: state.active_player });
      render();
    });
  });
}

function clearSelection() {
  selectedCardId = null;
  stagedPlotSource = null;
  choiceActions = [];
  mulliganSelection = new Set();
}

function selectCard(cardId) {
  if (selectedCardId === cardId) {
    clearSelection();
  } else {
    selectedCardId = cardId;
    stagedPlotSource = null;
    choiceActions = [];
  }
  renderInteractiveState();
}

function interactionHintFor(card) {
  const actions = selectedActions();
  if (!actions.length) return "This card has no legal play right now.";
  if (actions.some((a) => a.kind === "PlaySubject")) return "Choose an empty battlefield position.";
  if (actions.some((a) => a.kind === "PlayLink")) return "Choose one of your Subjects without a Link.";
  if (actions.some((a) => a.kind === "PlayName")) return "Choose an open Link. If movement is possible, you will choose it next.";
  if (actions.some((a) => a.kind === "PlayScheme")) return "Choose a Front to set this Scheme face-down.";
  if (actions.some((a) => a.kind === "PlayPlot")) {
    if (stagedPlotSource) return "Now choose the destination for " + card.title + ".";
    return actions.some((a) => a.targets.length === 2)
      ? "Choose the first target; the legal destinations will then light up."
      : "Choose a highlighted target on the battlefield.";
  }
  return "Choose a legal action.";
}

function renderInteraction() {
  const title = $("interaction-title");
  const hint = $("interaction-hint");
  const cancel = $("cancel-selection");
  const tray = $("choice-tray");

  if (state.phase === "mulligan") {
    if (state.viewer == null) {
      title.textContent = "Hidden opening hand";
      hint.textContent = "Pass the device, then reveal the next player's opening hand.";
    } else {
      title.textContent = "Opening mulligan";
      hint.textContent = "Select up to two cards to shuffle back, then confirm. You draw the same number of replacements.";
    }
    cancel.hidden = true;
    tray.hidden = true;
    return;
  }

  if (state.phase === "complete") {
    title.textContent = "Match complete";
    hint.textContent = "Player " + (state.winner + 1) + " wins the match.";
    cancel.hidden = true;
    tray.hidden = true;
    return;
  }

  if (state.viewer == null) {
    title.textContent = "Hidden hand";
    hint.textContent = "Pass the device, then reveal the active player’s hand.";
    cancel.hidden = true;
    tray.hidden = true;
    return;
  }

  if (!selectedCardId) {
    const choose = state.legal_actions.filter((a) => a.kind === "ChooseFirst");
    if (choose.length) {
      title.textContent = "Choose the next first player";
      hint.textContent = "You lost the previous Battle, so you choose who takes initiative.";
    } else {
      title.textContent = "Choose a card";
      hint.textContent = "Click a card, or drag it onto a highlighted position. Press P to Pass.";
    }
    cancel.hidden = true;
  } else {
    const card = cards[selectedCardId];
    title.textContent = card.title;
    let message = interactionHintFor(card);
    if ($("show-reasons").checked) {
      const reason = selectedActions()[0]?.reason;
      if (reason) message += " " + reason;
    }
    hint.textContent = message;
    cancel.hidden = false;
  }

  renderChoiceTray();
}

function choiceLabel(action) {
  if (action.kind === "PlayName") {
    if (!action.move_to) return "Complete here · stay";
    return "Complete here · move to " + action.move_to.front_name + " " + action.move_to.rank_name;
  }
  return action.label;
}

function renderChoiceTray() {
  const tray = $("choice-tray");
  let actions = choiceActions;
  if (!actions.length && selectedCardId) {
    const direct = selectedActions().filter((a) =>
      a.kind === "PlayPlot" && a.targets.length === 0
    );
    if (direct.length === 1) actions = direct;
  }
  if (!actions.length) {
    tray.hidden = true;
    tray.innerHTML = "";
    return;
  }
  tray.hidden = false;
  tray.innerHTML = "<strong>Choose:</strong>" + actions.map((action) =>
    '<button type="button" data-choice-key="' + encodeURIComponent(action.key) + '">' +
    esc(choiceLabel(action)) + "</button>"
  ).join("");
  tray.querySelectorAll("[data-choice-key]").forEach((button) => {
    button.addEventListener("click", () => {
      const action = state.legal_actions.find((a) => a.key === decodeURIComponent(button.dataset.choiceKey));
      if (action) executeAction(action);
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

  if (state.phase === "mulligan") {
    $("hand-title").textContent =
      "Player " + (state.viewer + 1) + " opening hand · choose up to " + state.mulligan_limit;
    hand.innerHTML = state.hand.map((cardId, index) => {
      const card = cards[cardId];
      const selected = mulliganSelection.has(index);
      const classes = ["hand-card", "mulligan-card", "card-" + card.type];
      if (selected) classes.push("selected");
      return '<article class="' + classes.join(" ") + '" data-mulligan-index="' + index + '">' +
        "<header><span>" + esc(cardType(card)) + "</span><strong>" + esc(card.title) + "</strong>" +
        (Number.isInteger(card.strength) ? "<b>" + card.strength + "</b>" : "") + "</header>" +
        "<p>" + esc(card.text || "No rules text.") + "</p>" +
        "<footer><span>" + (selected ? "Return this card" : "Keep") + "</span></footer></article>";
    }).join("");

    hand.querySelectorAll("[data-mulligan-index]").forEach((cardEl) => {
      cardEl.addEventListener("click", () => {
        const index = Number(cardEl.dataset.mulliganIndex);
        if (mulliganSelection.has(index)) {
          mulliganSelection.delete(index);
        } else if (mulliganSelection.size < state.mulligan_limit) {
          mulliganSelection.add(index);
        }
        renderHand();
        renderInteraction();
      });
    });

    const count = mulliganSelection.size;
    actions.innerHTML =
      '<button type="button" class="initiative-button" id="confirm-mulligan">' +
      (count ? "Return " + count + " card" + (count === 1 ? "" : "s") : "Keep this hand") +
      "</button>";
    $("confirm-mulligan").addEventListener("click", submitMulligan);
    return;
  }

  $("hand-title").textContent = "Player " + (state.viewer + 1) + " hand · " + state.hand.length + " cards";
  const grouped = new Map();
  for (const cardId of state.hand) grouped.set(cardId, (grouped.get(cardId) || 0) + 1);

  hand.innerHTML = [...grouped.entries()].map(([cardId, count]) => {
    const card = cards[cardId];
    const playable = state.legal_actions.some((action) => action.card_id === cardId);
    const classes = ["hand-card", "card-" + card.type];
    if (playable) classes.push("playable");
    if (selectedCardId === cardId) classes.push("selected");
    return '<article class="' + classes.join(" ") + '" data-hand-card="' + esc(cardId) + '" draggable="' + playable + '">' +
      "<header><span>" + esc(cardType(card)) + (count > 1 ? " ×" + count : "") + "</span>" +
      "<strong>" + esc(card.title) + "</strong>" +
      (Number.isInteger(card.strength) ? "<b>" + card.strength + "</b>" : "") +
      "</header><p>" + esc(card.text || "No rules text.") + "</p>" +
      '<footer><span>' + (playable ? "Select to play" : "No legal play") + "</span></footer></article>";
  }).join("");

  hand.querySelectorAll("[data-hand-card]").forEach((cardEl) => {
    const cardId = cardEl.dataset.handCard;
    cardEl.addEventListener("click", () => {
      if (state.legal_actions.some((a) => a.card_id === cardId)) selectCard(cardId);
    });
    cardEl.addEventListener("dragstart", (event) => {
      if (!state.legal_actions.some((a) => a.card_id === cardId)) {
        event.preventDefault();
        return;
      }
      selectedCardId = cardId;
      stagedPlotSource = null;
      choiceActions = [];
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", cardId);
      syncTargetClasses();
      renderInteraction();
    });
  });

  const chooseActions = state.legal_actions.filter((a) => a.kind === "ChooseFirst");
  actions.innerHTML = chooseActions.map((action) =>
    '<button type="button" class="initiative-button" data-choice-first="' + encodeURIComponent(action.key) + '">' +
    "Player " + (action.choose_player + 1) + " starts</button>"
  ).join("");
  actions.querySelectorAll("[data-choice-first]").forEach((button) => {
    button.addEventListener("click", () => {
      const action = state.legal_actions.find((a) => a.key === decodeURIComponent(button.dataset.choiceFirst));
      if (action) executeAction(action);
    });
  });
}

function renderPublicZones() {
  if (state.phase === "mulligan") {
    $("public-zones").innerHTML = "";
    return;
  }
  const viewer = currentViewer();
  const order = [viewer, opponentOf(viewer)];
  $("public-zones").innerHTML = order.map((player) => {
    const ps = state.players[player];
    const discard = [...ps.discard].reverse();
    return '<details class="public-zone"><summary>Player ' + (player + 1) +
      " · deck " + ps.deck_count + " · discard " + discard.length +
      (ps.passed ? " · PASSED" : "") + "</summary>" +
      '<div class="discard-list">' +
      (discard.length ? discard.map((id) => "<span>" + esc(cardTitle(id)) + "</span>").join("") : "<span>Empty discard</span>") +
      "</div></details>";
  }).join("");
}

function renderHistory() {
  $("history").innerHTML = state.log.map((line) => "<li>" + esc(line) + "</li>").join("");
}

function bindBoardTargets() {
  document.querySelectorAll("[data-board-owner]").forEach((el) => {
    const owner = Number(el.dataset.boardOwner);
    const front = Number(el.dataset.boardFront);
    const rank = el.dataset.boardRank;
    el.addEventListener("click", () => handleBoardTarget(owner, front, rank));
    el.addEventListener("dragover", (event) => {
      if (targetActionsForSlot(owner, front, rank).length) {
        event.preventDefault();
        event.dataTransfer.dropEffect = "move";
      }
    });
    el.addEventListener("drop", (event) => {
      event.preventDefault();
      handleBoardTarget(owner, front, rank);
    });
  });
  document.querySelectorAll("[data-scheme-front]").forEach((el) => {
    const owner = Number(el.dataset.schemeOwner);
    const front = Number(el.dataset.schemeFront);
    el.addEventListener("click", () => {
      if (owner === currentViewer()) handleFrontTarget(front);
    });
    el.addEventListener("dragover", (event) => {
      if (owner === currentViewer() && targetActionsForFront(front).length) event.preventDefault();
    });
    el.addEventListener("drop", (event) => {
      event.preventDefault();
      if (owner === currentViewer()) handleFrontTarget(front);
    });
  });
}

function handleBoardTarget(owner, front, rank) {
  if (!selectedCardId) return;
  const all = selectedActions();
  const isTwoTargetPlot = all.some((a) => a.kind === "PlayPlot" && a.targets.length === 2);
  if (isTwoTargetPlot && !stagedPlotSource) {
    const sourceMatches = all.filter((a) => a.targets.length === 2 && locEquals(a.targets[0], owner, front, rank));
    if (!sourceMatches.length) return;
    stagedPlotSource = { player: owner, front, rank };
    choiceActions = [];
    renderInteractiveState();
    return;
  }

  const matches = targetActionsForSlot(owner, front, rank);
  if (matches.length === 1) {
    executeAction(matches[0]);
  } else if (matches.length > 1) {
    choiceActions = matches;
    renderChoiceTray();
  }
}

function handleFrontTarget(front) {
  if (!selectedCardId) return;
  const matches = targetActionsForFront(front);
  if (matches.length === 1) executeAction(matches[0]);
  else if (matches.length > 1) { choiceActions = matches; renderChoiceTray(); }
}

function syncTargetClasses() {
  document.querySelectorAll("[data-board-owner]").forEach((el) => {
    const owner = Number(el.dataset.boardOwner);
    const front = Number(el.dataset.boardFront);
    const rank = el.dataset.boardRank;
    el.classList.toggle("targetable", targetActionsForSlot(owner, front, rank).length > 0);
    el.classList.toggle("staged-source", !!stagedPlotSource && locEquals(stagedPlotSource, owner, front, rank));
  });
  document.querySelectorAll("[data-scheme-front]").forEach((el) => {
    const owner = Number(el.dataset.schemeOwner);
    const front = Number(el.dataset.schemeFront);
    el.classList.toggle("targetable", owner === currentViewer() && targetActionsForFront(front).length > 0);
  });
}

function renderInteractiveState() {
  renderBattlefield();
  renderHand();
  renderInteraction();
}

async function submitMulligan() {
  if (!state || state.phase !== "mulligan" || state.viewer == null) return;
  const indices = [...mulliganSelection].sort((a, b) => a - b);
  await runBusy(async () => {
    state = await request({
      type: "mulligan",
      indices,
      viewer: state.viewer,
    });
    clearSelection();
    render();
  });
}

async function executeAction(action) {
  if (!action || state.viewer == null) return;
  await runBusy(async () => {
    state = await request({ type: "act", key: action.key, viewer: state.viewer });
    clearSelection();
    render();
  });
}

function render() {
  $("game").hidden = false;
  renderStrip();
  renderPrivacy();
  renderBattlefield();
  renderPublicZones();
  renderHand();
  renderInteraction();
  renderHistory();
  if (state.phase === "complete") {
    $("privacy-gate").hidden = false;
    $("privacy-gate").innerHTML = "<p><strong>Player " + (state.winner + 1) + " wins the match.</strong></p>";
  }
}

async function runBusy(fn) {
  document.body.classList.add("is-busy");
  $("engine-status").textContent = "Resolving turn…";
  try {
    await fn();
    $("engine-status").textContent = "Rules engine ready";
  } catch (error) {
    $("engine-status").textContent = "Action failed";
    window.alert(error.message);
  } finally {
    document.body.classList.remove("is-busy");
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
    clearSelection();
    $("play-setup").hidden = true;
    render();
  });
});

$("restart").addEventListener("click", () => {
  state = null;
  clearSelection();
  $("game").hidden = true;
  $("play-setup").hidden = false;
});

$("show-reasons").addEventListener("change", () => {
  if (state) renderInteraction();
});

$("cancel-selection").addEventListener("click", () => {
  clearSelection();
  renderInteractiveState();
});

$("pass-button").addEventListener("click", () => {
  const pass = actionForPass();
  if (pass) executeAction(pass);
});

document.addEventListener("keydown", (event) => {
  if (!state || state.viewer == null || state.phase === "complete") return;
  if (state.phase === "mulligan") {
    if (event.key === "Escape") {
      mulliganSelection = new Set();
      renderHand();
      renderInteraction();
    }
    return;
  }
  if (event.key === "Escape") {
    clearSelection();
    renderInteractiveState();
  }
  if ((event.key === "p" || event.key === "P") && !event.metaKey && !event.ctrlKey) {
    const pass = actionForPass();
    if (pass) executeAction(pass);
  }
});

loadCards().catch((error) => { $("setup-note").textContent = error.message; });