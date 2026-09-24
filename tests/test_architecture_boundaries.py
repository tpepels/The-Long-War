from __future__ import annotations

import inspect
import re
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

    paid_free = GameRules.force_experiment("paid-free")
    discard9 = GameRules.force_experiment("auto-discard9")
    discard7 = GameRules.force_experiment("auto-discard7")
    cap10 = GameRules.force_experiment("auto-cap10")

    assert paid_free.paid_draw_enabled
    assert not paid_free.paid_draw_consumes_operation
    assert discard9.automatic_draw and discard9.battle_end_hand_limit == 9
    assert discard7.automatic_draw and discard7.battle_end_hand_limit == 7
    assert cap10.automatic_draw and cap10.automatic_draw_hand_limit == 10


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


def test_cardflow_runner_selects_profile_not_individual_rules() -> None:
    source = (
        ROOT / "tools" / "cardflow_experiment.py"
    ).read_text(encoding="utf-8")
    assert "--rules-profile" in source
    for profile in (
        "force-paid-free",
        "force-auto-discard9",
        "force-auto-discard7",
        "force-auto-cap10",
    ):
        assert profile in source
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


def test_cython_engine_contains_no_heuristic_policy() -> None:
    engine_source = (
        ROOT / "src" / "longwar" / "_fast_search.pyx"
    ).read_text(encoding="utf-8")
    heuristic_source = (
        ROOT / "src" / "longwar" / "_heuristic_core.pxi"
    ).read_text(encoding="utf-8")

    assert 'include "_heuristic_core.pxi"' in engine_source
    assert 'include "_alpha_beta_core.pxi"' in engine_source
    assert 'include "_ismcts_core.pxi"' in engine_source
    assert 'include "_mccfr_core.pxi"' in engine_source

    for method in (
        "cdef double evaluate_fast(",
        "cdef double strategic_evaluate_fast(",
        "cdef double action_order_score_fast(",
        "cdef double rollout_prior_fast(",
        "cdef double pass_score_fast(",
    ):
        assert method not in engine_source
        assert method in heuristic_source


def test_native_algorithms_do_not_contain_rule_switches() -> None:
    forbidden = (
        "automatic_draw",
        "paid_draw_enabled",
        "pass_final_operation",
        "completion_command_refund",
        "public_stratagems",
        "reshuffle_on_empty",
    )
    for filename in (
        "_alpha_beta_core.pxi",
        "_ismcts_core.pxi",
        "_mccfr_core.pxi",
    ):
        source = (
            ROOT / "src" / "longwar" / filename
        ).read_text(encoding="utf-8")
        assert not any(term in source for term in forbidden), filename


def test_native_search_uses_current_heuristic_interface() -> None:
    root = Path(__file__).resolve().parents[1]
    for filename in ("_alpha_beta_core.pxi", "_ismcts_core.pxi"):
        source = (root / "src" / "longwar" / filename).read_text(
            encoding="utf-8"
        )
        assert "score_action_fast" not in source
        assert "action_order_score_fast" in source


def test_ismcts_hot_tree_path_is_native() -> None:
    source = (
        ROOT / "src" / "longwar" / "_ismcts_core.pxi"
    ).read_text(encoding="utf-8")
    assert "cdef ISMCTSTree tree" in source
    assert "int path_nodes[MAX_ISMCTS_DEPTH]" in source
    assert "uint16_t path_indices[MAX_ISMCTS_DEPTH]" in source
    assert "information_hash_fast" in source
    assert "cdef dict tree" not in source
    assert "path_nodes = []" not in source
    assert "path_indices = []" not in source
    assert "information_key_fast" not in source


def test_native_alpha_beta_has_transposition_table() -> None:
    source = (
        ROOT / "src" / "longwar" / "_alpha_beta_core.pxi"
    ).read_text(encoding="utf-8")
    assert "cdef class NativeTranspositionTable" in source
    assert "state_hash_fast" in source
    assert "table.probe" in source
    assert "table.store" in source


def test_ismcts_depends_on_engine_contract_not_rule_schema() -> None:
    """Adding/changing a GameRules field must not require ISMCTS edits."""
    algorithm_source = (
        ROOT / "src" / "longwar" / "_ismcts_core.pxi"
    ).read_text(encoding="utf-8")
    agent_source = (
        ROOT / "src" / "longwar" / "agents" / "ismcts_agent.py"
    ).read_text(encoding="utf-8")

    for field in GameRules.__dataclass_fields__:
        pattern = rf"\b{re.escape(field)}\b"
        assert not re.search(pattern, algorithm_source), field
        assert not re.search(pattern, agent_source), field

    assert "GameRules" not in algorithm_source
    assert "GameRules" not in agent_source

    engine_calls = set(
        re.findall(r"\bengine\.([A-Za-z_]\w*)", algorithm_source)
    )
    assert engine_calls <= {
        "legal_actions_into",
        "apply_fast",
        "information_hash_fast",
    }


def test_information_state_schema_has_one_canonical_encoder() -> None:
    source = (
        ROOT / "src" / "longwar" / "_fast_search.pyx"
    ).read_text(encoding="utf-8")

    assert "cdef int _information_state_encode(" in source

    hash_start = source.index(
        "    cdef InfoHash128 information_hash_fast("
    )
    hash_end = source.index(
        "    cpdef tuple information_hash(",
        hash_start,
    )
    hash_body = source[hash_start:hash_end]
    assert "_information_state_encode(" in hash_body
    assert "state." not in hash_body

    key_start = source.index(
        "    cdef bytes information_key_fast("
    )
    key_end = source.index(
        "    cpdef bytes information_key(",
        key_start,
    )
    key_body = source[key_start:key_end]
    assert "_information_state_encode(" in key_body
    assert "state." not in key_body


def test_serious_ismcts_defaults_are_not_smoke_budgets() -> None:
    """Gameplay entry points should never silently fall back to tiny searches."""
    agent = (
        ROOT / "src" / "longwar" / "agents" / "ismcts_agent.py"
    ).read_text(encoding="utf-8")
    simulation = (
        ROOT / "src" / "longwar" / "simulate.py"
    ).read_text(encoding="utf-8")
    cli = (ROOT / "tools" / "simulate.py").read_text(encoding="utf-8")
    experiments = (
        ROOT / "tools" / "run_experiments.py"
    ).read_text(encoding="utf-8")

    assert "iterations: int = 100_000" in agent
    assert simulation.count("ismcts_iterations: int = 100_000") >= 2
    assert (
        'parser.add_argument("--ismcts-iterations", type=int, default=100_000)'
        in cli
    )
    assert (
        'strength_bench.add_argument("--iterations", type=int, default=100_000)'
        in experiments
    )
    assert 'suite.add_argument("--iterations", type=int, default=100_000)' in experiments
