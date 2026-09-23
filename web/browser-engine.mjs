const FRONT_NAMES = ["Left", "Center", "Right"];
const RANK_NAMES = { front: "Frontline", rear: "Rear" };
const RANKS = ["front", "rear"];
const POSITIONS = [];
for (let front = 0; front < 3; front += 1) {
  for (const rank of RANKS) POSITIONS.push({ front, rank });
}

class SeededRng {
  constructor(seed) {
    this.state = (Number(seed) >>> 0) || 0x6d2b79f5;
  }

  next() {
    let t = this.state += 0x6d2b79f5;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }

  int(limit) {
    return Math.floor(this.next() * limit);
  }

  shuffle(values) {
    for (let index = values.length - 1; index > 0; index -= 1) {
      const other = this.int(index + 1);
      [values[index], values[other]] = [values[other], values[index]];
    }
    return values;
  }
}

function emptySlot() {
  return { subject: null, link: null, name: null, temporary_strength: 0 };
}

function slotOccupied(slot) {
  return Boolean(slot.subject || slot.link || slot.name);
}

function nextShuffleSeed(seed) {
  return (Math.imul(seed >>> 0, 1664525) + 1013904223) >>> 0;
}

function shuffleForBattle(values, seed) {
  for (let index = values.length - 1; index > 0; index -= 1) {
    seed = nextShuffleSeed(seed);
    const other = seed % (index + 1);
    [values[index], values[other]] = [values[other], values[index]];
  }
  return seed >>> 0;
}

function makeBoard() {
  return Array.from({ length: 2 }, () =>
    Array.from({ length: 3 }, () => [emptySlot(), emptySlot()])
  );
}

function slotAt(state, player, front, rank) {
  return state.board[player][front][rank === "front" ? 0 : 1];
}

function positionPayload(position) {
  return {
    front: position.front,
    front_name: FRONT_NAMES[position.front],
    rank: position.rank,
    rank_name: RANK_NAMES[position.rank],
  };
}

function adjacentPositions(position) {
  const result = [];
  if (position.front > 0) result.push({ front: position.front - 1, rank: position.rank });
  if (position.front < 2) result.push({ front: position.front + 1, rank: position.rank });
  return result;
}

function cloneState(state) {
  return JSON.parse(JSON.stringify(state));
}

function actionKey(action) {
  if (action.kind === "Pass") return "pass";
  if (action.kind === "Draw") return "draw";
  if (action.kind === "Cycle") return "cycle:" + action.card_id;
  if (action.kind === "ChooseFirst") return "choose_first:" + action.choose_player;
  if (action.kind === "PlaySubject") {
    return "subject:" + action.card_id + ":" + action.position.front + ":" + action.position.rank;
  }
  if (action.kind === "PlayLink") {
    return "link:" + action.card_id + ":" + action.position.front + ":" + action.position.rank;
  }
  if (action.kind === "PlayName") {
    const move = action.move_to
      ? action.move_to.front + ":" + action.move_to.rank
      : "stay";
    return "name:" + action.card_id + ":" + action.position.front + ":" +
      action.position.rank + ":" + move;
  }
  if (action.kind === "PlayScheme") {
    return "scheme:" + action.card_id + ":" + action.front;
  }
  if (action.kind === "SetStratagem") return "stratagem:" + action.card_id;
  if (action.kind === "PlayPlot") {
    const targets = (action.targets || [])
      .map((target) => target.player + ":" + target.front + ":" + target.rank)
      .join(";");
    return "plot:" + action.card_id + ":" + targets;
  }
  throw new Error("Unsupported action kind: " + action.kind);
}

function unique(values) {
  return [...new Set(values)];
}

class BrowserEngine {
  constructor(cardData) {
    this.cards = Object.fromEntries(cardData.cards.map((card) => [card.id, card]));
  }

  newOpeningState(deck, rng) {
    const decks = [rng.shuffle([...deck]), rng.shuffle([...deck])];
    const players = decks.map((cards) => ({
      deck: cards,
      hand: [],
      discard: [],
      victories: 0,
      passed: false,
      command: 20,
      free_cycle: false,
    }));
    const state = {
      players,
      board: makeBoard(),
      schemes: [[null, null, null], [null, null, null]],
      stratagems: [null, null],
      stratagem_used: [false, false],
      draw_used: [false, false],
      discarded_this_battle: [0, 0],
      command_spent_this_battle: [0, 0],
      command_refunded_this_battle: [0, 0],
      battle_start_command: [20, 20],
      deck_reshuffles: [0, 0],
      pass_order: [],
      battle: 1,
      phase: "battle",
      active_player: 0,
      chooser: null,
      winner: null,
      turn_number: 0,
      shuffle_seed: 0,
    };
    this.draw(state, 0, 10);
    this.draw(state, 1, 10);
    return state;
  }

  reshuffleDiscardIntoDeck(state, player) {
    const ps = state.players[player];
    if (ps.deck.length || !ps.discard.length) return false;
    const pool = [...ps.discard];
    ps.discard = [];
    state.shuffle_seed = shuffleForBattle(pool, state.shuffle_seed >>> 0);
    ps.deck = pool;
    state.deck_reshuffles[player] += 1;
    return true;
  }

  draw(state, player, count) {
    const ps = state.players[player];
    for (let i = 0; i < count; i += 1) {
      if (!ps.deck.length) this.reshuffleDiscardIntoDeck(state, player);
      if (!ps.deck.length) break;
      ps.hand.push(ps.deck.pop());
    }
  }

  applyMulligan(state, player, indices, rng) {
    const ordered = [...indices].sort((a, b) => a - b);
    if (ordered.length > 2 || new Set(ordered).size !== ordered.length) {
      throw new Error("Choose at most two distinct cards");
    }
    const hand = state.players[player].hand;
    if (ordered.some((index) => index < 0 || index >= hand.length)) {
      throw new Error("Mulligan selection is outside the opening hand");
    }
    const returned = ordered.map((index) => hand[index]);
    for (const index of [...ordered].sort((a, b) => b - a)) hand.splice(index, 1);
    state.players[player].deck.push(...returned);
    rng.shuffle(state.players[player].deck);
    this.draw(state, player, returned.length);
  }

  legalActions(state) {
    if (state.phase === "complete") return [];
    if (state.phase === "choose_first") {
      return [this.action("ChooseFirst", { choose_player: 0 }), this.action("ChooseFirst", { choose_player: 1 })];
    }

    const player = state.active_player;
    if (state.players[player].passed) throw new Error("A passed player cannot become active");
    let actions = [this.action("Pass")];
    const playerState = state.players[player];
    if (
      playerState.hand.length &&
      (playerState.deck.length || playerState.discard.length)
    ) {
      actions.push(...unique(playerState.hand).map((cardId) =>
        this.action("Cycle", { card_id: cardId })
      ));
    }

    for (const cardId of unique(state.players[player].hand)) {
      const card = this.cards[cardId];
      if (!card) continue;
      if (card.type === "subject") actions.push(...this.subjectActions(state, player, cardId));
      else if (card.type === "link") actions.push(...this.linkActions(state, player, cardId));
      else if (card.type === "name") actions.push(...this.nameActions(state, player, cardId));
      else if (card.type === "plot" && card.veiled) actions.push(...this.schemeActions(state, player, cardId));
      else if (card.type === "plot" && !this.immediateStoryLocked(state, player)) {
        actions.push(...this.plotActions(state, player, cardId));
      } else if (
        card.type === "stratagem" &&
        !state.stratagem_used[player] &&
        state.stratagems[player] == null
      ) {
        actions.push(this.action("SetStratagem", { card_id: cardId }));
      }
    }
    actions = actions.filter((action) =>
      this.commandCostForAction(state, action) <= playerState.command
    );
    return actions;
  }

  commandCostForAction(state, action) {
    const player = state.active_player;
    if (action.kind === "Cycle") {
      return state.players[player].free_cycle ? 0 : 1;
    }
    if (["Pass", "ChooseFirst", "Draw"].includes(action.kind)) return 0;
    if (!action.card_id) return 0;

    let cost = Number(this.cards[action.card_id].command_cost || 0);
    let targetFront = null;
    if (["PlaySubject", "PlayLink", "PlayName"].includes(action.kind)) {
      targetFront = action.position?.front ?? null;
    } else if (action.kind === "PlayScheme") {
      targetFront = action.front;
    }
    if (targetFront != null) {
      cost = Math.max(1, cost - this.adjacentCommandDiscount(state, player, targetFront));
    }
    return cost;
  }

  adjacentCommandDiscount(state, player, targetFront) {
    let discount = 0;
    for (const position of POSITIONS) {
      const slot = slotAt(state, player, position.front, position.rank);
      if (!(slot.subject && slot.link && slot.name)) continue;
      if (Math.abs(position.front - targetFront) !== 1) continue;
      discount = Math.max(
        discount,
        Number(this.cards[slot.name].rules?.adjacent_command_discount || 0)
      );
    }
    return discount;
  }

  spendCommand(state, player, amount) {
    if (amount < 0 || amount > state.players[player].command) {
      throw new Error("Not enough Command");
    }
    state.players[player].command -= amount;
    state.command_spent_this_battle[player] += amount;
  }

  gainCommand(state, player, amount) {
    const before = state.players[player].command;
    state.players[player].command = Math.min(20, before + Math.max(0, amount));
    state.command_refunded_this_battle[player] += state.players[player].command - before;
  }

  action(kind, fields = {}) {
    const action = {
      kind,
      card_id: null,
      position: null,
      front: null,
      targets: [],
      move_to: null,
      choose_player: null,
      ...fields,
    };
    action.key = actionKey(action);
    return action;
  }

  subjectActions(state, player, cardId) {
    const required = this.cards[cardId].rules?.placement?.rank ?? null;
    return POSITIONS
      .filter((position) => !required || position.rank === required)
      .filter((position) => !slotAt(state, player, position.front, position.rank).subject)
      .map((position) => this.action("PlaySubject", { card_id: cardId, position: { ...position } }));
  }

  linkActions(state, player, cardId) {
    return POSITIONS
      .filter((position) => {
        const slot = slotAt(state, player, position.front, position.rank);
        return !slot.link;
      })
      .map((position) => this.action("PlayLink", { card_id: cardId, position: { ...position } }));
  }

  nameActions(state, player, cardId) {
    const actions = [];
    const effect = this.cards[cardId].rules?.on_name_attached;
    for (const position of POSITIONS) {
      const slot = slotAt(state, player, position.front, position.rank);
      if (slot.name) continue;
      actions.push(this.action("PlayName", { card_id: cardId, position: { ...position } }));
      if (effect !== "move_adjacent_optional" || !slot.subject) continue;
      for (const destination of adjacentPositions(position)) {
        if (!slotOccupied(slotAt(state, player, destination.front, destination.rank))) {
          actions.push(this.action("PlayName", {
            card_id: cardId,
            position: { ...position },
            move_to: { ...destination },
          }));
        }
      }
    }
    return actions;
  }

  plotActions(state, player, cardId) {
    const effect = this.cards[cardId].rules?.effect;
    const actions = [];
    if (effect === "discredit_subject" || effect === "return_name_or_weaken") {
      const opponent = 1 - player;
      for (const position of POSITIONS) {
        const slot = slotAt(state, opponent, position.front, position.rank);
        if (!slot.subject || this.subjectProtectedFromStory(slot)) continue;
        actions.push(this.action("PlayPlot", {
          card_id: cardId,
          targets: [{ player: opponent, ...position }],
        }));
      }
      return actions;
    }
    if (effect === "move_subject") {
      for (const source of POSITIONS) {
        const sourceSlot = slotAt(state, player, source.front, source.rank);
        if (!sourceSlot.subject) continue;
        const required = this.cards[sourceSlot.subject].rules?.placement?.rank ?? null;
        for (const destination of POSITIONS) {
          if (source.front === destination.front && source.rank === destination.rank) continue;
          if (required && destination.rank !== required) continue;
          if (slotAt(state, player, destination.front, destination.rank).subject) continue;
          actions.push(this.action("PlayPlot", {
            card_id: cardId,
            targets: [
              { player, ...source },
              { player, ...destination },
            ],
          }));
        }
      }
      return actions;
    }
    actions.push(this.action("PlayPlot", { card_id: cardId }));
    return actions;
  }

  schemeActions(state, player, cardId) {
    const actions = [];
    for (let front = 0; front < 3; front += 1) {
      if (state.schemes[player][front] == null) {
        actions.push(this.action("PlayScheme", { card_id: cardId, front }));
      }
    }
    return actions;
  }

  subjectProtectedFromStory(slot) {
    if (!slot.link || !slot.name || !slot.subject) return false;
    if (this.cards[slot.link].rules?.protect_subject_from_opponent_plot) return true;
    return Boolean(
      this.cards[slot.name].rules?.complete_protection_from_opponent_plot
    );
  }

  takeFromHand(state, player, cardId) {
    const index = state.players[player].hand.indexOf(cardId);
    if (index < 0) throw new Error("Card is not in hand: " + cardId);
    state.players[player].hand.splice(index, 1);
  }

  discardCard(state, player, cardId) {
    state.players[player].discard.push(cardId);
    state.discarded_this_battle[player] += 1;
  }

  apply(state, action, { validate = true } = {}) {
    if (validate) {
      const legal = new Map(this.legalActions(state).map((candidate) => [candidate.key, candidate]));
      if (!legal.has(action.key)) throw new Error("Action is no longer legal");
      action = legal.get(action.key);
    }

    const events = [];
    if (action.kind === "ChooseFirst") {
      state.active_player = action.choose_player;
      state.chooser = null;
      state.phase = "battle";
      state.turn_number += 1;
      return events;
    }

    const actor = state.active_player;
    if (action.kind === "Pass") {
      this.pass(state, actor, events);
      return events;
    }

    if (action.kind === "Draw") {
      throw new Error("Draw is disabled in the canonical Command rules");
    }

    if (action.kind === "Cycle") {
      const cost = this.commandCostForAction(state, action);
      this.spendCommand(state, actor, cost);
      const wasFree = state.players[actor].free_cycle;
      this.takeFromHand(state, actor, action.card_id);
      this.discardCard(state, actor, action.card_id);
      this.draw(state, actor, 1);
      if (wasFree) state.players[actor].free_cycle = false;
      this.advanceTurn(state);
      state.turn_number += 1;
      return events;
    }

    if (["PlaySubject", "PlayLink", "PlayName", "PlayPlot", "PlayScheme", "SetStratagem"].includes(action.kind)) {
      this.spendCommand(state, actor, this.commandCostForAction(state, action));
    }

    const completionBefore = ["PlaySubject", "PlayLink", "PlayName"].includes(action.kind)
      ? (() => {
          const slot = slotAt(state, actor, action.position.front, action.position.rank);
          return Boolean(slot.subject && slot.link && slot.name);
        })()
      : null;
    let completionPosition = action.position ? { ...action.position } : null;

    if (action.kind === "PlaySubject") {
      this.takeFromHand(state, actor, action.card_id);
      const target = slotAt(state, actor, action.position.front, action.position.rank);
      target.subject = action.card_id;
      this.resolveTriggeredSchemes(state, actor, "opponent_plays_subject", action.position, events);
      this.resolveStratagemEvent(state, "subject_played", actor, action.card_id, action.position, events);
    } else if (action.kind === "PlayLink") {
      this.takeFromHand(state, actor, action.card_id);
      const target = slotAt(state, actor, action.position.front, action.position.rank);
      target.link = action.card_id;
      if (target.subject) {
        const subject = this.cards[target.subject];
        target.temporary_strength += Number(subject.rules?.on_link_attached?.temporary_strength || 0);
      }
      this.resolveTriggeredSchemes(state, actor, "opponent_plays_link", action.position, events);
    } else if (action.kind === "PlayName") {
      this.takeFromHand(state, actor, action.card_id);
      const target = slotAt(state, actor, action.position.front, action.position.rank);
      target.name = action.card_id;
      const finalPosition = this.onNameAttached(state, actor, action.position, action.move_to, events);
      completionPosition = { ...finalPosition };
      this.resolveStratagemEvent(state, "name_played", actor, action.card_id, finalPosition, events);
    } else if (action.kind === "PlayPlot") {
      this.takeFromHand(state, actor, action.card_id);
      const targets = action.targets.map((target) => ({ ...target }));
      const cancelled = this.resolvePreStoryStratagem(state, actor, events);
      if (!cancelled) {
        this.resolvePlot(state, actor, action);
        this.resolvePlotTargetSchemes(state, actor, targets, events);
      }
      this.discardCard(state, actor, action.card_id);
    } else if (action.kind === "PlayScheme") {
      this.takeFromHand(state, actor, action.card_id);
      state.schemes[actor][action.front] = { card_id: action.card_id, revealed: false };
    } else if (action.kind === "SetStratagem") {
      this.takeFromHand(state, actor, action.card_id);
      state.stratagems[actor] = { card_id: action.card_id, revealed: false };
      state.stratagem_used[actor] = true;
    } else {
      throw new Error("Unhandled action: " + action.kind);
    }

    if (completionBefore === false && completionPosition) {
      const completed = slotAt(
        state,
        actor,
        completionPosition.front,
        completionPosition.rank
      );
      if (completed.subject && completed.link && completed.name) {
        this.resolveNameCompletion(
          state,
          actor,
          completionPosition,
          events
        );
      }
    }

    this.advanceTurn(state);
    state.turn_number += 1;
    return events;
  }

  advanceTurn(state) {
    const opponent = 1 - state.active_player;
    if (!state.players[opponent].passed) state.active_player = opponent;
  }

  pass(state, player, events) {
    state.players[player].passed = true;
    state.pass_order.push(player);
    this.resolveStratagemEvent(state, "pass", player, null, null, events);
    this.resolvePassSchemes(state, player, events);
    const opponent = 1 - player;
    if (state.players[opponent].passed) this.scoreBattle(state, events);
    else state.active_player = opponent;
    state.turn_number += 1;
  }

  scoreBattle(state, events) {
    const scores = [0, 1].map((player) =>
      [0, 1, 2].map((front) => this.frontStrength(state, player, front))
    );
    const controls = [0, 0];
    for (let front = 0; front < 3; front += 1) {
      if (scores[0][front] > scores[1][front]) controls[0] += 1;
      else if (scores[1][front] > scores[0][front]) controls[1] += 1;
    }

    let winner;
    if (controls[0] >= 2) winner = 0;
    else if (controls[1] >= 2) winner = 1;
    else {
      const totals = [scores[0].reduce((a, b) => a + b, 0), scores[1].reduce((a, b) => a + b, 0)];
      if (totals[0] > totals[1]) winner = 0;
      else if (totals[1] > totals[0]) winner = 1;
      else winner = state.pass_order[0];
    }

    state.players[winner].victories += 1;
    const loser = 1 - winner;
    this.revealStratagemsAtBattleEnd(state, events);
    this.discardBattlefield(state);

    if (state.players[winner].victories >= 2) {
      state.phase = "complete";
      state.winner = winner;
      state.chooser = null;
      return;
    }

    state.battle += 1;
    state.discarded_this_battle = [0, 0];
    state.command_spent_this_battle = [0, 0];
    state.command_refunded_this_battle = [0, 0];
    state.stratagem_used = [false, false];
    state.draw_used = [false, false];
    state.pass_order = [];
    for (let player = 0; player < 2; player += 1) {
      const ps = state.players[player];
      ps.command = Math.min(20, ps.command + 10);
      ps.free_cycle = false;
      this.draw(state, player, Math.max(0, 10 - ps.hand.length));
      ps.passed = false;
    }
    state.battle_start_command = [
      state.players[0].command,
      state.players[1].command,
    ];
    state.phase = "choose_first";
    state.chooser = loser;
    state.active_player = loser;
  }

  recycleNonHandCards(state) {
    let seed = state.shuffle_seed >>> 0;
    for (let player = 0; player < 2; player += 1) {
      const ps = state.players[player];
      const pool = [...ps.deck, ...ps.discard];
      ps.discard = [];
      seed = shuffleForBattle(pool, seed);
      ps.deck = pool;
      this.draw(state, player, Math.max(0, 10 - ps.hand.length));
    }
    state.shuffle_seed = seed >>> 0;
  }

  discardBattlefield(state) {
    for (let player = 0; player < 2; player += 1) {
      for (const position of POSITIONS) {
        const slot = slotAt(state, player, position.front, position.rank);
        for (const cardId of [slot.subject, slot.link, slot.name]) {
          if (cardId) state.players[player].discard.push(cardId);
        }
        Object.assign(slot, emptySlot());
      }
      for (let front = 0; front < 3; front += 1) {
        const scheme = state.schemes[player][front];
        if (scheme) state.players[player].discard.push(scheme.card_id);
        state.schemes[player][front] = null;
      }
      const stratagem = state.stratagems[player];
      if (stratagem) state.players[player].discard.push(stratagem.card_id);
      state.stratagems[player] = null;
    }
  }

  removeLink(state, player, position) {
    const slot = slotAt(state, player, position.front, position.rank);
    const linkId = slot.link;
    const nameId = slot.name;
    slot.link = null;
    slot.name = null;
    if (linkId) this.discardCard(state, player, linkId);
    if (nameId) state.players[player].hand.push(nameId);
  }

  removeName(state, player, position, toHand = true) {
    const slot = slotAt(state, player, position.front, position.rank);
    if (!slot.name) return;
    const nameId = slot.name;
    slot.name = null;
    if (toHand) state.players[player].hand.push(nameId);
    else this.discardCard(state, player, nameId);
  }

  moveSubject(state, player, source, destination, adjacentOnly = false) {
    const from = slotAt(state, player, source.front, source.rank);
    const to = slotAt(state, player, destination.front, destination.rank);
    if (!from.subject) throw new Error("Source has no Subject");
    if (slotOccupied(to)) throw new Error("Destination is occupied");
    if (adjacentOnly && !adjacentPositions(source).some((pos) =>
      pos.front === destination.front && pos.rank === destination.rank
    )) throw new Error("Destination is not adjacent");
    const required = this.cards[from.subject].rules?.placement?.rank ?? null;
    if (required && destination.rank !== required) throw new Error("Subject cannot occupy that rank");
    Object.assign(to, from);
    Object.assign(from, emptySlot());
  }

  resolvePlot(state, actor, action) {
    const effect = this.cards[action.card_id].rules?.effect;
    if (effect === "discredit_subject") {
      const target = action.targets[0];
      const slot = slotAt(state, target.player, target.front, target.rank);
      if (slot.link) this.removeLink(state, target.player, target);
      else if (slot.subject) slot.temporary_strength -= 2;
      return;
    }
    if (effect === "return_name_or_weaken") {
      const target = action.targets[0];
      const slot = slotAt(state, target.player, target.front, target.rank);
      if (slot.name) this.removeName(state, target.player, target, true);
      else if (slot.subject) slot.temporary_strength -= 2;
      return;
    }
    if (effect === "move_subject") {
      const [source, destination] = action.targets;
      this.moveSubject(state, actor, source, destination, false);
    }
  }

  resolveNameCompletion(state, player, position, events) {
    const slot = slotAt(state, player, position.front, position.rank);
    if (!(slot.subject && slot.link && slot.name)) return;
    const completion = this.cards[slot.name].rules?.on_completion || {};
    const effect = completion.effect;

    if (effect === "gain_command") {
      this.gainCommand(state, player, Number(completion.amount || 1));
    } else if (effect === "grant_free_cycle") {
      state.players[player].free_cycle = true;
    } else if (effect === "reveal_enemy_scheme") {
      const owner = 1 - player;
      const scheme = state.schemes[owner][position.front];
      if (scheme && !scheme.revealed) {
        scheme.revealed = true;
        events.push({ type: "reveal", zone: "scheme", card_id: scheme.card_id });
      }
    } else if (effect === "recover_recent_link") {
      const discard = state.players[player].discard;
      for (let index = discard.length - 1; index >= 0; index -= 1) {
        const cardId = discard[index];
        if (this.cards[cardId]?.type !== "link") continue;
        discard.splice(index, 1);
        state.players[player].hand.push(cardId);
        break;
      }
    }
  }

  onNameAttached(state, player, position, moveTo, events) {
    const slot = slotAt(state, player, position.front, position.rank);
    const card = this.cards[slot.name];
    const effect = card.rules?.on_name_attached;
    if (effect === "reveal_enemy_scheme") {
      const owner = 1 - player;
      const scheme = state.schemes[owner][position.front];
      if (scheme && !scheme.revealed) {
        scheme.revealed = true;
        events.push({ type: "reveal", zone: "scheme", card_id: scheme.card_id });
      }
    }
    if (effect === "move_adjacent_optional" && moveTo) {
      this.moveSubject(state, player, position, moveTo, true);
      return moveTo;
    }
    return position;
  }

  preferredSubjectPosition(state, player, front) {
    if (slotAt(state, player, front, "front").subject) return { front, rank: "front" };
    if (slotAt(state, player, front, "rear").subject) return { front, rank: "rear" };
    return null;
  }

  resolveTriggeredSchemes(state, actor, event, position, events) {
    const front = position.front;
    const controller = 1 - actor;
    const scheme = state.schemes[controller][front];
    if (!scheme) return;
    const rules = this.cards[scheme.card_id].rules?.scheme || {};
    if (rules.trigger !== event) return;
    if (rules.requires_own_subject && !this.preferredSubjectPosition(state, controller, front)) return;
    this.revealAndResolveScheme(state, controller, front, actor, position, events);
  }

  resolvePlotTargetSchemes(state, actor, targets, events) {
    const opponent = 1 - actor;
    const fronts = unique(
      targets.filter((target) => target.player === opponent).map((target) => target.front)
    ).sort();
    for (const front of fronts) {
      const scheme = state.schemes[opponent][front];
      if (!scheme) continue;
      const rules = this.cards[scheme.card_id].rules?.scheme || {};
      if (rules.trigger !== "opponent_plot_targets_your_card") continue;
      if (rules.requires_own_subject && !this.preferredSubjectPosition(state, opponent, front)) continue;
      this.revealAndResolveScheme(state, opponent, front, actor, null, events);
    }
  }

  resolvePassSchemes(state, actor, events) {
    const opponent = 1 - actor;
    for (let front = 0; front < 3; front += 1) {
      const scheme = state.schemes[opponent][front];
      if (!scheme) continue;
      const rules = this.cards[scheme.card_id].rules?.scheme || {};
      if (rules.trigger !== "opponent_passes") continue;
      if (rules.requires_own_subject && !this.preferredSubjectPosition(state, opponent, front)) continue;
      this.revealAndResolveScheme(state, opponent, front, actor, null, events);
    }
  }

  revealAndResolveScheme(state, controller, front, actor, position, events) {
    const scheme = state.schemes[controller][front];
    if (!scheme) return;
    if (!scheme.revealed) {
      scheme.revealed = true;
      events.push({ type: "reveal", zone: "scheme", card_id: scheme.card_id });
    }
    const cardId = scheme.card_id;
    const rules = this.cards[cardId].rules?.scheme || {};
    const amount = Number(rules.amount || 0);
    if (rules.effect === "penalize_played_subject" && position) {
      const target = slotAt(state, actor, position.front, position.rank);
      if (target.subject) target.temporary_strength -= amount;
    } else if (rules.effect === "discard_played_link" && position) {
      const target = slotAt(state, actor, position.front, position.rank);
      if (target.link) this.removeLink(state, actor, position);
    } else if (rules.effect === "reinforce_front") {
      const target = this.preferredSubjectPosition(state, controller, front);
      if (target) slotAt(state, controller, target.front, target.rank).temporary_strength += amount;
    }
    state.schemes[controller][front] = null;
    this.discardCard(state, controller, cardId);
  }

  stratagemTriggerMatches(controller, rules, event, actor, cardId, position) {
    const trigger = rules.trigger || {};
    if (trigger.event !== event) return false;
    const scope = trigger.actor || "either";
    if (scope === "opponent" && actor === controller) return false;
    if (scope === "controller" && actor !== controller) return false;
    if (trigger.roles && (!cardId || !trigger.roles.includes(this.cards[cardId]?.role))) return false;
    if (trigger.ranks && (!position || !trigger.ranks.includes(position.rank))) return false;
    return true;
  }

  revealStratagem(state, controller, events) {
    const stratagem = state.stratagems[controller];
    if (!stratagem) return {};
    if (!stratagem.revealed) {
      stratagem.revealed = true;
      events.push({ type: "reveal", zone: "stratagem", card_id: stratagem.card_id });
    }
    return this.cards[stratagem.card_id].rules?.stratagem || {};
  }

  resolveStratagemEvent(state, event, actor, cardId, position, events) {
    for (const controller of [actor, 1 - actor]) {
      const stratagem = state.stratagems[controller];
      if (!stratagem || stratagem.revealed) continue;
      const rules = this.cards[stratagem.card_id].rules?.stratagem || {};
      if (!this.stratagemTriggerMatches(controller, rules, event, actor, cardId, position)) continue;
      const revealed = this.revealStratagem(state, controller, events);
      const effect = revealed.reveal_effect || {};
      if (effect.effect === "penalize_trigger_subject" && position) {
        const target = slotAt(state, actor, position.front, position.rank);
        if (target.subject) target.temporary_strength -= Number(effect.amount || 0);
      }
    }
  }

  resolvePreStoryStratagem(state, actor, events) {
    const controller = 1 - actor;
    const stratagem = state.stratagems[controller];
    if (!stratagem || stratagem.revealed) return false;
    const rules = this.cards[stratagem.card_id].rules?.stratagem || {};
    if (!this.stratagemTriggerMatches(controller, rules, "immediate_story_played", actor, null, null)) {
      return false;
    }
    const revealed = this.revealStratagem(state, controller, events);
    return Boolean(revealed.reveal_effect?.cancel_story);
  }

  revealStratagemsAtBattleEnd(state, events) {
    for (let controller = 0; controller < 2; controller += 1) {
      const stratagem = state.stratagems[controller];
      if (stratagem && !stratagem.revealed) this.revealStratagem(state, controller, events);
    }
  }

  revealedStratagemRules(state) {
    const rows = [];
    for (let controller = 0; controller < 2; controller += 1) {
      const stratagem = state.stratagems[controller];
      if (stratagem?.revealed) {
        rows.push([controller, this.cards[stratagem.card_id].rules?.stratagem || {}]);
      }
    }
    return rows;
  }

  immediateStoryLocked(state, player) {
    return this.revealedStratagemRules(state).some(([controller, rules]) =>
      controller === player && Boolean(rules.continuous?.controller_immediate_story_lock)
    );
  }

  lineDefenseDisabled(state) {
    return this.revealedStratagemRules(state).some(([, rules]) =>
      Boolean(rules.continuous?.disable_line_defense)
    );
  }

  positionStrength(state, player, position) {
    const slot = slotAt(state, player, position.front, position.rank);
    if (!slot.subject) return 0;
    const subject = this.cards[slot.subject];
    let value = Number(subject.strength || 0) + Number(slot.temporary_strength || 0);

    if (position.rank === "front" && !this.lineDefenseDisabled(state)) value += 1;

    if (subject.role === "swordsman" && position.rank === "front") value += 1;
    if (
      subject.role === "spearman" &&
      position.rank === "front" &&
      slotAt(state, player, position.front, "rear").subject
    ) value += 1;
    if (
      subject.role === "archer" &&
      position.rank === "rear" &&
      slotAt(state, player, position.front, "front").subject
    ) value += 2;
    if ((subject.role === "ship" || subject.role === "stronghold") && position.rank === "rear") value += 1;

    if (position.rank === "front") {
      const rear = slotAt(state, player, position.front, "rear");
      if (rear.subject && this.cards[rear.subject].role === "healer") value += 2;
    }

    for (const adjacent of adjacentPositions(position)) {
      const sourceSlot = slotAt(state, player, adjacent.front, adjacent.rank);
      if (!sourceSlot.subject) continue;
      const source = this.cards[sourceSlot.subject];
      const aura = Number(source.rules?.adjacent_strength_aura || 0);
      const required = source.rules?.aura_requires_rank ?? null;
      if (aura && (!required || adjacent.rank === required)) value += aura;
    }

    for (const modifier of subject.rules?.strength_modifiers || []) {
      const when = modifier.when || {};
      if (when.rank && when.rank !== position.rank) continue;
      if (when.own_discard_at_least != null && state.players[player].discard.length < Number(when.own_discard_at_least)) continue;
      if (when.adjacent_subject_has_name) {
        const found = adjacentPositions(position).some((adjacent) => {
          const adjacentSlot = slotAt(state, player, adjacent.front, adjacent.rank);
          return Boolean(adjacentSlot.subject && adjacentSlot.name);
        });
        if (!found) continue;
      }
      value += Number(modifier.amount || 0);
    }

    let linkRules = null;
    if (slot.link) {
      linkRules = this.cards[slot.link].rules || {};
      value += Number(linkRules.strength_bonus || 0);
    }
    if (slot.name) {
      const name = this.cards[slot.name];
      value += Number(name.strength || 0);
      const rankBonus = name.rules?.rank_strength_bonus;
      if (rankBonus && rankBonus.rank === position.rank) value += Number(rankBonus.amount || 0);
      if (linkRules) {
        value += Number(linkRules.named_strength_bonus || 0);
        if (linkRules.discard_strength_bonus) {
          value += Math.min(
            state.discarded_this_battle[player] * Number(linkRules.discard_strength_bonus.per_card || 1),
            Number(linkRules.discard_strength_bonus.maximum || 0)
          );
        }
      }
    }

    for (const [controller, rules] of this.revealedStratagemRules(state)) {
      const continuous = rules.continuous || {};
      value += Number(continuous.role_strength_modifiers?.[subject.role] || 0);
      value += Number(continuous.rank_strength_modifiers?.[position.rank] || 0);
      if (controller === player) {
        value += Number(continuous.controller_rank_strength_modifiers?.[position.rank] || 0);
      }
      value += Number(
        slot.name
          ? continuous.named_subject_modifier || 0
          : continuous.unnamed_subject_modifier || 0
      );
    }

    return Math.max(0, value);
  }

  frontStrength(state, player, front) {
    let value =
      this.positionStrength(state, player, { front, rank: "front" }) +
      this.positionStrength(state, player, { front, rank: "rear" });

    const scheme = state.schemes[player][front];
    if (scheme && !scheme.revealed) {
      value += Number(this.cards[scheme.card_id].rules?.scheme?.face_down_front_bonus || 0);
    }

    const opponent = 1 - player;
    for (const rank of RANKS) {
      const enemy = slotAt(state, opponent, front, rank);
      if (enemy.subject && enemy.link && enemy.name) {
        value += Number(this.cards[enemy.link].rules?.opposing_front_modifier || 0);
      }
    }
    return value;
  }

  frontStrengths(state) {
    return [0, 1].map((player) => [0, 1, 2].map((front) => this.frontStrength(state, player, front)));
  }
}

function openingMulliganIndices(engine, hand, maximum = 2) {
  if (!hand.length || maximum <= 0) return [];
  const types = hand.map((id) => engine.cards[id].type);
  const stratagemCount = types.filter((value) => value === "stratagem").length;
  let seenStratagems = 0;
  const scored = hand.map((cardId, index) => {
    const card = engine.cards[cardId];
    let score = 2.5;
    if (card.type === "subject") score = 5 + 0.08 * Number(card.strength || 0);
    else if (card.type === "link") score = 3.2;
    else if (card.type === "name") score = 3.0;
    else if (card.type === "plot") score = card.veiled ? 3.7 : 2.6;
    else if (card.type === "stratagem") {
      seenStratagems += 1;
      score = seenStratagems === 1 ? 3.2 : 2.0;
      if (stratagemCount >= 3) score -= 0.35;
    }
    return { score, index };
  });
  scored.sort((a, b) => a.score - b.score || a.index - b.index);
  return scored.slice(0, maximum).map((item) => item.index).sort((a, b) => a - b);
}

class LightweightAgent {
  constructor(engine) {
    this.engine = engine;
  }

  chooseMulligan(hand) {
    return openingMulliganIndices(this.engine, hand);
  }

  choose(state) {
    const actions = this.engine.legalActions(state);
    if (actions.length <= 1) return actions[0];
    const player = state.active_player;
    let best = actions[0];
    let bestScore = -Infinity;
    for (const action of actions) {
      const clone = cloneState(state);
      this.engine.apply(clone, action, { validate: false });
      let score = this.evaluate(clone, player);
      if (action.kind === "SetStratagem") score += 0.75;
      if (action.kind === "Cycle") score -= 0.3;
      if (action.kind === "PlayName") {
        const slot = slotAt(state, player, action.position.front, action.position.rank);
        score += slot.subject ? 0.35 : 1.50;
      }
      if (action.kind === "PlayScheme") score += 0.2;
      if (action.kind === "PlayLink") {
        const slot = slotAt(state, player, action.position.front, action.position.rank);
        score += slot.subject ? 0.1 : 1.35;
      }
      if (score > bestScore || (score === bestScore && action.key < best.key)) {
        best = action;
        bestScore = score;
      }
    }
    return best;
  }

  evaluate(state, player) {
    if (state.phase === "complete") return state.winner === player ? 10000 : -10000;
    const opponent = 1 - player;
    let score = 80 * (state.players[player].victories - state.players[opponent].victories);
    const strengths = this.engine.frontStrengths(state);
    const margins = [0, 1, 2].map((front) => strengths[player][front] - strengths[opponent][front]);
    const ownControls = margins.filter((margin) => margin > 0).length;
    const enemyControls = margins.filter((margin) => margin < 0).length;
    score += 10 * (ownControls - enemyControls);
    if (ownControls >= 2) score += 14;
    if (enemyControls >= 2) score -= 14;
    score += 0.75 * margins.reduce((sum, margin) => sum + Math.max(-10, Math.min(10, margin)), 0);
    score += 1.25 * (state.players[player].hand.length - state.players[opponent].hand.length);
    score += 0.45 * (state.players[player].command - state.players[opponent].command);
    score += 0.35 * (Number(state.players[player].free_cycle) - Number(state.players[opponent].free_cycle));
    if (state.phase === "choose_first" && state.chooser === player) score += state.active_player === player ? 0 : 0.5;
    return score;
  }
}

export class BrowserSession {
  constructor(cardData, deckPayload, mode = "heuristic", seed = 1) {
    if (!["heuristic", "hotseat"].includes(mode)) throw new Error("Unsupported browser play mode: " + mode);
    const deck = Array.isArray(deckPayload) ? [...deckPayload] : [...deckPayload.cards];
    this.engine = new BrowserEngine(cardData);
    this.cards = this.engine.cards;
    this.deck = deck;
    this.mode = mode;
    this.seed = Number(seed) || 1;
    this.rng = new SeededRng(this.seed);
    this.humanPlayers = mode === "hotseat" ? new Set([0, 1]) : new Set([0]);
    this.state = this.engine.newOpeningState(deck, this.rng);
    this.state.shuffle_seed = (this.seed ^ 0x9e3779b9) >>> 0;
    this.setupComplete = false;
    this.mulliganPlayer = 0;
    this.mulliganChoices = new Map();
    this.log = [];
    this.actionSerial = 0;
    this.lastAction = null;
    this.openingPlayer = null;
    this.agent = mode === "heuristic" ? new LightweightAgent(this.engine) : null;
  }

  mulligan(indices, viewer) {
    if (this.setupComplete) throw new Error("The mulligan is already complete");
    if (!this.humanPlayers.has(viewer)) throw new Error("That player is not human-controlled");
    if (viewer !== this.mulliganPlayer) throw new Error("It is not that player's mulligan");
    const normalized = [...indices].map(Number).sort((a, b) => a - b);
    if (normalized.length > 2 || new Set(normalized).size !== normalized.length) {
      throw new Error("Choose at most two distinct cards");
    }
    this.mulliganChoices.set(viewer, normalized);

    if (this.mode === "hotseat" && viewer === 0) {
      this.mulliganPlayer = 1;
      return this.snapshot(null);
    }

    if (this.mode === "heuristic") {
      this.mulliganChoices.set(1, this.agent.chooseMulligan(this.state.players[1].hand));
    }

    this.finishMulligans();
    return this.snapshot(this.mode === "hotseat" ? null : 0);
  }

  finishMulligans() {
    for (let player = 0; player < 2; player += 1) {
      this.engine.applyMulligan(this.state, player, this.mulliganChoices.get(player) || [], this.rng);
    }
    this.state.active_player = this.rng.int(2);
    this.openingPlayer = this.state.active_player;
    this.engine.draw(this.state, this.state.active_player, 1);
    this.setupComplete = true;
    this.log.push(
      "Battle I begins. Player " + (this.state.active_player + 1) +
      " goes first and draws 1 additional opening card."
    );
  }

  act(key, viewer) {
    if (!this.setupComplete) throw new Error("Complete the opening mulligan first");
    if (!this.humanPlayers.has(viewer)) throw new Error("That player is not human-controlled");
    if (this.state.phase === "complete") throw new Error("The match is already complete");
    if (this.state.active_player !== viewer) throw new Error("It is not that player's turn");
    const action = this.engine.legalActions(this.state).find((item) => item.key === key);
    if (!action) throw new Error("That action is no longer legal");
    this.applyWithLog(action);
    if (this.mode === "hotseat") {
      return this.snapshot(null);
    }
    return this.snapshot(0);
  }

  view(viewer) {
    return this.snapshot(viewer);
  }

  aiStep() {
    if (!this.setupComplete) throw new Error("Complete the opening mulligan first");
    if (this.mode !== "heuristic") throw new Error("AI stepping is only available against the Tactical AI");
    if (this.state.phase === "complete" || this.humanPlayers.has(this.state.active_player)) {
      return this.snapshot(0);
    }
    const action = this.agent.choose(this.state);
    if (!action) throw new Error("AI has no legal action");
    this.applyWithLog(action);
    return this.snapshot(0);
  }

  applyWithLog(action) {
    const actor = this.state.active_player;
    const battleBefore = this.state.battle;
    const victoriesBefore = this.state.players.map((player) => player.victories);
    const label = this.describeAction(action, actor, false);
    const privateLabel = this.describeAction(action, actor, true);
    const events = this.engine.apply(this.state, action);
    this.actionSerial += 1;
    this.lastAction = {
      id: this.actionSerial,
      actor,
      kind: action.kind,
      card_id: action.card_id || null,
      public_label: label,
      private_label: privateLabel,
      events: events.map((event) => ({ ...event })),
      position: action.position ? { ...action.position } : null,
      front: action.front ?? null,
      targets: (action.targets || []).map((target) => ({ ...target })),
      move_to: action.move_to ? { ...action.move_to } : null,
      choose_player: action.choose_player ?? null,
    };
    this.log.push(label);

    for (const event of events) {
      if (event.type !== "reveal") continue;
      const title = this.cards[event.card_id]?.title || event.card_id;
      this.log.push((event.zone === "stratagem" ? "Stratagem" : "Veiled Story") + " revealed: " + title + ".");
    }

    const winner = [0, 1].find((player) => this.state.players[player].victories > victoriesBefore[player]);
    if (winner != null) this.log.push("Player " + (winner + 1) + " wins Battle " + this.roman(battleBefore) + ".");
    if (this.state.phase === "complete") {
      this.log.push("Player " + (this.state.winner + 1) + " wins the match.");
    } else if (this.state.battle !== battleBefore) {
      this.log.push(
        "Battle " + this.roman(this.state.battle) + " begins. Player " +
        (this.state.chooser + 1) + " chooses who starts."
      );
    }
  }

  snapshot(viewer = null) {
    if (viewer != null && viewer !== 0 && viewer !== 1) throw new Error("viewer must be 0, 1, or null");
    const state = this.state;
    const displayActive = this.setupComplete ? state.active_player : this.mulliganPlayer;
    const displayPhase = this.setupComplete ? state.phase : "mulligan";

    const players = state.players.map((player) => ({
      victories: player.victories,
      passed: player.passed,
      hand_count: player.hand.length,
      deck_count: player.deck.length,
      discard: [...player.discard],
      command: player.command,
      free_cycle: player.free_cycle,
    }));

    const board = [[], []];
    for (let owner = 0; owner < 2; owner += 1) {
      for (const position of POSITIONS) {
        const slot = slotAt(state, owner, position.front, position.rank);
        board[owner].push({
          ...positionPayload(position),
          subject: slot.subject,
          link: slot.link,
          name: slot.name,
          complete: Boolean(slot.subject && slot.link && slot.name),
          strength: this.engine.positionStrength(state, owner, position),
        });
      }
    }

    const schemes = [[], []];
    for (let owner = 0; owner < 2; owner += 1) {
      for (let front = 0; front < 3; front += 1) {
        const scheme = state.schemes[owner][front];
        if (!scheme) schemes[owner].push(null);
        else if (viewer === owner || scheme.revealed) {
          schemes[owner].push({ hidden: false, card_id: scheme.card_id, revealed: scheme.revealed });
        } else {
          schemes[owner].push({ hidden: true, card_id: null, revealed: false });
        }
      }
    }

    const stratagems = [];
    for (let owner = 0; owner < 2; owner += 1) {
      const stratagem = state.stratagems[owner];
      if (!stratagem) stratagems.push(null);
      else if (viewer === owner || stratagem.revealed) {
        stratagems.push({ hidden: false, card_id: stratagem.card_id, revealed: stratagem.revealed });
      } else {
        stratagems.push({ hidden: true, card_id: null, revealed: false });
      }
    }

    const frontStrengths = this.engine.frontStrengths(state);
    const frontControl = [0, 1, 2].map((front) =>
      frontStrengths[0][front] > frontStrengths[1][front]
        ? 0
        : frontStrengths[1][front] > frontStrengths[0][front]
          ? 1
          : null
    );

    let hand = [];
    let legalActions = [];
    if (!this.setupComplete) {
      if (viewer != null && viewer === this.mulliganPlayer && this.humanPlayers.has(viewer)) {
        hand = [...state.players[viewer].hand];
      }
    } else if (
      viewer != null &&
      this.humanPlayers.has(viewer) &&
      state.phase !== "complete" &&
      (this.mode === "heuristic" || viewer === state.active_player)
    ) {
      // Against the AI, keep the player's hand on the table while the
      // opponent takes its paced turn. Hot-seat still hides inactive hands.
      hand = [...state.players[viewer].hand];
      if (viewer === state.active_player) {
        legalActions = this.engine.legalActions(state).map((action) => this.actionView(action));
      }
    }

    return {
      mode: this.mode,
      seed: this.seed,
      opening_player: this.setupComplete ? this.openingPlayer : null,
      battle: state.battle,
      phase: displayPhase,
      active_player: displayActive,
      chooser: this.setupComplete ? state.chooser : null,
      winner: state.winner,
      viewer,
      needs_reveal: this.mode === "hotseat" && viewer == null && (!this.setupComplete || state.phase !== "complete"),
      mulligan_available: !this.setupComplete && viewer != null && viewer === this.mulliganPlayer,
      mulligan_limit: 2,
      players,
      board,
      schemes,
      stratagems,
      stratagem_used: [...state.stratagem_used],
      needs_ai: this.setupComplete && this.mode === "heuristic" &&
        state.phase !== "complete" && !this.humanPlayers.has(state.active_player),
      last_action: this.lastActionView(viewer),
      front_strengths: frontStrengths,
      front_control: frontControl,
      hand,
      legal_actions: legalActions,
      log: this.log.slice(-40),
    };
  }

  lastActionView(viewer) {
    if (!this.lastAction) return null;
    const hiddenPlay = this.lastAction.kind === "PlayScheme" || this.lastAction.kind === "SetStratagem";
    const maySeeIdentity = !hiddenPlay || viewer === this.lastAction.actor;
    return {
      id: this.lastAction.id,
      actor: this.lastAction.actor,
      kind: this.lastAction.kind,
      card_id: maySeeIdentity ? this.lastAction.card_id : null,
      label: maySeeIdentity ? this.lastAction.private_label : this.lastAction.public_label,
      events: this.lastAction.events.map((event) => ({ ...event })),
      position: this.lastAction.position ? positionPayload(this.lastAction.position) : null,
      front: this.lastAction.front,
      targets: this.lastAction.targets.map((target) => ({
        player: target.player,
        ...positionPayload(target),
      })),
      move_to: this.lastAction.move_to ? positionPayload(this.lastAction.move_to) : null,
      choose_player: this.lastAction.choose_player,
    };
  }

  actionView(action) {
    return {
      key: action.key,
      kind: action.kind,
      card_id: action.card_id,
      label: this.describeAction(action, this.state.active_player, true),
      reason: this.legalReason(action),
      position: action.position ? positionPayload(action.position) : null,
      front: action.front,
      targets: (action.targets || []).map((target) => ({
        player: target.player,
        ...positionPayload(target),
      })),
      move_to: action.move_to ? positionPayload(action.move_to) : null,
      choose_player: action.choose_player,
      command_cost: this.engine.commandCostForAction(this.state, action),
    };
  }

  describeAction(action, actor, privateText) {
    const prefix = "Player " + (actor + 1);
    if (action.kind === "Pass") return prefix + " Passes.";
    if (action.kind === "Draw") return prefix + " draws 1 card.";
    if (action.kind === "Cycle") return prefix + " Cycles " + this.cards[action.card_id].title + ".";
    if (action.kind === "ChooseFirst") return prefix + " chooses Player " + (action.choose_player + 1) + " to start the next Battle.";
    if (action.kind === "PlaySubject") {
      return prefix + " plays " + this.cards[action.card_id].title + " to " +
        FRONT_NAMES[action.position.front] + " " + RANK_NAMES[action.position.rank] + ".";
    }
    if (action.kind === "PlayLink") {
      return prefix + " plays the Bond " + this.cards[action.card_id].title + " in " +
        FRONT_NAMES[action.position.front] + " " + RANK_NAMES[action.position.rank] + ".";
    }
    if (action.kind === "PlayName") {
      let move = "";
      if (action.move_to) {
        move = " and moves that Subject and its attachments to " +
          FRONT_NAMES[action.move_to.front] + " " + RANK_NAMES[action.move_to.rank];
      }
      return prefix + " plays " + this.cards[action.card_id].title + " as the Name in " +
        FRONT_NAMES[action.position.front] + " " + RANK_NAMES[action.position.rank] + move + ".";
    }
    if (action.kind === "PlayScheme") {
      return privateText
        ? "Set " + this.cards[action.card_id].title + " face-down in " + FRONT_NAMES[action.front] + "."
        : prefix + " sets a face-down Story in " + FRONT_NAMES[action.front] + ".";
    }
    if (action.kind === "SetStratagem") {
      return privateText
        ? "Set " + this.cards[action.card_id].title + " face-down as your Stratagem."
        : prefix + " sets a face-down Stratagem.";
    }
    if (action.kind === "PlayPlot") {
      const title = this.cards[action.card_id].title;
      if (!action.targets?.length) return prefix + " plays " + title + ".";
      const targets = action.targets.map((target) =>
        "Player " + (target.player + 1) + " " + FRONT_NAMES[target.front] + " " + RANK_NAMES[target.rank]
      ).join(", ");
      return prefix + " plays " + title + " targeting " + targets + ".";
    }
    return action.kind;
  }

  legalReason(action) {
    if (action.kind === "Pass") return "Pass is always legal while you are still active in the Battle.";
    if (action.kind === "Draw") return "Draw is disabled in the canonical Command rules.";
    if (action.kind === "Cycle") return "Pay 1 Command (or 0 after a free-Cycle effect), discard this card, then draw 1.";
    if (action.kind === "ChooseFirst") return "The previous Battle loser chooses who takes the first turn.";
    if (action.kind === "PlaySubject") return "This position has no Subject. Prepared Bond or Name cards may already be here.";
    if (action.kind === "PlayLink") return "This position has no Bond. The Bond may be prepared before its Subject.";
    if (action.kind === "PlayName") return "This position has no Name. The Name may be prepared before its Subject or Bond; Subject-dependent text waits for a Subject.";
    if (action.kind === "PlayScheme") return "You have no Veiled Story in this Front.";
    if (action.kind === "SetStratagem") return "You have not set a Stratagem this Battle. Setting it is your operation for the turn and costs its printed Command.";
    if (action.kind === "PlayPlot") return "The Story has all targets required by its rules text.";
    return "Legal according to the browser rules engine.";
  }

  roman(value) {
    return ({ 1: "I", 2: "II", 3: "III" })[value] || String(value);
  }
}

export { actionKey, openingMulliganIndices };
