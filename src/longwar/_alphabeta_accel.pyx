# cython: language_level=3, boundscheck=False, wraparound=False, initializedcheck=False, cdivision=True
from __future__ import annotations


class SearchLimit(RuntimeError):
    """Raised when the shared alpha-beta node budget is exhausted."""


cdef class SearchBudget:
    cdef public long limit
    cdef public long nodes

    def __init__(self, long limit):
        if limit <= 0:
            raise ValueError("search budget must be positive")
        self.limit = limit
        self.nodes = 0

    cdef inline void visit(self) except *:
        self.nodes += 1
        if self.nodes > self.limit:
            raise SearchLimit


cdef double _alphabeta(
    object agent,
    object engine,
    object state,
    int root_player,
    int depth,
    double alpha,
    double beta,
    SearchBudget budget,
    dict transposition,
    list scratch,
    int level,
) except *:
    cdef int actor
    cdef bint maximizing
    cdef bint cutoff = False
    cdef double value
    cdef double child_value
    cdef object actions
    cdef object action
    cdef object child
    cdef object cache_key
    cdef object cached

    budget.visit()

    if depth <= 0 or state.phase.value == "complete":
        return <double>agent._strategic_state_value(
            engine,
            state,
            root_player,
        )

    cache_key = (
        depth,
        root_player,
        agent._state_key(state),
    )
    cached = transposition.get(cache_key)
    if cached is not None:
        return <double>cached

    actor = state.active_player
    actions = agent._ordered_actions(
        engine,
        state,
        actor,
        width=agent.candidate_width,
    )
    if not actions:
        return <double>agent._strategic_state_value(
            engine,
            state,
            root_player,
        )

    maximizing = actor == root_player
    value = -1.7976931348623157e308 if maximizing else 1.7976931348623157e308

    for action in actions:
        if level < len(scratch):
            child = scratch[level]
            child.copy_from(state)
        else:
            child = state.clone()
            scratch.append(child)

        engine.apply(child, action, validate=False)
        child_value = _alphabeta(
            agent,
            engine,
            child,
            root_player,
            depth - 1,
            alpha,
            beta,
            budget,
            transposition,
            scratch,
            level + 1,
        )

        if maximizing:
            if child_value > value:
                value = child_value
            if value > alpha:
                alpha = value
        else:
            if child_value < value:
                value = child_value
            if value < beta:
                beta = value

        if beta <= alpha:
            cutoff = True
            break

    # A cutoff gives only a bound. Cache exact values only.
    if not cutoff:
        transposition[cache_key] = value
    return value


cpdef double search_value(
    object agent,
    object engine,
    object state,
    int root_player,
    int depth,
    double alpha,
    double beta,
    SearchBudget budget,
    dict transposition,
    list scratch,
):
    """Compiled alpha-beta recursion over the authoritative Python game engine.

    Mutable GameState allocation is avoided below the root by reusing one
    scratch state per search depth and copying the current branch into it.
    """
    return _alphabeta(
        agent,
        engine,
        state,
        root_player,
        depth,
        alpha,
        beta,
        budget,
        transposition,
        scratch,
        0,
    )
