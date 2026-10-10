# Canonical native game-engine composition.
#
# Keep rule/state/card transition implementation here so host search builds and
# browser play consume exactly the same engine source graph. Search policies are
# deliberately included by their own composition layer.

include "_fast_constants.pxi"
include "_fast_state.pxi"

cdef class FastEngine

include "_fast_engine_cards.pxi"
include "_fast_engine_v2.pxi"
include "_fast_engine_state_io.pxi"
include "_fast_engine_strength.pxi"
include "_fast_engine_attack.pxi"
include "_fast_engine_costs.pxi"
include "_fast_engine_actions.pxi"
include "_fast_engine_effects.pxi"
include "_fast_engine_battleflow.pxi"
include "_fast_engine_resolution.pxi"
include "_fast_engine_pending.pxi"
include "_fast_engine_hashing.pxi"
include "_fast_engine_class.pxi"
