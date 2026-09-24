import { BrowserSession, initializeBrowserEngine } from "./browser-engine.mjs";

let session = null;
let cardData = null;
let referenceDeck = null;
let cards = {};
let state = null;
let selectedCardId = null;
let stagedPlotSource = null;
let choiceActions = [];
let mulliganSelection = new Set();
let cardsReady = false;
let aiStepTimer = null;
let actionBannerTimer = null;
let lastShownActionId = 0;
let openingAnnouncementShown = false;

const moduleUrl = new URL(import.meta.url);
const buildVersion = moduleUrl.searchParams.get("v") || "";

function dataUrl(path) {
  const url = new URL(path, moduleUrl);
  if (buildVersion) url.searchParams.set("v", buildVersion);
  return url;
}

const $ = (id) => document.getElementById(id);

function updateStartAvailability() {
  const ready = cardsReady;
  $("mode").disabled = !ready;
  $("seed").disabled = !ready;
  $("randomize-seed").disabled = !ready;
  $("start-game").disabled = !ready;
  $("engine-status").textContent = ready
    ? "Ready"
    : "Loading game…";
}
const frontNames = ["Left", "Center", "Right"];

function esc(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

const TERM_HINTS = {
  "battle": "A round of play. Control at least two of the three Fronts to win it.",
  "bond": "A formation component. It may be prepared before the Subject; Subject-dependent text stays inactive until a Subject is present.",
  "discard": "Move a card to its owner's discard pile.",
  "discarded": "Moved to the discard pile.",
  "discard pile": "Public cards that have been discarded or cleared from the battlefield.",
  "draw": "Spend your normal action to draw 1 card. You may do this once per Battle.",
  "front": "One of the three lanes: Left, Center, or Right.",
  "frontline": "The position nearest the Battle Line. It normally receives +1 Line Defense.",
  "frontline subject": "The Subject occupying the Frontline position of that Front.",
  "frontline subjects": "Subjects occupying Frontline positions.",
  "line defense": "The default +1 Strength bonus given to a Subject in the Frontline.",
  "move": "Relocate a Subject, keeping its attached Bond and Name unless the effect says otherwise.",
  "name": "A Unique formation component. It may be prepared before the Subject or Bond; Subject-dependent text stays inactive until a Subject is present.",
  "pass": "End your participation in this Battle. You take no more turns until the next Battle.",
  "passes": "Pass ends that player's participation in the current Battle; they take no more turns.",
  "rear": "The position behind the Frontline in the same Front.",
  "rear subject": "The Subject occupying the Rear position of that Front.",
  "rear subjects": "Subjects occupying Rear positions.",
  "stories": "Story cards change the battlefield without occupying a Subject position.",
  "story": "A card that resolves its effect and is then discarded.",
  "strength": "The value compared in each Front. Higher total Strength controls that Front.",
  "subject": "The unit or place that activates a formation's Strength and Subject-dependent Bond or Name text.",
  "subjects": "Cards that activate formations in Frontline or Rear positions.",
  "prepared": "A Bond or Name already placed in a formation before its Subject. It remains inactive where text depends on a Subject.",
  "veiled stories": "Stories set face-down in a Front and revealed when their trigger occurs.",
  "veiled story": "A Story set face-down in a Front and revealed when its trigger occurs.",
  "adjacent": "Immediately left or right in the same rank.",
  "adjacent subject": "A Subject immediately left or right in the same rank.",
  "adjacent subjects": "Subjects immediately left or right in the same rank.",
  "return": "Move a card from the battlefield back to its owner's hand."
};

function termMarkup(label) {
  const key = String(label).trim().toLowerCase();
  const hint = TERM_HINTS[key] || "An important game term. See the rulebook for its full definition.";
  return '<strong class="game-term" data-term-hint="' + esc(hint) + '">' + label + '</strong>';
}

function formatGameText(value) {
  return esc(value)
    .replace(/\*\*([^*]+)\*\*/g, (_, label) => termMarkup(label))
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

function cardPropertyMarkup(card) {
  const classes = (card.classes || [])
    .filter((value) => value !== "hero" && value !== card.role)
    .map((value) => titleCase(value));
  const role = card.type === "subject" && card.role
    ? '<span class="play-card-role"><strong>' + esc(titleCase(card.role)) + '</strong><span>' +
      esc(window.CardRules.roleHint(card)) + '</span></span>'
    : "";
  const classMarkup = classes.length
    ? '<span class="play-card-classes">' + classes.map((value) => '<em>' + esc(value) + '</em>').join(' · ') + '</span>'
    : '<span class="play-card-classes">&nbsp;</span>';
  return role + classMarkup;
}

async function request(payload) {
  // Yield once so busy/loading UI paints before the small synchronous rules step.
  await new Promise((resolve) => setTimeout(resolve, 0));

  if (payload.type === "new_game") {
    if (!cardData || !referenceDeck) throw new Error("Game data is not loaded yet.");
    session?.destroy();
    session = new BrowserSession(cardData, referenceDeck, payload.mode, payload.seed);
    return session.snapshot(payload.mode === "hotseat" ? null : 0);
  }
  if (!session) throw new Error("Start a match first.");
  if (payload.type === "view") return session.view(payload.viewer);
  if (payload.type === "act") return session.act(payload.key, payload.viewer);
  if (payload.type === "ai_step") return session.aiStep();
  if (payload.type === "mulligan") return session.mulligan(payload.indices || [], payload.viewer);
  throw new Error("Unknown game request: " + payload.type);
}

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
  const mark = cardInitials(card.title);
  const symbol = card.type === "plot"
    ? (card.veiled ? "◐" : "⌁")
    : { subject: "◆", link: "⛓", name: "✦", stratagem: "⚑" }[card.type] || "•";
  return '<div class="play-card-art motif-' + (hash % 5) + (compact ? " compact" : "") + '">' +
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

  const strength = Number.isInteger(card.strength)
    ? '<span class="play-card-strength">' + card.strength + '</span>'
    : "";
  const badge = count > 1
    ? '<span class="copy-badge">×' + count + '</span>'
    : options.copyLabel
      ? '<span class="copy-badge copy-index">' + esc(options.copyLabel) + '</span>'
      : "";
  const footer = options.footer || "";
  const propertyMarkup = cardPropertyMarkup(card);

  return '<button type="button" class="' + classes.filter(Boolean).join(" ") + '" data-card-id="' + esc(cardId) + '" ' + (options.attrs || "") + '>' +
    '<div class="play-card-meta"><span>' + esc(cardType(card)) + '</span>' + badge + '</div>' +
    '<h3>' + esc(card.title) + '</h3>' +
    '<div class="play-card-properties">' + propertyMarkup + '</div>' +
    strength +
    '<div class="play-card-rules">' +
      window.CardRules.markup(card, formatGameText, '<em>No special rules.</em>') +
    '</div>' +
    '<footer>' + footer + '</footer>' +
  '</button>';
}

function boardCardMarkup(cardId, role, owner) {
  if (!cardId) return "";
  const card = cards[cardId];
  return '<button type="button" class="board-card board-card-' + role + ' card-' + card.type +
    (card.veiled ? " card-scheme" : "") + (card.hero ? " card-hero" : "") +
    '" data-inspect-card="' + esc(cardId) + '" data-inspect-owner="' + owner + '" data-inspect-zone="' + esc(role) +
    '" aria-label="Inspect ' + esc(card.title) + '">' +
    '<span class="board-card-face">' +
      '<span class="board-card-type">' + esc(cardType(card)) + '</span>' +
      '<strong>' + esc(card.title) + '</strong>' +
      (Number.isInteger(card.strength)
        ? '<span class="board-card-strength">' + card.strength + '</span>'
        : "") +
    '</span>' +
  '</button>';
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

function actionForDraw() {
  if (!state || state.phase === "mulligan") return null;
  return state.legal_actions.find((action) => action.kind === "Draw") || null;
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
  const hasFormation = Boolean(slot?.subject || slot?.link || slot?.name);
  const classes = ["digital-slot", hasFormation ? "occupied" : "empty"];
  if (hasFormation && !slot?.subject) classes.push("prepared");
  if (targetable) classes.push("targetable");
  if (stagedPlotSource && locEquals(stagedPlotSource, owner, front, rank)) classes.push("staged-source");
  const recent = state.last_action;
  const recentPosition =
    (recent?.actor === owner && posEquals(recent.position, front, rank)) ||
    (recent?.move_to && recent.actor === owner && posEquals(recent.move_to, front, rank)) ||
    (recent?.targets || []).some((target) => locEquals(target, owner, front, rank));
  if (recentPosition) classes.push("recent-action");

  const attrs =
    'data-board-owner="' + owner + '" data-board-front="' + front + '" data-board-rank="' + rank + '"';

  if (!hasFormation) {
    return '<div class="' + classes.join(" ") + '" ' + attrs + '>' +
      '<span class="empty-slot-mark">＋</span><span>' +
      (rank === "front" ? "Frontline" : "Rear") + '</span>' +
      (targetable ? '<b class="legal-target-cue">PLAY HERE</b>' : '') +
      '</div>';
  }

  return '<div class="' + classes.join(" ") + '" ' + attrs + '>' +
    '<span class="slot-rank">' + esc(slot.rank_name) +
      (rank === "front" ? " · Line Defense +1" : "") + '</span>' +
    '<div class="board-legend">' +
      (slot.subject
        ? boardCardMarkup(slot.subject, "subject", owner)
        : '<span class="prepared-formation-label">' + termMarkup("Prepared") + '<small>Subject open</small></span>') +
      (slot.link ? '<div class="board-attachment link">' + boardCardMarkup(slot.link, "link", owner) + '</div>' : "") +
      (slot.name ? '<div class="board-attachment name">' + boardCardMarkup(slot.name, "name", owner) + '</div>' : "") +
    '</div>' +
    '<span class="slot-strength' + (slot.subject ? '' : ' inactive') + '">' +
      (slot.subject ? slot.strength : "—") + '</span>' +
    (targetable ? '<b class="legal-target-cue">PLAY HERE</b>' : '') +
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
    return '<div class="' + classes.join(" ") + '" ' + attrs + '><span>Veiled Story</span><b>' +
      (targetable ? 'PLAY HERE' : 'empty') + '</b></div>';
  }
  if (scheme.hidden) {
    return '<div class="' + classes.join(" ") + '" ' + attrs + '><span>Veiled Story</span><b>face-down</b></div>';
  }
  return '<div class="' + classes.join(" ") + '" ' + attrs + '><span>Veiled Story</span>' +
    '<button type="button" class="public-card-link" data-inspect-card="' + esc(scheme.card_id) +
    '" data-inspect-owner="' + owner + '" data-inspect-zone="veiled story">' +
    esc(cardTitle(scheme.card_id)) + (scheme.revealed ? " · revealed" : "") + '</button></div>';
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
  const inspect = stratagem?.card_id && !stratagem.hidden
    ? ' data-inspect-card="' + esc(stratagem.card_id) + '" data-inspect-owner="' + owner + '" data-inspect-zone="stratagem"'
    : "";
  return '<div class="' + classes.join(" ") + '"' + inspect + '><span>' + esc(title) + '</span><b>' + esc(label) + '</b></div>';
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
  bindCardInspectors();
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
    $("draw-button").hidden = true;
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
  const passButton = $("pass-button");
  passButton.hidden = !pass || state.viewer == null;
  passButton.disabled = !pass || state.viewer == null;
  passButton.classList.toggle("danger-pass", !!pass && state.players[opponentOf(currentViewer())].passed);
  passButton.textContent = state.players[opponentOf(currentViewer())].passed ? "Pass · score Battle" : "Pass";

  const draw = actionForDraw();
  const drawButton = $("draw-button");
  drawButton.hidden = !draw || state.viewer == null;
  drawButton.disabled = !draw || state.viewer == null;
  drawButton.textContent = "Draw 1";
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
  if (!actions.length) return "No legal play for this card right now.";
  if (actions.some((a) => a.kind === "PlaySubject")) return "Choose a position without a Subject. Prepared Bond or Name cards may already be there.";
  if (actions.some((a) => a.kind === "PlayLink")) return "Choose a position without a Bond. It may be prepared before the Subject.";
  if (actions.some((a) => a.kind === "PlayName")) return "Choose a position without a Name. It may be prepared before the Subject or Bond; movement is offered only when a Subject is already there.";
  if (actions.some((a) => a.kind === "PlayScheme")) return "Choose a Front to set this Veiled Story face-down.";
  if (actions.some((a) => a.kind === "SetStratagem")) return "Set this face-down in your Stratagem space, then take your normal action.";
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
      title.textContent = "Mulligan";
      hint.textContent = "Select up to two cards to shuffle back. You draw the same number of replacements.";
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

  if (state.needs_ai) {
    title.textContent = "Opponent’s turn";
    hint.textContent = "Watch the battlefield: the opponent’s action will resolve before your next turn.";
    cancel.hidden = true;
    tray.hidden = true;
    return;
  }

  if (!selectedCardId) {
    const choose = state.legal_actions.filter((a) => a.kind === "ChooseFirst");
    if (choose.length) {
      title.textContent = "Choose who starts the next Battle";
      hint.textContent = "The loser of the previous Battle chooses the first player.";
    } else {
      title.textContent = "Choose a card";
      hint.textContent = "Play a card, Draw 1 once this Battle, or Pass. Legal destinations highlight when you select a card.";
    }
    cancel.hidden = true;
  } else {
    const card = cards[selectedCardId];
    title.textContent = card.title;
    let message = interactionHintFor(card);
    const reason = selectedActions()[0]?.reason;
    if (reason) message += " " + reason;
    hint.textContent = message;
    cancel.hidden = false;
  }

  renderChoiceTray();
}

function choiceLabel(action) {
  if (action.kind === "PlayName") {
    if (!action.move_to) return "Play the Name here · stay";
    return "Play the Name here · move the Subject to " + action.move_to.front_name + " " + action.move_to.rank_name;
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
        footer: selected ? "REDRAW THIS CARD" : "KEEP",
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
      '<div class="mulligan-action-copy">' +
        '<strong>' + (count ? count + " selected" : "No cards selected") + '</strong>' +
        '<span>' + (count ? "These cards will be shuffled back and replaced." : "Keep all 10 cards and begin the Battle.") + '</span>' +
      '</div>' +
      '<button type="button" class="initiative-button mulligan-confirm" id="confirm-mulligan">' +
      (count ? "Redraw " + count + " selected" : "Keep all 10") +
      "</button>";
    $("confirm-mulligan").addEventListener("click", submitMulligan);
    window.CardLayoutGuard?.schedule(hand);
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
      footer: playable ? "SELECT TO PLAY · CLICK AGAIN TO READ" : "CLICK TO READ",
    });
  }).join("");

  hand.querySelectorAll("[data-hand-card]").forEach((cardEl) => {
    const cardId = cardEl.dataset.handCard;
    cardEl.addEventListener("click", () => {
      const playable = state.legal_actions.some((a) => a.card_id === cardId);
      if (!playable || selectedCardId === cardId) {
        openCardInspector(cardId, currentViewer(), "hand");
        return;
      }
      selectCard(cardId);
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
  window.CardLayoutGuard?.schedule(hand);
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

function closeCardInspector() {
  const inspector = $("card-inspector");
  if (!inspector) return;
  inspector.hidden = true;
  inspector.setAttribute("aria-hidden", "true");
  $("card-inspector-card").innerHTML = "";
}

function openCardInspector(cardId, owner, zone = "card") {
  const card = cards[cardId];
  if (!card) return;
  const inspector = $("card-inspector");
  const ownerLabel = owner === currentViewer() ? "Your" : "Opponent's";
  $("card-inspector-context").textContent = ownerLabel + " " + zone;
  $("card-inspector-title").textContent = card.title;
  $("card-inspector-card").innerHTML = playCardMarkup(cardId, {
    footer: ownerLabel.toUpperCase() + " · " + zone.toUpperCase(),
    attrs: 'tabindex="-1"',
  });
  inspector.hidden = false;
  inspector.setAttribute("aria-hidden", "false");
  $("card-inspector-close").focus();
}

function bindCardInspectors() {
  document.querySelectorAll("[data-inspect-card]").forEach((el) => {
    el.addEventListener("click", (event) => {
      if (selectedCardId && el.closest(".digital-slot")) return;
      event.preventDefault();
      event.stopPropagation();
      openCardInspector(
        el.dataset.inspectCard,
        Number(el.dataset.inspectOwner),
        el.dataset.inspectZone || "card"
      );
    });
  });
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

function updateGameStatus() {
  const status = $("engine-status");
  if (!state) {
    status.textContent = cardsReady ? "Ready" : "Loading cards…";
    return;
  }
  if (state.phase === "mulligan") {
    status.textContent = "Opening mulligan";
    return;
  }
  if (state.phase === "complete") {
    status.textContent = "Match complete";
    return;
  }
  if (state.needs_ai) {
    status.textContent = "Opponent’s turn";
    return;
  }
  status.textContent = "Battle " + state.battle + " · " +
    (state.mode === "hotseat" ? "Player " + (state.active_player + 1) : "Your turn");
}

function renderActionFeedback() {
  const banner = $("action-banner");

  if (
    !openingAnnouncementShown &&
    state?.phase === "battle" &&
    state.opening_player != null
  ) {
    openingAnnouncementShown = true;
    const own = state.opening_player === state.viewer;
    $("action-banner-kicker").textContent = own ? "YOU GO FIRST" : "OPPONENT GOES FIRST";
    $("action-banner-title").textContent = "+1 opening card";
    $("action-banner-detail").textContent =
      "The Battle I starter draws one additional card after mulligans.";
    banner.hidden = false;
    banner.classList.remove("show");
    void banner.offsetWidth;
    banner.classList.add("show");
    clearTimeout(actionBannerTimer);
    actionBannerTimer = setTimeout(() => {
      banner.classList.remove("show");
      setTimeout(() => { banner.hidden = true; }, 180);
    }, 1800);
    return;
  }

  const action = state?.last_action;
  if (!action || action.id === lastShownActionId) return;
  lastShownActionId = action.id;
  const own = action.actor === state.viewer;
  const card = action.card_id ? cards[action.card_id] : null;
  let kicker = own ? "YOUR ACTION" : "OPPONENT ACTION";
  let title = card?.title || action.label;

  if (action.kind === "Draw") {
    kicker = own ? "YOU DRAW" : "OPPONENT DRAWS";
    title = "1 card";
  } else if (action.kind === "Pass") {
    kicker = own ? "YOU PASS" : "OPPONENT PASSES";
    title = "No more turns this Battle";
  } else if (action.kind === "PlaySubject") {
    kicker = own ? "YOU DEPLOY" : "OPPONENT DEPLOYS";
  } else if (action.kind === "PlayLink") {
    kicker = own ? "YOU ATTACH A BOND" : "OPPONENT ATTACHES A BOND";
  } else if (action.kind === "PlayName") {
    kicker = own ? "YOU NAME A SUBJECT" : "OPPONENT NAMES A SUBJECT";
  } else if (action.kind === "PlayPlot") {
    kicker = own ? "YOU PLAY A STORY" : "OPPONENT PLAYS A STORY";
  } else if (action.kind === "PlayScheme") {
    kicker = own ? "YOU SET A VEILED STORY" : "OPPONENT SETS A VEILED STORY";
    if (!card) title = "Face-down card";
  } else if (action.kind === "SetStratagem") {
    kicker = own ? "YOU SET A STRATAGEM" : "OPPONENT SETS A STRATAGEM";
    if (!card) title = "Face-down card";
  }

  $("action-banner-kicker").textContent = kicker;
  $("action-banner-title").textContent = title;
  $("action-banner-detail").textContent = action.label || "";
  banner.hidden = false;
  banner.classList.remove("show");
  void banner.offsetWidth;
  banner.classList.add("show");

  clearTimeout(actionBannerTimer);
  actionBannerTimer = setTimeout(() => {
    banner.classList.remove("show");
    setTimeout(() => { banner.hidden = true; }, 180);
  }, 1800);
}

function cancelAiStep() {
  if (aiStepTimer) clearTimeout(aiStepTimer);
  aiStepTimer = null;
  document.body.classList.remove("ai-waiting", "ai-resolving");
}

function scheduleAiStep(delay = 2000) {
  cancelAiStep();
  if (!state?.needs_ai || state.phase === "complete") return;
  document.body.classList.add("ai-waiting");
  updateGameStatus();

  aiStepTimer = setTimeout(async () => {
    aiStepTimer = null;
    if (!state?.needs_ai || state.phase === "complete") {
      document.body.classList.remove("ai-waiting");
      return;
    }
    document.body.classList.remove("ai-waiting");
    document.body.classList.add("ai-resolving");
    try {
      state = await request({ type: "ai_step" });
      clearSelection();
      render();
      if (state.needs_ai) scheduleAiStep(1950);
    } catch (error) {
      $("engine-status").textContent = "Opponent action failed";
      $("interaction-hint").textContent = error.message;
      $("interaction-strip").classList.add("interaction-error");
      console.error("[play]", error);
    } finally {
      document.body.classList.remove("ai-resolving");
    }
  }, delay);
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
  scheduleAiStep();
}

async function executeAction(action) {
  if (!action || state.viewer == null || state.needs_ai) return;
  await runBusy(async () => {
    state = await request({ type: "act", key: action.key, viewer: state.viewer });
    clearSelection();
    render();
  });
  scheduleAiStep();
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
  renderActionFeedback();
  updateGameStatus();
  if (state.phase === "complete") {
    cancelAiStep();
    $("privacy-gate").hidden = false;
    $("privacy-gate").innerHTML = "<p><strong>Player " + (state.winner + 1) + " wins the match.</strong></p>";
  }
}

async function runBusy(fn) {
  document.body.classList.add("is-busy");
  try {
    await fn();
    if ($("interaction-strip")) $("interaction-strip").classList.remove("interaction-error");
  } catch (error) {
    $("engine-status").textContent = "Action failed";
    if ($("interaction-hint")) $("interaction-hint").textContent = error.message;
    if ($("interaction-strip")) $("interaction-strip").classList.add("interaction-error");
    if (!state) $("setup-note").textContent = error.message;
    console.error("[play]", error);
  } finally {
    document.body.classList.remove("is-busy");
    updateGameStatus();
  }
}

async function loadCards() {
  const [cardsResponse, deckResponse] = await Promise.all([
    fetch(dataUrl("data/cards.json"), { cache: "default" }),
    fetch(dataUrl("data/reference-deck.json"), { cache: "default" }),
    initializeBrowserEngine(),
  ]);
  if (!cardsResponse.ok || !deckResponse.ok) {
    throw new Error("Could not load the card or deck data.");
  }
  cardData = await cardsResponse.json();
  referenceDeck = await deckResponse.json();
  cards = Object.fromEntries(cardData.cards.map((card) => [card.id, card]));
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
  closeCardInspector();
  cancelAiStep();
  clearTimeout(actionBannerTimer);
  lastShownActionId = 0;
  openingAnnouncementShown = false;
  $("action-banner").hidden = true;
  state = null;
  clearSelection();
  $("game").hidden = true;
  $("play-setup").hidden = false;
  randomizeSeed();
});

$("cancel-selection").addEventListener("click", () => {
  clearSelection();
  renderInteractiveState();
});

$("card-inspector-close").addEventListener("click", closeCardInspector);
document.querySelectorAll("[data-inspector-close]").forEach((el) => {
  el.addEventListener("click", closeCardInspector);
});

$("draw-button").addEventListener("click", () => {
  const draw = actionForDraw();
  if (draw) executeAction(draw);
});

$("pass-button").addEventListener("click", () => {
  const pass = actionForPass();
  if (pass) executeAction(pass);
});

function showTermHint(term) {
  const hint = $("term-hint");
  if (!term || !hint) return;
  hint.textContent = term.dataset.termHint || "";
  hint.hidden = false;
  const rect = term.getBoundingClientRect();
  const hintRect = hint.getBoundingClientRect();
  const left = Math.max(12, Math.min(
    window.innerWidth - hintRect.width - 12,
    rect.left + rect.width / 2 - hintRect.width / 2
  ));
  const below = rect.bottom + 9;
  const top = below + hintRect.height <= window.innerHeight - 10
    ? below
    : Math.max(10, rect.top - hintRect.height - 9);
  hint.style.left = left + "px";
  hint.style.top = top + "px";
}

function hideTermHint() {
  const hint = $("term-hint");
  if (hint) hint.hidden = true;
}

document.addEventListener("mouseover", (event) => {
  const term = event.target.closest?.(".game-term");
  if (term) showTermHint(term);
});
document.addEventListener("mouseout", (event) => {
  const term = event.target.closest?.(".game-term");
  if (term && !term.contains(event.relatedTarget)) hideTermHint();
});
document.addEventListener("focusin", (event) => {
  const term = event.target.closest?.(".game-term");
  if (term) showTermHint(term);
});
document.addEventListener("focusout", (event) => {
  if (event.target.closest?.(".game-term")) hideTermHint();
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !$("card-inspector").hidden) {
    closeCardInspector();
    return;
  }
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
  if ((event.key === "d" || event.key === "D") && !event.metaKey && !event.ctrlKey) {
    const draw = actionForDraw();
    if (draw) executeAction(draw);
  }
  if ((event.key === "p" || event.key === "P") && !event.metaKey && !event.ctrlKey) {
    const pass = actionForPass();
    if (pass) executeAction(pass);
  }
});

loadCards().catch((error) => { $("setup-note").textContent = error.message; });
