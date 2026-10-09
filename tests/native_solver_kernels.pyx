# cython: language_level=3, boundscheck=False, wraparound=False, initializedcheck=False, cdivision=True
"""Test-only native game compiling the ORIGINAL optimized search kernels.

The three algorithm .pxi files are included directly, unchanged. Their
_sg_* dependency is supplied by this small independent solved-game engine.
No Long War cards, state transitions, or production hot paths are involved.
"""
cimport cython
from libc.stdint cimport int8_t, int16_t, uint8_t, uint16_t, uint32_t, int32_t, uint64_t
from libc.stddef cimport size_t
from libc.stdlib cimport malloc, free, realloc
from libc.string cimport memset, memcpy
from libc.math cimport tanh, log, sqrt, pow, isfinite
from time import perf_counter
import random
import itertools
import json
import hashlib

DEF MAX_ACTIONS = 4
DEF MAX_PENDING_EFFECTS = 2

# The MCCFR file also contains a legacy information-key *diagnostic decoder*.
# These constants are needed only to compile that unrelated, unused decoder.
DEF INFORMATION_KEY_VERSION = 1
DEF PHASE_BATTLE = 0
DEF PHASE_COMPLETE = 1
DEF U32_BYTES = 4
DEF U16_BYTES = 2
DEF INFO_TURN_FLOW_BYTES = 2
DEF PLAYER_COUNT = 2
DEF INFO_PLAYER_BASE_BYTES = 6
DEF INFO_PLAYER_SEARCH_EXTRA_BYTES = 3
DEF INFO_PENDING_EFFECT_BYTES = 16
DEF INFO_PENDING_RESUME_BYTES = 2
DEF INFO_MANEUVER_COUNT_BYTES = 4
DEF SLOT_COUNT = 24
DEF INFO_CONSTRAINT_BYTES = 18
DEF INFO_RESOLUTION_FIXED_BYTES = 15
DEF POSITIONS_PER_PLAYER = 12
DEF RANK_COUNT = 3
DEF RANK_FRONT = 0
DEF RANK_MIDDLE = 1
DEF INFO_BOARD_SLOT_BASE_BYTES = 19
DEF INFO_NARRATIVE_SEARCH_BYTES = 5
DEF FRONT_COUNT = 4
DEF DIRECTION_LEFT = 1
DEF DIRECTION_RIGHT = 2
DEF INFO_STRATAGEM_SEARCH_BYTES = 7

DEF GAME_NIM = 0
DEF GAME_HIDDEN_CHOICE = 1
DEF GAME_KUHN = 2

cdef struct InfoHash128:
    uint64_t a
    uint64_t b

cdef class FastState:
    cdef public int mode
    cdef public int stones
    cdef public int actor
    cdef public int winner
    cdef public int stage
    cdef public int history
    cdef public int private_outcome
    cdef public int card0
    cdef public int card1
    cdef public int turn_number
    cdef public double payoff

    def __cinit__(self):
        self.winner = -1
        self.history = 1
        self.card0 = -1
        self.card1 = -1

    cdef void copy_from_fast(self, FastState source) noexcept:
        self.mode = source.mode
        self.stones = source.stones
        self.actor = source.actor
        self.winner = source.winner
        self.stage = source.stage
        self.history = source.history
        self.private_outcome = source.private_outcome
        self.card0 = source.card0
        self.card1 = source.card1
        self.turn_number = source.turn_number
        self.payoff = source.payoff


cdef class FastEngine:
    cdef public object card_ids

    def __init__(self):
        self.card_ids = ()

    cpdef FastState from_game_state(self, object source):
        cdef FastState result = FastState()
        if not isinstance(source, FastState):
            raise TypeError("Native oracle expects packed FastState")
        result.copy_from_fast(<FastState>source)
        return result


cdef class NativeHeuristicEvaluator:
    def __init__(self, FastEngine engine):
        pass


cdef inline int _sg_actor(FastState state) noexcept:
    return state.actor

cdef inline bint _sg_terminal(FastState state) noexcept:
    if state.mode == GAME_NIM:
        return state.stones == 0
    if state.mode == GAME_HIDDEN_CHOICE:
        return state.stage == 1
    return state.stage == 3 or (
        state.stage == 2 and state.history != 14
    )

cdef inline bint _sg_forced_substep(FastState state) noexcept:
    return False

cdef inline int _sg_round_epoch(FastState state) noexcept:
    return 1

cdef inline int _sg_turn_serial(FastState state) noexcept:
    return state.turn_number

cdef inline int _sg_actions_in_turn(FastState state) noexcept:
    return 0

cdef inline int _sg_action_kind(uint64_t action) noexcept:
    return <int>action

cdef inline bint _sg_priority_action(uint64_t action) noexcept:
    return False

cdef inline str _sg_action_id(FastEngine engine, uint64_t action):
    return str(action)

cdef inline int _sg_legal_actions(
    FastEngine game, FastState state, uint64_t* actions
) except -1:
    if _sg_terminal(state):
        return 0
    actions[0] = 1
    if state.mode == GAME_NIM and state.stones == 1:
        return 1
    actions[1] = 2
    return 2

cdef inline void _sg_apply(
    FastEngine game, FastState state, uint64_t action
) except *:
    cdef int p
    if action not in (1, 2) or _sg_terminal(state):
        raise ValueError("Illegal solved-game action")
    p = state.actor
    if state.mode == GAME_NIM:
        if action > state.stones:
            raise ValueError("Cannot take more than available stones")
        state.stones -= <int>action
        if state.stones == 0:
            state.winner = p
        state.actor = 1 - p
    elif state.mode == GAME_HIDDEN_CHOICE:
        state.payoff = (
            0.4 if action == 1 else <double>state.private_outcome
        )
        state.stage = 1
        state.actor = 1
    else:
        state.history = state.history * 3 + <int>action
        state.stage += 1
        state.actor = 1 - p
        if _sg_terminal(state):
            if state.history == 16:    # bet / fold
                state.payoff = 1.0
            elif state.history == 43:  # check / bet / fold
                state.payoff = -1.0
            elif state.history in (13, 17, 44):
                state.payoff = (
                    2.0 if state.history != 13 else 1.0
                ) * (1.0 if state.card0 > state.card1 else -1.0)
            else:
                raise ValueError("Unexpected Kuhn terminal history")
    state.turn_number += 1

cdef inline bint _sg_completed_turn(
    FastEngine game, FastState state, int serial, int actions_before, int kind
) noexcept:
    return state.turn_number != serial

cdef inline double _sg_terminal_reward(FastState state, int player) noexcept:
    if state.mode == GAME_NIM:
        return 1.0 if state.winner == player else -1.0
    return state.payoff if player == 0 else -state.payoff

cdef inline double _sg_strategic_value(
    NativeHeuristicEvaluator evaluator, FastState state, int player
) noexcept:
    if _sg_terminal(state):
        return _sg_terminal_reward(state, player)
    return 0.0

cdef inline double _sg_leaf_value(
    NativeHeuristicEvaluator evaluator, FastState state,
    int player, double leaf_scale
) noexcept:
    if _sg_terminal(state):
        return _sg_terminal_reward(state, player)
    return 0.0

cdef inline double _sg_boundary_value(
    NativeHeuristicEvaluator evaluator, FastState state,
    int player, double leaf_scale
) noexcept:
    return _sg_strategic_value(evaluator, state, player)

cdef inline double _sg_rollout_value(
    NativeHeuristicEvaluator evaluator, FastState state,
    int player, double leaf_scale
) noexcept:
    return _sg_strategic_value(evaluator, state, player)

cdef inline double _sg_order_score(
    NativeHeuristicEvaluator evaluator, FastState state,
    int player, uint64_t action, FastState scratch
) noexcept:
    return 0.0

cdef inline double _sg_rollout_prior(
    NativeHeuristicEvaluator evaluator, FastState state,
    int player, uint64_t action
) noexcept:
    return 1.0

cdef inline bint _sg_rollout_reject_action(
    NativeHeuristicEvaluator evaluator, FastState state,
    int player, uint64_t action, FastState scratch
) noexcept:
    return False

cdef inline bytes _sg_information_key(
    FastEngine game, FastState state, int player
):
    if state.mode == GAME_NIM:
        return bytes((GAME_NIM, player, state.actor, state.stones))
    if state.mode == GAME_HIDDEN_CHOICE:
        return bytes((GAME_HIDDEN_CHOICE, player, state.actor, state.stage))
    # Only the player's own private card is visible; history is public.
    return bytes((
        GAME_KUHN, player, state.actor, state.stage,
        state.history, (state.card0 if player == 0 else state.card1) + 1,
    ))

cdef inline InfoHash128 _sg_information_hash(
    FastEngine game, FastState state, int player
) noexcept:
    cdef InfoHash128 result
    cdef uint64_t identifier = (
        (<uint64_t>state.mode << 56)
        | (<uint64_t>player << 48)
        | (<uint64_t>state.actor << 40)
        | (<uint64_t>state.stage << 32)
    )
    if state.mode == GAME_NIM:
        identifier |= <uint64_t>state.stones
    elif state.mode == GAME_KUHN:
        identifier |= (
            (<uint64_t>state.history << 16)
            | <uint64_t>((state.card0 if player == 0 else state.card1) + 1)
        )
    result.a = identifier
    result.b = identifier ^ 0x9E3779B97F4A7C15ULL
    return result

cdef inline InfoHash128 _sg_state_hash(
    FastEngine game, FastState state
) noexcept:
    cdef InfoHash128 result
    result = _sg_information_hash(game, state, 0)
    result.b = (
        (<uint64_t>(state.winner + 1) << 56)
        | (<uint64_t>(state.card0 + 1) << 48)
        | (<uint64_t>(state.card1 + 1) << 40)
        | (<uint64_t>(state.private_outcome + 2) << 32)
        | (<uint64_t>state.turn_number << 16)
        | <uint64_t>state.actor
    )
    return result


# Include the optimized Cython search implementations themselves, not a
# reimplementation, simplified copy or Python fallback.
include "_alpha_beta_core.pxi"
include "_ismcts_core.pxi"
include "_mccfr_core.pxi"


def _nim_state(int stones, int actor=0):
    if stones <= 0 or stones >= 255 or actor not in (0, 1):
        raise ValueError("Invalid Nim fixture")
    cdef FastState state = FastState()
    state.mode = GAME_NIM
    state.stones = stones
    state.actor = actor
    return state


def _hidden_state(int outcome):
    if outcome not in (-1, 1):
        raise ValueError("Hidden chance outcome must be -1 or 1")
    cdef FastState state = FastState()
    state.mode = GAME_HIDDEN_CHOICE
    state.private_outcome = outcome
    return state


def _kuhn_state(int card0, int card1):
    if card0 == card1 or card0 not in (0, 1, 2) or card1 not in (0, 1, 2):
        raise ValueError("Invalid Kuhn deal")
    cdef FastState state = FastState()
    state.mode = GAME_KUHN
    state.card0 = card0
    state.card1 = card1
    return state


def solve_nim_alpha_beta(int stones, int actor=0, int root_player=0):
    cdef FastEngine engine = FastEngine()
    cdef NativeHeuristicEvaluator evaluator = NativeHeuristicEvaluator(engine)
    cdef NativeSearchBudget budget = NativeSearchBudget(50000)
    cdef NativeTranspositionTable table = NativeTranspositionTable(1024)
    return native_search_value(
        engine, _nim_state(stones, actor), root_player, stones,
        -1.0e300, 1.0e300, budget, 2, evaluator, table,
    )


def solve_nim_ismcts(
    int stones, int seed=1, int iterations=1800,
    int actor=0,
):
    cdef FastEngine engine = FastEngine()
    cdef NativeHeuristicEvaluator evaluator = NativeHeuristicEvaluator(engine)
    return ismcts_search(
        engine, evaluator, [_nim_state(stones, actor)], actor,
        iterations=iterations, rollout_depth=stones + 1,
        post_battle_rollout_depth=0,
        tree_depth_limit=stones + 1,
        rollout_policy=2, seed=seed, exploration=0.65,
    )


def solve_hidden_ismcts(int seed=1, int iterations=4000):
    cdef FastEngine engine = FastEngine()
    cdef NativeHeuristicEvaluator evaluator = NativeHeuristicEvaluator(engine)
    return ismcts_search(
        engine, evaluator, [_hidden_state(-1), _hidden_state(1)], 0,
        iterations=iterations, rollout_depth=2,
        post_battle_rollout_depth=0,
        tree_depth_limit=2,
        rollout_policy=2, seed=seed, exploration=0.8,
    )


def solve_kuhn_mccfr(int iterations=25000, int seed=20261009):
    cdef FastEngine engine = FastEngine()
    cdef NativeHeuristicEvaluator evaluator = NativeHeuristicEvaluator(engine)
    cdef list scratch = make_scratch(3)
    cdef object rng = random.Random(seed)
    cdef dict nodes = {}
    cdef FastState state
    cdef object deals = tuple(itertools.permutations(range(3), 2))
    cdef int i, traverser, card0, card1
    cdef bytes key
    cdef object node
    cdef int card, history, actor
    cdef str word
    cdef dict policy = {}
    cdef dict raw
    for i in range(iterations):
        card0, card1 = rng.choice(deals)
        for traverser in (0, 1):
            state = _kuhn_state(card0, card1)
            packed_external_sampling_traverse(
                engine, state, traverser,
                depth=0, max_depth=3, nodes=nodes, rng=rng,
                scratch=scratch, evaluator=evaluator,
            )

    for key, node in nodes.items():
        actor = key[1]
        history = key[4]
        card = key[5] - 1
        if history == 1:
            word = ""
        elif history == 4:
            word = "p"
        elif history == 5:
            word = "b"
        elif history == 14:
            word = "pb"
        else:
            raise RuntimeError(f"Unexpected Kuhn info-set {history}")
        raw = node.average_strategy((1, 2))
        policy[f"{actor}:{card}:{word}"] = {
            "p": raw[1], "b": raw[2],
        }
    return policy
