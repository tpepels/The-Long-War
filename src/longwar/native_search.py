"""Stable Python boundary for native search implementations.

Search agents depend on named backend capabilities here, not on the physical
Cython extension layout. This keeps native packaging changes out of agents and
the game core.
"""
from __future__ import annotations

from .native_fingerprint import assert_native_module_current


def _native_module():
    from . import _fast_search
    return assert_native_module_current(_fast_search)


def strategic_backend():
    module = _native_module()
    return (
        module.FastEngine,
        module.NativeHeuristicEvaluator,
        module.NativeSearchBudget,
        module.NativeSearchLimit,
        module.NativeTranspositionTable,
        module.native_search_value,
    )


def ismcts_backend():
    module = _native_module()
    return (
        module.FastEngine,
        module.ISMCTSTree,
        module.NativeHeuristicEvaluator,
        module.ismcts_search,
    )


def mccfr_backend():
    module = _native_module()
    return (
        module.FastCFRNode,
        module.FastEngine,
        module.NativeHeuristicEvaluator,
        module.make_scratch,
        module.packed_external_sampling_traverse,
        module.stable_information_id_from_fast_key,
    )
