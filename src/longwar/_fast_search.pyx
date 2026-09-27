# cython: language_level=3, boundscheck=False, wraparound=False, initializedcheck=False, cdivision=True
from libc.stdint cimport int8_t, int16_t, uint8_t, uint16_t, uint32_t, int32_t, uint64_t
from libc.stddef cimport size_t
from libc.string cimport memcpy, memset
from libc.stdlib cimport malloc, free, realloc
from libc.math cimport tanh, log, sqrt
from cpython.bytes cimport PyBytes_FromStringAndSize
import hashlib
import json
from time import perf_counter

include "_fast_constants.pxi"
include "_fast_state.pxi"

cdef class FastEngine

include "_fast_engine_cards.pxi"
include "_fast_engine_state_io.pxi"
include "_fast_engine_strength.pxi"
include "_fast_engine_costs.pxi"
include "_fast_engine_actions.pxi"
include "_fast_engine_effects.pxi"
include "_fast_engine_battleflow.pxi"
include "_fast_engine_resolution.pxi"
include "_fast_engine_pending.pxi"
include "_fast_engine_hashing.pxi"

include "_fast_engine_class.pxi"

# Keep one compiled extension/shared packed state, but separate policies and
# algorithms physically so rule changes do not invite heuristic/search edits.
include "_heuristic_core.pxi"
include "_alpha_beta_core.pxi"
include "_ismcts_core.pxi"
include "_mccfr_core.pxi"
