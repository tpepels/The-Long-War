"""Stable Python boundary for the canonical native game engine.

The compiled module name and layout are implementation details. Game/core code
imports this module instead of importing a Cython extension directly.
"""
from __future__ import annotations

from typing import Any

from .native_fingerprint import assert_native_module_current


def _native_module():
    try:
        from . import _fast_search
    except ImportError as exc:
        raise RuntimeError(
            "The canonical native game engine is not built. "
            "Run: make native-build"
        ) from exc
    return assert_native_module_current(_fast_search)


def create_fast_engine(engine: Any):
    return _native_module().FastEngine(engine)


def create_heuristic_evaluator(
    fast_engine: Any,
    weights: Any = None,
    *,
    sampled_opponent_resources: bool = False,
):
    return _native_module().NativeHeuristicEvaluator(
        fast_engine,
        weights,
        sampled_opponent_resources=sampled_opponent_resources,
    )
