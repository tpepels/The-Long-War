from __future__ import annotations

import inspect
import re
from pathlib import Path

import pytest

from longwar.cards import CARD_CAPABILITY_BITS, load_card_file
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


def test_native_engine_consumes_compiled_card_mechanics() -> None:
    """Raw design JSON stops at cards.py; native runtime sees compiled mechanics."""
    engine_source = (SRC / "game" / "engine.py").read_text(encoding="utf-8")
    native_cards = (SRC / "_fast_engine_cards.pxi").read_text(encoding="utf-8")
    native_class = (SRC / "_fast_engine_class.pxi").read_text(encoding="utf-8")

    assert "compile_card_mechanics" in engine_source
    assert "self.card_mechanics" in engine_source
    assert "engine.card_mechanics[card_id]" in native_cards
    assert 'card.get("design_rules")' not in native_cards
    assert "_capability_bits" in native_cards
    assert "cdef uint64_t card_capabilities[MAX_CARDS]" in native_class

    # Registered boolean capabilities share the bitset instead of growing one
    # MAX_CARDS array per mechanic.
    for capability in CARD_CAPABILITY_BITS:
        assert f"cdef uint8_t {capability}[MAX_CARDS]" not in native_class


def test_native_card_loader_uses_typed_protocol_vocabulary() -> None:
    """Native card compilation must consume shared vocabulary, not re-spell it."""
    from longwar.game.model import Rank
    from longwar.protocol import CardField, DesignField, DesignToken, ForceRole

    source = (SRC / "_fast_engine_cards.pxi").read_text(encoding="utf-8")
    typed_values = {
        item.value
        for enum_type in (CardField, DesignField, DesignToken, ForceRole, Rank)
        for item in enum_type
    }
    leaked = sorted(
        value
        for value in typed_values
        if re.search(
            rf"""(?P<quote>['"]){re.escape(str(value))}(?P=quote)""",
            source,
        )
    )
    assert not leaked, f"native card loader duplicates typed values: {leaked}"


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
        leaked = sorted(
            card_id
            for card_id in card_ids
            if re.search(rf"""(?P<quote>['"]){re.escape(card_id)}(?P=quote)""", source)
        )
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
    assert "exactly 34" not in engine_source
    # The engine may delegate validation to the deck-format module, but must not
    # duplicate deck-construction rules as match rules.
    assert "validate_deck_definition(deck, self.cards)" in engine_source

    simulator_source = (ROOT / "tools" / "simulate.py").read_text(
        encoding="utf-8"
    )
    assert "--deck-size" not in simulator_source
    assert "rules.deck_size" not in simulator_source


def test_game_core_does_not_know_shipped_decks() -> None:
    """Reference/archetype decks are content passed to the engine, not rules."""
    from longwar.reference_decks import DECK_CATALOG

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
    assert "decks/" not in core
    for entry in DECK_CATALOG:
        assert entry["file"] not in core


def test_browser_build_packages_only_game_runtime_python(tmp_path) -> None:
    from tools import build_browser_runtime

    packaged = set(build_browser_runtime.BROWSER_PYTHON_FILES)
    assert set(build_browser_runtime.BROWSER_PYTHON_ENTRYPOINTS) <= packaged

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
        "native_search.py",
        "agents/ismcts_agent.py",
        "agents/mccfr_agent.py",
        "agents/online_mccfr_agent.py",
        "agents/strategic_heuristic_agent.py",
        "algorithms/alpha_beta.py",
    }
    assert not forbidden & packaged

    native = set(build_browser_runtime.BROWSER_NATIVE_FILES)
    assert set(build_browser_runtime.BROWSER_NATIVE_ROOTS) <= native
    assert "_fast_engine_core.pxi" in native
    assert "_heuristic_core.pxi" in native
    assert "_heuristic_weights.generated.pxi" in native
    assert "_alpha_beta_core.pxi" not in native
    assert "_ismcts_core.pxi" not in native
    assert "_mccfr_core.pxi" not in native
    assert "_mccfr_accel.pyx" not in native

    source = tmp_path / "browser-source"
    build_browser_runtime.prepare_browser_source(source)
    package = source / "src" / "longwar"
    copied_python = {
        path.relative_to(package).as_posix()
        for path in package.rglob("*.py")
    }
    copied_native = {
        path.relative_to(package).as_posix()
        for path in package.rglob("*.pxi")
    }
    assert copied_python == packaged
    assert copied_native == native
    assert not forbidden & copied_python
    assert "_mccfr_accel.pyx" not in {
        path.name for path in package.rglob("*.pyx")
    }
    assert "_mccfr_accel" not in (source / "setup.py").read_text(encoding="utf-8")
    browser_fast = (package / "_fast_search.pyx").read_text(encoding="utf-8")
    assert 'include "_fast_engine_core.pxi"' in browser_fast
    assert 'include "_heuristic_core.pxi"' in browser_fast
    assert 'include "_ismcts_core.pxi"' not in browser_fast


def test_browser_runtime_dependency_closures_are_complete() -> None:
    from tools import build_browser_runtime

    packaged = set(build_browser_runtime.BROWSER_PYTHON_FILES)
    for relative in packaged:
        assert build_browser_runtime._browser_python_imports(relative) <= packaged

    native = set(build_browser_runtime.BROWSER_NATIVE_FILES)
    assert set(
        build_browser_runtime.cython_include_closure(
            *build_browser_runtime.BROWSER_NATIVE_ROOTS
        )
    ) == native

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
    from longwar.protocol import GameMode

    page = (ROOT / "web" / "play.html").read_text(encoding="utf-8")

    assert {mode.value for mode in GameMode} == {"hotseat", "remote", "computer"}
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
        "web-protocol",
        "verify",
        "verify-algorithms",
        "test",
        "test-fast",
        "test-integration",
        "simulate",
        "balance",
        "experiments",
        "full-lab",
        "pages",
        "browser-parity",
    }


def test_native_compile_time_protocol_is_generated() -> None:
    """Native topology/capacity constants derive from canonical Python values."""
    from tools import build_native_protocol

    generated = SRC / "_fast_protocol.generated.pxi"
    assert generated.read_text(encoding="utf-8") == build_native_protocol.render()

    constants = (SRC / "_fast_constants.pxi").read_text(encoding="utf-8")
    assert 'include "_fast_protocol.generated.pxi"' in constants
    for name in (
        "PLAYER_COUNT",
        "FRONT_COUNT",
        "RANK_COUNT",
        "DIRECTION_COUNT",
        "NARRATIVE_SLOTS_PER_PLAYER",
        "RANK_FRONT",
        "RANK_REAR",
        "DIRECTION_NONE",
        "DIRECTION_LEFT",
        "DIRECTION_RIGHT",
    ):
        assert f"DEF {name} =" not in constants
        assert f"cdef int {name} =" not in constants


def test_heuristic_weight_protocol_is_generated_and_fully_consumed() -> None:
    from longwar.heuristics import HEURISTIC_KEYS
    from tools import build_heuristic_weights

    generated = SRC / "_heuristic_weights.generated.pxi"
    assert generated.read_text(encoding="utf-8") == build_heuristic_weights.render()
    source = (SRC / "_heuristic_core.pxi").read_text(encoding="utf-8")
    for key in HEURISTIC_KEYS:
        assert f"self.weights[HW_{key.upper()}]" in source, key
    assert "DEF HEUR_" not in source


def test_native_heuristic_has_preindexed_card_categories() -> None:
    native_class = (SRC / "_fast_engine_class.pxi").read_text(encoding="utf-8")
    native_cards = (SRC / "_fast_engine_cards.pxi").read_text(encoding="utf-8")
    for category in (
        "force", "bond", "name", "narrative", "stratagem", "hero", "name_mode"
    ):
        assert f"{category}_codes[MAX_CARDS]" in native_class
        assert f"{category}_count" in native_class
    assert "self.name_mode_codes[self.name_mode_count]" in native_cards


def test_game_engine_delegates_rule_fields_without_mirroring() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    rules = GameRules.standard()
    engine = GameEngine(data, rules=rules)

    for field in GameRules.__dataclass_fields__:
        assert getattr(engine, field) == getattr(rules, field)

    source = (SRC / "game" / "engine.py").read_text(encoding="utf-8")
    for field in GameRules.__dataclass_fields__:
        assert f"self.{field} = rules.{field}" not in source


def test_public_game_engine_uses_native_engine_facade() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    engine = GameEngine(data)

    native = engine._native_core()
    assert type(native).__name__ == "FastEngine"

    engine_source = (SRC / "game" / "engine.py").read_text(encoding="utf-8")
    assert "from ..native_engine import" in engine_source
    assert "_fast_search" not in engine_source

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
    assert type(native).__name__ == "NativeHeuristicEvaluator"

    source = inspect.getsource(StrategicEvaluator._strategic_state_value)
    assert "_native_heuristic" not in source
    assert "strategic_evaluate" in source


def test_compiled_native_module_is_hidden_behind_facades() -> None:
    allowed = {
        SRC / "native_engine.py",
        SRC / "native_search.py",
    }
    for path in SRC.rglob("*.py"):
        if path in allowed:
            continue
        assert "_fast_search" not in path.read_text(encoding="utf-8"), path

    engine_facade = (SRC / "native_engine.py").read_text(encoding="utf-8")
    search_facade = (SRC / "native_search.py").read_text(encoding="utf-8")
    assert "_fast_search" in engine_facade
    assert "_fast_search" in search_facade


def test_native_engine_composition_contains_no_search_implementation() -> None:
    engine_core = (SRC / "_fast_engine_core.pxi").read_text(encoding="utf-8")
    host = (SRC / "_fast_search.pyx").read_text(encoding="utf-8")

    assert 'include "_fast_engine_core.pxi"' in host
    for search_include in (
        "_alpha_beta_core.pxi",
        "_ismcts_core.pxi",
        "_mccfr_core.pxi",
    ):
        assert search_include not in engine_core
        assert f'include "{search_include}"' in host


def test_search_algorithms_depend_on_engine_contract_not_rule_fields() -> None:
    """Changing a GameRules field must not require search-algorithm edits."""
    sources = {
        "python alpha-beta": (
            SRC / "algorithms" / "alpha_beta.py"
        ).read_text(encoding="utf-8"),
        "native alpha-beta": (
            SRC / "_alpha_beta_core.pxi"
        ).read_text(encoding="utf-8"),
        "native ISMCTS": (
            SRC / "_ismcts_core.pxi"
        ).read_text(encoding="utf-8"),
        "native MCCFR": (
            SRC / "_mccfr_core.pxi"
        ).read_text(encoding="utf-8"),
    }
    for label, source in sources.items():
        assert "GameRules" not in source, label
        for field in GameRules.__dataclass_fields__:
            assert not re.search(rf"\b{re.escape(field)}\b", source), (
                label,
                field,
            )


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


def test_ismcts_uses_only_the_narrow_native_engine_contract() -> None:
    algorithm_source = (SRC / "_ismcts_core.pxi").read_text(encoding="utf-8")
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
    source = (SRC / "_fast_engine_hashing.pxi").read_text(encoding="utf-8")
    assert "cdef int _fe__information_state_encode(" in source

    hash_start = source.index("cdef InfoHash128 _fe_information_hash_fast(")
    hash_end = source.index("cdef tuple _fe_information_hash(", hash_start)
    hash_body = source[hash_start:hash_end]
    assert "_fe__information_state_encode(" in hash_body
    assert "state." not in hash_body

    key_start = source.index("cdef bytes _fe_information_key_fast(")
    key_end = source.index("cdef bytes _fe_information_key(", key_start)
    key_body = source[key_start:key_end]
    assert "_fe__information_state_encode(" in key_body
    assert "state." not in key_body


def test_ismcts_iteration_default_is_shared(monkeypatch) -> None:
    """Every serious caller consumes the shared ISMCTS iteration default."""
    import ast
    import sys

    from longwar.agents.ismcts_agent import DEFAULT_ISMCTS_ITERATIONS, ISMCTSAgent
    from longwar.simulate import make_agent, simulate_games

    agent_default = inspect.signature(ISMCTSAgent.__init__).parameters["iterations"].default
    assert agent_default == DEFAULT_ISMCTS_ITERATIONS

    for target in (make_agent, simulate_games):
        default = inspect.signature(target).parameters["ismcts_iterations"].default
        assert default == DEFAULT_ISMCTS_ITERATIONS, target.__name__

    # The human-facing experiment CLI was deliberately collapsed. The
    # decision-grade strength benchmark keeps the serious default; batch
    # balance runs have their own explicit lower work budget.
    from tools import run_experiments

    monkeypatch.setattr(sys, "argv", ["run_experiments.py", "strength-bench"])
    args = run_experiments.parse_args()
    assert args.iterations == DEFAULT_ISMCTS_ITERATIONS

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


def test_verify_runs_python_undefined_name_lint() -> None:
    source = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "python -m ruff check src tools tests --select F821,F822,F823" in source


def test_native_heuristic_weights_are_runtime_configuration() -> None:
    from longwar.heuristics import DEFAULT_HEURISTIC_WEIGHTS
    from longwar.native_engine import create_heuristic_evaluator

    data = load_card_file(ROOT / "cards" / "cards.json")
    engine = GameEngine(data)
    custom_weights = DEFAULT_HEURISTIC_WEIGHTS.with_overrides(
        terminal_win_score=12345.0,
    )
    custom = create_heuristic_evaluator(engine._native_core(), custom_weights)
    index = tuple(DEFAULT_HEURISTIC_WEIGHTS.as_dict()).index("terminal_win_score")
    assert custom.weight_values()[index] == 12345.0


def test_native_source_fingerprint_is_generated_and_current() -> None:
    from tools import build_native_fingerprint

    generated = SRC / "_native_source_fingerprint.generated.pxi"
    assert generated.read_text(encoding="utf-8") == build_native_fingerprint.render()


def test_native_source_guard_rejects_stale_host_binary() -> None:
    from types import SimpleNamespace
    from longwar.native_fingerprint import assert_native_module_current

    stale = SimpleNamespace(
        NATIVE_SOURCE_CHECKABLE=True,
        NATIVE_SOURCE_FINGERPRINT="definitely-stale",
    )
    with pytest.raises(RuntimeError, match="make native-build"):
        assert_native_module_current(stale)


def test_browser_native_artifact_skips_host_source_check() -> None:
    from types import SimpleNamespace
    from longwar.native_fingerprint import assert_native_module_current

    browser = SimpleNamespace(
        NATIVE_SOURCE_CHECKABLE=False,
        NATIVE_SOURCE_FINGERPRINT="browser-build",
    )
    assert assert_native_module_current(browser) is browser


def test_verify_rebuilds_native_extension_before_tests() -> None:
    source = (ROOT / "Makefile").read_text(encoding="utf-8")
    verify = source.split("verify:", 1)[1].split("\n\n", 1)[0]
    assert "$(MAKE) native-build" in verify
    assert "build_native_fingerprint.py" in source


def test_native_topology_dimensions_are_not_cross_wired() -> None:
    resolution = (SRC / "_fast_engine_resolution.pxi").read_text(
        encoding="utf-8"
    )
    strength = (SRC / "_fast_engine_strength.pxi").read_text(
        encoding="utf-8"
    )

    assert "slot_index(0, front, p)" not in resolution
    assert "slot_index(1, front, p)" not in resolution
    assert "for rank in range(RANK_COUNT):" in resolution
    assert "slot_index(player, front, 1)" not in strength
    assert "slot_index(enemy, front, 0)" not in strength
    assert "slot_index(enemy, front, 1)" not in strength


def test_ongoing_narrative_storage_is_not_treated_as_front_index() -> None:
    effects = (SRC / "_fast_engine_effects.pxi").read_text(encoding="utf-8")
    strength = (SRC / "_fast_engine_strength.pxi").read_text(encoding="utf-8")

    assert "controller * NARRATIVE_SLOTS_PER_PLAYER + front" not in effects
    assert "player * NARRATIVE_SLOTS_PER_PLAYER + front" not in strength
    assert "state.narrative_front_mask[ix] & (1 << front)" in effects
    assert "narrative_front_mask" in strength


def test_native_slot_access_never_uses_literal_rank_codes() -> None:
    pattern = re.compile(r"slot_index\([^()\n]*,\s*[01]\s*\)")
    offenders: list[str] = []
    for path in sorted(SRC.glob("_fast_engine*.pxi")):
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            if pattern.search(line):
                offenders.append(f"{path.name}:{lineno}: {line.strip()}")
    assert not offenders, "\n".join(offenders)
