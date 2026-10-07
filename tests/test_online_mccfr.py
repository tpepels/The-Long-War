from __future__ import annotations

import json
from pathlib import Path

import pytest


from longwar.agents.online_mccfr_agent import OnlineMCCFRAgent
from longwar.cards import load_card_file
from longwar.game import EndTurn, Front, GameEngine, GameState, Position, Rank
from longwar.game.model import PlayerState
from longwar.mccfr import action_key, search_information_set_id
from longwar.online_mccfr import OnlineMCCFRResolver

ROOT = Path(__file__).resolve().parents[1]
pytestmark = [pytest.mark.research, pytest.mark.algorithm]


def setup():
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "mobility-open-bonds.json").read_text(encoding="utf-8")
    )["cards"]
    return GameEngine(data), deck


def test_online_resolver_has_root_coverage_without_true_opponent_deck() -> None:
    engine, deck = setup()
    state = engine.new_game(deck, deck, seed=12, first_player=0)
    resolver = OnlineMCCFRResolver(
        engine,
        seed=44,
        iterations=4,
        max_depth=1,
    )

    result = resolver.solve(state)
    legal_keys = {action_key(action) for action in engine.legal_actions(state)}

    assert result.root_coverage == 1.0
    assert result.root_average_visits > 0
    assert set(result.strategy) == legal_keys
    assert sum(result.strategy.values()) == pytest.approx(1.0)
    assert result.belief_prior == "CardPoolDeckPrior"
    assert result.root_information_set == search_information_set_id(
        engine,
        state,
        state.active_player,
    )


def test_online_mccfr_agent_allows_legal_midbattle_zero_command_play() -> None:
    engine, deck = setup()
    state = engine.new_game(
        deck,
        deck,
        seed=13,
        first_player=0,
        opening_bonus=False,
    )
    state.battle = 3
    state.players[0].command = 1
    state.players[1].command = 5
    player = state.players[0]
    for zone in (player.hand, player.deck):
        if "the-grey-riders" in zone:
            zone.remove("the-grey-riders")
            break
    else:
        raise AssertionError("expected The Grey Riders in player 0 hidden zones")
    if "marched-with" not in player.hand:
        player.deck.remove("marched-with")
        if len(player.hand) >= engine.hand_limit:
            player.deck.append(player.hand.pop())
        player.hand.append("marched-with")
    slot = state.slot(0, Position(Front.FIRST, Rank.FRONT))
    slot.force = "the-grey-riders"

    agent = OnlineMCCFRAgent(
        engine,
        seed=45,
        iterations=1,
        max_depth=1,
        deterministic=True,
    )
    action = agent.choose(engine, state)

    assert action in engine.legal_actions(state)
    child = state.clone()
    engine.apply(child, action)
    assert child.phase.value == "battle"
    assert child.players[1].command == 5
    assert agent.last_decision["command_guard_applied"] is False
    assert agent.last_decision["command_guard_filtered_actions"] == 0


def test_online_resolver_handles_final_closing_turn_with_unknown_deck() -> None:
    engine, deck = setup()

    p0_hidden = list(deck)
    p0_hidden.remove("the-unnamed-host")
    p0_hidden.remove("the-late-banner")
    p0_hidden.remove("the-black-company")
    state = GameState(
        players=[
            PlayerState(
                deck=p0_hidden,
                hand=["the-black-company"],
                passed=True,
                command=engine.starting_command,
            ),
            PlayerState(
                deck=list(deck),
                hand=[],
                command=engine.starting_command,
            ),
        ],
        active_player=0,
        battle=3,
        pass_order=[0],
        closing_turns_remaining=1,
    )
    state.slot(0, Position(Front.FIRST, Rank.FRONT)).force = "the-unnamed-host"
    state.slot(0, Position(Front.SECOND, Rank.FRONT)).force = "the-late-banner"

    legal = engine.legal_actions(state)
    legal_keys = {action_key(action) for action in legal}
    assert "end-turn" in legal_keys
    assert "pass" not in legal_keys
    assert len(legal_keys) > 1

    end_state = state.clone()
    engine.apply(end_state, EndTurn())
    assert end_state.battle == 4
    assert end_state.winner is None

    resolver = OnlineMCCFRResolver(
        engine,
        seed=123,
        iterations=50,
        max_depth=1,
    )
    result = resolver.solve(state)

    assert result.root_coverage == 1.0
    assert set(result.strategy) == legal_keys
    assert sum(result.strategy.values()) == pytest.approx(1.0)

