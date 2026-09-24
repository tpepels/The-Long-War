from __future__ import annotations

import inspect
import re
from pathlib import Path

from longwar.cards import load_card_file
from longwar.game import GameEngine
from longwar.heuristics import StrategicEvaluator
from longwar.rules import GameRules

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "longwar"


def test_game_core_dependencies_point_inward_only() -> None:
    """The rules engine must never depend on its consumers."""
    core_files = [
        SRC / "cards.py",
        SRC / "rules.py",
        SRC / "game" / "actions.py",
        SRC / "game" / "model.py",
        SRC / "game" / "engine.py",
    ]
    forbidden = (
        "longwar.agents",
        "..agents",
        ".agents",
        "longwar.algorithms",
        "..algorithms",
        ".algorithms",
        "longwar.simulate",
        "..simulate",
        ".simulate",
        "longwar.telemetry",
        "..telemetry",
        ".telemetry",
        "longwar.balance",
        "..balance",
        ".balance",
        "longwar.counterfactual",
        "..counterfactual",
        ".counterfactual",
        "longwar.web_api",
        "..web_api",
        ".web_api",
        "mccfr",
        "cardflow",
    )
    for path in core_files:
        source = path.read_text(encoding="utf-8")
        assert not any(term in source for term in forbidden), path


def test_runtime_and_search_do_not_special_case_card_ids() -> None:
    """Cards express capabilities as data; implementations never branch on ids."""
    import json

    card_data = json.loads((ROOT / "cards" / "cards.json").read_text(encoding="utf-8"))
    card_ids = {card["id"] for card in card_data["cards"]}

    implementation_files = [
        SRC / "game" / "engine.py",
        SRC / "_fast_search.pyx",
        SRC / "_heuristic_core.pxi",
        SRC / "_alpha_beta_core.pxi",
        SRC / "_ismcts_core.pxi",
        SRC / "_mccfr_core.pxi",
        SRC / "heuristics.py",
        SRC / "agents" / "heuristic_agent.py",
        SRC / "agents" / "strategic_heuristic_agent.py",
        SRC / "agents" / "ismcts_agent.py",
    ]
    for path in implementation_files:
        source = path.read_text(encoding="utf-8")
        leaked = sorted(card_id for card_id in card_ids if card_id in source)
        assert not leaked, f"{path} special-cases cards: {leaked}"


def test_game_core_does_not_know_shipped_decks() -> None:
    """Reference/archetype decks are content passed to the engine, not rules."""
    core = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            SRC / "rules.py",
            SRC / "cards.py",
            SRC / "game" / "engine.py",
            SRC / "game" / "model.py",
            SRC / "game" / "actions.py",
        )
    )
    for marker in (
        "decks/",
        "reference.json",
        "avaros-line",
        "mara-rear",
        "sera-support",
    ):
        assert marker not in core


def test_browser_adapter_has_no_research_dependencies() -> None:
    source = (SRC / "web_api.py").read_text(encoding="utf-8")
    for forbidden in (
        "mccfr",
        "counterfactual",
        "telemetry",
        "human_flow",
        "playability",
        "cardflow",
        "strategic_heuristic",
        "ismcts",
        "simulate",
    ):
        assert forbidden not in source
    assert "action_key" in source
    assert "from .game.actions import" in source


def test_makefile_is_a_small_lifecycle_surface() -> None:
    """Experiment parameter combinations must not become Make targets."""
    source = (ROOT / "Makefile").read_text(encoding="utf-8")
    targets = set(re.findall(r"^([A-Za-z][A-Za-z0-9_.-]*):", source, re.MULTILINE))
    assert targets == {
        "install",
        "native-build",
        "browser-build",
        "verify",
        "verify-algorithms",
        "test",
        "test-fast",
        "test-integration",
        "simulate",
        "balance",
        "experiments",
        "pages",
        "browser-parity",
    }


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


def test_heuristic_policy_is_separate_from_rule_transitions() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    engine = GameEngine(data)
    evaluator = StrategicEvaluator()

    native = engine._native_heuristic()
    assert type(native).__module__ == "longwar._fast_search"

    source = inspect.getsource(StrategicEvaluator._strategic_state_value)
    assert "_native_heuristic" not in source
    assert "strategic_evaluate" in source


def test_python_facade_contains_no_duplicate_rule_engine() -> None:
    """Rule transitions must exist only in the canonical native engine."""
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


def test_canonical_native_engine_is_required_build_output() -> None:
    source = (ROOT / "setup.py").read_text(encoding="utf-8")
    marker = '"longwar._fast_search"'
    assert marker in source
    fast_block = source.split(marker, 1)[1].split("),", 1)[0]
    assert "optional=True" not in fast_block


def test_native_engine_section_contains_no_search_implementation() -> None:
    """Bundling is temporary; engine semantics must still point only outward."""
    source = (SRC / "_fast_search.pyx").read_text(encoding="utf-8")
    marker = "# Keep one compiled extension/shared packed state"
    assert marker in source
    engine_body = source.split(marker, 1)[0]

    for search_symbol in (
        "ISMCTSTree",
        "ismcts_search",
        "NativeTranspositionTable",
        "native_search_value",
        "FastCFRNode",
        "packed_external_sampling_traverse",
    ):
        assert search_symbol not in engine_body


def test_alpha_beta_algorithm_contains_no_rule_switches() -> None:
    source = (SRC / "algorithms" / "alpha_beta.py").read_text(encoding="utf-8")
    forbidden = (
        "automatic_draw",
        "paid_draw_enabled",
        "pass_final_operation",
        "completion_command_refund",
        "public_stratagems",
        "reshuffle_on_empty",
    )
    assert not any(term in source for term in forbidden)


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
        source = (SRC / filename).read_text(encoding="utf-8")
        assert not any(term in source for term in forbidden), filename


def test_native_search_uses_current_heuristic_interface() -> None:
    for filename in ("_alpha_beta_core.pxi", "_ismcts_core.pxi"):
        source = (SRC / filename).read_text(encoding="utf-8")
        assert "score_action_fast" not in source
        assert "action_order_score_fast" in source


def test_ismcts_hot_tree_path_is_native() -> None:
    source = (SRC / "_ismcts_core.pxi").read_text(encoding="utf-8")
    assert "cdef class ISMCTSTree" in source
    assert "ISMCTSTree tree=None" in source
    assert "int path_nodes[MAX_ISMCTS_DEPTH]" in source
    assert "uint16_t path_indices[MAX_ISMCTS_DEPTH]" in source
    assert "information_hash_fast" in source
    assert "cdef dict tree" not in source
    assert "path_nodes = []" not in source
    assert "path_indices = []" not in source
    assert "information_key_fast" not in source


def test_native_alpha_beta_has_transposition_table() -> None:
    source = (SRC / "_alpha_beta_core.pxi").read_text(encoding="utf-8")
    assert "cdef class NativeTranspositionTable" in source
    assert "state_hash_fast" in source
    assert "table.probe" in source
    assert "table.store" in source


def test_ismcts_depends_on_engine_contract_not_rule_schema() -> None:
    """Adding/changing a GameRules field must not require ISMCTS edits."""
    algorithm_source = (SRC / "_ismcts_core.pxi").read_text(encoding="utf-8")
    agent_source = (SRC / "agents" / "ismcts_agent.py").read_text(encoding="utf-8")

    for field in GameRules.__dataclass_fields__:
        pattern = rf"\b{re.escape(field)}\b"
        assert not re.search(pattern, algorithm_source), field
        assert not re.search(pattern, agent_source), field

    assert "GameRules" not in algorithm_source
    assert "GameRules" not in agent_source
    assert "battle_boundary_evaluate_fast" in algorithm_source
    assert "cleanup_pending" not in algorithm_source
    assert "PHASE_CHOOSE" not in algorithm_source

    engine_calls = set(re.findall(r"\bengine\.([A-Za-z_]\w*)", algorithm_source))
    assert engine_calls <= {
        "legal_actions_into",
        "apply_fast",
        "information_hash_fast",
    }


def test_information_state_schema_has_one_canonical_encoder() -> None:
    source = (SRC / "_fast_search.pyx").read_text(encoding="utf-8")
    assert "cdef int _information_state_encode(" in source

    hash_start = source.index("    cdef InfoHash128 information_hash_fast(")
    hash_end = source.index("    cpdef tuple information_hash(", hash_start)
    hash_body = source[hash_start:hash_end]
    assert "_information_state_encode(" in hash_body
    assert "state." not in hash_body

    key_start = source.index("    cdef bytes information_key_fast(")
    key_end = source.index("    cpdef bytes information_key(", key_start)
    key_body = source[key_start:key_end]
    assert "_information_state_encode(" in key_body
    assert "state." not in key_body


def test_serious_ismcts_defaults_are_not_smoke_budgets() -> None:
    agent = (SRC / "agents" / "ismcts_agent.py").read_text(encoding="utf-8")
    simulation = (SRC / "simulate.py").read_text(encoding="utf-8")
    cli = (ROOT / "tools" / "simulate.py").read_text(encoding="utf-8")
    experiments = (ROOT / "tools" / "run_experiments.py").read_text(encoding="utf-8")

    assert "iterations: int = 100_000" in agent
    assert simulation.count("ismcts_iterations: int = 100_000") >= 2
    assert 'parser.add_argument("--ismcts-iterations", type=int, default=100_000)' in cli
    assert 'strength_bench.add_argument("--iterations", type=int, default=100_000)' in experiments
    assert 'suite.add_argument("--iterations", type=int, default=100_000)' in experiments
