from __future__ import annotations

import json
import re
from pathlib import Path

from longwar.cards import load_card_file
from longwar.game import GameEngine
from longwar.rules import GameRules

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "longwar"


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_game_core_dependencies_point_inward_only() -> None:
    """The rules engine must not depend on UI, research, or simulation consumers."""
    core_files = (
        SRC / "cards.py",
        SRC / "rules.py",
        SRC / "game" / "actions.py",
        SRC / "game" / "model.py",
        SRC / "game" / "engine.py",
    )
    forbidden = (
        "longwar.agents",
        ".agents",
        "longwar.algorithms",
        ".algorithms",
        "longwar.simulate",
        ".simulate",
        "longwar.telemetry",
        ".telemetry",
        "longwar.balance",
        ".balance",
        "longwar.counterfactual",
        ".counterfactual",
        "longwar.web_api",
        ".web_api",
        "mccfr",
    )
    for path in core_files:
        text = path.read_text(encoding="utf-8")
        assert not any(term in text for term in forbidden), path


def test_runtime_and_search_do_not_special_case_canonical_card_ids() -> None:
    """Reusable mechanics, not named cards, belong in runtime/search code."""
    payload = json.loads(source("cards/cards.json"))
    card_ids = {card["id"] for card in payload["cards"]}

    for path in sorted(
        p for pattern in ("*.py", "*.pyx", "*.pxi") for p in SRC.rglob(pattern)
    ):
        text = path.read_text(encoding="utf-8")
        leaked = [
            card_id
            for card_id in card_ids
            if re.search(rf"""(?P<q>['"]){re.escape(card_id)}(?P=q)""", text)
        ]
        assert not leaked, f"{path} special-cases cards: {leaked}"


def test_cards_are_compiled_before_entering_native_runtime() -> None:
    """Raw authored mechanics stop at the Python card boundary."""
    engine = source("src/longwar/game/engine.py")
    native_cards = source("src/longwar/_fast_engine_cards.pxi")

    assert "compile_card_mechanics" in engine
    assert "self.card_mechanics" in engine
    assert 'card.get("design_rules")' not in native_cards


def test_deck_construction_is_not_a_match_rule() -> None:
    """Deck policy is content validation, not GameRules state."""
    assert "deck_size" not in GameRules.__dataclass_fields__

    engine = source("src/longwar/game/engine.py")
    assert "validate_deck_definition(deck, self.cards)" in engine

    core = "\n".join(
        source(path)
        for path in (
            "src/longwar/rules.py",
            "src/longwar/cards.py",
            "src/longwar/game/engine.py",
            "src/longwar/game/model.py",
            "src/longwar/game/actions.py",
        )
    )
    assert "decks/" not in core


def test_browser_runtime_excludes_research_dependencies() -> None:
    """The playable browser build must not package analysis/training systems."""
    from tools import build_browser_runtime

    packaged = set(build_browser_runtime.BROWSER_PYTHON_FILES)
    forbidden = {
        "simulate.py",
        "telemetry.py",
        "balance.py",
        "health.py",
        "playability.py",
        "counterfactual.py",
        "targeted_counterfactual.py",
        "mccfr.py",
        "online_mccfr.py",
        "parallel_mccfr.py",
        "agents/mccfr_agent.py",
        "agents/online_mccfr_agent.py",
    }
    assert not forbidden & packaged

    web_api = source("src/longwar/web_api.py")
    for name in ("mccfr", "counterfactual", "telemetry", "balance", "simulate"):
        assert name not in web_api


def test_browser_runtime_dependency_closure_is_complete() -> None:
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


def test_compiled_native_module_is_hidden_behind_facades() -> None:
    """Python consumers use native_engine/native_search rather than importing Cython directly."""
    allowed = {SRC / "native_engine.py", SRC / "native_search.py"}
    for path in SRC.rglob("*.py"):
        if path in allowed:
            continue
        assert "_fast_search" not in path.read_text(encoding="utf-8"), path


def test_native_engine_core_contains_no_search_implementation() -> None:
    engine_core = source("src/longwar/_fast_engine_core.pxi")
    host = source("src/longwar/_fast_search.pyx")

    assert 'include "_fast_engine_core.pxi"' in host
    for search_include in (
        "_alpha_beta_core.pxi",
        "_ismcts_core.pxi",
        "_mccfr_core.pxi",
    ):
        assert search_include not in engine_core


def test_search_algorithms_do_not_own_match_rules() -> None:
    """Changing a GameRules field should not require search-algorithm semantics."""
    sources = (
        source("src/longwar/algorithms/alpha_beta.py"),
        source("src/longwar/_alpha_beta_core.pxi"),
        source("src/longwar/_ismcts_core.pxi"),
        source("src/longwar/_mccfr_core.pxi"),
    )
    for text in sources:
        assert "GameRules" not in text
        for field in GameRules.__dataclass_fields__:
            assert not re.search(rf"\b{re.escape(field)}\b", text), field


def test_public_game_engine_delegates_to_rules_and_native_runtime() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    rules = GameRules.standard()
    engine = GameEngine(data, rules=rules)

    for field in GameRules.__dataclass_fields__:
        assert getattr(engine, field) == getattr(rules, field)

    engine_source = source("src/longwar/game/engine.py")
    assert "from ..native_engine import" in engine_source
    assert "_fast_search" not in engine_source
