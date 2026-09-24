from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from longwar.cards import load_card_file
from longwar.fingerprint import current_game_fingerprint
from longwar.game import (
    ChooseFirst,
    Front,
    GameEngine,
    Pass,
    Phase,
    PlayLink,
    PlayName,
    PlayPlot,
    PlayScheme,
    PlaySubject,
    Position,
    Rank,
    SetStratagem,
)
from longwar.game.actions import action_key
from longwar.game.model import GameState, PlayerState, Slot, SchemeState, StratagemState
from longwar.rules import GameRules
from longwar.web_api import PlaySession

ROOT = Path(__file__).resolve().parents[1]


def project_state(state) -> dict[str, object]:
    return {
        "players": [
            {
                "deck": list(player.deck),
                "hand": list(player.hand),
                "discard": list(player.discard),
                "victories": player.victories,
                "passed": player.passed,
                "command": player.command,
                "free_cycle": player.free_cycle,
            }
            for player in state.players
        ],
        "board": [
            [
                [
                    {
                        "subject": slot.subject,
                        "link": slot.link,
                        "name": slot.name,
                        "temporary_strength": slot.temporary_strength,
                    }
                    for slot in front
                ]
                for front in side
            ]
            for side in state.board
        ],
        "schemes": [
            [
                None
                if scheme is None
                else {
                    "card_id": scheme.card_id,
                    "revealed": scheme.revealed,
                }
                for scheme in side
            ]
            for side in state.schemes
        ],
        "stratagems": [
            None
            if stratagem is None
            else {
                "card_id": stratagem.card_id,
                "revealed": stratagem.revealed,
            }
            for stratagem in state.stratagems
        ],
        "stratagem_used": list(state.stratagem_used),
        "hero_used": list(state.hero_used),
        "draw_used": list(state.draw_used),
        "discarded_this_battle": list(state.discarded_this_battle),
        "command_spent_this_battle": list(state.command_spent_this_battle),
        "command_refunded_this_battle": list(state.command_refunded_this_battle),
        "completion_command_refunded_this_battle": list(state.completion_command_refunded_this_battle),
        "battle_start_command": list(state.battle_start_command),
        "battle_start_hand_size": list(state.battle_start_hand_size),
        "cards_drawn_this_battle": list(state.cards_drawn_this_battle),
        "completion_count_this_battle": list(state.completion_count_this_battle),
        "operations_this_battle": list(state.operations_this_battle),
        "deck_reshuffles": list(state.deck_reshuffles),
        "reshuffle_card_totals": list(state.reshuffle_card_totals),
        "reshuffle_hand_card_totals": list(state.reshuffle_hand_card_totals),
        "known_hidden_hand": [[dict(known) for known in side] for side in state.known_hidden_hand],
        "pass_order": list(state.pass_order),
        "battle": state.battle,
        "phase": state.phase.value,
        "active_player": state.active_player,
        "chooser": state.chooser,
        "winner": state.winner,
        "turn_number": state.turn_number,
        "shuffle_seed": state.shuffle_seed,
    }


def front_strengths(engine: GameEngine, state) -> list[list[int]]:
    return [
        [
            engine.front_strength(state, player, front)
            for front in Front
        ]
        for player in range(2)
    ]


def choose_contract_action(engine: GameEngine, state):
    legal = engine.legal_actions(state)
    if state.phase is Phase.CHOOSE_FIRST:
        preferred = (state.battle + state.active_player) % 2
        return next(
            (
                action
                for action in legal
                if isinstance(action, ChooseFirst)
                and action.player == preferred
            ),
            legal[0],
        )

    pass_action = next(
        (action for action in legal if isinstance(action, Pass)),
        None,
    )
    if (
        pass_action is not None
        and state.operations_this_battle[state.active_player] >= 3
    ):
        return pass_action

    priorities = (
        PlaySubject,
        PlayLink,
        PlayName,
        PlayScheme,
        SetStratagem,
        PlayPlot,
    )
    for kind in priorities:
        candidates = [
            action
            for action in legal
            if isinstance(action, kind)
        ]
        if candidates:
            return min(candidates, key=action_key)

    non_pass = [
        action
        for action in legal
        if not isinstance(action, Pass)
    ]
    return min(non_pass or legal, key=action_key)


def trace_scenario(engine: GameEngine, deck: list[str]) -> dict[str, object]:
    state = engine.new_game(
        deck,
        deck,
        seed=1701,
        first_player=0,
    )
    initial = project_state(state)
    steps: list[dict[str, object]] = []

    for _ in range(60):
        if state.phase is Phase.COMPLETE:
            break
        legal = engine.legal_actions(state)
        action = choose_contract_action(engine, state)
        engine.apply(state, action)
        steps.append(
            {
                "legal": sorted(action_key(item) for item in legal),
                "action": action_key(action),
                "after": project_state(state),
                "front_strengths": front_strengths(engine, state),
            }
        )

    return {
        "name": "deterministic-standard-trace",
        "initial": initial,
        "steps": steps,
    }


def prepared_destination_scenario(
    engine: GameEngine,
    deck: list[str],
) -> dict[str, object]:
    state = engine.new_game(
        deck,
        deck,
        seed=2201,
        first_player=0,
        opening_bonus=False,
    )

    for player in range(2):
        state.players[player].hand.clear()
        state.players[player].deck.clear()
        state.players[player].discard.clear()
        state.players[player].passed = False
        for front in range(3):
            for rank in range(2):
                slot = state.board[player][front][rank]
                slot.subject = None
                slot.link = None
                slot.name = None
                slot.temporary_strength = 0
            state.schemes[player][front] = None
        state.stratagems[player] = None

    state.active_player = 0
    state.phase = Phase.BATTLE
    state.chooser = None
    state.winner = None
    state.pass_order.clear()
    state.stratagem_used[:] = [False, False]
    state.draw_used[:] = [False, False]
    state.discarded_this_battle[:] = [0, 0]
    state.operations_this_battle[:] = [0, 0]

    state.players[0].hand[:] = ["they-chose-another"]
    source = state.slot(
        0,
        Position(Front.CENTER, Rank.FRONT),
    )
    source.subject = "the-fifty-men"

    occupied_destination = state.slot(
        0,
        Position(Front.LEFT, Rank.FRONT),
    )
    occupied_destination.link = "followed"

    legal = sorted(action_key(item) for item in engine.legal_actions(state))
    forbidden_prefix = "plot:they-chose-another:0:1:front;0:0:front"
    assert forbidden_prefix not in legal

    return {
        "name": "prepared-component-blocks-move-destination",
        "initial": project_state(state),
        "legal": legal,
        "front_strengths": front_strengths(engine, state),
    }


def command_scenarios(engine: GameEngine, deck: list[str]) -> list[dict[str, object]]:
    """Pin standard Command, completion, automatic-draw and persistence rules."""

    def record(target, current, predicate):
        legal = engine.legal_actions(current)
        action = next(action for action in legal if predicate(action))
        engine.apply(current, action)
        target["steps"].append({
            "legal": sorted(action_key(item) for item in legal),
            "action": action_key(action),
            "after": project_state(current),
            "front_strengths": front_strengths(engine, current),
        })

    completion = engine.new_game(
        deck,
        deck,
        seed=921,
        first_player=0,
        opening_bonus=False,
    )
    completion.players[1].passed = True
    completion.players[0].hand = [
        "namar",
        "followed",
        "the-fifty-men",
    ]
    completion_scenario = {
        "name": "command-completion-refunds",
        "initial": project_state(completion),
        "steps": [],
    }
    position = Position(Front.CENTER, Rank.FRONT)
    for kind in (PlayName, PlayLink, PlaySubject):
        record(
            completion_scenario,
            completion,
            lambda action, kind=kind: (
                isinstance(action, kind)
                and action.position == position
            ),
        )
    expected = (
        20
        - sum(
            engine.cards[card]["command_cost"]
            for card in ("namar", "followed", "the-fifty-men")
        )
        + 2  # standard completion refund + Namar's own refund
    )
    assert completion.players[0].command == expected
    assert completion.completion_command_refunded_this_battle[0] == 1

    automatic = engine.new_game(
        deck,
        deck,
        seed=923,
        first_player=1,
        opening_bonus=False,
    )
    automatic.players[1].hand = ["the-fifty-men"]
    automatic.players[0].deck = []
    automatic.players[0].discard = ["carried"]
    automatic_scenario = {
        "name": "automatic-draw-reshuffle",
        "initial": project_state(automatic),
        "steps": [],
    }
    record(
        automatic_scenario,
        automatic,
        lambda action: (
            isinstance(action, PlaySubject)
            and action.card_id == "the-fifty-men"
        ),
    )
    assert automatic.active_player == 0
    assert "carried" in automatic.players[0].hand
    assert automatic.deck_reshuffles[0] == 1
    assert automatic.players[0].discard == []

    persistent = engine.new_game(
        deck,
        deck,
        seed=922,
        first_player=0,
        opening_bonus=False,
    )
    held = []
    discards = []
    original_decks = []
    for player, command, keep in ((0, 7, 4), (1, 14, 6)):
        ps = persistent.players[player]
        ps.command = command
        ps.discard.extend(ps.hand[keep:])
        del ps.hand[keep:]
        held.append(list(ps.hand))
        discards.append(list(ps.discard))
        original_decks.append(list(ps.deck))
    persistent.operations_this_battle[:] = [1, 1]

    refill = {
        "name": "command-carry-persistent-refill",
        "initial": project_state(persistent),
        "steps": [],
    }
    record(refill, persistent, lambda action: isinstance(action, Pass))
    record(refill, persistent, lambda action: isinstance(action, Pass))

    assert persistent.battle == 2
    assert persistent.phase is Phase.BATTLE
    assert persistent.active_player == 0
    assert persistent.chooser is None
    assert [ps.command for ps in persistent.players] == [17, 20]
    assert persistent.battle_start_hand_size == [10, 10]
    assert [len(ps.hand) for ps in persistent.players] == [11, 10]
    assert persistent.players[0].discard == discards[0]
    assert persistent.players[1].discard == discards[1]
    assert persistent.players[0].deck == original_decks[0][:-7]
    assert persistent.players[1].deck == original_decks[1][:-4]
    assert persistent.deck_reshuffles == [0, 0]
    assert Counter(held[0]) <= Counter(persistent.players[0].hand)
    assert Counter(held[1]) <= Counter(persistent.players[1].hand)

    return [completion_scenario, automatic_scenario, refill]

def check_engine_contract_json(cards_json: str, contract_json: str) -> int:
    """Replay native fixtures in the compiled browser engine, including targets."""
    engine = GameEngine(json.loads(cards_json))
    contract = json.loads(contract_json)
    for scenario in contract["scenarios"]:
        values = dict(scenario["initial"])
        values["players"] = [PlayerState(**player) for player in values["players"]]
        values["board"] = [[[Slot(**slot) for slot in front] for front in side] for side in values["board"]]
        values["schemes"] = [[None if scheme is None else SchemeState(**scheme) for scheme in side] for side in values["schemes"]]
        values["stratagems"] = [None if item is None else StratagemState(**item) for item in values["stratagems"]]
        values["phase"] = Phase(values["phase"])
        state = GameState(**values)
        if "legal" in scenario:
            assert sorted(action_key(action) for action in engine.legal_actions(state)) == scenario["legal"], scenario["name"]
            assert front_strengths(engine, state) == scenario["front_strengths"], scenario["name"]
        for step in scenario.get("steps", []):
            legal = {action_key(action): action for action in engine.legal_actions(state)}
            assert sorted(legal) == step["legal"], scenario["name"]
            engine.apply(state, legal[step["action"]])
            assert project_state(state) == step["after"], scenario["name"]
            assert front_strengths(engine, state) == step["front_strengths"], scenario["name"]
    return len(contract["scenarios"])


def session_trace(cards, deck, mode: str, seed: int) -> dict[str, object]:
    session = PlaySession(json.dumps(cards), json.dumps(deck), mode, seed, paced_ai=True)
    steps = []

    def record(method, args, snapshot):
        steps.append({"method": method, "args": args, "snapshot": snapshot})

    record("snapshot", [None if mode == "hotseat" else 0], session.snapshot(None if mode == "hotseat" else 0))
    record("view", [0], session.snapshot(0))
    record("mulligan", [[0, 1], 0], session.mulligan([0, 1], 0))
    if mode == "hotseat":
        record("view", [1], session.snapshot(1))
        record("mulligan", [[], 1], session.mulligan([], 1))
    for _ in range(150):
        if session.state.phase is Phase.COMPLETE:
            break
        player = session.state.active_player
        if player not in session.human_players:
            record("aiStep", [], session.ai_step())
        else:
            record("view", [player], session.snapshot(player))
            key = action_key(choose_contract_action(session.engine, session.state))
            record("act", [key, player], session.act(key, player))
    assert session.state.phase is Phase.COMPLETE, "Browser session fixture must cover a complete game"
    return {"mode": mode, "seed": seed, "steps": steps}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/browser-engine-contract.json"),
    )
    args = parser.parse_args()

    cards = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "reference.json").read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(cards)

    payload = {
        "game_fingerprint": current_game_fingerprint(),
        "scenarios": [
            trace_scenario(engine, deck),
            prepared_destination_scenario(engine, deck),
            *command_scenarios(engine, deck),
        ],
        "sessions": [session_trace(cards, deck, mode, seed)
                     for mode, seed in (("hotseat", 1701), ("hotseat", 17), ("heuristic", 1701))],
    }

    output = args.output
    if not output.is_absolute():
        output = ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote browser parity contract: {output}")


if __name__ == "__main__":
    main()
