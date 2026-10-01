"""Stable Python boundary for the canonical native game engine.

The compiled module name and layout are implementation details. Game/core code
imports this module instead of importing a Cython extension directly.
"""
from __future__ import annotations

from typing import Any


def create_fast_engine(engine: Any):
    try:
        from ._fast_search import FastEngine
    except ImportError as exc:
        raise RuntimeError(
            "The canonical native game engine is not built. "
            "Run: python -m pip install -e '.[dev]'"
        ) from exc
    return FastEngine(engine)


def create_heuristic_evaluator(fast_engine: Any, weights: Any = None):
    try:
        from ._fast_search import NativeHeuristicEvaluator
    except ImportError as exc:
        raise RuntimeError(
            "The canonical native heuristic evaluator is not built. "
            "Run: python -m pip install -e '.[dev]'"
        ) from exc
    return NativeHeuristicEvaluator(fast_engine, weights)
