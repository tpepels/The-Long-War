include "_fast_protocol.generated.pxi"

DEF POSITIONS_PER_PLAYER = FRONT_COUNT * RANK_COUNT
DEF SLOT_COUNT = PLAYER_COUNT * POSITIONS_PER_PLAYER
# Storage capacity is intentionally independent of the current rules limit.
DEF NARRATIVE_COUNT = PLAYER_COUNT * NARRATIVE_SLOTS_PER_PLAYER
DEF FRONT_MASK = (1 << FRONT_COUNT) - 1
DEF BATTLE_ONE_ACTIVE_FRONT_MASK = (1 << 1) | (1 << 2)
DEF BATTLE_TWO_ACTIVE_FRONT_MASK = BATTLE_ONE_ACTIVE_FRONT_MASK | (1 << 0)
DEF ALL_PLAYERS_MASK = (1 << PLAYER_COUNT) - 1

cdef inline uint8_t active_front_mask_for_battle(int battle) noexcept:
    if battle <= 1:
        return <uint8_t>BATTLE_ONE_ACTIVE_FRONT_MASK
    if battle == 2:
        return <uint8_t>BATTLE_TWO_ACTIVE_FRONT_MASK
    return <uint8_t>FRONT_MASK

cdef inline bint front_is_active(int battle, int front) noexcept:
    return bool(active_front_mask_for_battle(battle) & (1 << front))
DEF NEXT_OPERATION_TURN_OFFSET = 1

DEF FIRST_FRONT_INDEX = 0
DEF LAST_FRONT_INDEX = FRONT_COUNT - 1
DEF ADJACENT_FRONT_DISTANCE = 1
DEF ADJACENT_FRONT_PAIR_SIZE = 2
DEF ADJACENT_FRONT_PAIR_COUNT = FRONT_COUNT - ADJACENT_FRONT_PAIR_SIZE + 1
DEF ADJACENT_FRONT_PAIR_MASK = (1 << ADJACENT_FRONT_PAIR_SIZE) - 1
DEF THREE_FRONT_WINDOW_SIZE = 3
DEF ENCIRCLEMENT_LEFT_MASK = (1 << THREE_FRONT_WINDOW_SIZE) - 1
DEF ENCIRCLEMENT_RIGHT_MASK = (
    ENCIRCLEMENT_LEFT_MASK << (FRONT_COUNT - THREE_FRONT_WINDOW_SIZE)
)
DEF ENCIRCLEMENT_LEFT_TARGET_FRONT = FIRST_FRONT_INDEX + 1
DEF ENCIRCLEMENT_RIGHT_TARGET_FRONT = LAST_FRONT_INDEX - 1
DEF COMBINED_FRONT_SELECTION_COUNT = 2
DEF SINGLE_CARD_DISCARD_COUNT = 1
DEF COPIES_REQUIRED_TO_PLAY_AND_DISCARD_SAME_CARD = 2

DEF HIDDEN_KNOWN_SINGLE_CARD = 0
DEF HIDDEN_KNOWN_ONGOING_NARRATIVE = 1
DEF HIDDEN_KNOWN_STRATAGEM = 2

DEF PRE_RESOLUTION_CONTROLLER_END = PLAYER_COUNT
DEF PRE_RESOLUTION_RETREAT_END = PRE_RESOLUTION_CONTROLLER_END + SLOT_COUNT
DEF PRE_RESOLUTION_CONTRIBUTION_END = PRE_RESOLUTION_RETREAT_END + SLOT_COUNT
DEF PRE_RESOLUTION_SUPPRESSION_END = PRE_RESOLUTION_CONTRIBUTION_END + SLOT_COUNT
DEF PRE_RESOLUTION_SACRIFICE_END = PRE_RESOLUTION_SUPPRESSION_END + SLOT_COUNT

DEF MAX_CARDS = 127
# A legal deck may contain four copies of every non-Unique card. Size native
# card zones for the full wire-format card pool rather than imposing a hidden
# 254-card deck rule.
DEF MAX_DECK = MAX_CARDS * 4
DEF MAX_ACTIONS = 1024
DEF INFORMATION_KEY_VERSION = 14

DEF U16_BYTES = 2
DEF U32_BYTES = 4
DEF INFO_PLAYER_BASE_BYTES = 6
DEF INFO_PLAYER_SEARCH_EXTRA_BYTES = 3
DEF INFO_TURN_FLOW_BYTES = 2
DEF INFO_PENDING_EFFECT_BYTES = 14
DEF INFO_PENDING_RESUME_BYTES = 2
DEF INFO_MANEUVER_COUNT_BYTES = PLAYER_COUNT * U16_BYTES
DEF INFO_CONSTRAINT_BYTES = 12
DEF INFO_RESOLUTION_FIXED_BYTES = 17
DEF INFO_BOARD_SLOT_BASE_BYTES = 5
DEF INFO_NARRATIVE_SEARCH_BYTES = 5
DEF INFO_STRATAGEM_SEARCH_BYTES = 7

DEF MAX_RECOVERY_SCHEDULE = 32
DEF MAX_PENDING_EFFECTS = 32
DEF MAX_CONSTRAINTS = 16
DEF NONE = -1

# Packed action wire format. Keep shifts/masks here so layout changes are atomic.
DEF ACTION_KIND_SHIFT = 0
DEF ACTION_KIND_BITS = 4
DEF ACTION_CARD_SHIFT = ACTION_KIND_SHIFT + ACTION_KIND_BITS
DEF ACTION_CARD_BITS = 7
DEF ACTION_POSITION_SHIFT = ACTION_CARD_SHIFT + ACTION_CARD_BITS
DEF ACTION_POSITION_BITS = 5
DEF ACTION_DESTINATION_SHIFT = ACTION_POSITION_SHIFT + ACTION_POSITION_BITS
DEF ACTION_DESTINATION_BITS = 5
DEF ACTION_PLAYER_SHIFT = ACTION_DESTINATION_SHIFT + ACTION_DESTINATION_BITS
DEF ACTION_PLAYER_BITS = 1
DEF ACTION_EXTRA_SHIFT = ACTION_PLAYER_SHIFT + ACTION_PLAYER_BITS
DEF ACTION_SENTINEL_OFFSET = 1

DEF ACTION_KIND_MASK = (1 << ACTION_KIND_BITS) - 1
DEF ACTION_CARD_MASK = (1 << ACTION_CARD_BITS) - 1
DEF ACTION_POSITION_MASK = (1 << ACTION_POSITION_BITS) - 1
DEF ACTION_DESTINATION_MASK = (1 << ACTION_DESTINATION_BITS) - 1
DEF ACTION_PLAYER_MASK = (1 << ACTION_PLAYER_BITS) - 1

DEF BYTE_MASK = 0xFF
DEF U16_MASK = 0xFFFF
DEF FNV64_OFFSET_BASIS = 0xCBF29CE484222325
DEF ALT_HASH_OFFSET_BASIS = 0x84222325CBF29CE4
DEF FNV64_PRIME = 0x100000001B3
DEF ALT_HASH_PRIME = 0xC2B2AE3D27D4EB4F
DEF ALT_HASH_MIX_SHIFT = 29

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
cdef int TYPE_CYCLE = 13
cdef int TYPE_END_TURN = 14

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
cdef int CONSTRAINT_DISCARD_SOURCE_NARRATIVE = 16
cdef int CONSTRAINT_EXPIRES_END_OF_ACTIVATED_TURN = 32

cdef inline int other_player(int player) noexcept:
    return (player + 1) % PLAYER_COUNT


cdef inline int slot_index(int player, int front, int rank) noexcept:
    return player * POSITIONS_PER_PLAYER + front * RANK_COUNT + rank

cdef inline int owner_from_slot(int slot) noexcept:
    return slot // POSITIONS_PER_PLAYER

cdef inline int local_slot(int slot) noexcept:
    return slot % POSITIONS_PER_PLAYER

cdef inline int front_from_slot(int slot) noexcept:
    return local_slot(slot) // RANK_COUNT

cdef inline int rank_from_slot(int slot) noexcept:
    return local_slot(slot) % RANK_COUNT

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
        <uint64_t>(kind & ACTION_KIND_MASK)
        | (
            <uint64_t>(card + ACTION_SENTINEL_OFFSET)
            << ACTION_CARD_SHIFT
        )
        | (
            <uint64_t>(pos + ACTION_SENTINEL_OFFSET)
            << ACTION_POSITION_SHIFT
        )
        | (
            <uint64_t>(dest + ACTION_SENTINEL_OFFSET)
            << ACTION_DESTINATION_SHIFT
        )
        | (
            <uint64_t>(player & ACTION_PLAYER_MASK)
            << ACTION_PLAYER_SHIFT
        )
        | (<uint64_t>extra << ACTION_EXTRA_SHIFT)
    )

cdef inline int action_kind(uint64_t action) noexcept:
    return <int>((action >> ACTION_KIND_SHIFT) & ACTION_KIND_MASK)

cdef inline int action_card(uint64_t action) noexcept:
    return <int>((action >> ACTION_CARD_SHIFT) & ACTION_CARD_MASK) - ACTION_SENTINEL_OFFSET

cdef inline int action_pos(uint64_t action) noexcept:
    return <int>((action >> ACTION_POSITION_SHIFT) & ACTION_POSITION_MASK) - ACTION_SENTINEL_OFFSET

cdef inline int action_dest(uint64_t action) noexcept:
    return <int>((action >> ACTION_DESTINATION_SHIFT) & ACTION_DESTINATION_MASK) - ACTION_SENTINEL_OFFSET

cdef inline int action_player(uint64_t action) noexcept:
    return <int>((action >> ACTION_PLAYER_SHIFT) & ACTION_PLAYER_MASK)


cdef inline uint32_t action_extra(uint64_t action) noexcept:
    return <uint32_t>(action >> ACTION_EXTRA_SHIFT)


cdef struct InfoHash128:
    uint64_t a
    uint64_t b


cdef inline void _info_hash_init(InfoHash128* h) noexcept:
    h.a = <uint64_t>FNV64_OFFSET_BASIS
    h.b = <uint64_t>ALT_HASH_OFFSET_BASIS


cdef inline void _info_hash_feed(InfoHash128* h, uint8_t value) noexcept:
    h.a ^= <uint64_t>value
    h.a *= <uint64_t>FNV64_PRIME
    h.b ^= <uint64_t>value
    h.b *= <uint64_t>ALT_HASH_PRIME
    h.b ^= h.b >> ALT_HASH_MIX_SHIFT


cdef inline void _info_hash_feed_u16(
    InfoHash128* h,
    uint16_t value,
) noexcept:
    _info_hash_feed(h, <uint8_t>(value & BYTE_MASK))
    _info_hash_feed(h, <uint8_t>((value >> 8) & 255))


cdef inline void _info_hash_feed_u32(
    InfoHash128* h,
    uint32_t value,
) noexcept:
    _info_hash_feed_u16(h, <uint16_t>(value & U16_MASK))
    _info_hash_feed_u16(h, <uint16_t>((value >> 16) & U16_MASK))


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
    _info_emit(buf, n, h, <uint8_t>(value & BYTE_MASK))
    _info_emit(buf, n, h, <uint8_t>(value >> 8))

cdef inline void _info_emit_u32(
    unsigned char* buf, int* n, InfoHash128* h, uint32_t value,
) noexcept:
    _info_emit_u16(buf, n, h, <uint16_t>(value & U16_MASK))
    _info_emit_u16(buf, n, h, <uint16_t>((value >> 16) & U16_MASK))

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
