from __future__ import annotations

import argparse
import json
from pathlib import Path

from longwar.cards import load_card_file
from longwar.game import (
    Discard,
    GameEngine,
    Maneuver,
    Pass,
    Phase,
    PlayBond,
    PlayForce,
    PlayName,
    PlayStory,
    PlayStratagem,
)
from longwar.game.actions import action_key
from longwar.game.model import (
    GameState,
    PlayerState,
    Slot,
    StoryState,
    StratagemState,
)
from longwar.web_api import PlaySession

ROOT = Path(__file__).resolve().parents[1]


def project_state(state: GameState) -> dict[str, object]:
    return {
        "players": [
            {
                "deck": list(player.deck),
                "hand": list(player.hand),
                "discard": list(player.discard),
                "passed": player.passed,
                "command": player.command,
            }
            for player in state.players
        ],
        "board": [
            [
                [
                    {
                        "force": slot.force,
                        "bond": slot.bond,
                        "name": slot.name,
                        "temporary_strength": slot.temporary_strength,
                    }
                    for slot in front
                ]
                for front in side
            ]
            for side in state.board
        ],
        "stories": [
            [
                {
                    "card_id": story.card_id,
                    "ongoing": story.ongoing,
                    "fronts": [int(front) for front in story.fronts],
                    "target_player": story.target_player,
                    "target_position": (
                        None
                        if story.target_position is None
                        else {
                            "front": int(story.target_position.front),
                            "rank": story.target_position.rank.value,
                        }
                    ),
                }
                for story in side
            ]
            for side in state.stories
        ],
        "stratagems": [
            (
                None
                if stratagem is None
                else {
                    "card_id": stratagem.card_id,
                    "fronts": [int(front) for front in stratagem.fronts],
                    "direction": stratagem.direction,
                    "targets": [
                        {
                            "player": player,
                            "front": int(position.front),
                            "rank": position.rank.value,
                        }
                        for player, position in stratagem.targets
                    ],
                }
            )
            for stratagem in state.stratagems
        ],
        "stratagem_used": list(state.stratagem_used),
        "hero_used": list(state.hero_used),
        "discarded_this_battle": list(state.discarded_this_battle),
        "command_spent_this_battle": list(
            state.command_spent_this_battle
        ),
        "command_refunded_this_battle": list(
            state.command_refunded_this_battle
        ),
        "battle_start_command": list(state.battle_start_command),
        "battle_start_hand_size": list(state.battle_start_hand_size),
        "cards_drawn_this_battle": list(
            state.cards_drawn_this_battle
        ),
        "completion_count_this_battle": list(
            state.completion_count_this_battle
        ),
        "operations_this_battle": list(state.operations_this_battle),
        "deck_reshuffles": list(state.deck_reshuffles),
        "reshuffle_card_totals": list(state.reshuffle_card_totals),
        "reshuffle_hand_card_totals": list(
            state.reshuffle_hand_card_totals
        ),
        "known_hidden_hand": [
            [dict(known) for known in side]
            for side in state.known_hidden_hand
        ],
        "pass_order": list(state.pass_order),
        "pending_draw_discard_for": state.pending_draw_discard_for,
        "battle": state.battle,
        "phase": state.phase.value,
        "active_player": state.active_player,
        "winner": state.winner,
        "turn_number": state.turn_number,
        "shuffle_seed": state.shuffle_seed,
    }


def front_strengths(
    engine: GameEngine,
    state: GameState,
) -> list[list[int]]:
    return [
        list(engine.front_strength_matrix(state)[player])
        for player in range(2)
    ]


def choose_contract_action(engine: GameEngine, state: GameState):
    legal = engine.legal_actions(state)

    discard = next(
        (action for action in legal if isinstance(action, Discard)),
        None,
    )
    if discard is not None:
        return discard

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
        PlayForce,
        PlayBond,
        PlayName,
        PlayStory,
        PlayStratagem,
        Maneuver,
    )
    for kind in priorities:
        candidates = [
            action
            for action in legal
            if isinstance(action, kind)
        ]
        if candidates:
            return min(candidates, key=action_key)

    return min(legal, key=action_key)


def record_step(
    engine: GameEngine,
    state: GameState,
    action,
) -> dict[str, object]:
    legal = engine.legal_actions(state)
    key = action_key(action)
    assert key in {action_key(item) for item in legal}
    engine.apply(state, action)
    return {
        "legal": sorted(action_key(item) for item in legal),
        "action": key,
        "after": project_state(state),
        "front_strengths": front_strengths(engine, state),
    }


def trace_scenario(
    engine: GameEngine,
    deck: list[str],
) -> dict[str, object]:
    state = engine.new_game(
        deck,
        deck,
        seed=1701,
        first_player=0,
    )
    initial = project_state(state)
    steps: list[dict[str, object]] = []

    for _ in range(80):
        if state.phase is Phase.COMPLETE:
            break
        action = choose_contract_action(engine, state)
        steps.append(record_step(engine, state, action))

    return {
        "name": "deterministic-standard-trace",
        "initial": initial,
        "steps": steps,
    }


def consecutive_pass_scenario(
    engine: GameEngine,
    deck: list[str],
) -> dict[str, object]:
    state = engine.new_game(
        deck,
        deck,
        seed=260925,
        first_player=0,
        opening_bonus=False,
    )
    state.operations_this_battle[:] = [1, 1]

    if len(state.players[1].hand) >= engine.hand_limit:
        card = state.players[1].hand.pop()
        state.players[1].deck.append(card)

    scenario = {
        "name": "two-consecutive-passes",
        "initial": project_state(state),
        "steps": [],
    }

    first = next(
        action
        for action in engine.legal_actions(state)
        if isinstance(action, Pass)
    )
    scenario["steps"].append(record_step(engine, state, first))

    assert state.battle == 1
    assert state.active_player == 1
    assert state.pass_order == [0]
    assert state.players[0].passed
    assert not state.players[1].passed

    second = next(
        action
        for action in engine.legal_actions(state)
        if isinstance(action, Pass)
    )
    scenario["steps"].append(record_step(engine, state, second))

    assert state.battle == 2
    assert state.active_player == 0
    assert state.pass_order == []
    return scenario


def narrative_limit_scenario(
    engine: GameEngine,
    deck: list[str],
) -> dict[str, object]:
    state = engine.new_game(
        deck,
        deck,
        seed=260926,
        first_player=0,
        opening_bonus=False,
    )
    state.players[0].hand[:] = ["they-returned-with-names"]
    state.players[0].command = 20

    legal = sorted(
        action_key(action)
        for action in engine.legal_actions(state)
    )
    narrative_actions = [
        key
        for key in legal
        if key.startswith("story:they-returned-with-names:ongoing:")
    ]

    assert engine.ongoing_narrative_limit == 2
    assert narrative_actions == [
        "story:they-returned-with-names:ongoing:0",
        "story:they-returned-with-names:ongoing:1",
    ]

    return {
        "name": "two-ongoing-narrative-slots",
        "initial": project_state(state),
        "legal": legal,
        "front_strengths": front_strengths(engine, state),
    }


def _restore_state(values: dict[str, object]) -> GameState:
    values = dict(values)
    values["players"] = [
        PlayerState(**player)
        for player in values["players"]
    ]
    values["board"] = [
        [
            [Slot(**slot) for slot in front]
            for front in side
        ]
        for side in values["board"]
    ]
    values["stories"] = [
        [StoryState(**story) for story in side]
        for side in values["stories"]
    ]
    values["stratagems"] = [
        None if item is None else StratagemState(**item)
        for item in values["stratagems"]
    ]
    values["phase"] = Phase(values["phase"])
    return GameState(**values)


def check_engine_contract_json(
    cards_json: str,
    contract_json: str,
) -> int:
    """Replay native fixtures in the compiled browser engine."""
    engine = GameEngine(json.loads(cards_json))
    contract = json.loads(contract_json)

    for scenario in contract["scenarios"]:
        state = _restore_state(scenario["initial"])

        if "legal" in scenario:
            assert sorted(
                action_key(action)
                for action in engine.legal_actions(state)
            ) == scenario["legal"], scenario["name"]
            assert front_strengths(
                engine,
                state,
            ) == scenario["front_strengths"], scenario["name"]

        for step in scenario.get("steps", []):
            legal = {
                action_key(action): action
                for action in engine.legal_actions(state)
            }
            assert sorted(legal) == step["legal"], scenario["name"]
            engine.apply(state, legal[step["action"]])
            assert project_state(state) == step["after"], scenario["name"]
            assert front_strengths(
                engine,
                state,
            ) == step["front_strengths"], scenario["name"]

    return len(contract["scenarios"])


def session_trace(
    cards,
    deck,
    mode: str,
    seed: int,
) -> dict[str, object]:
    session = PlaySession(
        json.dumps(cards),
        json.dumps(deck),
        mode,
        seed,
        paced_ai=True,
    )
    steps = []

    def record(method, args, snapshot):
        steps.append(
            {
                "method": method,
                "args": args,
                "snapshot": snapshot,
            }
        )

    initial_viewer = None if mode == "hotseat" else 0
    record(
        "snapshot",
        [initial_viewer],
        session.snapshot(initial_viewer),
    )
    record("view", [0], session.snapshot(0))
    record(
        "mulligan",
        [[0, 1], 0],
        session.mulligan([0, 1], 0),
    )
    if mode == "hotseat":
        record("view", [1], session.snapshot(1))
        record("mulligan", [[], 1], session.mulligan([], 1))

    for _ in range(400):
        if session.state.phase is Phase.COMPLETE:
            break
        player = session.state.active_player
        if player not in session.human_players:
            record("aiStep", [], session.ai_step())
        else:
            record("view", [player], session.snapshot(player))
            key = action_key(
                choose_contract_action(
                    session.engine,
                    session.state,
                )
            )
            record(
                "act",
                [key, player],
                session.act(key, player),
            )

    assert (
        session.state.phase is Phase.COMPLETE
    ), "Browser session fixture must cover a complete game"
    return {
        "mode": mode,
        "seed": seed,
        "steps": steps,
    }


def main() -> None:
    from longwar.fingerprint import current_game_fingerprint

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/browser-engine-contract.json"),
    )
    args = parser.parse_args()

    cards = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "mobility-open-bonds.json").read_text(
            encoding="utf-8"
        )
    )["cards"]
    engine = GameEngine(cards)

    payload = {
        "game_fingerprint": current_game_fingerprint(),
        "scenarios": [
            trace_scenario(engine, deck),
            consecutive_pass_scenario(engine, deck),
            narrative_limit_scenario(engine, deck),
        ],
        "sessions": [
            session_trace(cards, deck, mode, seed)
            for mode, seed in (
                ("hotseat", 1701),
                ("hotseat", 17),
                ("computer", 1701),
            )
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
