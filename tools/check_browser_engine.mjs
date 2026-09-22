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
if (view.phase !== "complete") {
  assert(view.active_player === 0, "AI did not yield back to the human");
  assert(view.legal_actions.length > 0, "Human has no legal actions");
}

let turns = 0;
while (view.phase !== "complete" && turns < 30) {
  turns += 1;
  const action = view.legal_actions.find((item) => item.kind === "Pass") || view.legal_actions[0];
  assert(action, "No action available during heuristic smoke match");
  view = heuristic.act(action.key, 0);
  if (view.phase === "choose_first" && view.active_player === 0) {
    const choose = view.legal_actions.find((item) => item.kind === "ChooseFirst" && item.choose_player === 1)
      || view.legal_actions[0];
    view = heuristic.act(choose.key, 0);
  }
}
assert(turns < 30 || view.phase === "complete", "Heuristic smoke match did not make progress");

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

console.log("PASS: native browser engine starts, mulligans, preserves privacy, and progresses without Pyodide");
