import { BrowserSession, initializeBrowserEngine } from "./browser-engine.mjs";

let session = null;
let cardData = null;
let referenceDeck = null;
let cards = {};
let state = null;
let selectedCardId = null;
let selectedHandIndex = null;
let stagedPlotSource = null;
let choiceActions = [];
let mulliganSelection = new Set();
let cardsReady = false;
let aiStepTimer = null;
let actionBannerTimer = null;
let lastShownActionId = 0;
let openingAnnouncementShown = false;
let renderedState = null;
let inspectorOrigin = null;
let drawerOrigin = null;
let activeDrawer = null;
let aiDueAt = 0;
let aiStepRunning = false;
let sessionGeneration = 0;
let busy = false;
let handLayoutFrame = null;
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

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
  "command": "Your operation budget. Start at 20; gain 10 between Battles, up to 20. Unspent Command carries over.",
  "cycle": "Some experimental rules use Cycle, but it is not part of the standard game.",
  "draw": "At the start of each turn, draw 1 card. Your draw pile persists; shuffle the discard only when an empty deck must supply a draw.",
  "front": "One of the three lanes: Left, Center, or Right.",
  "frontline": "The position nearest the Battle Line. It normally receives +1 Line Defense.",
  "frontline subject": "The Subject occupying the Frontline position of that Front.",
  "frontline subjects": "Subjects occupying Frontline positions.",
  "line defense": "The default +1 Strength bonus given to a Subject in the Frontline.",
  "move": "Relocate a Subject, keeping its attached Bond and Name unless the effect says otherwise.",
  "name": "A Unique formation component. It may be prepared before the Subject or Bond; Subject-dependent text stays inactive until a Subject is present.",
  "pass": "End your operations in this Battle. After the first Pass, the opponent gets exactly one final operation before scoring.",
  "passes": "After the first Pass, the opponent gets exactly one final operation before the Battle is scored.",
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
  const requestedSession = session;
  // Yield once so busy/loading UI paints before the small synchronous rules step.
  await new Promise((resolve) => setTimeout(resolve, 0));

  if (payload.type === "new_game") {
    if (!cardData || !referenceDeck) throw new Error("Game data is not loaded yet.");
    sessionGeneration += 1;
    session?.destroy();
    session = new BrowserSession(cardData, referenceDeck, payload.mode, payload.seed);
    return session.snapshot(payload.mode === "hotseat" ? null : 0);
  }
  if (!session) throw new Error("Start a match first.");
  if (session !== requestedSession) throw new Error("This match has ended.");
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
  const commandCost = Number.isInteger(card.command_cost)
    ? '<span class="play-command-cost" aria-label="Command cost ' + card.command_cost + '">C ' + card.command_cost + '</span>'
    : "";
  const badge = count > 1
    ? '<span class="copy-badge">×' + count + '</span>'
    : options.copyLabel
      ? '<span class="copy-badge copy-index">' + esc(options.copyLabel) + '</span>'
      : "";
  const footer = options.footer || "";
  const propertyMarkup = cardPropertyMarkup(card);

  return '<button type="button" class="' + classes.filter(Boolean).join(" ") + '" data-card-id="' + esc(cardId) + '" aria-label="' + esc(card.title) + '" ' + (options.attrs || "") + '>' +
    '<div class="play-card-meta"><span>' + esc(cardType(card)) + '</span><span class="play-card-meta-badges">' + commandCost + badge + '</span></div>' +
    '<h3 class="' + (card.title.length > 28 ? 'long-title' : '') + '">' + esc(card.title) + '</h3>' +
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

function actionForCycle() {
  if (!state || !selectedCardId || state.phase !== "battle") return null;
  return selectedActions().find((action) => action.kind === "Cycle") || null;
}

function commandCostLabel(actions) {
  const costs = [...new Set(actions.map((action) => action.command_cost).filter(Number.isInteger))];
  if (!costs.length) return "";
  return (costs.length === 1 ? costs[0] : Math.min(...costs) + "–" + Math.max(...costs)) + " C";
}

function renderCycleControl() {
  const button = $("cycle-button");
  const action = actionForCycle();
  const cycleAvailable = state.legal_actions.some((item) => item.kind === "Cycle");
  button.hidden = state.phase !== "battle" || state.viewer == null || state.needs_ai || !cycleAvailable;
  button.disabled = !action;
  button.textContent = action ? "Cycle · " + commandCostLabel([action]) : "Cycle";
  button.title = action ? "Discard " + cardTitle(selectedCardId) + ", then draw one card (C)" : "Select a card to Cycle it";
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

function renderSlot(owner, front, rank) {
  const slot = boardSlot(owner, front, rank);
  const targets = targetActionsForSlot(owner, front, rank);
  const targetable = targets.length > 0;
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
    'data-board-owner="' + owner + '" data-board-front="' + front + '" data-board-rank="' + rank + '"' +
    (targetable ? ' role="button" tabindex="0" aria-label="Play ' + esc(cardTitle(selectedCardId)) + ' at ' + (owner === currentViewer() ? 'your ' : 'opponent ') + frontNames[front] + ' ' + rank + '"' : '');

  if (!hasFormation) {
    return '<div class="' + classes.join(" ") + '" ' + attrs + '>' +
      '<span class="empty-slot-mark">＋</span><span>' +
      (rank === "front" ? "Frontline" : "Rear") + '</span>' +
      (targetable ? '<b class="legal-target-cue">PLAY · ' + commandCostLabel(targets) + '</b>' : '') +
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
    (targetable ? '<b class="legal-target-cue">PLAY · ' + commandCostLabel(targets) + '</b>' : '') +
  '</div>';
}
function renderScheme(owner, front) {
  const scheme = state.schemes[owner][front];
  const targetable = owner === currentViewer() && targetActionsForFront(front).length > 0;
  const classes = ["scheme-marker"];
  if (targetable) classes.push("targetable");
  if (!scheme) classes.push("empty");
  if (scheme?.hidden) classes.push("hidden");
  else if (scheme && !scheme.revealed) classes.push("hidden", "known");
  const attrs = 'data-scheme-owner="' + owner + '" data-scheme-front="' + front + '"' +
    (targetable ? ' role="button" tabindex="0" aria-label="Set Veiled Story at ' + frontNames[front] + '"' : '');

  if (!scheme) {
    return '<div class="' + classes.join(" ") + '" ' + attrs + '><span>Veiled Story</span><b>' +
      (targetable ? 'SET · ' + commandCostLabel(targetActionsForFront(front)) : 'empty') + '</b></div>';
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
  const targetable = owner === currentViewer() && selectedActions().some((action) => action.kind === "SetStratagem");
  if (targetable) classes.push("targetable");
  let title = "Stratagem";
  let label = targetable ? "SET · " + commandCostLabel(selectedActions().filter((action) => action.kind === "SetStratagem")) : "empty";
  if (stratagem?.hidden) {
    classes.push("hidden");
    label = "face-down";
  } else if (stratagem?.card_id) {
    if (!stratagem.revealed) classes.push("hidden", "known");
    title = cardTitle(stratagem.card_id);
    label = stratagem.revealed ? "face-up" : "face-down";
  }
  const inspect = stratagem?.card_id && !stratagem.hidden
    ? ' data-inspect-card="' + esc(stratagem.card_id) + '" data-inspect-owner="' + owner + '" data-inspect-zone="stratagem"'
    : "";
  return '<div class="' + classes.join(" ") + '" data-stratagem-owner="' + owner + '"' +
    (targetable ? ' role="button" tabindex="0" aria-label="Set your Stratagem"' : inspect ? ' role="button" tabindex="0" aria-label="Inspect Stratagem"' : '') + inspect + '><span>' + esc(title) + '</span><b>' + esc(label) + '</b></div>';
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
  bindCardInspectors($("battlefield"));
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
    $("cycle-button").hidden = true;
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


}

function commandCounter(player) {
  const label = "Command " + player.command + (player.free_cycle ? ", free Cycle ready" : "");
  return '<div class="command-counter" aria-label="' + esc(label) + '"><span>Command</span><b>' + player.command + '</b>' +
    (player.free_cycle ? '<small>Free Cycle</small>' : '') + '</div>';
}

function renderOpponentRack() {
  if (!state) return;
  const viewer = currentViewer();
  const opponent = opponentOf(viewer);
  const ps = state.players[opponent];
  const handCount = ps.hand_count || 0;

  $("opponent-label").textContent = (state.mode === "hotseat" ? "Player " + (opponent + 1) : "Opponent") + " · " + handCount + " cards" + (ps.passed ? " · PASSED" : "");

  const visibleBacks = Math.min(handCount, 12);
  $("opponent-hand").innerHTML = Array.from({ length: visibleBacks }, (_, index) => {
    const center = (visibleBacks - 1) / 2;
    const rotation = (index - center) * 2.2;
    const lift = Math.abs(index - center) * 1.2;
    return '<span class="card-back" style="--back-rot:' + rotation + 'deg;--back-y:' + lift + 'px"></span>';
  }).join("") + (handCount > visibleBacks ? '<b class="hand-overflow">+' + (handCount - visibleBacks) + '</b>' : "");

  const discard = ps.discard || [];
  const topDiscard = discard.length ? cardTitle(discard[discard.length - 1]) : "Empty";
  $("opponent-piles").innerHTML = commandCounter(ps) +
    '<button type="button" class="rack-pile deck-pile" data-open-drawer="piles" data-pile-owner="' + opponent + '" aria-label="Opponent deck and discard"><span>Deck</span><b>' + ps.deck_count + '</b></button>' +
    '<button type="button" class="rack-pile discard-pile" data-open-drawer="piles" data-pile-owner="' + opponent + '" aria-label="Opponent discard, ' + discard.length + ' cards"><span>Discard</span><b>' + discard.length + '</b><small>' + esc(topDiscard) + '</small></button>';

  const own = state.players[viewer];
  const ownDiscard = own.discard || [];
  const ownTopDiscard = ownDiscard.length ? cardTitle(ownDiscard[ownDiscard.length - 1]) : "Empty";
  $("player-piles").innerHTML = commandCounter(own) +
    '<button type="button" class="rack-pile deck-pile" data-open-drawer="piles" data-pile-owner="' + viewer + '" aria-label="Your deck and discard"><span>Deck</span><b>' + own.deck_count + '</b></button>' +
    '<button type="button" class="rack-pile discard-pile" data-open-drawer="piles" data-pile-owner="' + viewer + '" aria-label="Your discard, ' + ownDiscard.length + ' cards"><span>Discard</span><b>' + ownDiscard.length + '</b><small>' + esc(ownTopDiscard) + '</small></button>';
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
  $("reveal-hand").focus();
  $("reveal-hand").addEventListener("click", async () => {
    await runBusy(async () => {
      state = await request({ type: "view", viewer: state.active_player });
      render();
    });
  });
}

function clearSelection() {
  selectedCardId = null;
  selectedHandIndex = null;
  stagedPlotSource = null;
  choiceActions = [];
  mulliganSelection = new Set();
}

function selectCard(cardId, index) {
  if (selectedCardId === cardId && selectedHandIndex === index) {
    clearSelection();
  } else {
    selectedCardId = cardId;
    selectedHandIndex = index;
    stagedPlotSource = null;
    choiceActions = [];
  }
  renderInteractiveState();
}

function interactionHintFor(card) {
  const actions = selectedActions();
  if (!actions.length) return "No legal play for this card right now.";
  if (actions.some((a) => a.kind === "PlaySubject")) return "Choose a highlighted formation.";
  if (actions.some((a) => a.kind === "PlayLink")) return "Choose a formation for this Bond.";
  if (actions.some((a) => a.kind === "PlayName")) return "Choose a formation for this Name.";
  if (actions.some((a) => a.kind === "PlayScheme")) return "Choose a Veiled Story space.";
  if (actions.some((a) => a.kind === "SetStratagem")) return "Choose your Stratagem space. This spends Command and uses your operation.";
  if (actions.some((a) => a.kind === "PlayPlot")) {
    if (stagedPlotSource) return "Now choose the destination for " + card.title + ".";
    return actions.some((a) => a.targets.length === 2)
      ? "Choose the first highlighted target."
      : "Choose a highlighted target.";
  }
  if (actions.some((action) => action.kind === "Cycle")) return "Cycle this card to draw a replacement.";
  return "Choose a legal action.";
}

function renderInteraction() {
  renderCycleControl();
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
      hint.textContent = "Return up to two cards, or keep your hand.";
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
    hint.textContent = "Thinking…";
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
      title.textContent = "Your turn";
      hint.textContent = "Draw 1 automatically · Select a card to play · Pass";
    }
    cancel.hidden = true;
  } else {
    const card = cards[selectedCardId];
    title.textContent = card.title;
    let message = interactionHintFor(card);
    const plays = selectedActions().filter((action) => action.kind !== "Cycle");
    if (plays.length) message += " Play: " + commandCostLabel(plays) + ".";
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
      (a.kind === "PlayPlot" && a.targets.length === 0)
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
  hand.classList.toggle("mulligan-hand", state.phase === "mulligan");
  if (state.viewer == null || state.phase === "complete") {
    hand.innerHTML = "";
    actions.innerHTML = "";
    return;
  }

  if (state.phase === "mulligan") {
    $("hand-title").textContent =
      "Opening hand · " + state.hand.length + " cards";

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
        attrs: 'data-mulligan-index="' + index + '" aria-pressed="' + selected + '"',
        footer: selected ? "REDRAW THIS CARD" : "KEEP",
      });
    }).join("");

    hand.querySelectorAll("[data-mulligan-index]").forEach((cardEl) => {
      bindHandInspection(cardEl, state.hand[Number(cardEl.dataset.mulliganIndex)], "opening hand");
      cardEl.addEventListener("click", () => {
        const index = Number(cardEl.dataset.mulliganIndex);
        if (mulliganSelection.has(index)) {
          mulliganSelection.delete(index);
        } else if (mulliganSelection.size < state.mulligan_limit) {
          mulliganSelection.add(index);
        }
        const focus = focusIdentity();
        renderHand();
        renderInteraction();
        restoreFocus(focus);
      });
    });

    const count = mulliganSelection.size;
    actions.innerHTML =
      '<div class="mulligan-action-copy">' +
        '<strong>' + (count ? count + " selected" : "No cards selected") + '</strong>' +
        '<span>' + (count ? "These cards will be shuffled back and replaced." : "Your opening hand is ready.") + '</span>' +
      '</div>' +
      '<button type="button" class="initiative-button mulligan-confirm" id="confirm-mulligan">' +
      (count ? "Redraw " + count + " selected" : "Keep hand") +
      "</button>";
    $("confirm-mulligan").addEventListener("click", submitMulligan);
    layoutHand();
    window.CardLayoutGuard?.schedule(hand);
    return;
  }

  $("hand-title").textContent = (state.mode === "hotseat" ? "Player " + (state.viewer + 1) : "Your hand") + " · " + state.hand.length;

  hand.innerHTML = state.hand.map((cardId, index) => {
    const playable = state.legal_actions.some((action) => action.card_id === cardId && action.kind !== "Cycle");
    const cyclable = state.legal_actions.some((action) => action.card_id === cardId && action.kind === "Cycle");
    return playCardMarkup(cardId, {
      playable,
      selected: selectedCardId === cardId && selectedHandIndex === index,
      attrs: 'data-hand-card="' + esc(cardId) + '" data-hand-index="' + index + '" aria-pressed="' + (selectedCardId === cardId && selectedHandIndex === index) + '"',
      footer: playable ? "SELECT · CLICK AGAIN TO INSPECT" : cyclable ? "SELECT TO CYCLE · CLICK AGAIN TO INSPECT" : "INSPECT",
    });
  }).join("");

  hand.querySelectorAll("[data-hand-card]").forEach((cardEl) => {
    const cardId = cardEl.dataset.handCard;
    cardEl.addEventListener("click", () => {
      const playable = state.legal_actions.some((a) => a.card_id === cardId);
      if (!playable || (selectedCardId === cardId && selectedHandIndex === Number(cardEl.dataset.handIndex))) {
        openCardInspector(cardId, currentViewer(), "hand");
        return;
      }
      selectCard(cardId, Number(cardEl.dataset.handIndex));
    });
    bindHandInspection(cardEl, cardId);
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
  layoutHand();
  window.CardLayoutGuard?.schedule(hand);
}

function bindHandInspection(cardEl, cardId, zone = "hand") {
  cardEl.setAttribute("aria-keyshortcuts", "I Shift+F10");
  cardEl.setAttribute("aria-description", "Press I or right-click to inspect this card.");
  const inspect = (event) => {
    event.preventDefault();
    event.stopPropagation();
    openCardInspector(cardId, currentViewer(), zone);
  };
  cardEl.addEventListener("contextmenu", inspect);
  cardEl.addEventListener("keydown", (event) => {
    if ((!event.ctrlKey && !event.metaKey && !event.altKey && event.key.toLowerCase() === "i") || event.key === "ContextMenu" || (event.shiftKey && event.key === "F10")) inspect(event);
  });
}

function layoutHand() {
  const hand = $("hand");
  // Commit the fan as one layout, before restoring hover/selection transitions.
  // Newly rendered cards must not animate out of a temporary stack at center.
  cancelAnimationFrame(handLayoutFrame);
  hand.classList.add("laying-out");
  const elements = [...hand.querySelectorAll(".play-card")];
  const scale = Math.min(.78, Math.max(.42, (hand.clientHeight - 24) / 286));
  const spread = Math.max(0, Math.min(110 * scale, (hand.clientWidth - 204 * scale - 44) / Math.max(1, elements.length - 1)));
  const middle = (elements.length - 1) / 2;
  elements.forEach((el, index) => {
    const t = middle ? (index - middle) / middle : 0;
    el.style.setProperty("--fan-x", ((index - middle) * spread) + "px");
    el.style.setProperty("--fan-y", (Math.abs(t) * 10) + "px");
    el.style.setProperty("--fan-rot", (t * 5) + "deg");
    el.style.setProperty("--fan-scale", String(scale));
    el.style.setProperty("--fan-order", String(index + 1));
  });
  void hand.offsetHeight;
  handLayoutFrame = requestAnimationFrame(() => {
    hand.classList.remove("laying-out");
    handLayoutFrame = null;
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
    return '<details class="public-zone" data-public-owner="' + player + '"><summary>Player ' + (player + 1) +
      " · deck " + ps.deck_count + " · discard " + discard.length +
      (ps.passed ? " · PASSED" : "") + "</summary>" +
      '<div class="discard-list">' +
      (discard.length ? discard.map((id) => '<button type="button" class="public-card-link" data-inspect-card="' + esc(id) + '" data-inspect-owner="' + player + '" data-inspect-zone="discard">' + esc(cardTitle(id)) + "</button>").join("") : "<span>Empty discard</span>") +
      "</div></details>";
  }).join("");
  bindCardInspectors($("public-zones"));
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
  restoreFocus(inspectorOrigin);
  inspectorOrigin = null;
}

function openCardInspector(cardId, owner, zone = "card") {
  const card = cards[cardId];
  if (!card) return;
  const inspector = $("card-inspector");
  if (inspector.hidden) inspectorOrigin = focusIdentity();
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

function bindCardInspectors(root = document) {
  root.querySelectorAll("[data-inspect-card]").forEach((el) => {
    if (el.tagName !== "BUTTON") el.addEventListener("keydown", (event) => {
      if (!el.classList.contains("targetable") && (event.key === "Enter" || event.key === " ")) {
        event.preventDefault();
        el.click();
      }
    });
    el.addEventListener("click", (event) => {
      if (selectedCardId && el.closest(".targetable")) return;
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

function bindTarget(el, activate) {
  el.addEventListener("click", activate);
  el.addEventListener("keydown", (event) => {
    if (event.target !== el || !el.classList.contains("targetable")) return;
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      activate();
    }
  });
}

function bindBoardTargets() {
  document.querySelectorAll("[data-board-owner]").forEach((el) => {
    bindTarget(el, () => handleBoardTarget(Number(el.dataset.boardOwner), Number(el.dataset.boardFront), el.dataset.boardRank));
  });
  document.querySelectorAll("[data-scheme-front]").forEach((el) => {
    bindTarget(el, () => {
      if (Number(el.dataset.schemeOwner) === currentViewer()) handleFrontTarget(Number(el.dataset.schemeFront));
    });
  });
  document.querySelectorAll("[data-stratagem-owner]").forEach((el) => {
    bindTarget(el, () => {
      if (Number(el.dataset.stratagemOwner) !== currentViewer()) return;
      const action = selectedActions().find((candidate) => candidate.kind === "SetStratagem");
      if (action) executeAction(action);
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
    $("choice-tray").querySelector("button")?.focus();
  }
}

function handleFrontTarget(front) {
  if (!selectedCardId) return;
  const matches = targetActionsForFront(front);
  if (matches.length === 1) executeAction(matches[0]);
  else if (matches.length > 1) { choiceActions = matches; renderChoiceTray(); $("choice-tray").querySelector("button")?.focus(); }
}

function renderInteractiveState() {
  const focus = focusIdentity();
  renderBattlefield();
  renderHand();
  renderInteraction();
  restoreFocus(focus);
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

function showActionBanner(kicker, title, detail = "") {
  const banner = $("action-banner");
  $("action-banner-kicker").textContent = kicker;
  $("action-banner-title").textContent = title;
  $("action-banner-detail").textContent = detail;
  banner.hidden = false;
  banner.classList.add("show");
  clearTimeout(actionBannerTimer);
  actionBannerTimer = setTimeout(() => { banner.classList.remove("show"); banner.hidden = true; }, 1800);
}

function renderActionFeedback() {
  if (renderedState && renderedState.battle !== state.battle && state.phase !== "complete") {
    lastShownActionId = state.last_action?.id || lastShownActionId;
    const victor = state.players.findIndex((player, index) => player.victories > renderedState.players[index].victories);
    const result = victor < 0 ? "A drawn Battle" : state.mode === "hotseat"
      ? "Player " + (victor + 1) + " gains a Victory"
      : victor === currentViewer() ? "You gain a Victory" : "Opponent gains a Victory";
    showActionBanner("BATTLE " + renderedState.battle + " RESOLVED", result, "Battle " + state.battle + " begins");
    return;
  }

  if (
    !openingAnnouncementShown &&
    state?.phase === "battle" &&
    state.opening_player != null
  ) {
    openingAnnouncementShown = true;
    const own = state.opening_player === state.viewer;
    showActionBanner(own ? "YOU GO FIRST" : "OPPONENT GOES FIRST", "Draw 1 to start the turn");
    return;
  }

  const action = state?.last_action;
  if (!action || action.id === lastShownActionId) return;
  lastShownActionId = action.id;
  const own = action.actor === state.viewer;
  const card = action.card_id ? cards[action.card_id] : null;
  let kicker = own ? "YOUR ACTION" : "OPPONENT ACTION";
  let title = card?.title || action.label;

  if (action.kind === "Cycle") {
    kicker = own ? "YOU CYCLE" : "OPPONENT CYCLES";
  } else if (action.kind === "Draw") {
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

  showActionBanner(kicker, title, action.label || "");
}

function cancelAiStep() {
  clearTimeout(aiStepTimer);
  aiStepTimer = null;
  aiDueAt = 0;
  document.body.classList.remove("ai-waiting", "ai-resolving");
}

async function resolveAiStep() {
  clearTimeout(aiStepTimer);
  aiStepTimer = null;
  aiDueAt = 0;
  if (!state?.needs_ai || state.phase === "complete" || aiStepRunning) return;
  aiStepRunning = true;
  const generation = sessionGeneration;
  document.body.classList.remove("ai-waiting");
  document.body.classList.add("ai-resolving");
  try {
    const next = await request({ type: "ai_step" });
    if (generation !== sessionGeneration || !state) return;
    state = next;
    clearSelection();
    render();
    if (state.needs_ai) scheduleAiStep(1100);
  } catch (error) {
    if (generation !== sessionGeneration || !state) return;
    $("engine-status").textContent = "Opponent action failed";
    $("interaction-hint").textContent = error.message;
    $("interaction-strip").classList.add("interaction-error");
    console.error("[play]", error);
  } finally {
    aiStepRunning = false;
    document.body.classList.remove("ai-resolving");
  }
}

function scheduleAiStep(delay = 650) {
  cancelAiStep();
  if (!state?.needs_ai || state.phase === "complete") return;
  document.body.classList.add("ai-waiting");
  updateGameStatus();
  aiDueAt = performance.now() + delay;
  aiStepTimer = setTimeout(resolveAiStep, delay);
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
  if (!action || busy || state.viewer == null || state.needs_ai) return;
  await runBusy(async () => {
    state = await request({ type: "act", key: action.key, viewer: state.viewer });
    clearSelection();
    render();
  });
  scheduleAiStep();
}

function render() {
  const previous = renderedState;
  if (previous && previous.viewer !== state.viewer) closeCardInspector();
  const anchors = captureCardAnchors(previous);
  $("game").hidden = false;
  document.body.classList.add("match-active");
  $("game").dataset.phase = state.phase;
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
  renderMatchResult();
  animateSnapshot(previous, anchors);
  renderedState = state;
}

async function runBusy(fn) {
  if (busy) return;
  busy = true;
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
    busy = false;
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
  scheduleAiStep();
});

function restartMatch() {
  if (busy) return;
  closeCardInspector();
  cancelAiStep();
  clearTimeout(actionBannerTimer);
  lastShownActionId = 0;
  openingAnnouncementShown = false;
  $("action-banner").hidden = true;
  sessionGeneration += 1;
  state = null;
  renderedState = null;
  session?.destroy();
  session = null;
  closeDrawer(false);
  document.body.classList.remove("match-active");
  if ($("match-result")) $("match-result").hidden = true;
  clearSelection();
  $("game").hidden = true;
  $("play-setup").hidden = false;
  randomizeSeed();
  $("start-game").focus();
}

$("restart").addEventListener("click", restartMatch);
$("play-again")?.addEventListener("click", restartMatch);

$("cancel-selection").addEventListener("click", () => {
  clearSelection();
  renderInteractiveState();
});

$("card-inspector-close").addEventListener("click", closeCardInspector);
document.querySelectorAll("[data-inspector-close]").forEach((el) => {
  el.addEventListener("click", closeCardInspector);
});

$("cycle-button").addEventListener("click", () => {
  const cycle = actionForCycle();
  if (cycle) executeAction(cycle);
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
  if (event.key === "Escape") {
    event.preventDefault();
    if (!$("card-inspector").hidden) closeCardInspector();
    else if (activeDrawer) closeDrawer();
    else if (state && (selectedCardId || mulliganSelection.size)) {
      clearSelection();
      renderInteractiveState();
    }
    hideTermHint();
    return;
  }
  const overlay = !$("card-inspector").hidden ? $("card-inspector") : activeDrawer ? $("game-drawer") : $("match-result") && !$("match-result").hidden ? $("match-result") : state?.needs_reveal ? $("privacy-gate") : null;
  if (overlay) {
    trapFocus(event, overlay);
    return;
  }
  if (event.ctrlKey || event.metaKey || event.altKey || /INPUT|SELECT|TEXTAREA/.test(event.target.tagName)) return;
  if (event.key.toLowerCase() === "f") {
    event.preventDefault();
    toggleFullscreen();
    return;
  }
  if (!state || state.viewer == null || state.phase !== "battle") return;
  if (event.key.toLowerCase() === "c") {
    const cycle = actionForCycle();
    if (cycle) executeAction(cycle);
  }
  if (event.key.toLowerCase() === "p") {
    const pass = actionForPass();
    if (pass) executeAction(pass);
  }
});

// Focus survives snapshot-driven DOM replacement, without retaining hidden cards.
function focusIdentity() {
  const el = document.activeElement;
  if (!el || el === document.body) return null;
  const names = ["hand-index", "mulligan-index", "inspect-card", "inspect-owner", "inspect-zone", "board-owner", "board-front", "board-rank", "scheme-owner", "scheme-front", "stratagem-owner"];
  if (el.id) return { id: el.id };
  const attrs = names.filter((name) => el.hasAttribute("data-" + name)).map((name) => ["data-" + name, el.getAttribute("data-" + name)]);
  return { el, attrs };
}

function restoreFocus(identity) {
  if (!identity) return;
  let el = identity.id ? $(identity.id) : identity.el?.isConnected ? identity.el : null;
  if (!el && identity.attrs?.length) {
    el = document.querySelector(identity.attrs.map(([name, value]) => "[" + name + '="' + CSS.escape(value) + '"]').join(""));
  }
  if (el && !el.closest("[hidden]")) el.focus({ preventScroll: true });
}

function trapFocus(event, overlay) {
  if (event.key !== "Tab") return;
  const elements = [...overlay.querySelectorAll('button:not([disabled]), a[href], input, select, [tabindex="0"]')].filter((el) => !el.closest("[hidden]") && el.getClientRects().length);
  const first = elements[0];
  const last = elements.at(-1);
  if (!first) return;
  if (!overlay.contains(document.activeElement)) { event.preventDefault(); first.focus(); }
  else if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
}

function openDrawer(name, owner = null) {
  const drawer = $("game-drawer");
  if (!drawer) return;
  if (!activeDrawer) drawerOrigin = focusIdentity();
  activeDrawer = name;
  drawer.hidden = false;
  $("drawer-title").textContent = { menu: "Game menu", rules: "How to play", log: "Battle log", piles: "Decks & discards" }[name] || "Game menu";
  drawer.querySelectorAll("[data-drawer-content]").forEach((section) => { section.hidden = section.dataset.drawerContent !== name; });
  if (name === "piles" && owner !== null) drawer.querySelectorAll("[data-public-owner]").forEach((zone) => { zone.open = Number(zone.dataset.publicOwner) === Number(owner); });
  $("drawer-close").focus();
}

function closeDrawer(restore = true) {
  const drawer = $("game-drawer");
  if (!drawer) return;
  drawer.hidden = true;
  activeDrawer = null;
  if (restore) restoreFocus(drawerOrigin);
  drawerOrigin = null;
}

document.addEventListener("click", (event) => {
  const open = event.target.closest("[data-open-drawer]");
  if (open) openDrawer(open.dataset.openDrawer, open.dataset.pileOwner ?? null);
  if (event.target.closest("[data-drawer-close]")) closeDrawer();
});
$("drawer-close")?.addEventListener("click", () => closeDrawer());

async function toggleFullscreen() {
  try {
    if (document.fullscreenElement) await document.exitFullscreen();
    else await document.documentElement.requestFullscreen();
  } catch { /* The browser may disallow fullscreen in embedded previews. */ }
}
$("fullscreen-button")?.addEventListener("click", toggleFullscreen);
window.addEventListener("resize", layoutHand);

function renderMatchResult() {
  const result = $("match-result");
  if (!result) return;
  const complete = state.phase === "complete";
  const wasHidden = result.hidden;
  result.hidden = !complete;
  if (!complete) return;
  cancelAiStep();
  $("privacy-gate").hidden = true;
  $("result-title").textContent = state.mode === "hotseat" ? "Player " + (state.winner + 1) + " wins" : state.winner === currentViewer() ? "Victory" : "Defeat";
  $("result-detail").textContent = state.players.map((player) => player.victories).join(" — ") + " · A war decided in " + state.battle + " Battles";
  if (wasHidden) $("play-again")?.focus();
}

function pileNode(owner, kind) {
  return document.querySelector((owner === currentViewer() ? "#player-piles" : "#opponent-piles") + " ." + kind + "-pile");
}

function captureCardAnchors(snapshot) {
  if (!snapshot) return [];
  const anchors = [];
  document.querySelectorAll("#hand [data-card-id], #battlefield [data-inspect-card]").forEach((node) => {
    const slot = node.closest("[data-board-owner]");
    const scheme = node.closest("[data-scheme-front]");
    const stratagem = node.closest("[data-stratagem-owner]");
    const owner = node.closest("#hand") ? snapshot.viewer : Number(node.dataset.inspectOwner);
    const zone = slot ? `slot:${slot.dataset.boardFront}:${slot.dataset.boardRank}:${node.dataset.inspectZone}` : scheme ? "scheme:" + scheme.dataset.schemeFront : stratagem ? "stratagem" : "hand";
    anchors.push({ owner, zone, cardId: node.dataset.cardId || node.dataset.inspectCard, node, rect: node.getBoundingClientRect() });
  });
  return anchors;
}

function flyCard(from, destination, face = null) {
  if (!from || !destination || reducedMotion.matches) return;
  const start = from.rect || from.getBoundingClientRect();
  const end = destination.rect || destination.getBoundingClientRect();
  if (!start.width || !end.width) return;
  const ghost = document.createElement("div");
  ghost.className = "card-flight";
  ghost.setAttribute("aria-hidden", "true");
  Object.assign(ghost.style, { position: "fixed", left: start.left + "px", top: start.top + "px", width: start.width + "px", height: start.height + "px", pointerEvents: "none", zIndex: "80", borderRadius: "7px", overflow: "hidden", background: "#263b37", border: "1px solid #c0a878", display: "grid", placeItems: "center", color: "#f1e2be", font: "600 13px Georgia,serif", padding: "8px", textAlign: "center" });
  ghost.textContent = face ? cardTitle(face) : "✦";
  document.body.append(ghost);
  const animation = ghost.animate([
    { transform: "translate(0,0) rotate(-3deg)", opacity: .94 },
    { transform: `translate(${end.left - start.left}px,${end.top - start.top}px) scale(${end.width / start.width},${end.height / start.height}) rotate(0deg)`, opacity: .78 }
  ], { duration: 420, easing: "cubic-bezier(.22,.72,.2,1)", fill: "forwards" });
  animation.finished.catch(() => {}).finally(() => ghost.remove());
}

// Motion compares visible authoritative snapshots. It never predicts rule results.
function animateSnapshot(previous, before) {
  if (!previous || reducedMotion.matches || previous.viewer !== state.viewer || previous.phase === "mulligan") return;
  if (previous.last_action?.id === state.last_action?.id && previous.battle === state.battle) return;
  const after = captureCardAnchors(state);
  const unused = new Set(after);
  const removed = [];
  for (const old of before) {
    const same = [...unused].find((next) => next.owner === old.owner && next.cardId === old.cardId && next.zone === old.zone);
    if (same) unused.delete(same);
    else removed.push(old);
  }
  for (const old of removed) {
    const moved = [...unused].find((next) => next.owner === old.owner && next.cardId === old.cardId);
    if (moved) { unused.delete(moved); flyCard(old, moved, old.cardId); }
    else {
      const handGrew = state.players[old.owner].hand_count > previous.players[old.owner].hand_count;
      const discardGrew = state.players[old.owner].discard.length > previous.players[old.owner].discard.length;
      flyCard(old, handGrew && !discardGrew && old.owner !== currentViewer() ? $("opponent-hand") : pileNode(old.owner, "discard"), old.cardId);
    }
  }
  for (const added of unused) {
    const revealed = state.last_action?.events?.some((event) => event.card_id === added.cardId && event.owner === added.owner);
    const origin = added.zone === "hand" ? pileNode(added.owner, "deck") : added.owner !== currentViewer() ? $("opponent-hand") : $("hand");
    if (!revealed) flyCard(origin, added, added.cardId);
    added.node.animate([{ opacity: .2 }, { opacity: 1 }], { duration: 450 });
  }
  const action = state.last_action;
  if (action?.actor !== currentViewer() && action?.kind === "Cycle") {
    flyCard($("opponent-hand"), pileNode(action.actor, "discard"), action.card_id);
    flyCard(pileNode(action.actor, "deck"), $("opponent-hand"));
  }
  if (action?.kind === "PlayScheme" || action?.kind === "SetStratagem") {
    const target = action.kind === "SetStratagem" ? document.querySelector('[data-stratagem-owner="' + action.actor + '"]') : document.querySelector('[data-scheme-owner="' + action.actor + '"][data-scheme-front="' + action.front + '"]');
    if (!action.card_id) flyCard($("opponent-hand"), target);
  }
  for (const event of action?.events || []) {
    const node = after.find((item) => item.cardId === event.card_id && item.owner === event.owner)?.node;
    node?.animate([{ transform: "rotateY(90deg)", filter: "brightness(1.7)" }, { transform: "rotateY(0)", filter: "brightness(1)" }], { duration: 500 });
  }
  if (previous.battle !== state.battle || previous.phase !== state.phase) $("battlefield").animate([{ opacity: .35 }, { opacity: 1 }], { duration: 550 });
  if (state.players.some((player, i) => player.victories !== previous.players[i].victories)) $("match-strip").animate([{ filter: "brightness(2)" }, { filter: "brightness(1)" }], { duration: 750 });
}

window.render_game_to_text = () => JSON.stringify({
  coordinate_system: "Fronts 0=Left, 1=Center, 2=Right; ranks front=Frontline, rear=Rear; viewer at bottom",
  ready: cardsReady,
  ...(state ? Object.fromEntries(["phase", "battle", "viewer", "active_player", "needs_ai", "needs_reveal", "winner", "players", "hand", "board", "schemes", "stratagems", "front_strengths", "front_control", "legal_actions", "last_action"].map((key) => [key, state[key]])) : { phase: "setup" }),
  selected_card: selectedCardId,
  selected_hand_index: selectedHandIndex,
  selected_source: stagedPlotSource,
  mulligan_selection: [...mulliganSelection],
  drawer: activeDrawer,
  inspector: !$("card-inspector").hidden ? $("card-inspector-title").textContent : null,
});

window.advanceTime = async (milliseconds) => {
  let remaining = Math.max(0, Number(milliseconds) || 0);
  let steps = 0;
  while (aiDueAt && steps++ < 200) {
    const delay = Math.max(0, aiDueAt - performance.now());
    if (delay > remaining) {
      scheduleAiStep(delay - remaining);
      break;
    }
    remaining -= delay;
    await resolveAiStep();
  }
  document.getAnimations().forEach((animation) => { try { animation.finish(); } catch {} });
  await new Promise(requestAnimationFrame);
};

loadCards().catch((error) => { $("setup-note").textContent = error.message; });
