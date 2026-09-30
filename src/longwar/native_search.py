"""Stable Python boundary for native search implementations.

Search agents depend on named backend capabilities here, not on the physical
Cython extension layout. This keeps native packaging changes out of agents and
the game core.
"""
from __future__ import annotations


def strategic_backend():
    from ._fast_search import (
        FastEngine,
        NativeHeuristicEvaluator,
        NativeSearchBudget,
        NativeSearchLimit,
        NativeTranspositionTable,
        native_search_value,
    )
    return (
        FastEngine,
        NativeHeuristicEvaluator,
        NativeSearchBudget,
        NativeSearchLimit,
        NativeTranspositionTable,
        native_search_value,
    )


def ismcts_backend():
    from ._fast_search import (
        FastEngine,
        ISMCTSTree,
        NativeHeuristicEvaluator,
        ismcts_search,
    )
    return FastEngine, ISMCTSTree, NativeHeuristicEvaluator, ismcts_search


def mccfr_backend():
    from ._fast_search import (
        FastCFRNode,
        FastEngine,
        NativeHeuristicEvaluator,
        make_scratch,
        packed_external_sampling_traverse,
        stable_information_id_from_fast_key,
    )
    return (
        FastCFRNode,
        FastEngine,
        NativeHeuristicEvaluator,
        make_scratch,
        packed_external_sampling_traverse,
        stable_information_id_from_fast_key,
    )
