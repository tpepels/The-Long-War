DEF MAX_CARDS = 127
DEF MAX_DECK = 254
DEF SLOT_COUNT = 16
DEF NARRATIVE_COUNT = 8
DEF MAX_ACTIONS = 1024
DEF MAX_RECOVERY_SCHEDULE = 32
DEF MAX_PENDING_EFFECTS = 32
DEF MAX_CONSTRAINTS = 16
DEF NONE = -1

cdef int PHASE_BATTLE = 0
cdef int PHASE_COMPLETE = 2

cdef int TYPE_PASS = 0
cdef int TYPE_FORCE = 2
cdef int TYPE_BOND = 3
cdef int TYPE_NAME = 4
cdef int TYPE_NARRATIVE = 5
cdef int TYPE_ONGOING_NARRATIVE = 6
cdef int TYPE_STRATAGEM = 7
cdef int TYPE_DISCARD = 10
cdef int TYPE_MANEUVER = 11
cdef int TYPE_EFFECT = 12

cdef int EFFECT_NONE = 0
cdef int EFFECT_FREE_MANEUVER = 1
cdef int EFFECT_MOVE = 2
cdef int EFFECT_SWAP = 3
cdef int EFFECT_RECOVER = 4
cdef int EFFECT_FRONT_CONTRIBUTION = 5
cdef int EFFECT_SUPPRESS = 6
cdef int EFFECT_SACRIFICE = 7
cdef int EFFECT_INTERCEPT = 8
cdef int EFFECT_RETREAT = 9
cdef int EFFECT_PROTECT_RETREAT = 10
cdef int EFFECT_TRANSFER_COMPONENT = 11
cdef int EFFECT_SUCCESSION = 12

cdef int EFFECT_OPTIONAL = 1
cdef int EFFECT_ALLOW_UNNAMED = 2
cdef int EFFECT_ADJACENT_PAIR = 4
cdef int EFFECT_CARD_MOVE = 8
cdef int EFFECT_SAME_FRONT_PAIR = 16

# Reusable boolean card capabilities. These live in one per-card bitset so
# adding another boolean mechanic does not require another MAX_CARDS array on
# FastEngine.
cdef uint64_t CAP_ADJACENT_RETREAT_FREE_MANEUVER = (<uint64_t>1) << 0
cdef uint64_t CAP_AFTER_FRONTLINE_RETREAT_SIDEWAYS_FORCE = (<uint64_t>1) << 1
cdef uint64_t CAP_AFTER_MANEUVER_SWAP_OTHER_FRIENDLIES = (<uint64_t>1) << 2
cdef uint64_t CAP_AFTER_SELF_MANEUVER_FREE_OTHER_NAMED_IF_WIDE = (<uint64_t>1) << 3
cdef uint64_t CAP_AFTER_SELF_RETREAT_SIDEWAYS_NAME = (<uint64_t>1) << 4
cdef uint64_t CAP_FOLLOW_INTO_VACATED_AFTER_ADJACENT_MANEUVER = (<uint64_t>1) << 5
cdef uint64_t CAP_NARRATIVE_COMMAND_GAIN_FREE_MANEUVER_FORCE = (<uint64_t>1) << 6
cdef uint64_t CAP_ON_PLAY_TAKE_ADJACENT_OPEN_BOND_NAME = (<uint64_t>1) << 7
cdef uint64_t CAP_ON_PLAY_TAKE_ADJACENT_PREPARED_COMPONENT_FORCE = (<uint64_t>1) << 8
cdef uint64_t CAP_OPPOSING_MANEUVER_SAME_FRONT_FREE_MANEUVER = (<uint64_t>1) << 9
cdef uint64_t CAP_OPPOSING_NAMED_SAME_FRONT_FREE_MANEUVER = (<uint64_t>1) << 10
cdef uint64_t CAP_OPTIONAL_SELF_DRIVE_PREVENT_FRONTLINE_RETREAT_FORCE = (<uint64_t>1) << 11
cdef uint64_t CAP_PREPARED_ON_PLAY_FREE_MANEUVER_FORCE = (<uint64_t>1) << 12
cdef uint64_t CAP_SUCCESSION_ON_DRIVE_OFF_NAME = (<uint64_t>1) << 13
cdef uint64_t CAP_TRANSFER_OPEN_BOND_AFTER_MOVE_BOND = (<uint64_t>1) << 14

cdef int RESUME_NONE = 0
cdef int RESUME_FINISH_OPERATION = 1
cdef int RESUME_BATTLE_RESOLUTION = 2
cdef int RESUME_START_BATTLE = 3

cdef int RESOLUTION_NONE = 0
cdef int RESOLUTION_PREPARE = 1
cdef int RESOLUTION_COMPARE = 2
cdef int RESOLUTION_RETREATS = 3
cdef int RESOLUTION_NARRATIVES = 4
cdef int RESOLUTION_RECOVERY = 5

cdef int CARD_FORCE = 1
cdef int CARD_BOND = 2
cdef int CARD_NAME = 3
cdef int CARD_NARRATIVE = 4
cdef int CARD_STRATAGEM = 5

cdef int ROLE_NONE = 0
cdef int ROLE_SWORDSMAN = 1
cdef int ROLE_SPEARMAN = 2
cdef int ROLE_ARCHER = 3
cdef int ROLE_HEALER = 4
cdef int ROLE_SHIP = 5
cdef int ROLE_STRONGHOLD = 6

cdef int FORCE_TEXT_NONE = 0
cdef int FORCE_TEXT_FRONT_BONUS = 1
cdef int FORCE_TEXT_REAR_BONUS = 2
cdef int FORCE_TEXT_SUPPORT_AHEAD = 3
cdef int FORCE_TEXT_FRONT_IF_REAR = 4
cdef int FORCE_TEXT_REAR_IF_FRONT = 5

cdef int NAME_NONE = 0
cdef int NAME_MOVE_ADJACENT = 1
cdef int NAME_REVEAL_NARRATIVE = 2

cdef int COMPLETE_NONE = 0
cdef int COMPLETE_GAIN_COMMAND = 1
cdef int COMPLETE_DRAW = 3
cdef int COMPLETE_REVEAL_NARRATIVE = 4
cdef int COMPLETE_RECOVER_BOND = 5

cdef int NARRATIVE_NONE = 0
cdef int NARRATIVE_DISCREDIT = 1
cdef int NARRATIVE_RETURN_NAME = 2
cdef int NARRATIVE_MOVE_FORCE = 3

cdef int EVENT_NONE = 0
cdef int EVENT_FORCE = 1
cdef int EVENT_BOND = 2
cdef int EVENT_PASS = 3
cdef int EVENT_NARRATIVE_TARGET = 4
cdef int EVENT_IMMEDIATE_NARRATIVE = 5
cdef int EVENT_NAME = 6

cdef int ONGOING_EFFECT_NONE = 0
cdef int ONGOING_EFFECT_PENALIZE_FORCE = 1
cdef int ONGOING_EFFECT_DISCARD_BOND = 2
cdef int ONGOING_EFFECT_REINFORCE = 3

cdef int STRAT_REVEAL_NONE = 0
cdef int STRAT_REVEAL_PENALIZE = 1

cdef int ACTOR_EITHER = 0
cdef int ACTOR_OPPONENT = 1
cdef int ACTOR_CONTROLLER = 2

cdef int NARRATIVE_CHOICE_NONE = 0
cdef int NARRATIVE_CHOICE_FRONT = 1
cdef int NARRATIVE_CHOICE_NAMED_FORMATION = 2

cdef int NARR_TRIGGER_NONE = 0
cdef int NARR_TRIGGER_FRIENDLY_NAMED = 1
cdef int NARR_TRIGGER_FRIENDLY_RETREAT = 2
cdef int NARR_TRIGGER_OPPONENT_NAMED = 3
cdef int NARR_TRIGGER_OPPONENT_BOTH_RANKS = 4

cdef int NARR_SECONDARY_NONE = 0
cdef int NARR_SECONDARY_FREE_TRIGGERED = 1
cdef int NARR_SECONDARY_SIDEWAYS_TRIGGERED = 2
cdef int NARR_SECONDARY_FREE_ANY_NAMED = 3
cdef int NARR_SECONDARY_MOVE_VACATED = 4

cdef int NARR_END_NONE = 0
cdef int NARR_END_NOT_LOST = 1
cdef int NARR_END_WON = 2
cdef int NARR_END_TARGET_SURVIVES = 3

cdef int STRAT_CHOICE_NONE = 0
cdef int STRAT_CHOICE_FRONT = 1
cdef int STRAT_CHOICE_ADJACENT_FRONTS = 2
cdef int STRAT_CHOICE_EDGE_FRONT = 3
cdef int STRAT_CHOICE_DIRECTION = 4
cdef int STRAT_CHOICE_WHEEL = 5
cdef int STRAT_CHOICE_RESERVES = 6

cdef int NARRATIVE_CHOICE_NAMED_DIRECTION = 3

cdef int CONSTRAINT_NONE = 0
cdef int CONSTRAINT_AFFECT_FRONT = 1
cdef int CONSTRAINT_MANEUVER = 2
cdef int CONSTRAINT_SPECIFIC_MANEUVER = 3

cdef int CONSTRAINT_EXPIRES_AFTER_OPERATION = 1
cdef int CONSTRAINT_PERSISTS_BATTLE = 2
cdef int CONSTRAINT_ZERO_COST = 4
cdef int CONSTRAINT_DRAW_ON_SATISFY = 8
cdef int CONSTRAINT_DISCARD_SOURCE_STORY = 16

cdef inline int slot_index(int player, int front, int rank) noexcept:
    return player * 8 + front * 2 + rank

cdef inline int owner_from_slot(int slot) noexcept:
    return 0 if slot < 8 else 1

cdef inline int local_slot(int slot) noexcept:
    return slot if slot < 8 else slot - 8

cdef inline int front_from_slot(int slot) noexcept:
    return local_slot(slot) >> 1

cdef inline int rank_from_slot(int slot) noexcept:
    return local_slot(slot) & 1

cdef inline int _append_action(uint64_t* actions, int n, uint64_t action) except -1:
    # Reserve one entry for Pass; guard before every write, including cards
    # producing multiple target combinations.
    if n >= MAX_ACTIONS - 1:
        raise RuntimeError("Native legal-action capacity exceeded")
    actions[n] = action
    return n + 1


cdef inline int popcount16(uint32_t value) noexcept:
    cdef int count = 0
    value &= 0xFFFF
    while value:
        count += value & 1
        value >>= 1
    return count


cdef inline uint64_t encode_action(
    int kind,
    int card=-1,
    int pos=-1,
    int dest=-1,
    int player=0,
    uint32_t extra=0,
) noexcept:
    return (
        <uint64_t>(kind & 15)
        | (<uint64_t>(card + 1) << 4)
        | (<uint64_t>(pos + 1) << 11)
        | (<uint64_t>(dest + 1) << 16)
        | (<uint64_t>(player & 1) << 21)
        | (<uint64_t>extra << 22)
    )

cdef inline int action_kind(uint64_t action) noexcept:
    return <int>(action & 15)

cdef inline int action_card(uint64_t action) noexcept:
    return <int>((action >> 4) & 127) - 1

cdef inline int action_pos(uint64_t action) noexcept:
    return <int>((action >> 11) & 31) - 1

cdef inline int action_dest(uint64_t action) noexcept:
    return <int>((action >> 16) & 31) - 1

cdef inline int action_player(uint64_t action) noexcept:
    return <int>((action >> 21) & 1)


cdef inline uint32_t action_extra(uint64_t action) noexcept:
    return <uint32_t>(action >> 22)


cdef struct InfoHash128:
    uint64_t a
    uint64_t b


cdef inline void _info_hash_init(InfoHash128* h) noexcept:
    h.a = 0xCBF29CE484222325ULL
    h.b = 0x84222325CBF29CE4ULL


cdef inline void _info_hash_feed(InfoHash128* h, uint8_t value) noexcept:
    h.a ^= <uint64_t>value
    h.a *= 0x100000001B3ULL
    h.b ^= <uint64_t>value
    h.b *= 0xC2B2AE3D27D4EB4FULL
    h.b ^= h.b >> 29


cdef inline void _info_hash_feed_u16(
    InfoHash128* h,
    uint16_t value,
) noexcept:
    _info_hash_feed(h, <uint8_t>(value & 255))
    _info_hash_feed(h, <uint8_t>((value >> 8) & 255))


cdef inline void _info_hash_feed_u32(
    InfoHash128* h,
    uint32_t value,
) noexcept:
    _info_hash_feed_u16(h, <uint16_t>(value & 65535))
    _info_hash_feed_u16(h, <uint16_t>((value >> 16) & 65535))


cdef inline void _info_emit(
    unsigned char* buf,
    int* n,
    InfoHash128* h,
    uint8_t value,
) noexcept:
    """Emit one canonical information-state byte to either/both sinks."""
    if buf != NULL:
        buf[n[0]] = value
    if h != NULL:
        _info_hash_feed(h, value)
    n[0] += 1


cdef inline void _info_emit_u16(
    unsigned char* buf, int* n, InfoHash128* h, uint16_t value,
) noexcept:
    _info_emit(buf, n, h, <uint8_t>(value & 255))
    _info_emit(buf, n, h, <uint8_t>(value >> 8))

# Telemetry-only Command attribution. These values never enter game state or hashing.
DEF MAX_COMMAND_DIAG_EVENTS = 128
cdef int COMMAND_DIAG_GAIN = 1
cdef int COMMAND_DIAG_DISCOUNT = 2
cdef int COMMAND_DIAG_FRONT_LOSS_PROTECTION = 3
cdef int COMMAND_DETAIL_COMPLETION_GAIN = 1
cdef int COMMAND_DETAIL_NARRATIVE_GAIN = 2
cdef int COMMAND_DETAIL_RETREAT_GAIN = 3
cdef int COMMAND_DETAIL_DISCARD_GAIN = 4
cdef int COMMAND_DETAIL_CATCHUP_DISCOUNT = 5
cdef int COMMAND_DETAIL_COMPLETION_DISCOUNT = 6
cdef int COMMAND_DETAIL_NARRATIVE_DISCOUNT = 7
cdef int COMMAND_DETAIL_LOCAL_FRONT_DISCOUNT = 8
cdef int COMMAND_DETAIL_ADJACENT_DISCOUNT = 9
cdef int COMMAND_DETAIL_FRONTLINE_DISCOUNT = 10
cdef int COMMAND_DETAIL_FREE_MANEUVER = 11
cdef int COMMAND_DETAIL_STRATAGEM_MANEUVER = 12
cdef int COMMAND_DETAIL_FRONT_LOSS_PROTECTED_FRONT = 13
cdef int COMMAND_DETAIL_FRONT_LOSS_STRATAGEM = 14
