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
  nameEffects: new Set(["move_adjacent_optional", "reveal_enemy_scheme"]),
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
  const draw = view.legal_actions.find((item) => item.kind === "Draw");
  assert(draw, "Once-per-Battle Draw action is missing");
  const handBefore = view.hand.length;
  const deckBefore = view.players[0].deck_count;
  view = heuristic.act(draw.key, 0);
  assert(view.needs_ai, "Human Draw should expose the intermediate state before the AI reply");
  assert(view.last_action?.actor === 0 && view.last_action?.kind === "Draw", "Human Draw was not surfaced as the last action");
  assert(view.hand.length === handBefore + 1, "Draw did not add one visible card");
  assert(view.players[0].deck_count === deckBefore - 1, "Draw did not consume one deck card");
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

console.log("PASS: native browser engine supports Draw, paced AI turns, mulligans, privacy, and match progress");
