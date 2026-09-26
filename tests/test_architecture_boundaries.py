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
    )
    for path in core_files:
        source = path.read_text(encoding="utf-8")
        assert not any(term in source for term in forbidden), path


def test_runtime_and_search_do_not_special_case_card_ids() -> None:
    """Cards express capabilities as data; implementations never branch on ids.

    Scans every source file under ``src/longwar`` instead of a fixed list, so a
    newly added module cannot silently opt out of this invariant.
    """
    import json

    card_data = json.loads((ROOT / "cards" / "cards.json").read_text(encoding="utf-8"))
    card_ids = {card["id"] for card in card_data["cards"]}
    assert len(card_ids) >= 10, "expected the shipped card set to be non-trivial"

    implementation_files = sorted(
        path
        for pattern in ("*.py", "*.pyx", "*.pxi")
        for path in SRC.rglob(pattern)
    )
    assert len(implementation_files) >= 10, "expected to find game package source files"
    for path in implementation_files:
        source = path.read_text(encoding="utf-8")
        leaked = sorted(card_id for card_id in card_ids if card_id in source)
        assert not leaked, f"{path} special-cases cards: {leaked}"


def test_rules_are_values_not_named_experiment_profiles() -> None:
    for name in (
        "profile_names",
        "from_profile",
        "force_candidate",
        "force_experiment",
    ):
        assert not hasattr(GameRules, name)

    simulator_source = (ROOT / "tools" / "simulate.py").read_text(
        encoding="utf-8"
    )
    assert "--rules-profile" not in simulator_source


def test_deck_format_is_separate_from_match_rules() -> None:
    assert "deck_size" not in GameRules.__dataclass_fields__

    engine_source = (SRC / "game" / "engine.py").read_text(encoding="utf-8")
    assert "PLAYTEST_DECK_SIZE" not in engine_source
    assert "validate_deck_definition" not in engine_source
    assert "..decks" not in engine_source
    assert "exactly 34" not in engine_source

    simulator_source = (ROOT / "tools" / "simulate.py").read_text(
        encoding="utf-8"
    )
    assert "--deck-size" not in simulator_source
    assert "rules.deck_size" not in simulator_source


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


def test_browser_build_packages_only_game_runtime_python(tmp_path) -> None:
    from tools import build_browser_runtime

    expected = {
        "__init__.py",
        "cards.py",
        "rules.py",
        "heuristics.py",
        "web_api.py",
        "game/__init__.py",
        "game/actions.py",
        "game/engine.py",
        "game/model.py",
        "agents/__init__.py",
        "agents/heuristic_agent.py",
    }
    packaged = set(build_browser_runtime.BROWSER_PYTHON_FILES)
    assert packaged == expected

    forbidden = {
        "simulate.py",
        "telemetry.py",
        "human_flow.py",
        "balance.py",
        "health.py",
        "playability.py",
        "counterfactual.py",
        "targeted_counterfactual.py",
        "mccfr.py",
        "online_mccfr.py",
        "parallel_mccfr.py",
        "agents/ismcts_agent.py",
        "agents/mccfr_agent.py",
        "agents/online_mccfr_agent.py",
        "agents/strategic_heuristic_agent.py",
        "algorithms/alpha_beta.py",
    }
    assert not forbidden & packaged

    native = set(build_browser_runtime.BROWSER_NATIVE_FILES)
    assert "_fast_search.pyx" in native
    assert "_mccfr_accel.pyx" not in native

    source = tmp_path / "browser-source"
    build_browser_runtime.prepare_browser_source(source)
    package = source / "src" / "longwar"
    copied_python = {
        path.relative_to(package).as_posix()
        for path in package.rglob("*.py")
    }
    assert copied_python == expected
    assert not forbidden & copied_python
    assert "_mccfr_accel.pyx" not in {
        path.name for path in package.rglob("*.pyx")
    }
    assert "_mccfr_accel" not in (source / "setup.py").read_text(encoding="utf-8")


def test_browser_parity_replay_helper_needs_only_browser_runtime() -> None:
    source = (ROOT / "tools" / "build_browser_contract.py").read_text(
        encoding="utf-8"
    )
    import_surface = source.split("def main() -> None:", 1)[0]

    # Host-only metadata may be used when generating the contract, but replay
    # inside Pyodide must import only modules present in the minimal wheel.
    for forbidden in (
        "longwar.fingerprint",
        "longwar.simulate",
        "longwar.balance",
        "longwar.telemetry",
        "longwar.mccfr",
        "longwar.counterfactual",
    ):
        assert forbidden not in import_surface


def test_browser_modes_are_product_terms_not_solver_names() -> None:
    source = (SRC / "web_api.py").read_text(encoding="utf-8")
    page = (ROOT / "web" / "play.html").read_text(encoding="utf-8")

    assert '{"hotseat", "computer"}' in source
    assert 'value="computer"' in page

    browser_surfaces = (
        ROOT / "web" / "play.html",
        ROOT / "tools" / "build_browser_contract.py",
        ROOT / "tools" / "check_game_layout.py",
        ROOT / "tools" / "check_play_start.py",
        ROOT / "tests" / "test_web_api.py",
    )
    for path in browser_surfaces:
        content = path.read_text(encoding="utf-8")
        assert '"heuristic"' not in content
        assert "'heuristic'" not in content

    for solver_name in (
        'value="heuristic"',
        'value="ismcts"',
        'value="strategic_heuristic"',
        'value="mccfr"',
        'value="online_mccfr"',
    ):
        assert solver_name not in page


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
    remainder = source.split(marker, 1)[1]
    end_marker = "),"
    assert end_marker in remainder, "expected the Extension(...) call to close with '),'"
    fast_block = remainder.split(end_marker, 1)[0]
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
        "pass_final_operation",
        "completion_command_refund",
        "public_stratagems",
    )
    assert not any(term in source for term in forbidden)


def test_native_algorithms_do_not_contain_rule_switches() -> None:
    forbidden = (
        "pass_final_operation",
        "completion_command_refund",
        "public_stratagems",
    )
    for filename in (
        "_alpha_beta_core.pxi",
        "_ismcts_core.pxi",
        "_mccfr_core.pxi",
    ):
        source = (SRC / filename).read_text(encoding="utf-8")
        assert not any(term in source for term in forbidden), filename


def test_dead_rule_switches_are_removed() -> None:
    rules = (SRC / "rules.py").read_text(encoding="utf-8")
    engine = (SRC / "game" / "engine.py").read_text(encoding="utf-8")
    native = (SRC / "_fast_search.pyx").read_text(encoding="utf-8")
    simulate = (ROOT / "tools" / "simulate.py").read_text(encoding="utf-8")
    actions = (SRC / "game" / "actions.py").read_text(encoding="utf-8")

    obsolete = (
        "draw_action_enabled",
        "recycle_between_battles",
        "battle_command_gain",
        "automatic_draw_hand_limit",
        "battle_end_hand_limit",
        "automatic_draw",
        "paid_draw_enabled",
        "paid_draw_command_cost",
        "paid_draw_consumes_operation",
        "command_enabled",
        "reshuffle_on_empty",
    )
    for name in obsolete:
        assert name not in rules
        assert name not in engine
        assert name not in native
        assert name not in simulate

    assert "class Draw" not in actions
    assert '"draw"' not in actions
    assert "--automatic-draw" not in simulate
    assert "--paid-draw" not in simulate
    assert "--no-turn-draw" not in simulate
    assert "--no-command" not in simulate
    assert "--reshuffle-on-empty" not in simulate
    assert "--no-reshuffle-on-empty" not in simulate


def test_no_universal_line_defense_native_state() -> None:
    native = (SRC / "_fast_search.pyx").read_text(encoding="utf-8")
    assert "line_disabled" not in native
    assert "strat_disable_line" not in native


def test_public_stratagems_are_not_a_rule_variant() -> None:
    rules = (SRC / "rules.py").read_text(encoding="utf-8")
    engine = (SRC / "game" / "engine.py").read_text(encoding="utf-8")
    native = (SRC / "_fast_search.pyx").read_text(encoding="utf-8")
    simulate = (ROOT / "tools" / "simulate.py").read_text(encoding="utf-8")

    assert "public_stratagems" not in rules
    assert "public_stratagems" not in engine
    assert "public_stratagems" not in native
    assert "--hidden-stratagems" not in simulate
    assert "--public-stratagems" not in simulate


def test_canonical_game_vocabulary_has_no_obsolete_aliases() -> None:
    actions = (SRC / "game" / "actions.py").read_text(encoding="utf-8")
    model = (SRC / "game" / "model.py").read_text(encoding="utf-8")
    game_init = (SRC / "game" / "__init__.py").read_text(encoding="utf-8")

    for obsolete in (
        "PlaySubject",
        "PlayLink",
        "PlayPlot",
        "PlayScheme",
        "SetStratagem",
        "SchemeState",
        "Front.LEFT",
        "Front.CENTER",
        "Front.RIGHT",
    ):
        assert obsolete not in actions
        assert obsolete not in model
        assert obsolete not in game_init

    assert 'parts[0] == "force"' in actions
    assert 'parts[0] == "bond"' in actions
    assert 'parts[0] == "story"' in actions
    assert '"subject"' not in actions
    assert '"link"' not in actions
    assert '"plot"' not in actions
    assert '"scheme"' not in actions


def test_obsolete_choose_first_state_is_gone() -> None:
    actions = (SRC / "game" / "actions.py").read_text(encoding="utf-8")
    model = (SRC / "game" / "model.py").read_text(encoding="utf-8")
    native = (SRC / "_fast_search.pyx").read_text(encoding="utf-8")
    heuristic = (SRC / "_heuristic_core.pxi").read_text(encoding="utf-8")
    mccfr = (SRC / "_mccfr_core.pxi").read_text(encoding="utf-8")

    assert "ChooseFirst" not in actions
    assert "choose_first" not in actions
    assert "CHOOSE_FIRST" not in model
    for obsolete in (
        "PHASE_CHOOSE",
        "TYPE_CHOOSE",
        "cleanup_next_starter",
        "cleanup_next_chooser",
        "victories",
        "chooser",
    ):
        assert obsolete not in native
    assert "TYPE_CHOOSE" not in heuristic
    assert "choose_first" not in mccfr


def test_native_algorithms_do_not_reference_deleted_draw_action() -> None:
    for filename in ("_heuristic_core.pxi", "_alpha_beta_core.pxi", "_ismcts_core.pxi", "_mccfr_core.pxi"):
        source = (SRC / filename).read_text(encoding="utf-8")
        assert "TYPE_DRAW" not in source, filename


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


def test_serious_ismcts_defaults_are_not_smoke_budgets(monkeypatch) -> None:
    """AGENTS.md: "Serious ISMCTS default: 100,000 iterations."

    Every caller shares one constant (``DEFAULT_ISMCTS_ITERATIONS``) instead of
    re-literaling the number, so this checks resolved runtime defaults through
    that constant rather than pinning each call site's literal source text.
    That way reformatting a number can't break the test, and a caller that
    quietly reverts to its own hardcoded value can't escape it either.
    """
    import ast
    import sys

    from longwar.agents.ismcts_agent import DEFAULT_ISMCTS_ITERATIONS, ISMCTSAgent
    from longwar.simulate import make_agent, simulate_games

    assert DEFAULT_ISMCTS_ITERATIONS == 100_000

    agent_default = inspect.signature(ISMCTSAgent.__init__).parameters["iterations"].default
    assert agent_default == DEFAULT_ISMCTS_ITERATIONS

    for target in (make_agent, simulate_games):
        default = inspect.signature(target).parameters["ismcts_iterations"].default
        assert default == DEFAULT_ISMCTS_ITERATIONS, target.__name__

    # tools/run_experiments.py exposes a side-effect-free parser builder;
    # parse each ISMCTS-related subcommand for real and read back the value.
    from tools import run_experiments

    for command in ("ismcts-match", "strength-bench", "suite"):
        monkeypatch.setattr(sys, "argv", ["run_experiments.py", command])
        args = run_experiments.parse_args()
        assert args.iterations == DEFAULT_ISMCTS_ITERATIONS, command

    # tools/simulate.py builds its argparse parser inline inside main(), which
    # also runs a full simulation, so parse the source with ast instead of
    # executing it; require the default to reference the shared constant by
    # name rather than matching a specific literal spelling.
    cli_source = (ROOT / "tools" / "simulate.py").read_text(encoding="utf-8")
    tree = ast.parse(cli_source)
    matches = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "add_argument"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == "--ismcts-iterations"
    ]
    assert len(matches) == 1, "expected exactly one --ismcts-iterations argument"
    default_kwarg = next(kw.value for kw in matches[0].keywords if kw.arg == "default")
    assert (
        isinstance(default_kwarg, ast.Name) and default_kwarg.id == "DEFAULT_ISMCTS_ITERATIONS"
    ), "tools/simulate.py must default --ismcts-iterations from the shared constant, not a literal"
