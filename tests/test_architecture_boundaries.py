from __future__ import annotations

import inspect
import json
from pathlib import Path

from longwar.cards import load_card_file
from longwar.game import GameEngine
from longwar.heuristics import StrategicEvaluator
from longwar.rules import GameRules

ROOT = Path(__file__).resolve().parents[1]


def test_force_candidate_rules_live_in_named_profiles() -> None:
    automatic = GameRules.force_candidate("automatic")
    paid = GameRules.force_candidate("paid")

    assert automatic.deck_size == paid.deck_size == 34
    assert automatic.command_enabled and paid.command_enabled
    assert automatic.automatic_draw and not automatic.paid_draw_enabled
    assert paid.paid_draw_enabled and not paid.automatic_draw
    assert not automatic.cycle_enabled
    assert not paid.cycle_enabled
    assert automatic.pass_final_operation
    assert paid.pass_final_operation


def test_public_game_engine_is_a_cython_facade() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    engine = GameEngine(data)

    native = engine._native_core()
    assert type(native).__module__ == "longwar._fast_search"

    source = inspect.getsource(GameEngine.legal_actions)
    assert "_native_core" in source
    assert "action_from_key" in source

    apply_source = inspect.getsource(GameEngine.apply)
    assert "_native_action" in apply_source
    assert "native.apply" in apply_source


def test_heuristic_policy_is_separate_and_compiled() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    engine = GameEngine(data)
    evaluator = StrategicEvaluator()

    native = engine._native_heuristic()
    assert type(native).__module__ == "longwar._fast_search"

    source = inspect.getsource(StrategicEvaluator._strategic_state_value)
    assert "_native_heuristic" not in source
    assert "strategic_evaluate" in source


def test_alpha_beta_algorithm_contains_no_rule_switches() -> None:
    source = (
        ROOT / "src" / "longwar" / "algorithms" / "alpha_beta.py"
    ).read_text(encoding="utf-8")
    forbidden = (
        "automatic_draw",
        "paid_draw_enabled",
        "pass_final_operation",
        "completion_command_refund",
        "public_stratagems",
        "reshuffle_on_empty",
    )
    assert not any(term in source for term in forbidden)


def test_force_runner_selects_profile_not_individual_rules() -> None:
    source = (
        ROOT / "tools" / "run_force_draw_experiment.py"
    ).read_text(encoding="utf-8")
    assert "--rules-profile" in source
    for obsolete_flag in (
        "--pass-final-operation",
        "--completion-command-refund",
        "--public-stratagems",
        "--reshuffle-on-empty",
        "--disable-cycle",
    ):
        assert obsolete_flag not in source


def test_python_facade_contains_no_duplicate_rule_engine() -> None:
    """Rule transitions must exist only in the canonical Cython engine."""
    forbidden = (
        "_pass",
        "_score_battle",
        "_resolve_plot",
        "_resolve_triggered_schemes",
        "_resolve_stratagem_event",
        "_discard_subject",
        "_draw_for_battle",
        "_reshuffle_discard_into_deck",
        "_finish_operation",
        "_advance_turn",
    )
    for name in forbidden:
        assert not hasattr(GameEngine, name), name

    source = inspect.getsource(GameEngine)
    assert "During the migration the reference code remains" not in source


def test_canonical_cython_engine_is_required_build_output() -> None:
    source = (ROOT / "setup.py").read_text(encoding="utf-8")
    marker = '"longwar._fast_search"'
    assert marker in source
    fast_block = source.split(marker, 1)[1].split("),", 1)[0]
    assert "optional=True" not in fast_block
