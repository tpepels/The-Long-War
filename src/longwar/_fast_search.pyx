# cython: language_level=3, boundscheck=False, wraparound=False, initializedcheck=False, cdivision=True
cimport cython
from libc.stdint cimport int8_t, int16_t, uint8_t, uint16_t, uint32_t, int32_t, uint64_t
from libc.stddef cimport size_t
from libc.string cimport memcpy, memset
from libc.stdlib cimport malloc, free, realloc
from libc.math cimport tanh, log, sqrt
from cpython.bytes cimport PyBytes_FromStringAndSize
import hashlib
import json
from time import perf_counter
from longwar.protocol import CardType, DesignToken

# One canonical engine composition shared by host search and browser play.
include "_fast_engine_core.pxi"

# Search/evaluation policies consume the engine; they do not participate in
# rule composition.
include "_heuristic_core.pxi"
include "_alpha_beta_core.pxi"
include "_ismcts_core.pxi"
include "_mccfr_core.pxi"
