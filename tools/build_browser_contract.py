from __future__ import annotations

import argparse
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
        "draw_used": list(state.draw_used),
        "discarded_this_battle": list(state.discarded_this_battle),
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
        ],
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
