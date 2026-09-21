const worker = new Worker("play-worker.js", { type: "module" });
const pending = new Map();
let requestId = 0;
let cards = {};
let state = null;
let selectedCardId = null;
let stagedPlotSource = null;
let choiceActions = [];
let mulliganSelection = new Set();
let engineReady = false;
let cardsReady = false;

const $ = (id) => document.getElementById(id);

function updateStartAvailability() {
  const ready = engineReady && cardsReady;
  $("mode").disabled = !ready;
  $("seed").disabled = !ready;
  $("randomize-seed").disabled = !ready;
  $("start-game").disabled = !ready;
  $("engine-status").textContent = ready
    ? "Rules engine + card catalogue ready"
    : engineReady
      ? "Loading card catalogue…"
      : "Loading Python rules engine…";
}
const frontNames = ["Left", "Center", "Right"];

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

function plainGameText(value) {
  return String(value ?? "").replace(/\*\*|\*/g, "");
}

function titleCase(value) {
  return String(value ?? "")
    .split(/[-_ ]+/)
    .filter(Boolean)
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(" ");
}

function cardProperties(card) {
  const values = [];
  if (card.type === "subject" && card.role) values.push(titleCase(card.role));
  for (const value of card.classes || []) {
    if (value === "hero") continue;
    const label = titleCase(value);
    if (!values.includes(label)) values.push(label);
  }
  return values;
}

function cardDensityClass(card) {
  const length = plainGameText(card.text || "").length;
  if (length >= 220) return " card-density-max";
  if (length >= 160) return " card-density-dense";
  if (length >= 120) return " card-density-medium";
  return "";
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
    engineReady = true;
    updateStartAvailability();
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
  if (card.type === "plot") {
    const form = titleCase(card.story_form);
    return card.veiled ? form + " · Veiled Story" : form + " · Story";
  }
  if (card.type === "link") return "Bond";
  if (card.type === "stratagem") return "Stratagem";
  if (card.type === "subject" && card.hero) return "Hero · Subject";
  return card.type[0].toUpperCase() + card.type.slice(1);
}

function cardInitials(title) {
  return title
    .replace(/^(the|a|an)\s+/i, "")
    .split(/\s+/)
    .slice(0, 3)
    .map((word) => word[0] || "")
    .join("")
    .toUpperCase();
}

function cardHash(value) {
  let hash = 2166136261;
  for (const char of value) {
    hash ^= char.charCodeAt(0);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function cardVisual(cardId, compact = false) {
  const card = cards[cardId];
  const hash = cardHash(cardId);
  const x = 18 + (hash % 58);
  const y = 15 + ((hash >>> 7) % 35);
  const r = 10 + ((hash >>> 13) % 18);
  const mark = cardInitials(card.title);
  const symbol = card.type === "plot"
    ? (card.veiled ? "◐" : "⌁")
    : { subject: "◆", link: "⛓", name: "✦", stratagem: "⚑" }[card.type] || "•";
  return '<div class="play-card-art' + (compact ? " compact" : "") + '">' +
    '<svg viewBox="0 0 100 62" aria-hidden="true">' +
      '<circle cx="' + x + '" cy="' + y + '" r="' + r + '"></circle>' +
      '<path d="M4 ' + (54 - (hash % 18)) + ' Q 32 ' + (8 + (hash % 20)) +
      ' 52 ' + (34 + ((hash >>> 4) % 20)) + ' T 96 ' + (12 + ((hash >>> 10) % 38)) + '"></path>' +
      '<path d="M8 54 L' + (30 + (hash % 40)) + ' 12 L94 50"></path>' +
    '</svg>' +
    '<span class="play-card-symbol">' + symbol + '</span>' +
    '<b>' + esc(mark) + '</b>' +
  '</div>';
}

function playCardMarkup(cardId, options = {}) {
  const card = cards[cardId];
  const count = options.count || 1;
  const classes = ["play-card", "card-" + card.type];
  if (card.veiled) classes.push("card-scheme");
  if (card.hero) classes.push("card-hero");
  if (options.playable) classes.push("playable");
  if (options.selected) classes.push("selected");
  if (options.mulligan) classes.push("mulligan-card");
  classes.push(cardDensityClass(card).trim());

  const strength = Number.isInteger(card.strength)
    ? '<span class="play-card-strength">' + card.strength + '</span>'
    : "";
  const badge = count > 1
    ? '<span class="copy-badge">×' + count + '</span>'
    : options.copyLabel
      ? '<span class="copy-badge copy-index">' + esc(options.copyLabel) + '</span>'
      : "";
  const footer = options.footer || "";

  return '<article class="' + classes.filter(Boolean).join(" ") + '" ' + (options.attrs || "") + '>' +
    '<div class="play-card-meta"><span>' + esc(cardType(card)) + '</span>' + badge + '</div>' +
    '<h3>' + esc(card.title) + '</h3>' +
    (cardProperties(card).length
      ? '<div class="play-card-properties">' + cardProperties(card).map((value) => '<em>' + esc(value) + '</em>').join(' · ') + '</div>'
      : '') +
    strength +
    cardVisual(cardId) +
    '<div class="play-card-rules">' +
      (card.text ? formatGameText(card.text) : '<em>No special rules.</em>') +
    '</div>' +
    '<footer>' + footer + '</footer>' +
  '</article>';
}

function boardCardMarkup(cardId, role) {
  if (!cardId) return "";
  const card = cards[cardId];
  return '<div class="board-card board-card-' + role + ' card-' + card.type +
    (card.veiled ? " card-scheme" : "") + (card.hero ? " card-hero" : "") + '">' +
    '<div class="board-card-face">' +
      '<span class="board-card-type">' + esc(cardType(card)) + '</span>' +
      '<strong>' + esc(card.title) + '</strong>' +
      cardVisual(cardId, true) +
      (Number.isInteger(card.strength)
        ? '<span class="board-card-strength">' + card.strength + '</span>'
        : "") +
    '</div>' +
  '</div>';
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
  return [card.title, plainGameText(card.text || "")].filter(Boolean).join(" — ");
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
    return '<div class="' + classes.join(" ") + '" ' + attrs + '>' +
      '<span class="empty-slot-mark">＋</span><span>' +
      (rank === "front" ? "Frontline" : "Rear") + '</span></div>';
  }

  return '<div class="' + classes.join(" ") + '" ' + attrs + '>' +
    '<span class="slot-rank">' + esc(slot.rank_name) +
      (rank === "front" ? " · Line Defense +1" : "") + '</span>' +
    '<div class="board-legend">' +
      boardCardMarkup(slot.subject, "subject") +
      (slot.link ? '<div class="board-attachment link">' + boardCardMarkup(slot.link, "link") + '</div>' : "") +
      (slot.name ? '<div class="board-attachment name">' + boardCardMarkup(slot.name, "name") + '</div>' : "") +
    '</div>' +
    '<span class="slot-strength">' + slot.strength + '</span>' +
  '</div>';
}
function renderScheme(owner, front) {
  const scheme = state.schemes[owner][front];
  const targetable = owner === currentViewer() && targetActionsForFront(front).length > 0;
  const classes = ["scheme-marker"];
  if (targetable) classes.push("targetable");
  if (!scheme) classes.push("empty");
  if (scheme?.hidden) classes.push("hidden");
  const attrs = 'data-scheme-owner="' + owner + '" data-scheme-front="' + front + '"';

  if (!scheme) {
    return '<div class="' + classes.join(" ") + '" ' + attrs + '><span>Veiled Story</span><b>empty</b></div>';
  }
  if (scheme.hidden) {
    return '<div class="' + classes.join(" ") + '" ' + attrs + '><span>Veiled Story</span><b>face-down</b></div>';
  }
  return '<div class="' + classes.join(" ") + '" ' + attrs + '><span>Veiled Story</span><b>' +
    esc(cardTitle(scheme.card_id)) + (scheme.revealed ? " · revealed" : "") + '</b></div>';
}

function renderStratagem(owner) {
  const stratagem = state.stratagems?.[owner] || null;
  const classes = ["stratagem-marker"];
  let title = "Stratagem";
  let label = "empty";
  if (stratagem?.hidden) {
    classes.push("hidden");
    label = "face-down";
  } else if (stratagem?.card_id) {
    if (!stratagem.revealed) classes.push("hidden", "known");
    title = cardTitle(stratagem.card_id);
    label = stratagem.revealed ? "revealed" : "face-down";
  }
  return '<div class="' + classes.join(" ") + '"><span>' + esc(title) + '</span><b>' + esc(label) + '</b></div>';
}

function controlClass(front, viewer) {
  const owner = state.front_control[front];
  if (owner == null) return "front-tied";
  return owner === viewer ? "front-winning" : "front-losing";
}

function frontBanner(name, front, bottom, top) {
  const p0 = state.front_strengths[0][front];
  const p1 = state.front_strengths[1][front];
  const topScore = top === 0 ? p0 : p1;
  const bottomScore = bottom === 0 ? p0 : p1;
  const status = state.front_control[front] == null
    ? "Tied"
    : state.front_control[front] === bottom ? "You control" : "Opponent controls";
  return '<div class="front-banner ' + controlClass(front, bottom) + '">' +
    '<span>' + esc(name) + '</span>' +
    '<b><i>' + topScore + '</i><em>—</em><i>' + bottomScore + '</i></b>' +
    '<small>' + status + '</small>' +
  '</div>';
}

function renderRankRow(owner, rank, label) {
  return '<div class="rank-row rank-' + rank + '">' +
    '<span class="rank-label">' + esc(label) + '</span>' +
    frontNames.map((_, front) => renderSlot(owner, front, rank)).join("") +
  '</div>';
}

function renderSchemeRow(owner) {
  return '<div class="scheme-row"><span class="rank-label">Veiled</span>' +
    frontNames.map((_, front) => renderScheme(owner, front)).join("") +
  '</div>';
}

function renderBattlefield() {
  if (state.phase === "mulligan") {
    $("battlefield").innerHTML =
      '<div class="mulligan-placeholder"><strong>Opening mulligan</strong><span>Your cards are below. Settle the opening hand before the battlefield is revealed.</span></div>';
    return;
  }

  const bottom = currentViewer();
  const top = opponentOf(bottom);

  $("battlefield").innerHTML =
    '<div class="battlefield-table">' +
      '<div class="battle-stratagem-zone opponent"><span>Opponent Stratagem</span>' + renderStratagem(top) + '</div>' +
      '<div class="front-banner-row"><span></span>' +
        frontNames.map((name, front) => frontBanner(name, front, bottom, top)).join("") +
      '</div>' +
      '<div class="army-side opponent-army">' +
        renderSchemeRow(top) +
        renderRankRow(top, "rear", "Rear") +
        renderRankRow(top, "front", "Frontline") +
      '</div>' +
      '<div class="battle-line-wide"><span>THE BATTLE LINE</span></div>' +
      '<div class="army-side player-army">' +
        renderRankRow(bottom, "front", "Frontline") +
        renderRankRow(bottom, "rear", "Rear") +
        renderSchemeRow(bottom) +
      '</div>' +
      '<div class="battle-stratagem-zone player"><span>Your Stratagem</span>' + renderStratagem(bottom) + '</div>' +
    '</div>';

  bindBoardTargets();
}

function victoryPips(count) {
  return '<span class="victory-pips">' +
    [0, 1].map((index) => '<i class="' + (index < count ? "won" : "") + '"></i>').join("") +
  '</span>';
}

function renderStrip() {
  if (state.phase === "mulligan") {
    $("match-strip").innerHTML =
      '<div class="battle-medallion"><small>Opening</small><strong>Mulligan</strong></div>' +
      '<div class="turn-marker">Player ' + (state.active_player + 1) + ' · choose up to 2 returns</div>';
    $("pass-button").hidden = true;
    return;
  }

  const viewer = currentViewer();
  const opponent = opponentOf(viewer);
  const winnerText = state.winner == null ? "" : " · Player " + (state.winner + 1) + " wins";

  $("match-strip").innerHTML =
    '<div class="score-player ' + (state.active_player === opponent ? "active" : "") + '">' +
      '<span>P' + (opponent + 1) + '</span>' + victoryPips(state.players[opponent].victories) +
    '</div>' +
    '<div class="battle-medallion"><small>Battle</small><strong>' + state.battle + '</strong></div>' +
    '<div class="turn-marker">Turn · Player ' + (state.active_player + 1) + winnerText + '</div>' +
    '<div class="score-player ' + (state.active_player === viewer ? "active" : "") + '">' +
      '<span>P' + (viewer + 1) + '</span>' + victoryPips(state.players[viewer].victories) +
    '</div>';

  const pass = actionForPass();
  const button = $("pass-button");
  button.hidden = !pass || state.viewer == null;
  button.disabled = !pass || state.viewer == null;
  button.classList.toggle("danger-pass", !!pass && state.players[opponentOf(currentViewer())].passed);
  button.textContent = state.players[opponentOf(currentViewer())].passed ? "Pass · score Battle" : "Pass";
}

function renderOpponentRack() {
  if (!state) return;
  const viewer = currentViewer();
  const opponent = opponentOf(viewer);
  const ps = state.players[opponent];
  const handCount = ps.hand_count || 0;

  $("opponent-label").textContent = "Player " + (opponent + 1) + (ps.passed ? " · PASSED" : "");

  const visibleBacks = Math.min(handCount, 12);
  $("opponent-hand").innerHTML = Array.from({ length: visibleBacks }, (_, index) => {
    const center = (visibleBacks - 1) / 2;
    const rotation = (index - center) * 2.2;
    const lift = Math.abs(index - center) * 1.2;
    return '<span class="card-back" style="--back-rot:' + rotation + 'deg;--back-y:' + lift + 'px"></span>';
  }).join("") + (handCount > visibleBacks ? '<b class="hand-overflow">+' + (handCount - visibleBacks) + '</b>' : "");

  const discard = ps.discard || [];
  const topDiscard = discard.length ? cardTitle(discard[discard.length - 1]) : "Empty";
  $("opponent-piles").innerHTML =
    '<div class="rack-pile deck-pile"><span>Deck</span><b>' + ps.deck_count + '</b></div>' +
    '<div class="rack-pile discard-pile"><span>Discard</span><b>' + esc(topDiscard) + '</b><small>' + discard.length + ' cards</small></div>';

  const own = state.players[viewer];
  const ownDiscard = own.discard || [];
  const ownTopDiscard = ownDiscard.length ? cardTitle(ownDiscard[ownDiscard.length - 1]) : "Empty";
  $("player-piles").innerHTML =
    '<div class="rack-pile deck-pile"><span>Deck</span><b>' + own.deck_count + '</b></div>' +
    '<div class="rack-pile discard-pile"><span>Discard</span><b>' + esc(ownTopDiscard) + '</b><small>' + ownDiscard.length + ' cards</small></div>';
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
  if (actions.some((a) => a.kind === "PlayLink")) return "Choose one of your Subjects without a Bond.";
  if (actions.some((a) => a.kind === "PlayName")) return "Choose an open Bond. If movement is possible, you will choose it next.";
  if (actions.some((a) => a.kind === "PlayScheme")) return "Choose a Front to set this Veiled Story face-down.";
  if (actions.some((a) => a.kind === "SetStratagem")) return "Set this face-down in your Battle-wide Stratagem slot. You still take your normal action.";
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
    if (!action.move_to) return "Attach the Name here · stay";
    return "Attach the Name here · move the Subject to " + action.move_to.front_name + " " + action.move_to.rank_name;
  }
  return action.label;
}

function renderChoiceTray() {
  const tray = $("choice-tray");
  let actions = choiceActions;
  if (!actions.length && selectedCardId) {
    const direct = selectedActions().filter((a) =>
      (a.kind === "PlayPlot" && a.targets.length === 0) ||
      a.kind === "SetStratagem"
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

    const totals = new Map();
    for (const cardId of state.hand) totals.set(cardId, (totals.get(cardId) || 0) + 1);
    const seen = new Map();

    hand.innerHTML = state.hand.map((cardId, index) => {
      const ordinal = (seen.get(cardId) || 0) + 1;
      seen.set(cardId, ordinal);
      const total = totals.get(cardId) || 1;
      const selected = mulliganSelection.has(index);
      return playCardMarkup(cardId, {
        selected,
        mulligan: true,
        copyLabel: total > 1 ? ordinal + "/" + total : "",
        attrs: 'data-mulligan-index="' + index + '"',
        footer: selected ? "RETURN THIS COPY" : "KEEP",
      });
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
  const handCount = state.hand.length;
  const center = (handCount - 1) / 2;

  hand.innerHTML = state.hand.map((cardId, index) => {
    const playable = state.legal_actions.some((action) => action.card_id === cardId);
    const rotation = (index - center) * Math.min(1.45, 11 / Math.max(1, handCount));
    const offset = Math.abs(index - center) * 1.25;
    return playCardMarkup(cardId, {
      playable,
      selected: selectedCardId === cardId,
      attrs: 'data-hand-card="' + esc(cardId) + '" draggable="' + playable +
        '" style="--fan-rot:' + rotation + 'deg;--fan-y:' + offset + 'px"',
      footer: playable ? "SELECT OR DRAG TO PLAY" : "NO LEGAL PLAY",
    });
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
  renderOpponentRack();
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
  cardsReady = true;
  updateStartAvailability();
}

function freshSeed() {
  const values = new Uint32Array(1);
  crypto.getRandomValues(values);
  return (values[0] % 2147483646) + 1;
}

function randomizeSeed() {
  $("seed").value = String(freshSeed());
}

randomizeSeed();
updateStartAvailability();

$("randomize-seed").addEventListener("click", randomizeSeed);

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
  randomizeSeed();
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