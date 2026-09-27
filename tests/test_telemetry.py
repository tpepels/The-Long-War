from __future__ import annotations

import json

import pytest
from pathlib import Path

from longwar.cards import load_card_file
from longwar.game import GameEngine
from longwar.game.actions import Maneuver, Pass, PlayForce, PlayName
from longwar.game.model import Front, Position, Rank, StoryState
from longwar.progression import ProgressionTelemetry
from longwar.simulate import simulate_games
from longwar.telemetry import Telemetry

ROOT = Path(__file__).resolve().parents[1]


def setup():
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "mobility-open-bonds.json").read_text(encoding="utf-8")
    )["cards"]
    return GameEngine(data), deck


@pytest.mark.integration
def test_telemetry_contains_card_pass_battle_and_combo_metrics() -> None:
    engine, deck = setup()
    report = simulate_games(
        engine,
        deck,
        deck,
        games=20,
        seed=123,
        agent_names=("heuristic", "heuristic"),
    )

    telemetry = report.telemetry
    assert telemetry["battles"]["count"] >= 40
    assert telemetry["passes"]["events"] >= 40
    assert telemetry["cards"]
    assert "heuristic" in telemetry["decisions"]

    fifty = telemetry["cards"]["the-fifty-men"]
    assert fifty["draws"] > 0
    assert 0 <= fifty["play_rate_per_draw"] <= 1
    assert fifty["plays_per_draw"] >= 0
    assert 0 <= fifty["unplayable_turn_rate"] <= 1

    assert telemetry["legend_combinations"]


@pytest.mark.integration
def test_heuristic_beats_random_in_small_fixed_benchmark() -> None:
    engine, deck = setup()
    report = simulate_games(
        engine,
        deck,
        deck,
        games=80,
        seed=404,
        agent_names=("heuristic", "random"),
    )
    assert report.wins[0] > report.wins[1]


def test_telemetry_aggregates_ismcts_rollout_cutoffs() -> None:
    engine, deck = setup()
    state = engine.new_game(deck, deck, seed=505, first_player=0)
    telemetry = Telemetry()
    telemetry.start_game(state, engine)
    action = engine.legal_actions(state)[0]

    telemetry.before_action(
        engine,
        state,
        state.active_player,
        action,
        {
            "agent": "ismcts",
            "candidate_count": 4,
            "search_nodes": 20,
            "completed_depth": 3,
            "decision_seconds": 1.25,
            "search_timed_out": True,
            "ismcts_iterations": 20,
            "ismcts_rollouts_stopped_terminal": 7,
            "ismcts_rollouts_stopped_battle_boundary": 11,
            "ismcts_rollouts_stopped_depth": 2,
            "ismcts_rollout_actions": 53,
            "ismcts_root_reused": True,
            "ismcts_tree_nodes_before": 120,
            "ismcts_tree_nodes_added": 17,
            "ismcts_root_prior_visits": 9,
            "ismcts_tree_nodes_discarded": 70,
            "ismcts_tree_capacity_cutoffs": 4,
            "ismcts_tree_reset_reason": "context_changed",
        },
    )

    cutoffs = telemetry.summary()["decisions"]["ismcts"][
        "ismcts_rollout_cutoffs"
    ]
    assert cutoffs["iterations"] == 20
    assert cutoffs["terminal"] == 7
    assert cutoffs["battle_boundary"] == 11
    assert cutoffs["depth"] == 2
    assert cutoffs["terminal_rate"] == pytest.approx(7 / 20)
    assert cutoffs["battle_boundary_rate"] == pytest.approx(11 / 20)
    assert cutoffs["depth_rate"] == pytest.approx(2 / 20)
    assert cutoffs["rollout_actions"] == 53
    assert cutoffs["mean_rollout_actions_per_iteration"] == pytest.approx(
        53 / 20
    )

    reuse = telemetry.summary()["decisions"]["ismcts"]["ismcts_tree_reuse"]
    assert reuse["searched_decisions"] == 1
    assert reuse["root_reused_decisions"] == 1
    assert reuse["root_reuse_rate"] == pytest.approx(1.0)
    assert reuse["tree_nodes_before_total"] == 120
    assert reuse["tree_nodes_added_total"] == 17
    assert reuse["root_prior_visits_total"] == 9
    assert reuse["tree_nodes_discarded_total"] == 70
    assert reuse["tree_capacity_cutoffs"] == 4
    assert reuse["tree_resets"] == {"context_changed": 1}
    assert reuse["mean_tree_nodes_before"] == pytest.approx(120.0)
    assert reuse["mean_tree_nodes_added"] == pytest.approx(17.0)
    assert reuse["mean_root_prior_visits"] == pytest.approx(9.0)

    decisions = telemetry.summary()["decisions"]["ismcts"]
    assert decisions["mean_decision_seconds"] == pytest.approx(1.25)
    assert decisions["max_decision_seconds"] == pytest.approx(1.25)
    assert decisions["timed_out_decisions"] == 1
    assert decisions["timeout_rate"] == pytest.approx(1.0)
    assert decisions["searched_decisions"] == 1
    assert decisions["mean_searched_decision_seconds"] == pytest.approx(1.25)



def _position(front: Front = Front.FIRST, rank: Rank = Rank.FRONT) -> Position:
    return Position(front=front, rank=rank)


def test_formation_lifecycle_tracks_force_bond_name_without_resetting_identity() -> None:
    engine, _deck = setup()
    state = engine.new_game(_deck, _deck, seed=601, first_player=0)
    position = _position()
    state.slot(0, position).force = "the-fifty-men"

    progression = ProgressionTelemetry()
    progression.start_game(engine, state)
    formation_id = progression._formation_at[(0, position)]

    before = state.clone()
    state.slot(0, position).bond = "had-been-ordered-forward"
    progression._current_action = 3
    progression._reconcile_formations(
        engine, before, state, 0, Pass(), battle_resolved=False
    )

    before = state.clone()
    state.slot(0, position).name = "arel"
    progression._current_action = 7
    completions = progression._reconcile_formations(
        engine, before, state, 0, Pass(), battle_resolved=False
    )

    row = progression._formations[formation_id]
    assert progression._formation_at[(0, position)] == formation_id
    assert row["created_action"] == 0
    assert row["bond_action"] == 3
    assert row["name_action"] == 7
    assert row["completion_action"] == 7
    assert completions == 1

    lifecycle = progression.summary()["formation_lifecycle"]
    assert lifecycle["forces"] == 1
    assert lifecycle["forces_ever_bonded"] == 1
    assert lifecycle["forces_ever_named"] == 1
    assert lifecycle["force_to_bond_actions"]["median"] == 3
    assert lifecycle["bond_to_name_actions"]["median"] == 4
    assert lifecycle["force_to_name_actions"]["median"] == 7


def test_maneuver_preserves_formation_identity_and_age() -> None:
    engine, deck = setup()
    state = engine.new_game(deck, deck, seed=602, first_player=0)
    source = _position(Front.FIRST)
    destination = _position(Front.SECOND)
    state.slot(0, source).force = "the-fifty-men"
    state.slot(0, source).bond = "had-been-ordered-forward"

    progression = ProgressionTelemetry()
    progression.start_game(engine, state)
    formation_id = progression._formation_at[(0, source)]

    before = state.clone()
    moving = state.slot(0, source)
    target = state.slot(0, destination)
    target.force, target.bond, target.name = moving.force, moving.bond, moving.name
    moving.force = moving.bond = moving.name = None
    progression._current_action = 5
    progression._reconcile_formations(
        engine,
        before,
        state,
        0,
        Maneuver(source=source, destination=destination),
        battle_resolved=False,
    )

    assert (0, source) not in progression._formation_at
    assert progression._formation_at[(0, destination)] == formation_id
    assert progression._formations[formation_id]["created_action"] == 0
    assert progression._formations[formation_id]["removed_action"] is None


def test_incomplete_formation_removal_is_recorded_once() -> None:
    engine, deck = setup()
    state = engine.new_game(deck, deck, seed=603, first_player=0)
    position = _position()
    state.slot(0, position).force = "the-fifty-men"
    progression = ProgressionTelemetry()
    progression.start_game(engine, state)
    formation_id = progression._formation_at[(0, position)]

    before = state.clone()
    state.slot(0, position).force = None
    progression._current_action = 4
    progression._reconcile_formations(
        engine, before, state, 0, Pass(), battle_resolved=False
    )

    row = progression._formations[formation_id]
    assert row["removed_action"] == 4
    assert row["removed_reason"] == "effect_or_retreat"
    assert progression.summary()["formation_lifecycle"][
        "incomplete_removed_before_completion"
    ] == 1


def test_battlefield_snapshot_counts_occupied_active_and_contested_fronts() -> None:
    engine, deck = setup()
    state = engine.new_game(deck, deck, seed=604, first_player=0)
    state.slot(0, _position(Front.FIRST)).force = "the-fifty-men"
    state.slot(0, _position(Front.SECOND)).force = "the-vardai"
    state.slot(1, _position(Front.FIRST)).force = "the-vardai"

    progression = ProgressionTelemetry()
    progression.start_game(engine, state)
    snapshot = progression._snapshot(
        engine,
        state,
        actor=0,
        legal_count=6,
        constraint_active=False,
        constraint_sources=[],
    )

    assert snapshot["occupied"] == [2, 1]
    assert snapshot["active_fronts"] == 2
    assert snapshot["contested_fronts"] == 1
    assert snapshot["uncontested_fronts"] == 1
    assert snapshot["empty_fronts"] == 2
    assert snapshot["legal_actions"] == 6
    json.dumps(snapshot)


def test_mechanical_choice_and_pass_context_use_actual_legal_set() -> None:
    engine, deck = setup()
    state = engine.new_game(deck, deck, seed=605, first_player=0)
    progression = ProgressionTelemetry()
    progression.start_game(engine, state)

    pass_action = Pass()
    progression.before_action(engine, state, 0, pass_action, [pass_action])
    choice = progression.summary()["mechanical_choice"]

    assert choice["exactly_one_legal_action"] == 1
    assert choice["exactly_one_legal_action_rate"] == pytest.approx(1.0)
    assert choice["pass_mechanical_categories"] == {"no_alternative": 1}


def test_constraint_rule_source_is_not_misreported_as_active_constraint() -> None:
    engine, deck = setup()
    state = engine.new_game(deck, deck, seed=606, first_player=0)
    state.stories[0].append(
        StoryState(card_id="the-king-had-given-the-order", ongoing=True)
    )
    progression = ProgressionTelemetry()
    progression.start_game(engine, state)
    pass_action = Pass()
    progression.before_action(engine, state, 0, pass_action, [pass_action])

    choice = progression.summary()["mechanical_choice"]
    assert choice["constraint_rule_source_decisions"] == 1
    assert choice["constraint_active_decisions"] == 0
    assert progression._sample_traces[0]["constraint_rule_sources"] == [
        "the-king-had-given-the-order"
    ]
    assert progression._sample_traces[0]["constraint_active"] is False


def test_hero_modes_are_counted_separately() -> None:
    engine, deck = setup()
    progression = ProgressionTelemetry()

    state = engine.new_game(deck, deck, seed=607, first_player=0)
    progression.start_game(engine, state)
    position = _position()
    before = state.clone()
    state.slot(0, position).force = "avaros-the-bronze-king"
    progression._record_hero_action(
        engine,
        before,
        state,
        0,
        PlayForce("avaros-the-bronze-king", position),
    )

    before = state.clone()
    state.slot(0, position).bond = "had-been-ordered-forward"
    state.slot(0, position).name = "kael-the-roadless"
    progression._record_hero_action(
        engine,
        before,
        state,
        0,
        PlayName("kael-the-roadless", position),
    )

    heroes = progression.summary()["hero_modes"]
    assert heroes["avaros-the-bronze-king"]["force_plays"] == 1
    assert heroes["avaros-the-bronze-king"]["name_plays"] == 0
    assert heroes["kael-the-roadless"]["force_plays"] == 0
    assert heroes["kael-the-roadless"]["name_plays"] == 1


def test_battle_index_aggregation_keeps_first_three_battles_separate() -> None:
    progression = ProgressionTelemetry()
    base = {
        "game": 0,
        "actions": 4,
        "forces_played": 2,
        "bonds_played": 1,
        "names_played": 1,
        "completed_formations": 1,
        "incomplete_at_end": [1, 1],
        "complete_at_end": [1, 0],
        "mean_total_occupied": 3.0,
        "mean_active_fronts": 2.0,
        "mean_contested_fronts": 1.0,
        "mean_complete_formations": 1.0,
        "mean_partial_formations": 2.0,
        "mean_strength_concentration": [0.6, 0.7],
        "front_control_changes": 2,
        "control_balance_changes": 1,
        "lead_changes": 1,
        "maximum_abs_margin": 4,
        "midpoint_abs_margin": 2,
        "final_abs_margin": 3,
        "durable_lead_action": 3,
        "actions_remaining_after_durable_lead": 1,
        "no_control_change_after_midpoint": False,
        "command_start": [20, 20],
        "command_spent": [10, 9],
        "command_refunded": [1, 0],
        "command_remaining": [4, 5],
        "next_battle_command": [9, 10],
        "hand_remaining": [5, 6],
        "deck_remaining": [10, 11],
        "mean_legal_actions": 7.0,
        "constraint_source_decisions": 0,
        "constraint_active_decisions": 0,
        "cards_played": 5,
        "free_maneuvers": 1,
        "command_gained": 1,
    }
    for battle in (1, 2, 3, 4, 5):
        progression._battle_records.append({**base, "battle": battle})

    by_battle = progression.summary()["by_battle"]
    assert by_battle["1"]["battles"] == 1
    assert by_battle["2"]["battles"] == 1
    assert by_battle["3"]["battles"] == 1
    assert by_battle["4+"]["battles"] == 2
    assert by_battle["1"]["eventual_completion_rate_for_forces_deployed"] is None



def test_front_control_changes_are_detected_between_decision_states() -> None:
    engine, deck = setup()
    state = engine.new_game(deck, deck, seed=608, first_player=0)
    position = _position(Front.FIRST)
    state.slot(0, position).force = "the-fifty-men"

    progression = ProgressionTelemetry()
    progression.start_game(engine, state)
    pass_action = Pass()
    progression.before_action(engine, state, 0, pass_action, [pass_action])

    state.slot(0, position).force = None
    state.slot(1, position).force = "the-vardai"
    progression.before_action(engine, state, 1, pass_action, [pass_action])

    assert progression._battle_control_changes >= 1
    assert progression._battle_lead_changes >= 1


def test_command_flow_uses_actual_cost_and_excludes_between_battle_recovery() -> None:
    engine, deck = setup()
    state = engine.new_game(deck, deck, seed=609, first_player=0)
    progression = ProgressionTelemetry()
    progression.start_game(engine, state)

    action = next(
        candidate
        for candidate in engine.legal_actions(state)
        if isinstance(candidate, PlayForce)
    )
    before = state.clone()
    actual_cost = engine.command_cost_for_action(before, action)
    engine.apply(state, action)
    progression._record_command_flow(engine, before, state, 0, action)

    resources = progression.summary()["resources"]
    assert resources["command_spend"]["card_play"] == actual_cost
    if actual_cost == 0:
        assert resources["free_operations"] == 1


def test_partial_formation_counter_is_force_anchored() -> None:
    engine, deck = setup()
    state = engine.new_game(deck, deck, seed=610, first_player=0)
    state.slot(0, _position(Front.FIRST)).force = "the-fifty-men"
    state.slot(0, _position(Front.SECOND)).bond = "had-been-ordered-forward"

    progression = ProgressionTelemetry()
    assert progression._count_partial(state, 0) == 1
    assert progression._count_complete(state, 0) == 0



def test_forced_maneuver_is_separate_from_zero_cost_maneuver() -> None:
    engine, deck = setup()
    state = engine.new_game(deck, deck, seed=611, first_player=0)
    progression = ProgressionTelemetry()
    progression.start_game(engine, state)
    maneuver = Maneuver(
        source=_position(Front.FIRST),
        destination=_position(Front.SECOND),
    )
    progression.before_action(engine, state, 0, maneuver, [maneuver])
    choice = progression.summary()["mechanical_choice"]
    assert choice["forced_maneuvers"] == 1
    assert choice["forced_maneuver_rate"] == pytest.approx(1.0)
