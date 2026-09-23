import fs from "node:fs";
import process from "node:process";
import { BrowserSession } from "../web/browser-engine.mjs";

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const cards = JSON.parse(fs.readFileSync(new URL("../cards/cards.json", import.meta.url), "utf8"));
const deck = JSON.parse(fs.readFileSync(new URL("../decks/reference.json", import.meta.url), "utf8"));

const supported = {
  plotEffects: new Set(["discredit_subject", "return_name_or_weaken", "move_subject"]),
  schemeTriggers: new Set([
    "opponent_plays_subject",
    "opponent_plays_link",
    "opponent_passes",
    "opponent_plot_targets_your_card",
  ]),
  schemeEffects: new Set(["penalize_played_subject", "discard_played_link", "reinforce_front"]),
  stratagemEvents: new Set(["subject_played", "pass", "immediate_story_played", "name_played"]),
  nameEffects: new Set(["move_adjacent_optional"]),
};

for (const card of cards.cards) {
  const rules = card.rules || {};
  if (card.type === "plot" && !card.veiled && rules.effect) {
    assert(supported.plotEffects.has(rules.effect), "Unsupported Story effect: " + rules.effect);
  }
  if (card.veiled) {
    assert(supported.schemeTriggers.has(rules.scheme?.trigger), "Unsupported Veiled trigger: " + rules.scheme?.trigger);
    assert(supported.schemeEffects.has(rules.scheme?.effect), "Unsupported Veiled effect: " + rules.scheme?.effect);
  }
  if (card.type === "stratagem") {
    assert(supported.stratagemEvents.has(rules.stratagem?.trigger?.event), "Unsupported Stratagem event");
  }
  if (card.type === "name" && rules.on_name_attached) {
    assert(supported.nameEffects.has(rules.on_name_attached), "Unsupported Name effect");
  }
}

const prepared = new BrowserSession(cards, deck, "hotseat", 8172);
prepared.setupComplete = true;
prepared.state.active_player = 0;
prepared.state.players[0].hand = ["namar", "followed", "the-fifty-men"];
prepared.state.players[1].hand = [];

function formationAction(session, kind) {
  return session.engine.legalActions(session.state).find((action) =>
    action.kind === kind &&
    action.position?.front === 1 &&
    action.position?.rank === "front"
  );
}

let preparedAction = formationAction(prepared, "PlayName");
assert(preparedAction, "Name could not be prepared before Subject/Bond");
prepared.engine.apply(prepared.state, preparedAction);
let preparedSlot = prepared.state.board[0][1][0];
assert(preparedSlot.name === "namar" && !preparedSlot.subject && !preparedSlot.link, "Prepared Name was not retained");
assert(prepared.engine.positionStrength(prepared.state, 0, { front: 1, rank: "front" }) === 0, "Prepared Name contributed Strength without a Subject");

prepared.engine.apply(
  prepared.state,
  prepared.engine.legalActions(prepared.state).find((action) => action.kind === "Pass")
);
preparedAction = formationAction(prepared, "PlayLink");
assert(preparedAction, "Bond could not be added after a prepared Name");
prepared.engine.apply(prepared.state, preparedAction);
preparedAction = formationAction(prepared, "PlaySubject");
assert(preparedAction, "Subject could not be added to prepared Bond/Name");
prepared.engine.apply(prepared.state, preparedAction);
assert(prepared.engine.positionStrength(prepared.state, 0, { front: 1, rank: "front" }) === 10, "Prepared formation did not activate with the redesigned Name strength");
const expectedPreparedCommand =
  20
  - Number(cards.cards.find((card) => card.id === "namar").command_cost)
  - Number(cards.cards.find((card) => card.id === "followed").command_cost)
  - Number(cards.cards.find((card) => card.id === "the-fifty-men").command_cost)
  + 1;
assert(
  prepared.state.players[0].command === expectedPreparedCommand,
  "Namar completion did not refund exactly 1 Command"
);

const persistent = new BrowserSession(cards, deck, "hotseat", 9911);
persistent.setupComplete = true;
persistent.state.active_player = 0;
persistent.state.players[0].command = 7;
persistent.state.players[1].command = 14;
const keptHands = [];
const discardBefore = [];
for (const [player, target] of [[0, 4], [1, 6]]) {
  const ps = persistent.state.players[player];
  const moved = ps.hand.splice(target);
  ps.discard.push(...moved);
  discardBefore.push([...ps.discard]);
  keptHands.push([...ps.hand]);
}
persistent.engine.apply(
  persistent.state,
  persistent.engine.legalActions(persistent.state).find((action) => action.kind === "Pass")
);
persistent.engine.apply(
  persistent.state,
  persistent.engine.legalActions(persistent.state).find((action) => action.kind === "Pass")
);
assert(persistent.state.battle === 2 && persistent.state.phase === "choose_first", "Persistent Battle transition did not advance");
assert(
  persistent.state.players[0].command === 17 && persistent.state.players[1].command === 20,
  "Command did not carry and replenish by +10 to the cap"
);
for (let player = 0; player < 2; player += 1) {
  const ps = persistent.state.players[player];
  assert(ps.hand.length === 10, "Persistent Battle transition did not refill hand to 10");
  assert(ps.discard.length >= discardBefore[player].length, "Between-Battle transition unexpectedly recycled the discard pile");
  for (const cardId of keptHands[player]) {
    assert(ps.hand.includes(cardId), "Persistent Battle transition did not preserve held cards");
  }
}

const heuristic = new BrowserSession(cards, deck, "heuristic", 1701);
let view = heuristic.snapshot(0);
assert(view.phase === "mulligan", "Heuristic match did not start at mulligan");
assert(view.hand.length === 10, "Opening hand is not visible");
assert(view.legal_actions.length === 0, "Mulligan should not expose battle actions");

view = heuristic.mulligan([], 0);
assert(view.viewer === 0, "Heuristic mode did not return to Player 1");
assert(["battle", "choose_first", "complete"].includes(view.phase), "Unexpected post-mulligan phase");
assert(
  [...view.players.map((player) => player.hand_count)].sort((a, b) => a - b).join(",") === "10,11",
  "Battle I starter did not receive exactly one additional opening card"
);
assert(view.opening_player === view.active_player, "Opening player is not exposed consistently");
assert(view.players[view.opening_player].hand_count === 11, "Opening player does not have 11 cards");

function settleAi(current) {
  let safety = 0;
  while (current.needs_ai && current.phase !== "complete") {
    safety += 1;
    assert(safety < 30, "AI did not yield after paced actions");
    current = heuristic.aiStep();
  }
  return current;
}

view = settleAi(view);
if (view.phase !== "complete") {
  assert(view.active_player === 0, "AI did not yield back to the human");
  assert(view.legal_actions.length > 0, "Human has no legal actions");
  assert(!view.legal_actions.some((item) => item.kind === "Draw"), "Generic Draw should not exist in Command play");
  const cycle = view.legal_actions.find((item) => item.kind === "Cycle");
  assert(cycle, "Cycle action is missing");
  const handBefore = view.hand.length;
  const deckBefore = view.players[0].deck_count;
  const commandBefore = view.players[0].command;
  view = heuristic.act(cycle.key, 0);
  assert(view.needs_ai, "Human Cycle should expose the intermediate state before the AI reply");
  assert(view.last_action?.actor === 0 && view.last_action?.kind === "Cycle", "Human Cycle was not surfaced as the last action");
  assert(view.hand.length === handBefore, "Cycle should replace rather than grow the hand");
  assert(view.players[0].deck_count === deckBefore - 1, "Cycle did not consume one deck card");
  assert(view.players[0].command === commandBefore - cycle.command_cost, "Cycle did not spend its Command cost");
  view = settleAi(view);
  assert(view.last_action?.actor === 1 || view.phase === "complete", "AI action was not exposed one step at a time");
}

let turns = 0;
while (view.phase !== "complete" && turns < 40) {
  view = settleAi(view);
  if (view.phase === "complete") break;

  if (view.phase === "choose_first" && view.active_player === 0) {
    const choose = view.legal_actions.find((item) => item.kind === "ChooseFirst" && item.choose_player === 1)
      || view.legal_actions[0];
    assert(choose, "Human chooser has no legal start choice");
    view = heuristic.act(choose.key, 0);
    turns += 1;
    continue;
  }

  const action = view.legal_actions.find((item) => item.kind === "Pass") || view.legal_actions[0];
  assert(action, "No action available during heuristic smoke match");
  view = heuristic.act(action.key, 0);
  turns += 1;
}
view = settleAi(view);
assert(turns < 40 || view.phase === "complete", "Heuristic smoke match did not make progress");

const hotseat = new BrowserSession(cards, deck, "hotseat", 1701);
let hot = hotseat.snapshot(null);
assert(hot.needs_reveal === true, "Hot-seat opening should be private");
assert(hot.hand.length === 0, "Hot-seat public snapshot leaked a hand");

hot = hotseat.view(0);
assert(hot.hand.length === 10 && hot.mulligan_available, "Player 1 opening hand not revealable");
hot = hotseat.mulligan([], 0);
assert(hot.viewer === null && hot.needs_reveal, "Hot-seat did not return to privacy gate");
hot = hotseat.view(1);
assert(hot.hand.length === 10, "Player 2 opening hand not revealable");
hot = hotseat.mulligan([], 1);
assert(hot.viewer === null && hot.needs_reveal, "Battle did not return to privacy gate");

console.log("PASS: native browser engine supports Command, Cycle, persistent decks, flexible formations, completion utilities, paced AI turns, mulligans, privacy, and match progress");
