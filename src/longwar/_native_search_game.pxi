# Native packed search-game adapter (compile-time dispatch).
#
# Rules and physical game details belong to _fast_engine_core.pxi. Native
# search kernels should use only the _sg_* surface for state transitions,
# turn boundaries, observations and actor identity. Every entry point is
# inlined: no Python Protocol calls, allocations or virtual dispatch are
# added to the hot search loop.
#
# Future games can implement this same surface using their own packed state
# and engine types, compiling the unchanged search algorithms against it.

cdef inline int _sg_actor(FastState state) noexcept:
    return state.active_player


cdef inline bint _sg_terminal(FastState state) noexcept:
    return state.phase == PHASE_COMPLETE


cdef inline int _sg_winner(FastState state) noexcept:
    return state.winner


cdef inline int _sg_turn_serial(FastState state) noexcept:
    return state.turn_number


cdef inline int _sg_actions_in_turn(FastState state) noexcept:
    return state.actions_this_turn


cdef inline int _sg_battle(FastState state) noexcept:
    return state.battle


cdef inline bint _sg_forced_substep(FastState state) noexcept:
    return _fe_forced_substep_pending(state)


cdef inline int _sg_legal_actions(
    FastEngine game, FastState state, uint64_t* actions
) except -1:
    return _fe_legal_actions_into(game, state, actions)


cdef inline void _sg_apply(
    FastEngine game, FastState state, uint64_t action
):
    _fe_apply_fast(game, state, action)


cdef inline bint _sg_completed_turn(
    FastEngine game, FastState state, int serial, int actions_before, int kind
) noexcept:
    return _fe_transition_completed_turn(
        game, state, serial, actions_before, kind
    )


cdef inline int _sg_action_kind(uint64_t action) noexcept:
    return action_kind(action)


cdef inline bint _sg_priority_action(uint64_t action) noexcept:
    cdef int kind = action_kind(action)
    return kind == TYPE_PASS or kind == TYPE_END_TURN


cdef inline str _sg_action_id(FastEngine game, uint64_t action):
    return _fe_action_key(game, action)


cdef inline InfoHash128 _sg_state_hash(
    FastEngine game, FastState state
) noexcept:
    return _fe_state_hash_fast(game, state)


cdef inline InfoHash128 _sg_information_hash(
    FastEngine game, FastState state, int actor
) noexcept:
    return _fe_information_hash_fast(game, state, actor)


cdef inline bytes _sg_information_key(
    FastEngine game, FastState state, int actor
):
    return _fe_information_key_fast(game, state, actor)
