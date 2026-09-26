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

DEF MAX_CARDS = 127
DEF MAX_DECK = 254
DEF SLOT_COUNT = 16
DEF SCHEME_COUNT = 8
DEF MAX_ACTIONS = 1024
DEF MAX_RECOVERY_SCHEDULE = 32
DEF NONE = -1

cdef int PHASE_BATTLE = 0
cdef int PHASE_COMPLETE = 2

cdef int TYPE_PASS = 0
cdef int TYPE_SUBJECT = 2
cdef int TYPE_LINK = 3
cdef int TYPE_NAME = 4
cdef int TYPE_PLOT = 5
cdef int TYPE_SCHEME = 6
cdef int TYPE_STRATAGEM = 7
cdef int TYPE_DISCARD = 10
cdef int TYPE_MANEUVER = 11

cdef int CARD_SUBJECT = 1
cdef int CARD_LINK = 2
cdef int CARD_NAME = 3
cdef int CARD_PLOT = 4
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
cdef int NAME_REVEAL_SCHEME = 2

cdef int COMPLETE_NONE = 0
cdef int COMPLETE_GAIN_COMMAND = 1
cdef int COMPLETE_DRAW = 3
cdef int COMPLETE_REVEAL_SCHEME = 4
cdef int COMPLETE_RECOVER_LINK = 5

cdef int PLOT_NONE = 0
cdef int PLOT_DISCREDIT = 1
cdef int PLOT_RETURN_NAME = 2
cdef int PLOT_MOVE_SUBJECT = 3

cdef int EVENT_NONE = 0
cdef int EVENT_SUBJECT = 1
cdef int EVENT_LINK = 2
cdef int EVENT_PASS = 3
cdef int EVENT_PLOT_TARGET = 4
cdef int EVENT_IMMEDIATE_STORY = 5
cdef int EVENT_NAME = 6

cdef int SCHEME_NONE = 0
cdef int SCHEME_PENALIZE_SUBJECT = 1
cdef int SCHEME_DISCARD_LINK = 2
cdef int SCHEME_REINFORCE = 3

cdef int STRAT_REVEAL_NONE = 0
cdef int STRAT_REVEAL_PENALIZE = 1

cdef int ACTOR_EITHER = 0
cdef int ACTOR_OPPONENT = 1
cdef int ACTOR_CONTROLLER = 2

cdef int STORY_CHOICE_NONE = 0
cdef int STORY_CHOICE_FRONT = 1
cdef int STORY_CHOICE_NAMED_FORMATION = 2

cdef int NARR_TRIGGER_NONE = 0
cdef int NARR_TRIGGER_FRIENDLY_NAMED = 1
cdef int NARR_TRIGGER_FRIENDLY_RETREAT = 2
cdef int NARR_TRIGGER_OPPONENT_NAMED = 3
cdef int NARR_TRIGGER_OPPONENT_BOTH_RANKS = 4

cdef int STRAT_CHOICE_NONE = 0
cdef int STRAT_CHOICE_FRONT = 1
cdef int STRAT_CHOICE_ADJACENT_FRONTS = 2
cdef int STRAT_CHOICE_EDGE_FRONT = 3
cdef int STRAT_CHOICE_DIRECTION = 4
cdef int STRAT_CHOICE_WHEEL = 5
cdef int STRAT_CHOICE_RESERVES = 6

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


cdef class FastState:
    cdef int8_t deck[2][MAX_DECK]
    cdef uint8_t deck_len[2]
    cdef uint8_t deck_counts[2][MAX_CARDS]
    cdef uint8_t hand[2][MAX_CARDS]
    cdef uint8_t hand_len[2]
    cdef int8_t discard[2][MAX_DECK]
    cdef uint8_t discard_len[2]

    cdef int8_t subject[SLOT_COUNT]
    cdef int8_t link[SLOT_COUNT]
    cdef int8_t name[SLOT_COUNT]
    cdef int16_t temporary[SLOT_COUNT]
    cdef uint8_t maneuver_count[SLOT_COUNT]

    cdef int8_t scheme[SCHEME_COUNT]
    cdef uint8_t scheme_revealed[SCHEME_COUNT]
    cdef uint8_t scheme_front_mask[SCHEME_COUNT]
    cdef int8_t scheme_target_slot[SCHEME_COUNT]
    cdef uint8_t scheme_used[SCHEME_COUNT]
    cdef int8_t stratagem[2]
    cdef uint8_t stratagem_revealed[2]
    cdef uint8_t stratagem_front_mask[2]
    cdef uint8_t stratagem_direction[2]
    cdef uint16_t stratagem_target_mask[2]
    cdef uint8_t stratagem_used[2]
    cdef uint8_t hero_used[2]

    cdef uint8_t known_hidden[2][2][MAX_CARDS]

    cdef uint8_t passed[2]
    cdef int8_t pass_order[2]
    cdef uint8_t pass_len
    cdef uint8_t discarded_this_battle[2]
    cdef int16_t command[2]
    cdef uint16_t operations_this_battle[2]
    cdef uint8_t cards_played_this_turn_front_mask[2]
    cdef uint8_t cards_played_this_battle_front_mask[2]
    cdef uint8_t narratives_played_this_battle[2]
    cdef int16_t command_spent_this_battle[2]
    cdef int16_t command_refunded_this_battle[2]
    cdef int16_t battle_start_command[2]
    cdef int16_t battle_start_hand_size[2]
    cdef int16_t cards_drawn_this_battle[2]
    cdef int16_t completion_count_this_battle[2]
    cdef int16_t deck_reshuffles[2]
    cdef int16_t reshuffle_card_totals[2]
    cdef int16_t reshuffle_hand_card_totals[2]
    cdef uint8_t last_battle_valid
    cdef int16_t last_battle
    cdef int16_t last_front_scores[4][2]
    cdef int16_t last_command_start[2]
    cdef int16_t last_command_spent[2]
    cdef int16_t last_command_refunded[2]
    cdef int16_t last_command_remaining[2]
    cdef int16_t last_deck_remaining[2]
    cdef int16_t last_hand_size[2]
    cdef int16_t last_battle_start_hand_size[2]
    cdef int16_t last_cards_drawn[2]
    cdef int16_t last_completion_count[2]
    cdef int16_t last_operations[2]
    cdef int8_t last_pass_order[2]
    cdef uint8_t last_pass_len
    cdef uint8_t cleanup_pending
    cdef uint8_t pending_draw_count
    cdef uint8_t pending_draw_finish_operation

    cdef int8_t active_player
    cdef int16_t battle
    cdef int8_t phase
    cdef int8_t winner
    cdef int32_t turn_number
    cdef uint32_t shuffle_seed

    def __cinit__(self):
        memset(self.deck, 0xff, sizeof(self.deck))
        memset(self.deck_len, 0, sizeof(self.deck_len))
        memset(self.deck_counts, 0, sizeof(self.deck_counts))
        memset(self.hand, 0, sizeof(self.hand))
        memset(self.hand_len, 0, sizeof(self.hand_len))
        memset(self.discard, 0xff, sizeof(self.discard))
        memset(self.discard_len, 0, sizeof(self.discard_len))
        memset(self.subject, 0xff, sizeof(self.subject))
        memset(self.link, 0xff, sizeof(self.link))
        memset(self.name, 0xff, sizeof(self.name))
        memset(self.temporary, 0, sizeof(self.temporary))
        memset(self.maneuver_count, 0, sizeof(self.maneuver_count))
        memset(self.scheme, 0xff, sizeof(self.scheme))
        memset(self.scheme_revealed, 0, sizeof(self.scheme_revealed))
        memset(self.scheme_front_mask, 0, sizeof(self.scheme_front_mask))
        memset(self.scheme_target_slot, 0xff, sizeof(self.scheme_target_slot))
        memset(self.scheme_used, 0, sizeof(self.scheme_used))
        memset(self.stratagem, 0xff, sizeof(self.stratagem))
        memset(self.stratagem_revealed, 0, sizeof(self.stratagem_revealed))
        memset(self.stratagem_front_mask, 0, sizeof(self.stratagem_front_mask))
        memset(self.stratagem_direction, 0, sizeof(self.stratagem_direction))
        memset(self.stratagem_target_mask, 0, sizeof(self.stratagem_target_mask))
        memset(self.stratagem_used, 0, sizeof(self.stratagem_used))
        memset(self.hero_used, 0, sizeof(self.hero_used))
        memset(self.known_hidden, 0, sizeof(self.known_hidden))
        memset(self.passed, 0, sizeof(self.passed))
        memset(self.pass_order, 0xff, sizeof(self.pass_order))
        memset(self.discarded_this_battle, 0, sizeof(self.discarded_this_battle))
        memset(self.command, 0, sizeof(self.command))
        memset(self.operations_this_battle, 0, sizeof(self.operations_this_battle))
        memset(self.cards_played_this_turn_front_mask, 0, sizeof(self.cards_played_this_turn_front_mask))
        memset(self.cards_played_this_battle_front_mask, 0, sizeof(self.cards_played_this_battle_front_mask))
        memset(self.narratives_played_this_battle, 0, sizeof(self.narratives_played_this_battle))
        memset(self.command_spent_this_battle, 0, sizeof(self.command_spent_this_battle))
        memset(self.command_refunded_this_battle, 0, sizeof(self.command_refunded_this_battle))
        memset(self.battle_start_command, 0, sizeof(self.battle_start_command))
        memset(self.battle_start_hand_size, 0, sizeof(self.battle_start_hand_size))
        memset(self.cards_drawn_this_battle, 0, sizeof(self.cards_drawn_this_battle))
        memset(self.completion_count_this_battle, 0, sizeof(self.completion_count_this_battle))
        memset(self.deck_reshuffles, 0, sizeof(self.deck_reshuffles))
        memset(self.reshuffle_card_totals, 0, sizeof(self.reshuffle_card_totals))
        memset(self.reshuffle_hand_card_totals, 0, sizeof(self.reshuffle_hand_card_totals))
        self.last_battle_valid = 0
        self.last_battle = 0
        memset(self.last_front_scores, 0, sizeof(self.last_front_scores))
        memset(self.last_command_start, 0, sizeof(self.last_command_start))
        memset(self.last_command_spent, 0, sizeof(self.last_command_spent))
        memset(self.last_command_refunded, 0, sizeof(self.last_command_refunded))
        memset(self.last_command_remaining, 0, sizeof(self.last_command_remaining))
        memset(self.last_deck_remaining, 0, sizeof(self.last_deck_remaining))
        memset(self.last_hand_size, 0, sizeof(self.last_hand_size))
        memset(self.last_battle_start_hand_size, 0, sizeof(self.last_battle_start_hand_size))
        memset(self.last_cards_drawn, 0, sizeof(self.last_cards_drawn))
        memset(self.last_completion_count, 0, sizeof(self.last_completion_count))
        memset(self.last_operations, 0, sizeof(self.last_operations))
        memset(self.last_pass_order, 0xff, sizeof(self.last_pass_order))
        self.last_pass_len = 0
        self.cleanup_pending = 0
        self.pending_draw_count = 0
        self.pending_draw_finish_operation = 0
        self.pass_len = 0
        self.active_player = 0
        self.battle = 1
        self.phase = PHASE_BATTLE
        self.winner = -1
        self.turn_number = 0
        self.shuffle_seed = 0

    cdef void copy_from_fast(self, FastState other) noexcept:
        memcpy(self.deck, other.deck, sizeof(self.deck))
        memcpy(self.deck_len, other.deck_len, sizeof(self.deck_len))
        memcpy(self.deck_counts, other.deck_counts, sizeof(self.deck_counts))
        memcpy(self.hand, other.hand, sizeof(self.hand))
        memcpy(self.hand_len, other.hand_len, sizeof(self.hand_len))
        memcpy(self.discard, other.discard, sizeof(self.discard))
        memcpy(self.discard_len, other.discard_len, sizeof(self.discard_len))
        memcpy(self.subject, other.subject, sizeof(self.subject))
        memcpy(self.link, other.link, sizeof(self.link))
        memcpy(self.name, other.name, sizeof(self.name))
        memcpy(self.temporary, other.temporary, sizeof(self.temporary))
        memcpy(self.maneuver_count, other.maneuver_count, sizeof(self.maneuver_count))
        memcpy(self.scheme, other.scheme, sizeof(self.scheme))
        memcpy(self.scheme_revealed, other.scheme_revealed, sizeof(self.scheme_revealed))
        memcpy(self.scheme_front_mask, other.scheme_front_mask, sizeof(self.scheme_front_mask))
        memcpy(self.scheme_target_slot, other.scheme_target_slot, sizeof(self.scheme_target_slot))
        memcpy(self.scheme_used, other.scheme_used, sizeof(self.scheme_used))
        memcpy(self.stratagem, other.stratagem, sizeof(self.stratagem))
        memcpy(self.stratagem_revealed, other.stratagem_revealed, sizeof(self.stratagem_revealed))
        memcpy(self.stratagem_front_mask, other.stratagem_front_mask, sizeof(self.stratagem_front_mask))
        memcpy(self.stratagem_direction, other.stratagem_direction, sizeof(self.stratagem_direction))
        memcpy(self.stratagem_target_mask, other.stratagem_target_mask, sizeof(self.stratagem_target_mask))
        memcpy(self.stratagem_used, other.stratagem_used, sizeof(self.stratagem_used))
        memcpy(self.hero_used, other.hero_used, sizeof(self.hero_used))
        memcpy(self.known_hidden, other.known_hidden, sizeof(self.known_hidden))
        memcpy(self.passed, other.passed, sizeof(self.passed))
        memcpy(self.pass_order, other.pass_order, sizeof(self.pass_order))
        memcpy(self.discarded_this_battle, other.discarded_this_battle, sizeof(self.discarded_this_battle))
        memcpy(self.command, other.command, sizeof(self.command))
        memcpy(self.operations_this_battle, other.operations_this_battle, sizeof(self.operations_this_battle))
        memcpy(self.cards_played_this_turn_front_mask, other.cards_played_this_turn_front_mask, sizeof(self.cards_played_this_turn_front_mask))
        memcpy(self.cards_played_this_battle_front_mask, other.cards_played_this_battle_front_mask, sizeof(self.cards_played_this_battle_front_mask))
        memcpy(self.narratives_played_this_battle, other.narratives_played_this_battle, sizeof(self.narratives_played_this_battle))
        memcpy(self.command_spent_this_battle, other.command_spent_this_battle, sizeof(self.command_spent_this_battle))
        memcpy(self.command_refunded_this_battle, other.command_refunded_this_battle, sizeof(self.command_refunded_this_battle))
        memcpy(self.battle_start_command, other.battle_start_command, sizeof(self.battle_start_command))
        memcpy(self.battle_start_hand_size, other.battle_start_hand_size, sizeof(self.battle_start_hand_size))
        memcpy(self.cards_drawn_this_battle, other.cards_drawn_this_battle, sizeof(self.cards_drawn_this_battle))
        memcpy(self.completion_count_this_battle, other.completion_count_this_battle, sizeof(self.completion_count_this_battle))
        memcpy(self.deck_reshuffles, other.deck_reshuffles, sizeof(self.deck_reshuffles))
        memcpy(self.reshuffle_card_totals, other.reshuffle_card_totals, sizeof(self.reshuffle_card_totals))
        memcpy(self.reshuffle_hand_card_totals, other.reshuffle_hand_card_totals, sizeof(self.reshuffle_hand_card_totals))
        self.last_battle_valid = other.last_battle_valid
        self.last_battle = other.last_battle
        memcpy(self.last_front_scores, other.last_front_scores, sizeof(self.last_front_scores))
        memcpy(self.last_command_start, other.last_command_start, sizeof(self.last_command_start))
        memcpy(self.last_command_spent, other.last_command_spent, sizeof(self.last_command_spent))
        memcpy(self.last_command_refunded, other.last_command_refunded, sizeof(self.last_command_refunded))
        memcpy(self.last_command_remaining, other.last_command_remaining, sizeof(self.last_command_remaining))
        memcpy(self.last_deck_remaining, other.last_deck_remaining, sizeof(self.last_deck_remaining))
        memcpy(self.last_hand_size, other.last_hand_size, sizeof(self.last_hand_size))
        memcpy(self.last_battle_start_hand_size, other.last_battle_start_hand_size, sizeof(self.last_battle_start_hand_size))
        memcpy(self.last_cards_drawn, other.last_cards_drawn, sizeof(self.last_cards_drawn))
        memcpy(self.last_completion_count, other.last_completion_count, sizeof(self.last_completion_count))
        memcpy(self.last_operations, other.last_operations, sizeof(self.last_operations))
        memcpy(self.last_pass_order, other.last_pass_order, sizeof(self.last_pass_order))
        self.last_pass_len = other.last_pass_len
        self.cleanup_pending = other.cleanup_pending
        self.pending_draw_count = other.pending_draw_count
        self.pending_draw_finish_operation = other.pending_draw_finish_operation
        self.pass_len = other.pass_len
        self.active_player = other.active_player
        self.battle = other.battle
        self.phase = other.phase
        self.winner = other.winner
        self.turn_number = other.turn_number
        self.shuffle_seed = other.shuffle_seed

    cdef FastState clone_fast(self):
        cdef FastState other = FastState()
        other.copy_from_fast(self)
        return other

    cpdef FastState clone(self):
        return self.clone_fast()

    cpdef copy_from(self, FastState other):
        self.copy_from_fast(other)


cdef class FastEngine:
    cdef public object card_ids
    cdef public object id_to_code
    cdef int n_cards
    cdef int opening_hand_size
    cdef int command_cap
    cdef object command_recovery_schedule
    cdef int32_t command_recovery_values[MAX_RECOVERY_SCHEDULE]
    cdef uint8_t command_recovery_len
    cdef int command_collapse_threshold
    cdef int maneuver_command_cost
    cdef int hand_limit
    cdef int ongoing_story_limit

    cdef int8_t card_type[MAX_CARDS]
    cdef int8_t card_command_cost[MAX_CARDS]
    cdef int8_t adjacent_command_discount[MAX_CARDS]
    cdef int8_t completion_effect[MAX_CARDS]
    cdef int8_t completion_amount[MAX_CARDS]
    cdef uint8_t complete_plot_protection[MAX_CARDS]
    cdef int8_t role[MAX_CARDS]
    cdef int8_t strength[MAX_CARDS]
    cdef int8_t name_strength[MAX_CARDS]
    cdef uint8_t hero[MAX_CARDS]
    cdef int8_t placement_rank[MAX_CARDS]
    cdef int8_t force_text_effect[MAX_CARDS]
    cdef int8_t force_text_amount[MAX_CARDS]
    cdef uint8_t can_maneuver_unnamed[MAX_CARDS]
    cdef uint8_t maneuver_requires_open_bond[MAX_CARDS]
    cdef uint8_t bond_maneuver_adjacent_hero[MAX_CARDS]
    cdef uint8_t force_breakthrough[MAX_CARDS]
    cdef uint8_t name_breakthrough[MAX_CARDS]
    cdef uint8_t first_maneuver_free[MAX_CARDS]
    cdef uint8_t first_maneuver_free_empty_front[MAX_CARDS]
    cdef uint8_t local_catchup_discount_name[MAX_CARDS]
    cdef uint8_t first_front_card_battle_discount_name[MAX_CARDS]
    cdef uint8_t first_narrative_battle_discount_force[MAX_CARDS]
    cdef int8_t narrative_maneuver_empty_gain[MAX_CARDS]
    cdef int8_t narrative_trigger[MAX_CARDS]
    cdef int8_t narrative_trigger_gain[MAX_CARDS]
    cdef uint8_t narrative_trigger_discard[MAX_CARDS]
    cdef uint8_t immobile_force[MAX_CARDS]
    cdef uint8_t cannot_swap_target[MAX_CARDS]
    cdef uint8_t catchup_zero_cost[MAX_CARDS]
    cdef int8_t completion_discount_cost[MAX_CARDS]
    cdef int8_t frontline_force_discount[MAX_CARDS]
    cdef uint8_t frontline_force_discount_requires_named[MAX_CARDS]
    cdef uint8_t recovery_protected_front[MAX_CARDS]
    cdef uint8_t driven_bond_stays[MAX_CARDS]
    cdef uint8_t driven_bond_returns[MAX_CARDS]
    cdef uint8_t driven_name_returns[MAX_CARDS]
    cdef int8_t retreat_command_gain[MAX_CARDS]
    cdef uint8_t combat_frontline_only[MAX_CARDS]
    cdef int8_t strat_maneuver_cost[MAX_CARDS]
    cdef uint8_t strat_unnamed_maneuver[MAX_CARDS]
    cdef uint8_t strat_tie_control[MAX_CARDS]
    cdef uint8_t strat_recovery_loss_reduction[MAX_CARDS]
    cdef uint8_t strat_no_retreat[MAX_CARDS]
    cdef uint8_t strat_combine_fronts[MAX_CARDS]
    cdef uint8_t strat_refuse_flank[MAX_CARDS]
    cdef uint8_t strat_encirclement[MAX_CARDS]
    cdef uint8_t strat_directional_maneuver[MAX_CARDS]
    cdef int8_t on_link_bonus[MAX_CARDS]
    cdef int8_t aura[MAX_CARDS]
    cdef int8_t aura_rank[MAX_CARDS]
    cdef int8_t subject_mod_amount[MAX_CARDS]
    cdef int8_t subject_mod_discard_min[MAX_CARDS]
    cdef uint8_t subject_mod_adj_named[MAX_CARDS]

    cdef int8_t link_bonus[MAX_CARDS]
    cdef int8_t link_named_bonus[MAX_CARDS]
    cdef int8_t link_discard_per[MAX_CARDS]
    cdef int8_t link_discard_max[MAX_CARDS]
    cdef int8_t link_opposing[MAX_CARDS]
    cdef uint8_t link_protect[MAX_CARDS]
    cdef uint8_t bond_move_on_play[MAX_CARDS]
    cdef int8_t bond_optional_extra_cost[MAX_CARDS]
    cdef int8_t bond_optional_draw_count[MAX_CARDS]
    cdef int8_t story_discard_count[MAX_CARDS]
    cdef int8_t story_discard_gain_command[MAX_CARDS]

    cdef int8_t name_rank_bonus_rank[MAX_CARDS]
    cdef int8_t name_rank_bonus_amount[MAX_CARDS]
    cdef int8_t name_effect[MAX_CARDS]

    cdef int8_t plot_effect[MAX_CARDS]
    cdef uint8_t veiled[MAX_CARDS]
    cdef uint8_t story_choice_kind[MAX_CARDS]
    cdef int8_t scheme_trigger[MAX_CARDS]
    cdef int8_t scheme_effect[MAX_CARDS]
    cdef int8_t scheme_amount[MAX_CARDS]
    cdef uint8_t scheme_requires_subject[MAX_CARDS]
    cdef int8_t scheme_face_bonus[MAX_CARDS]

    cdef uint8_t strat_choice_kind[MAX_CARDS]
    cdef int8_t strat_trigger_event[MAX_CARDS]
    cdef int8_t strat_actor[MAX_CARDS]
    cdef uint16_t strat_role_mask[MAX_CARDS]
    cdef uint8_t strat_rank_mask[MAX_CARDS]
    cdef int8_t strat_reveal_effect[MAX_CARDS]
    cdef int8_t strat_reveal_amount[MAX_CARDS]
    cdef uint8_t strat_cancel_story[MAX_CARDS]
    cdef int8_t strat_role_mod[MAX_CARDS][8]
    cdef int8_t strat_rank_mod[MAX_CARDS][2]
    cdef int8_t strat_controller_rank_mod[MAX_CARDS][2]
    cdef int8_t strat_named_mod[MAX_CARDS]
    cdef int8_t strat_unnamed_mod[MAX_CARDS]
    cdef uint8_t strat_story_lock[MAX_CARDS]
    cdef uint8_t strat_global_story_lock[MAX_CARDS]

    def __cinit__(self):
        self.command_recovery_len = 0
        memset(
            self.command_recovery_values,
            0,
            sizeof(self.command_recovery_values),
        )
        memset(self.card_type, 0, sizeof(self.card_type))
        memset(self.card_command_cost, 0, sizeof(self.card_command_cost))
        memset(self.adjacent_command_discount, 0, sizeof(self.adjacent_command_discount))
        memset(self.completion_effect, 0, sizeof(self.completion_effect))
        memset(self.completion_amount, 0, sizeof(self.completion_amount))
        memset(self.complete_plot_protection, 0, sizeof(self.complete_plot_protection))
        memset(self.role, 0, sizeof(self.role))
        memset(self.strength, 0, sizeof(self.strength))
        memset(self.name_strength, 0, sizeof(self.name_strength))
        memset(self.hero, 0, sizeof(self.hero))
        memset(self.placement_rank, 0xff, sizeof(self.placement_rank))
        memset(self.force_text_effect, 0, sizeof(self.force_text_effect))
        memset(self.force_text_amount, 0, sizeof(self.force_text_amount))
        memset(self.can_maneuver_unnamed, 0, sizeof(self.can_maneuver_unnamed))
        memset(self.maneuver_requires_open_bond, 0, sizeof(self.maneuver_requires_open_bond))
        memset(self.bond_maneuver_adjacent_hero, 0, sizeof(self.bond_maneuver_adjacent_hero))
        memset(self.force_breakthrough, 0, sizeof(self.force_breakthrough))
        memset(self.name_breakthrough, 0, sizeof(self.name_breakthrough))
        memset(self.first_maneuver_free, 0, sizeof(self.first_maneuver_free))
        memset(self.first_maneuver_free_empty_front, 0, sizeof(self.first_maneuver_free_empty_front))
        memset(self.local_catchup_discount_name, 0, sizeof(self.local_catchup_discount_name))
        memset(self.first_front_card_battle_discount_name, 0, sizeof(self.first_front_card_battle_discount_name))
        memset(self.first_narrative_battle_discount_force, 0, sizeof(self.first_narrative_battle_discount_force))
        memset(self.narrative_maneuver_empty_gain, 0, sizeof(self.narrative_maneuver_empty_gain))
        memset(self.narrative_trigger, 0, sizeof(self.narrative_trigger))
        memset(self.narrative_trigger_gain, 0, sizeof(self.narrative_trigger_gain))
        memset(self.narrative_trigger_discard, 0, sizeof(self.narrative_trigger_discard))
        memset(self.immobile_force, 0, sizeof(self.immobile_force))
        memset(self.cannot_swap_target, 0, sizeof(self.cannot_swap_target))
        memset(self.catchup_zero_cost, 0, sizeof(self.catchup_zero_cost))
        memset(self.completion_discount_cost, 0xff, sizeof(self.completion_discount_cost))
        memset(self.frontline_force_discount, 0, sizeof(self.frontline_force_discount))
        memset(self.frontline_force_discount_requires_named, 0, sizeof(self.frontline_force_discount_requires_named))
        memset(self.recovery_protected_front, 0, sizeof(self.recovery_protected_front))
        memset(self.driven_bond_stays, 0, sizeof(self.driven_bond_stays))
        memset(self.driven_bond_returns, 0, sizeof(self.driven_bond_returns))
        memset(self.driven_name_returns, 0, sizeof(self.driven_name_returns))
        memset(self.retreat_command_gain, 0, sizeof(self.retreat_command_gain))
        memset(self.combat_frontline_only, 0, sizeof(self.combat_frontline_only))
        memset(self.strat_maneuver_cost, 0xff, sizeof(self.strat_maneuver_cost))
        memset(self.strat_unnamed_maneuver, 0, sizeof(self.strat_unnamed_maneuver))
        memset(self.strat_tie_control, 0, sizeof(self.strat_tie_control))
        memset(self.strat_recovery_loss_reduction, 0, sizeof(self.strat_recovery_loss_reduction))
        memset(self.strat_no_retreat, 0, sizeof(self.strat_no_retreat))
        memset(self.strat_combine_fronts, 0, sizeof(self.strat_combine_fronts))
        memset(self.strat_refuse_flank, 0, sizeof(self.strat_refuse_flank))
        memset(self.strat_encirclement, 0, sizeof(self.strat_encirclement))
        memset(self.strat_directional_maneuver, 0, sizeof(self.strat_directional_maneuver))
        memset(self.on_link_bonus, 0, sizeof(self.on_link_bonus))
        memset(self.aura, 0, sizeof(self.aura))
        memset(self.aura_rank, 0xff, sizeof(self.aura_rank))
        memset(self.subject_mod_amount, 0, sizeof(self.subject_mod_amount))
        memset(self.subject_mod_discard_min, 0, sizeof(self.subject_mod_discard_min))
        memset(self.subject_mod_adj_named, 0, sizeof(self.subject_mod_adj_named))
        memset(self.link_bonus, 0, sizeof(self.link_bonus))
        memset(self.link_named_bonus, 0, sizeof(self.link_named_bonus))
        memset(self.link_discard_per, 0, sizeof(self.link_discard_per))
        memset(self.link_discard_max, 0, sizeof(self.link_discard_max))
        memset(self.link_opposing, 0, sizeof(self.link_opposing))
        memset(self.link_protect, 0, sizeof(self.link_protect))
        memset(self.bond_move_on_play, 0, sizeof(self.bond_move_on_play))
        memset(self.bond_optional_extra_cost, 0, sizeof(self.bond_optional_extra_cost))
        memset(self.bond_optional_draw_count, 0, sizeof(self.bond_optional_draw_count))
        memset(self.story_discard_count, 0, sizeof(self.story_discard_count))
        memset(self.story_discard_gain_command, 0, sizeof(self.story_discard_gain_command))
        memset(self.name_rank_bonus_rank, 0xff, sizeof(self.name_rank_bonus_rank))
        memset(self.name_rank_bonus_amount, 0, sizeof(self.name_rank_bonus_amount))
        memset(self.name_effect, 0, sizeof(self.name_effect))
        memset(self.plot_effect, 0, sizeof(self.plot_effect))
        memset(self.veiled, 0, sizeof(self.veiled))
        memset(self.story_choice_kind, 0, sizeof(self.story_choice_kind))
        memset(self.scheme_trigger, 0, sizeof(self.scheme_trigger))
        memset(self.scheme_effect, 0, sizeof(self.scheme_effect))
        memset(self.scheme_amount, 0, sizeof(self.scheme_amount))
        memset(self.scheme_requires_subject, 0, sizeof(self.scheme_requires_subject))
        memset(self.scheme_face_bonus, 0, sizeof(self.scheme_face_bonus))
        memset(self.strat_choice_kind, 0, sizeof(self.strat_choice_kind))
        memset(self.strat_trigger_event, 0, sizeof(self.strat_trigger_event))
        memset(self.strat_actor, 0, sizeof(self.strat_actor))
        memset(self.strat_role_mask, 0, sizeof(self.strat_role_mask))
        memset(self.strat_rank_mask, 0, sizeof(self.strat_rank_mask))
        memset(self.strat_reveal_effect, 0, sizeof(self.strat_reveal_effect))
        memset(self.strat_reveal_amount, 0, sizeof(self.strat_reveal_amount))
        memset(self.strat_cancel_story, 0, sizeof(self.strat_cancel_story))
        memset(self.strat_role_mod, 0, sizeof(self.strat_role_mod))
        memset(self.strat_rank_mod, 0, sizeof(self.strat_rank_mod))
        memset(self.strat_controller_rank_mod, 0, sizeof(self.strat_controller_rank_mod))
        memset(self.strat_named_mod, 0, sizeof(self.strat_named_mod))
        memset(self.strat_unnamed_mod, 0, sizeof(self.strat_unnamed_mod))
        memset(self.strat_story_lock, 0, sizeof(self.strat_story_lock))
        memset(self.strat_global_story_lock, 0, sizeof(self.strat_global_story_lock))

    def __init__(self, engine):
        cdef int code, r
        self.card_ids = tuple(engine.cards)
        self.n_cards = len(self.card_ids)
        self.opening_hand_size = int(engine.opening_hand_size)
        self.command_cap = int(engine.command_cap)
        self.command_recovery_schedule = tuple(engine.command_recovery_schedule)
        if len(self.command_recovery_schedule) > MAX_RECOVERY_SCHEDULE:
            raise ValueError(
                f"Command recovery schedule supports at most "
                f"{MAX_RECOVERY_SCHEDULE} entries"
            )
        self.command_recovery_len = len(self.command_recovery_schedule)
        for r in range(self.command_recovery_len):
            self.command_recovery_values[r] = int(
                self.command_recovery_schedule[r]
            )
        self.command_collapse_threshold = int(engine.command_collapse_threshold)
        self.maneuver_command_cost = int(engine.maneuver_command_cost)
        self.hand_limit = int(engine.hand_limit)
        self.ongoing_story_limit = int(engine.ongoing_story_limit)
        if self.n_cards > MAX_CARDS:
            raise ValueError(f"The native engine supports at most {MAX_CARDS} card identities")
        if max(engine.starting_command, self.command_cap) > 32767:
            raise ValueError("Command settings exceed the native signed 16-bit capacity")
        self.id_to_code = {card_id: i for i, card_id in enumerate(self.card_ids)}

        type_map = {"force": CARD_SUBJECT, "bond": CARD_LINK, "name": CARD_NAME, "story": CARD_PLOT, "stratagem": CARD_STRATAGEM}
        role_map = {"swordsman": ROLE_SWORDSMAN, "spearman": ROLE_SPEARMAN, "archer": ROLE_ARCHER, "healer": ROLE_HEALER, "ship": ROLE_SHIP, "stronghold": ROLE_STRONGHOLD}
        name_effect_map = {"move_adjacent_optional": NAME_MOVE_ADJACENT, "reveal_enemy_scheme": NAME_REVEAL_SCHEME}
        completion_effect_map = {
            "gain_command": COMPLETE_GAIN_COMMAND,
            "draw_card": COMPLETE_DRAW,
            "reveal_enemy_scheme": COMPLETE_REVEAL_SCHEME,
            "recover_recent_link": COMPLETE_RECOVER_LINK,
        }
        plot_effect_map = {"discredit_subject": PLOT_DISCREDIT, "return_name_or_weaken": PLOT_RETURN_NAME, "move_subject": PLOT_MOVE_SUBJECT}
        scheme_trigger_map = {"opponent_plays_subject": EVENT_SUBJECT, "opponent_plays_link": EVENT_LINK, "opponent_passes": EVENT_PASS, "opponent_plot_targets_your_card": EVENT_PLOT_TARGET}
        scheme_effect_map = {"penalize_played_subject": SCHEME_PENALIZE_SUBJECT, "discard_played_link": SCHEME_DISCARD_LINK, "reinforce_front": SCHEME_REINFORCE}
        strat_event_map = {"subject_played": EVENT_SUBJECT, "pass": EVENT_PASS, "immediate_story_played": EVENT_IMMEDIATE_STORY, "name_played": EVENT_NAME}
        actor_map = {"either": ACTOR_EITHER, "opponent": ACTOR_OPPONENT, "controller": ACTOR_CONTROLLER}
        rank_map = {"front": 0, "rear": 1}
        force_text_map = {
            "frontline_strength_bonus": FORCE_TEXT_FRONT_BONUS,
            "rear_strength_bonus": FORCE_TEXT_REAR_BONUS,
            "support_force_ahead_strength_bonus": FORCE_TEXT_SUPPORT_AHEAD,
            "frontline_strength_bonus_if_force_behind": FORCE_TEXT_FRONT_IF_REAR,
            "rear_strength_bonus_if_force_ahead": FORCE_TEXT_REAR_IF_FRONT,
        }

        for code, card_id in enumerate(self.card_ids):
            card = engine.cards[card_id]
            self.card_type[code] = type_map[card["type"]]
            self.role[code] = role_map.get(card.get("role"), ROLE_NONE)
            self.strength[code] = int(card.get("strength", 0))
            self.name_strength[code] = int(
                card.get(
                    "hero_name_strength",
                    card.get("strength", 0) if card["type"] == "name" else 0,
                )
            )
            self.hero[code] = bool(card.get("hero", False))
            rules = card.get("rules", {})
            design = card.get("design_rules") or {}
            force_design = design.get("force") or design
            self.card_command_cost[code] = int(card.get("command_cost", 0))
            self.adjacent_command_discount[code] = int(rules.get("adjacent_command_discount", 0))

            completion = rules.get("on_completion") or {}
            self.completion_effect[code] = completion_effect_map.get(completion.get("effect"), COMPLETE_NONE)
            self.completion_amount[code] = int(completion.get("amount", 1))
            if (
                design.get("trigger") == "friendly_formation_becomes_named"
                and design.get("scope") == "this_formation"
            ):
                if design.get("gain_command"):
                    self.completion_effect[code] = COMPLETE_GAIN_COMMAND
                    self.completion_amount[code] = int(design["gain_command"])
                elif design.get("draw_cards"):
                    self.completion_effect[code] = COMPLETE_DRAW
                    self.completion_amount[code] = int(design["draw_cards"])
            if design.get("command") == "completion_refund":
                completion_design = design.get("on_completion") or {}
                if completion_design.get("gain_command"):
                    self.completion_effect[code] = COMPLETE_GAIN_COMMAND
                    self.completion_amount[code] = int(completion_design["gain_command"])

            self.complete_plot_protection[code] = bool(rules.get("complete_protection_from_opponent_plot"))
            placement = (
                force_design.get("deploy_rank")
                or design.get("deploy_rank")
                or rules.get("placement", {}).get("rank")
            )
            self.placement_rank[code] = rank_map.get(placement, -1)
            printed_effect = force_design.get("printed_role_effect") or design.get("printed_role_effect")
            self.force_text_effect[code] = force_text_map.get(printed_effect, FORCE_TEXT_NONE)
            self.force_text_amount[code] = int(
                force_design.get("amount", design.get("amount", 0))
            )
            self.can_maneuver_unnamed[code] = bool(
                force_design.get("can_maneuver_while_unnamed")
                or design.get("can_maneuver_while_unnamed")
            )
            if design.get("build_around") == "open_bond":
                self.maneuver_requires_open_bond[code] = 1
            if design.get("build_around") == "hero_retinue":
                self.bond_maneuver_adjacent_hero[code] = 1
            if design.get("first_maneuver_each_battle_cost") == 0:
                self.first_maneuver_free[code] = 1
            if design.get("first_self_maneuver_each_battle_cost") == 0:
                self.first_maneuver_free_empty_front[code] = 1
            if design.get("command") == "local_catch_up_discount":
                self.local_catchup_discount_name[code] = int(
                    design.get("first_card_each_turn_discount", 1)
                )
            name_design = design.get("name") or {}
            if name_design.get("command") == "first_card_in_front_each_battle_discount_1_min_1":
                self.first_front_card_battle_discount_name[code] = 1
            if force_design.get("story") == "first_story_each_battle_discount_1_min_1":
                self.first_narrative_battle_discount_force[code] = 1
            if force_design.get("combat") == "breakthrough":
                self.force_breakthrough[code] = 1
            name_design = design.get("name") or {}
            if name_design.get("combat") == "breakthrough_if_opponent_no_rear_force":
                self.name_breakthrough[code] = 1
            self.immobile_force[code] = bool(
                force_design.get("immobile") or design.get("immobile")
            )
            self.cannot_swap_target[code] = bool(
                force_design.get("cannot_be_swap_target")
                or design.get("cannot_be_swap_target")
            )
            if design.get("command") == "catch_up_discount":
                self.catchup_zero_cost[code] = 1
            if design.get("command") == "completion_discount":
                self.completion_discount_cost[code] = int(
                    design.get("discounted_cost", card.get("command_cost", 0))
                )
            if design.get("persistence") == "rear_rebuild_cost_reduction":
                self.frontline_force_discount[code] = 1
                self.frontline_force_discount_requires_named[code] = 1
            if force_design.get("command") == "frontline_force_discount_1_min_1":
                self.frontline_force_discount[code] = 1
            if force_design.get("command") == "lost_front_here_does_not_reduce_recovery":
                self.recovery_protected_front[code] = 1
            if design.get("persistence") == "inherited_bond":
                self.driven_bond_stays[code] = 1
            if design.get("persistence") == "bond_returns_to_hand_when_force_driven_off":
                self.driven_bond_returns[code] = 1
            if (
                design.get("persistence") == "name_returns_to_hand_when_formation_driven_off"
                or (design.get("name") or {}).get("effect") == "return_hero_to_hand_if_driven_off"
            ):
                self.driven_name_returns[code] = 1
            if design.get("persistence") == "retreat_command_compensation":
                self.retreat_command_gain[code] = int(design.get("amount", 1))
            if design.get("combat") == "frontline_only_comparison":
                self.combat_frontline_only[code] = 1
            if design.get("combat") == "tie_control":
                self.strat_tie_control[code] = 1
            if design.get("command") == "high_cost_battle_investment":
                self.strat_maneuver_cost[code] = int(design.get("maneuver_cost", -1))
                self.strat_unnamed_maneuver[code] = bool(
                    design.get("unnamed_formations_can_maneuver")
                )
            if design.get("command") == "improve_recovery":
                self.strat_recovery_loss_reduction[code] = max(
                    0, -int(design.get("lost_front_adjustment", 0))
                )
            if design.get("stratagem") == "no_retreat_front":
                self.strat_no_retreat[code] = 1
            if design.get("stratagem") == "combine_two_adjacent_fronts":
                self.strat_combine_fronts[code] = 1
            if design.get("stratagem") == "refuse_flank":
                self.strat_refuse_flank[code] = 1
            if design.get("stratagem") == "encirclement":
                self.strat_encirclement[code] = 1
            if design.get("stratagem") == "battle_turns_direction":
                self.strat_directional_maneuver[code] = 1

            self.on_link_bonus[code] = int(rules.get("on_link_attached", {}).get("temporary_strength", 0))
            self.aura[code] = int(rules.get("adjacent_strength_aura", 0))
            self.aura_rank[code] = rank_map.get(rules.get("aura_requires_rank"), -1)
            modifiers = rules.get("strength_modifiers", ())
            if modifiers:
                modifier = modifiers[0]
                condition = modifier.get("when", {})
                self.subject_mod_amount[code] = int(modifier.get("amount", 0))
                self.subject_mod_discard_min[code] = int(condition.get("own_discard_at_least", 0))
                self.subject_mod_adj_named[code] = bool(condition.get("adjacent_subject_has_name"))

            self.link_bonus[code] = int(
                design.get("strength_bonus", rules.get("strength_bonus", 0))
            )
            self.link_named_bonus[code] = int(
                design.get(
                    "named_additional_strength_bonus",
                    rules.get("named_strength_bonus", 0),
                )
            )
            discard_bonus = rules.get("discard_strength_bonus") or {}
            self.link_discard_per[code] = int(discard_bonus.get("per_card", 0))
            self.link_discard_max[code] = int(discard_bonus.get("maximum", 0))
            self.link_opposing[code] = int(rules.get("opposing_front_modifier", 0))
            self.link_protect[code] = bool(rules.get("protect_subject_from_opponent_plot"))
            on_play_bond = design.get("on_play_onto_force") or {}
            if on_play_bond.get("effect") == "optional_move_formation_adjacent_empty_position":
                self.bond_move_on_play[code] = 1
            if design.get("command") == "optional_extra_payment":
                self.bond_optional_extra_cost[code] = int(
                    design.get("extra_cost", 0)
                )
                if design.get("effect") == "draw_2":
                    self.bond_optional_draw_count[code] = 2
            if design.get("command") == "card_for_command":
                self.story_discard_count[code] = int(
                    design.get("discard_cards", 0)
                )
                self.story_discard_gain_command[code] = int(
                    design.get("gain_command", 0)
                )

            rank_bonus = rules.get("rank_strength_bonus") or {}
            self.name_rank_bonus_rank[code] = rank_map.get(rank_bonus.get("rank"), -1)
            self.name_rank_bonus_amount[code] = int(rank_bonus.get("amount", 0))
            self.name_effect[code] = name_effect_map.get(rules.get("on_name_attached"), NAME_NONE)

            self.plot_effect[code] = plot_effect_map.get(rules.get("effect"), PLOT_NONE)
            self.veiled[code] = bool(card.get("ongoing", False))
            if design.get("placement") == "chosen_front":
                self.story_choice_kind[code] = STORY_CHOICE_FRONT
            elif design.get("placement") == "chosen_named_formation":
                self.story_choice_kind[code] = STORY_CHOICE_NAMED_FORMATION
            if design.get("trigger") == "first_friendly_maneuver_into_empty_each_battle":
                self.narrative_maneuver_empty_gain[code] = int(
                    design.get("gain_command", 0)
                )
            if design.get("trigger") == "friendly_formation_becomes_named":
                self.narrative_trigger[code] = NARR_TRIGGER_FRIENDLY_NAMED
            elif design.get("trigger") == "friendly_named_formation_retreats":
                self.narrative_trigger[code] = NARR_TRIGGER_FRIENDLY_RETREAT
            elif design.get("trigger") == "opposing_formation_becomes_named":
                self.narrative_trigger[code] = NARR_TRIGGER_OPPONENT_NAMED
            elif design.get("trigger") == "opponent_has_force_in_both_ranks_same_front":
                self.narrative_trigger[code] = NARR_TRIGGER_OPPONENT_BOTH_RANKS
            self.narrative_trigger_gain[code] = int(
                design.get("gain_command", 0)
            )
            self.narrative_trigger_discard[code] = bool(
                design.get("discard_self", False)
            )
            scheme = rules.get("scheme") or {}
            self.scheme_trigger[code] = scheme_trigger_map.get(scheme.get("trigger"), EVENT_NONE)
            self.scheme_effect[code] = scheme_effect_map.get(scheme.get("effect"), SCHEME_NONE)
            self.scheme_amount[code] = int(scheme.get("amount", 0))
            self.scheme_requires_subject[code] = bool(scheme.get("requires_own_subject"))
            self.scheme_face_bonus[code] = int(scheme.get("face_down_front_bonus", 0))

            if design.get("stratagem") == "all_reserves_forward":
                self.strat_choice_kind[code] = STRAT_CHOICE_RESERVES
            elif design.get("stratagem") == "wheel_line":
                self.strat_choice_kind[code] = STRAT_CHOICE_WHEEL
            elif design.get("chosen_fronts") == 2:
                self.strat_choice_kind[code] = STRAT_CHOICE_ADJACENT_FRONTS
            elif design.get("chosen_edge_front"):
                self.strat_choice_kind[code] = STRAT_CHOICE_EDGE_FRONT
            elif design.get("chosen_front"):
                self.strat_choice_kind[code] = STRAT_CHOICE_FRONT
            elif design.get("direction_choice"):
                self.strat_choice_kind[code] = STRAT_CHOICE_DIRECTION

            strat = rules.get("stratagem") or {}
            trigger = strat.get("trigger") or {}
            self.strat_trigger_event[code] = strat_event_map.get(trigger.get("event"), EVENT_NONE)
            self.strat_actor[code] = actor_map.get(trigger.get("actor", "either"), ACTOR_EITHER)
            for role_name in trigger.get("roles", ()):
                r = role_map.get(role_name, ROLE_NONE)
                self.strat_role_mask[code] |= (1 << r)
            for rank_name in trigger.get("ranks", ()):
                r = rank_map.get(rank_name, -1)
                if r >= 0:
                    self.strat_rank_mask[code] |= (1 << r)
            reveal = strat.get("reveal_effect") or {}
            if reveal.get("effect") == "penalize_trigger_subject":
                self.strat_reveal_effect[code] = STRAT_REVEAL_PENALIZE
            self.strat_reveal_amount[code] = int(reveal.get("amount", 0))
            self.strat_cancel_story[code] = bool(reveal.get("cancel_story"))
            continuous = strat.get("continuous") or {}
            for role_name, amount in continuous.get("role_strength_modifiers", {}).items():
                r = role_map.get(role_name, ROLE_NONE)
                self.strat_role_mod[code][r] = int(amount)
            for rank_name, amount in continuous.get("rank_strength_modifiers", {}).items():
                self.strat_rank_mod[code][rank_map[rank_name]] = int(amount)
            for rank_name, amount in continuous.get("controller_rank_strength_modifiers", {}).items():
                self.strat_controller_rank_mod[code][rank_map[rank_name]] = int(amount)
            self.strat_named_mod[code] = int(continuous.get("named_subject_modifier", 0))
            self.strat_unnamed_mod[code] = int(continuous.get("unnamed_subject_modifier", 0))
            self.strat_story_lock[code] = bool(continuous.get("controller_immediate_story_lock"))
            self.strat_global_story_lock[code] = bool(continuous.get("global_immediate_story_lock"))

    cpdef FastState from_game_state(self, state):
        cdef FastState fast = FastState()
        cdef int p, i, f, r, slot, code, viewer, owner
        cdef object card_id, py_slot, story, strat, counter
        phase_map = {
            "battle": PHASE_BATTLE,
            "complete": PHASE_COMPLETE,
        }

        for p in range(2):
            if max(
                len(state.players[p].deck),
                len(state.players[p].hand),
                len(state.players[p].discard),
            ) > MAX_DECK:
                raise ValueError(
                    f"Player {p}: a card zone exceeds native capacity {MAX_DECK}"
                )
            fast.deck_len[p] = len(state.players[p].deck)
            for i, card_id in enumerate(state.players[p].deck):
                code = self.id_to_code[card_id]
                fast.deck[p][i] = code
                fast.deck_counts[p][code] += 1
            fast.hand_len[p] = len(state.players[p].hand)
            for card_id in state.players[p].hand:
                fast.hand[p][self.id_to_code[card_id]] += 1
            fast.discard_len[p] = len(state.players[p].discard)
            for i, card_id in enumerate(state.players[p].discard):
                fast.discard[p][i] = self.id_to_code[card_id]

            fast.passed[p] = state.players[p].passed
            fast.command[p] = state.players[p].command
            fast.operations_this_battle[p] = state.operations_this_battle[p]
            fast.cards_played_this_turn_front_mask[p] = state.cards_played_this_turn_front_mask[p]
            fast.cards_played_this_battle_front_mask[p] = state.cards_played_this_battle_front_mask[p]
            fast.narratives_played_this_battle[p] = state.narratives_played_this_battle[p]
            fast.command_spent_this_battle[p] = state.command_spent_this_battle[p]
            fast.command_refunded_this_battle[p] = state.command_refunded_this_battle[p]
            fast.battle_start_command[p] = state.battle_start_command[p]
            fast.battle_start_hand_size[p] = state.battle_start_hand_size[p]
            fast.cards_drawn_this_battle[p] = state.cards_drawn_this_battle[p]
            fast.completion_count_this_battle[p] = state.completion_count_this_battle[p]
            fast.deck_reshuffles[p] = state.deck_reshuffles[p]
            fast.reshuffle_card_totals[p] = state.reshuffle_card_totals[p]
            fast.reshuffle_hand_card_totals[p] = state.reshuffle_hand_card_totals[p]
            fast.discarded_this_battle[p] = state.discarded_this_battle[p]
            fast.stratagem_used[p] = state.stratagem_used[p]
            fast.hero_used[p] = state.hero_used[p]

            strat = state.stratagems[p]
            if strat is not None:
                fast.stratagem[p] = self.id_to_code[strat.card_id]
                fast.stratagem_revealed[p] = 1
                for front_choice in strat.fronts:
                    fast.stratagem_front_mask[p] |= 1 << int(front_choice)
                if strat.direction == "left":
                    fast.stratagem_direction[p] = 1
                elif strat.direction == "right":
                    fast.stratagem_direction[p] = 2
                for target_choice in strat.targets:
                    fast.stratagem_target_mask[p] |= (
                        1
                        << slot_index(
                            int(target_choice[0]),
                            int(target_choice[1].front),
                            0 if target_choice[1].rank.value == "front" else 1,
                        )
                    )

            for f in range(4):
                for r in range(2):
                    slot = slot_index(p, f, r)
                    py_slot = state.board[p][f][r]
                    if py_slot.force is not None:
                        fast.subject[slot] = self.id_to_code[py_slot.force]
                    if py_slot.bond is not None:
                        fast.link[slot] = self.id_to_code[py_slot.bond]
                    if py_slot.name is not None:
                        fast.name[slot] = self.id_to_code[py_slot.name]
                    fast.temporary[slot] = py_slot.temporary_strength
                    fast.maneuver_count[slot] = int(py_slot.maneuvers_this_battle)

            for i, story in enumerate(state.stories[p][:self.ongoing_story_limit]):
                fast.scheme[p * 4 + i] = self.id_to_code[story.card_id]
                fast.scheme_revealed[p * 4 + i] = 1
                fast.scheme_used[p * 4 + i] = bool(story.triggered_this_battle)
                for front_choice in story.fronts:
                    fast.scheme_front_mask[p * 4 + i] |= 1 << int(front_choice)
                if story.target_position is not None and story.target_player is not None:
                    fast.scheme_target_slot[p * 4 + i] = slot_index(
                        int(story.target_player),
                        int(story.target_position.front),
                        0 if story.target_position.rank.value == "front" else 1,
                    )

        fast.active_player = state.active_player
        fast.battle = state.battle
        fast.phase = phase_map[state.phase.value]
        fast.winner = -1 if state.winner is None else state.winner
        fast.turn_number = state.turn_number
        fast.shuffle_seed = state.shuffle_seed
        fast.pass_len = len(state.pass_order)
        fast.cleanup_pending = (
            state.pending_draw_discard_for is not None
        )
        fast.pending_draw_count = int(state.pending_draw_count)
        fast.pending_draw_finish_operation = bool(
            state.pending_draw_finish_operation
        )
        for i, p in enumerate(state.pass_order):
            fast.pass_order[i] = p

        for viewer in range(2):
            for owner in range(2):
                counter = state.known_hidden_counter(viewer, owner, "hand")
                for card_id, count in counter.items():
                    fast.known_hidden[viewer][owner][self.id_to_code[card_id]] = count

        snapshot = state.last_battle_snapshot
        if snapshot is not None:
            fast.last_battle_valid = 1
            fast.last_battle = int(snapshot.get("battle", 0))
            front_scores = snapshot.get("front_scores", ())
            for f in range(min(4, len(front_scores))):
                fast.last_front_scores[f][0] = int(front_scores[f][0])
                fast.last_front_scores[f][1] = int(front_scores[f][1])
            for p in range(2):
                fast.last_command_start[p] = int(
                    snapshot.get("command_start", (0, 0))[p]
                )
                fast.last_command_spent[p] = int(
                    snapshot.get("command_spent", (0, 0))[p]
                )
                fast.last_command_refunded[p] = int(
                    snapshot.get("command_refunded", (0, 0))[p]
                )
                fast.last_command_remaining[p] = int(
                    snapshot.get("command_remaining", (0, 0))[p]
                )
                fast.last_deck_remaining[p] = int(
                    snapshot.get("deck_remaining", (0, 0))[p]
                )
                fast.last_hand_size[p] = int(
                    snapshot.get("hand_size", (0, 0))[p]
                )
                fast.last_battle_start_hand_size[p] = int(
                    snapshot.get("battle_start_hand_size", (0, 0))[p]
                )
                fast.last_cards_drawn[p] = int(
                    snapshot.get("cards_drawn", (0, 0))[p]
                )
                fast.last_completion_count[p] = int(
                    snapshot.get("completion_count", (0, 0))[p]
                )
                fast.last_operations[p] = int(
                    snapshot.get("operations", (0, 0))[p]
                )
            pass_snapshot = snapshot.get("pass_order", ())
            fast.last_pass_len = min(2, len(pass_snapshot))
            for i in range(fast.last_pass_len):
                fast.last_pass_order[i] = int(pass_snapshot[i])

        return fast

    cdef inline int hand_size(self, FastState state, int player) noexcept:
        return state.hand_len[player]

    cdef int position_strength_fast(self, FastState state, int slot) noexcept:
        cdef int card = state.subject[slot]
        cdef int player, local, front, rank, value, rear, frontslot, other, adj, link, name, role, mod, strat, controller
        if card < 0:
            return 0
        player = owner_from_slot(slot)
        local = local_slot(slot)
        front = local >> 1
        rank = local & 1
        role = self.role[card]
        value = self.strength[card] + state.temporary[slot]

        # Printed card effects are explicit metadata; roles remain labels only.
        mod = self.force_text_effect[card]
        if mod == FORCE_TEXT_FRONT_BONUS and rank == 0:
            value += self.force_text_amount[card]
        elif mod == FORCE_TEXT_REAR_BONUS and rank == 1:
            value += self.force_text_amount[card]
        elif mod == FORCE_TEXT_FRONT_IF_REAR and rank == 0:
            rear = slot_index(player, front, 1)
            if state.subject[rear] >= 0:
                value += self.force_text_amount[card]
        elif mod == FORCE_TEXT_REAR_IF_FRONT and rank == 1:
            frontslot = slot_index(player, front, 0)
            if state.subject[frontslot] >= 0:
                value += self.force_text_amount[card]

        # Rear support effects add Strength to the Force directly ahead.
        if rank == 0:
            rear = slot_index(player, front, 1)
            other = state.subject[rear]
            if (
                other >= 0
                and self.force_text_effect[other] == FORCE_TEXT_SUPPORT_AHEAD
            ):
                value += self.force_text_amount[other]

        # Roles and classifications are labels only. They never grant
        # intrinsic Strength; any such effect must come from explicit card
        # rules. The role code remains available for cards that refer to a
        # role by name (for example a Stratagem affecting Archers).

        if front > 0:
            adj = slot_index(player, front - 1, rank)
            other = state.subject[adj]
            if other >= 0 and self.aura[other] and (self.aura_rank[other] < 0 or self.aura_rank[other] == rank):
                value += self.aura[other]
        if front < 3:
            adj = slot_index(player, front + 1, rank)
            other = state.subject[adj]
            if other >= 0 and self.aura[other] and (self.aura_rank[other] < 0 or self.aura_rank[other] == rank):
                value += self.aura[other]

        mod = self.subject_mod_amount[card]
        if mod:
            if self.subject_mod_discard_min[card] and state.discard_len[player] < self.subject_mod_discard_min[card]:
                pass
            elif self.subject_mod_adj_named[card]:
                other = 0
                if (
                    front > 0
                    and state.subject[slot_index(player, front - 1, rank)] >= 0
                    and state.name[slot_index(player, front - 1, rank)] >= 0
                ):
                    other = 1
                if (
                    front < 3
                    and state.subject[slot_index(player, front + 1, rank)] >= 0
                    and state.name[slot_index(player, front + 1, rank)] >= 0
                ):
                    other = 1
                if other:
                    value += mod
            else:
                value += mod

        link = state.link[slot]
        name = state.name[slot]
        if link >= 0:
            value += self.link_bonus[link]
            if name >= 0:
                value += self.link_named_bonus[link]
                if self.link_discard_per[link]:
                    mod = state.discarded_this_battle[player] * self.link_discard_per[link]
                    if mod > self.link_discard_max[link]:
                        mod = self.link_discard_max[link]
                    value += mod
        if name >= 0:
            value += self.name_strength[name]
            if self.name_rank_bonus_rank[name] == rank:
                value += self.name_rank_bonus_amount[name]

        for controller in range(2):
            strat = state.stratagem[controller]
            if strat < 0 or not state.stratagem_revealed[controller]:
                continue
            value += self.strat_role_mod[strat][role]
            value += self.strat_rank_mod[strat][rank]
            if controller == player:
                value += self.strat_controller_rank_mod[strat][rank]
            if name >= 0:
                value += self.strat_named_mod[strat]
            else:
                value += self.strat_unnamed_mod[strat]

        return value if value > 0 else 0

    cpdef int position_strength(self, FastState state, int player, int front, int rank):
        return self.position_strength_fast(state, slot_index(player, front, rank))

    cdef int front_strength_fast(self, FastState state, int player, int front) noexcept:
        cdef int value, scheme, enemy, slot, link
        value = self.position_strength_fast(state, slot_index(player, front, 0))
        value += self.position_strength_fast(state, slot_index(player, front, 1))
        scheme = state.scheme[player * 4 + front]
        if scheme >= 0 and not state.scheme_revealed[player * 4 + front]:
            value += self.scheme_face_bonus[scheme]
        enemy = 1 - player
        for slot in (slot_index(enemy, front, 0), slot_index(enemy, front, 1)):
            if state.subject[slot] >= 0 and state.link[slot] >= 0 and state.name[slot] >= 0:
                link = state.link[slot]
                value += self.link_opposing[link]
        return value

    cdef inline bint frontline_only_resolution(
        self,
        FastState state,
        int front,
    ) noexcept:
        cdef int player, rank, force
        for player in range(2):
            for rank in range(2):
                force = state.subject[slot_index(player, front, rank)]
                if force >= 0 and self.combat_frontline_only[force]:
                    return True
        return False

    cdef inline int resolution_front_strength_fast(
        self,
        FastState state,
        int player,
        int front,
    ) noexcept:
        cdef int strat = state.stratagem[player]
        cdef int mask = state.stratagem_front_mask[player]
        cdef int value, rank, slot, formation_bonus = 0
        cdef bint frontline_only = self.frontline_only_resolution(state, front)

        if (
            strat >= 0
            and self.strat_refuse_flank[strat]
            and (mask & (1 << front))
        ):
            return 0

        if frontline_only:
            value = self.position_strength_fast(
                state,
                slot_index(player, front, 0),
            )
        else:
            value = self.front_strength_fast(state, player, front)

        if strat >= 0 and self.strat_refuse_flank[strat]:
            if (mask == 1 and front == 1) or (mask == 8 and front == 2):
                for rank in range(1 if frontline_only else 2):
                    slot = slot_index(player, front, rank)
                    if state.subject[slot] >= 0:
                        formation_bonus += 1
                value += formation_bonus
        return value

    cdef inline bint breakthrough_active(
        self,
        FastState state,
        int player,
        int front,
    ) noexcept:
        cdef int rank, slot, force, name
        for rank in range(2):
            slot = slot_index(player, front, rank)
            force = state.subject[slot]
            if force < 0:
                continue
            if self.force_breakthrough[force]:
                return True
            name = state.name[slot]
            if name >= 0 and self.name_breakthrough[name]:
                return True
        return False

    cdef inline bint tie_control_active(
        self,
        FastState state,
    ) noexcept:
        cdef int p, strat
        for p in range(2):
            strat = state.stratagem[p]
            if strat >= 0 and self.strat_tie_control[strat]:
                return True
        return False

    cpdef int front_strength(self, FastState state, int player, int front):
        return self.front_strength_fast(state, player, front)

    cdef inline bint slot_complete(self, FastState state, int slot) noexcept:
        return (
            state.subject[slot] >= 0
            and state.link[slot] >= 0
            and state.name[slot] >= 0
        )

    cdef inline bint subject_protected(self, FastState state, int slot) noexcept:
        cdef int link = state.link[slot]
        cdef int name = state.name[slot]
        if link >= 0 and name >= 0 and self.link_protect[link]:
            return True
        return (
            self.slot_complete(state, slot)
            and name >= 0
            and self.complete_plot_protection[name]
        )

    cdef inline bint story_locked(self, FastState state, int player) noexcept:
        cdef int controller, strat
        for controller in range(2):
            strat = state.stratagem[controller]
            if strat < 0 or not state.stratagem_revealed[controller]:
                continue
            if self.strat_global_story_lock[strat]:
                return True
            if controller == player and self.strat_story_lock[strat]:
                return True
        return False

    cdef inline bint can_draw_fast(self, FastState state, int player) noexcept:
        return (
            state.deck_len[player] > 0
            or state.discard_len[player] > 0
        )

    cpdef bint can_draw(self, FastState state, int player):
        return self.can_draw_fast(state, player)

    cdef inline int local_front_discount_fast(
        self,
        FastState state,
        int player,
        int front,
    ) noexcept:
        cdef int rank, slot, name, discount = 0
        cdef uint8_t bit = <uint8_t>(1 << front)
        for rank in range(2):
            slot = slot_index(player, front, rank)
            if state.subject[slot] < 0:
                continue
            name = state.name[slot]
            if name < 0:
                continue
            if (
                self.local_catchup_discount_name[name]
                and state.command[player] < state.command[1 - player]
                and not (state.cards_played_this_turn_front_mask[player] & bit)
            ):
                discount = max(
                    discount,
                    self.local_catchup_discount_name[name],
                )
            if (
                self.first_front_card_battle_discount_name[name]
                and self.slot_complete(state, slot)
                and not (state.cards_played_this_battle_front_mask[player] & bit)
            ):
                discount = max(
                    discount,
                    self.first_front_card_battle_discount_name[name],
                )
        return discount

    cdef inline int first_narrative_discount_fast(
        self,
        FastState state,
        int player,
    ) noexcept:
        cdef int front, slot, force
        if state.narratives_played_this_battle[player]:
            return 0
        for front in range(4):
            slot = slot_index(player, front, 1)
            force = state.subject[slot]
            if (
                force >= 0
                and self.first_narrative_battle_discount_force[force]
            ):
                return 1
        return 0

    cdef inline int adjacent_discount_fast(
        self,
        FastState state,
        int player,
        int target_front,
    ) noexcept:
        cdef int local, slot, front, name, discount = 0
        for local in range(8):
            slot = player * 8 + local
            if not self.slot_complete(state, slot):
                continue
            front = local >> 1
            if abs(front - target_front) != 1:
                continue
            name = state.name[slot]
            if name >= 0 and self.adjacent_command_discount[name] > discount:
                discount = self.adjacent_command_discount[name]
        return discount

    cdef inline int command_cost_fast(
        self,
        FastState state,
        uint64_t action,
    ) noexcept:
        cdef int kind, card, pos, target_front=-1, cost, discount, rear, support, strat
        cdef int selected
        cdef uint32_t extra
        cdef int player = state.active_player
        kind = action_kind(action)
        if kind == TYPE_PASS:
            return 0
        if kind == TYPE_MANEUVER:
            if state.maneuver_count[action_pos(action)] == 0:
                card = state.subject[action_pos(action)]
                if (
                    card >= 0
                    and self.first_maneuver_free[card]
                    and (
                        not self.maneuver_requires_open_bond[card]
                        or (
                            state.link[action_pos(action)] >= 0
                            and state.name[action_pos(action)] < 0
                        )
                    )
                ):
                    return 0
                card = state.link[action_pos(action)]
                if (
                    card >= 0
                    and self.first_maneuver_free[card]
                    and self.adjacent_hero_formation(
                        state, player, action_pos(action)
                    )
                ):
                    return 0
                card = state.name[action_pos(action)]
                if (
                    card >= 0
                    and self.first_maneuver_free_empty_front[card]
                    and self.player_has_empty_front(state, player)
                ):
                    return 0
            strat = state.stratagem[player]
            if strat >= 0 and self.strat_maneuver_cost[strat] >= 0:
                return self.strat_maneuver_cost[strat]
            if (
                strat >= 0
                and self.strat_directional_maneuver[strat]
                and self.slot_complete(state, action_pos(action))
            ):
                if (
                    state.stratagem_direction[player] == 1
                    and front_from_slot(action_dest(action))
                    < front_from_slot(action_pos(action))
                ):
                    return 0
                if (
                    state.stratagem_direction[player] == 2
                    and front_from_slot(action_dest(action))
                    > front_from_slot(action_pos(action))
                ):
                    return 0
            return self.maneuver_command_cost
        card = action_card(action)
        if card < 0:
            return 0
        cost = self.card_command_cost[card]
        pos = action_pos(action)
        extra = action_extra(action)
        if (
            kind == TYPE_LINK
            and extra
            and self.bond_optional_extra_cost[card] > 0
        ):
            cost += self.bond_optional_extra_cost[card]
        if (
            kind == TYPE_STRATAGEM
            and self.strat_choice_kind[card] == STRAT_CHOICE_RESERVES
        ):
            selected = popcount16(extra)
            if selected > 1:
                cost += selected - 1

        if self.catchup_zero_cost[card] and state.command[player] < state.command[1 - player]:
            cost = 0
        elif (
            self.completion_discount_cost[card] >= 0
            and kind == TYPE_NAME
            and pos >= 0
            and state.subject[pos] >= 0
            and state.link[pos] >= 0
        ):
            cost = self.completion_discount_cost[card]

        if kind == TYPE_SUBJECT or kind == TYPE_LINK or kind == TYPE_NAME:
            target_front = front_from_slot(pos)
        if kind == TYPE_PLOT or kind == TYPE_SCHEME:
            discount = self.first_narrative_discount_fast(state, player)
            if discount:
                cost -= discount
                if cost < 1:
                    cost = 1
        if target_front >= 0:
            discount = self.adjacent_discount_fast(state, player, target_front)
            if self.local_front_discount_fast(state, player, target_front) > discount:
                discount = self.local_front_discount_fast(
                    state, player, target_front
                )
            if kind == TYPE_SUBJECT and rank_from_slot(pos) == 0:
                rear = slot_index(player, target_front, 1)
                support = state.subject[rear]
                if (
                    support >= 0
                    and self.frontline_force_discount[support] > discount
                    and (
                        not self.frontline_force_discount_requires_named[support]
                        or self.slot_complete(state, rear)
                    )
                ):
                    discount = self.frontline_force_discount[support]
            if discount:
                cost -= discount
                if cost < 1 and not self.catchup_zero_cost[card]:
                    cost = 1
        return cost

    cpdef int command_cost(self, FastState state, uint64_t action):
        return self.command_cost_fast(state, action)

    cdef inline void spend_command_fast(
        self,
        FastState state,
        int player,
        int amount,
    ) noexcept:
        if amount > state.command[player]:
            amount = state.command[player]
        state.command[player] -= amount
        state.command_spent_this_battle[player] += amount

    cdef inline void gain_command_fast(
        self,
        FastState state,
        int player,
        int amount,
    ) noexcept:
        cdef int before = state.command[player]
        state.command[player] += amount
        if state.command[player] > self.command_cap:
            state.command[player] = self.command_cap
        state.command_refunded_this_battle[player] += state.command[player] - before

    cdef inline int complete_mask(self, FastState state, int player) noexcept:
        cdef int local, slot, mask=0
        for local in range(8):
            slot = player * 8 + local
            if self.slot_complete(state, slot):
                mask |= 1 << local
        return mask

    cdef void recover_recent_link_fast(self, FastState state, int player) noexcept:
        cdef int i, j, card
        for i in range(state.discard_len[player] - 1, -1, -1):
            card = state.discard[player][i]
            if self.card_type[card] != CARD_LINK:
                continue
            for j in range(i, state.discard_len[player] - 1):
                state.discard[player][j] = state.discard[player][j + 1]
            state.discard_len[player] -= 1
            self.return_to_hand(state, player, card)
            return

    cdef void resolve_new_completions_fast(
        self,
        FastState state,
        int player,
        int before_mask,
    ):
        cdef int local, slot, name, effect, amount, front, enemy_ix
        cdef int after_mask = self.complete_mask(state, player)
        cdef int new_mask = after_mask & ~before_mask
        if new_mask == 0:
            return
        for local in range(8):
            if not (new_mask & (1 << local)):
                continue
            slot = player * 8 + local
            state.completion_count_this_battle[player] += 1
            name = state.name[slot]
            if name < 0:
                continue
            effect = self.completion_effect[name]
            amount = self.completion_amount[name]
            if effect == COMPLETE_GAIN_COMMAND:
                self.gain_command_fast(state, player, amount)
            elif effect == COMPLETE_DRAW:
                self.queue_battle_draws(state, player, amount)
            elif effect == COMPLETE_REVEAL_SCHEME:
                front = local >> 1
                enemy_ix = (1 - player) * 4 + front
                if state.scheme[enemy_ix] >= 0:
                    state.scheme_revealed[enemy_ix] = 1
            elif effect == COMPLETE_RECOVER_LINK:
                self.recover_recent_link_fast(state, player)
            self.resolve_named_narratives(state, player)

    cdef inline bint player_has_empty_front(
        self,
        FastState state,
        int player,
    ) noexcept:
        cdef int front
        for front in range(4):
            if (
                state.subject[slot_index(player, front, 0)] < 0
                and state.subject[slot_index(player, front, 1)] < 0
            ):
                return True
        return False

    cdef inline bint adjacent_hero_formation(
        self,
        FastState state,
        int player,
        int slot,
    ) noexcept:
        cdef int local = local_slot(slot)
        cdef int front = local >> 1
        cdef int rank = local & 1
        cdef int adjacent, force, name
        if front > 0:
            adjacent = slot_index(player, front - 1, rank)
            force = state.subject[adjacent]
            name = state.name[adjacent]
            if force >= 0 and (
                self.hero[force]
                or (name >= 0 and self.hero[name])
            ):
                return True
        if front < 3:
            adjacent = slot_index(player, front + 1, rank)
            force = state.subject[adjacent]
            name = state.name[adjacent]
            if force >= 0 and (
                self.hero[force]
                or (name >= 0 and self.hero[name])
            ):
                return True
        return False

    cdef inline bint maneuver_source_legal(
        self,
        FastState state,
        int player,
        int slot,
    ) noexcept:
        cdef int force, bond, strat
        force = state.subject[slot]
        if force < 0 or self.immobile_force[force]:
            return False
        if self.slot_complete(state, slot):
            return True
        if self.can_maneuver_unnamed[force]:
            if not self.maneuver_requires_open_bond[force]:
                return True
            if state.link[slot] >= 0 and state.name[slot] < 0:
                return True
        bond = state.link[slot]
        if (
            bond >= 0
            and self.bond_maneuver_adjacent_hero[bond]
            and self.adjacent_hero_formation(state, player, slot)
        ):
            return True
        strat = state.stratagem[player]
        return strat >= 0 and self.strat_unnamed_maneuver[strat]

    cdef inline bint maneuver_destination_legal(
        self,
        FastState state,
        int slot,
    ) noexcept:
        cdef int force = state.subject[slot]
        if force >= 0:
            return (
                not self.immobile_force[force]
                and not self.cannot_swap_target[force]
            )
        return state.link[slot] < 0 and state.name[slot] < 0

    cdef int legal_actions_into(
        self,
        FastState state,
        uint64_t* actions,
    ) except -1:
        cdef int n = 0
        cdef int player, card, slot, local, front, rank, source, dest, req, opponent, effect
        cdef int i, kept, can_pass, available, story_slot, choice, direction
        cdef uint32_t eligible_mask, subset
        cdef uint64_t action

        if state.phase == PHASE_COMPLETE:
            return 0

        player = state.active_player

        # A turn that starts at the hand limit must discard before its
        # automatic draw. This substep is not the turn's operation.
        if state.cleanup_pending:
            for card in range(self.n_cards):
                if state.hand[player][card] > 0:
                    n = _append_action(
                        actions,
                        n,
                        encode_action(TYPE_DISCARD, card, -1, -1, player),
                    )
            return n

        opponent = 1 - player

        for card in range(self.n_cards):
            if state.hand[player][card] == 0:
                continue

            if self.card_type[card] == CARD_SUBJECT:
                if not self.hero[card] or not state.hero_used[player]:
                    req = self.placement_rank[card]
                    for local in range(8):
                        slot = player * 8 + local
                        if state.subject[slot] >= 0:
                            continue
                        rank = local & 1
                        if req >= 0 and req != rank:
                            continue
                        n = _append_action(
                            actions,
                            n,
                            encode_action(TYPE_SUBJECT, card, slot, -1, player),
                        )

                    # Heroes are dual-use Force/Name cards. Playing either mode
                    # consumes the one-Hero-from-hand allowance for the Battle.
                    if self.hero[card]:
                        for local in range(8):
                            slot = player * 8 + local
                            if state.name[slot] < 0:
                                n = _append_action(
                                    actions,
                                    n,
                                    encode_action(TYPE_NAME, card, slot, -1, player),
                                )

            elif self.card_type[card] == CARD_LINK:
                for local in range(8):
                    slot = player * 8 + local
                    if state.link[slot] >= 0:
                        continue
                    n = _append_action(
                        actions,
                        n,
                        encode_action(TYPE_LINK, card, slot, -1, player),
                    )
                    if self.bond_optional_extra_cost[card] > 0:
                        n = _append_action(
                            actions,
                            n,
                            encode_action(
                                TYPE_LINK,
                                card,
                                slot,
                                -1,
                                player,
                                1,
                            ),
                        )
                    if (
                        self.bond_move_on_play[card]
                        and state.subject[slot] >= 0
                        and not self.immobile_force[state.subject[slot]]
                    ):
                        front = local >> 1
                        rank = local & 1
                        if front > 0:
                            dest = slot_index(player, front - 1, rank)
                            if (
                                state.subject[dest] < 0
                                and state.link[dest] < 0
                                and state.name[dest] < 0
                            ):
                                n = _append_action(
                                    actions,
                                    n,
                                    encode_action(
                                        TYPE_LINK,
                                        card,
                                        slot,
                                        dest,
                                        player,
                                    ),
                                )
                        if front < 3:
                            dest = slot_index(player, front + 1, rank)
                            if (
                                state.subject[dest] < 0
                                and state.link[dest] < 0
                                and state.name[dest] < 0
                            ):
                                n = _append_action(
                                    actions,
                                    n,
                                    encode_action(
                                        TYPE_LINK,
                                        card,
                                        slot,
                                        dest,
                                        player,
                                    ),
                                )

            elif self.card_type[card] == CARD_NAME:
                for local in range(8):
                    slot = player * 8 + local
                    if state.name[slot] >= 0:
                        continue
                    n = _append_action(
                        actions,
                        n,
                        encode_action(TYPE_NAME, card, slot, -1, player),
                    )

            elif self.card_type[card] == CARD_PLOT:
                if self.veiled[card]:
                    # Ongoing Narratives may carry a public Front or formation
                    # association selected when the card is played.
                    choice = self.story_choice_kind[card]
                    for story_slot in range(self.ongoing_story_limit):
                        if state.scheme[player * 4 + story_slot] >= 0:
                            continue
                        if choice == STORY_CHOICE_FRONT:
                            for front in range(4):
                                n = _append_action(
                                    actions,
                                    n,
                                    encode_action(
                                        TYPE_SCHEME,
                                        card,
                                        story_slot,
                                        -1,
                                        player,
                                        <uint32_t>(1 << front),
                                    ),
                                )
                        elif choice == STORY_CHOICE_NAMED_FORMATION:
                            for local in range(8):
                                slot = player * 8 + local
                                if self.slot_complete(state, slot):
                                    n = _append_action(
                                        actions,
                                        n,
                                        encode_action(
                                            TYPE_SCHEME,
                                            card,
                                            story_slot,
                                            slot,
                                            player,
                                        ),
                                    )
                        else:
                            n = _append_action(
                                actions,
                                n,
                                encode_action(
                                    TYPE_SCHEME,
                                    card,
                                    story_slot,
                                    -1,
                                    player,
                                ),
                            )
                else:
                    effect = self.plot_effect[card]
                    if effect == PLOT_DISCREDIT or effect == PLOT_RETURN_NAME:
                        for local in range(8):
                            slot = opponent * 8 + local
                            if (
                                state.subject[slot] >= 0
                                and not self.subject_protected(state, slot)
                            ):
                                n = _append_action(
                                    actions,
                                    n,
                                    encode_action(
                                        TYPE_PLOT,
                                        card,
                                        slot,
                                        -1,
                                        opponent,
                                    ),
                                )
                    elif effect == PLOT_MOVE_SUBJECT:
                        for source in range(player * 8, player * 8 + 8):
                            if state.subject[source] < 0:
                                continue
                            for dest in range(player * 8, player * 8 + 8):
                                if (
                                    dest == source
                                    or state.subject[dest] >= 0
                                    or state.link[dest] >= 0
                                    or state.name[dest] >= 0
                                ):
                                    continue
                                n = _append_action(
                                    actions,
                                    n,
                                    encode_action(
                                        TYPE_PLOT,
                                        card,
                                        source,
                                        dest,
                                        player,
                                    ),
                                )
                    else:
                        n = _append_action(
                            actions,
                            n,
                            encode_action(TYPE_PLOT, card, -1, -1, player),
                        )
                        if self.story_discard_count[card] == 1:
                            for i in range(self.n_cards):
                                if state.hand[player][i] <= 0:
                                    continue
                                if i == card and state.hand[player][i] < 2:
                                    continue
                                n = _append_action(
                                    actions,
                                    n,
                                    encode_action(
                                        TYPE_PLOT,
                                        card,
                                        -1,
                                        -1,
                                        player,
                                        <uint32_t>(i + 1),
                                    ),
                                )

            elif self.card_type[card] == CARD_STRATAGEM:
                if (
                    not state.stratagem_used[player]
                    and state.stratagem[player] < 0
                ):
                    choice = self.strat_choice_kind[card]
                    if choice == STRAT_CHOICE_FRONT:
                        for front in range(4):
                            n = _append_action(
                                actions,
                                n,
                                encode_action(
                                    TYPE_STRATAGEM,
                                    card,
                                    1 << front,
                                    -1,
                                    player,
                                ),
                            )
                    elif choice == STRAT_CHOICE_ADJACENT_FRONTS:
                        for front in range(3):
                            n = _append_action(
                                actions,
                                n,
                                encode_action(
                                    TYPE_STRATAGEM,
                                    card,
                                    3 << front,
                                    -1,
                                    player,
                                ),
                            )
                    elif choice == STRAT_CHOICE_EDGE_FRONT:
                        for front in (0, 3):
                            n = _append_action(
                                actions,
                                n,
                                encode_action(
                                    TYPE_STRATAGEM,
                                    card,
                                    1 << front,
                                    -1,
                                    player,
                                ),
                            )
                    elif choice == STRAT_CHOICE_DIRECTION:
                        for direction in range(2):
                            n = _append_action(
                                actions,
                                n,
                                encode_action(
                                    TYPE_STRATAGEM,
                                    card,
                                    -1,
                                    direction,
                                    player,
                                ),
                            )
                    elif choice == STRAT_CHOICE_WHEEL:
                        for direction in range(2):
                            eligible_mask = 0
                            for local in range(8):
                                source = player * 8 + local
                                if state.subject[source] < 0:
                                    continue
                                front = local >> 1
                                rank = local & 1
                                if direction == 0:
                                    if front == 0:
                                        continue
                                    dest = slot_index(player, front - 1, rank)
                                else:
                                    if front == 3:
                                        continue
                                    dest = slot_index(player, front + 1, rank)
                                if (
                                    state.subject[dest] < 0
                                    and state.link[dest] < 0
                                    and state.name[dest] < 0
                                ):
                                    eligible_mask |= <uint32_t>(1 << source)
                            subset = eligible_mask
                            while True:
                                n = _append_action(
                                    actions,
                                    n,
                                    encode_action(
                                        TYPE_STRATAGEM,
                                        card,
                                        -1,
                                        direction,
                                        player,
                                        subset,
                                    ),
                                )
                                if subset == 0:
                                    break
                                subset = (subset - 1) & eligible_mask
                    elif choice == STRAT_CHOICE_RESERVES:
                        eligible_mask = 0
                        for front in range(4):
                            source = slot_index(player, front, 1)
                            dest = slot_index(player, front, 0)
                            if (
                                state.subject[source] >= 0
                                and state.subject[dest] < 0
                                and state.link[dest] < 0
                                and state.name[dest] < 0
                            ):
                                eligible_mask |= <uint32_t>(1 << source)
                        subset = eligible_mask
                        while True:
                            n = _append_action(
                                actions,
                                n,
                                encode_action(
                                    TYPE_STRATAGEM,
                                    card,
                                    -1,
                                    -1,
                                    player,
                                    subset,
                                ),
                            )
                            if subset == 0:
                                break
                            subset = (subset - 1) & eligible_mask
                    else:
                        n = _append_action(
                            actions,
                            n,
                            encode_action(
                                TYPE_STRATAGEM,
                                card,
                                -1,
                                -1,
                                player,
                            ),
                        )

        # Maneuver moves to an empty position or swaps with another formation.
        # A prepared-only Bond/Name position is occupied but is not a formation.
        for local in range(8):
            source = player * 8 + local
            if not self.maneuver_source_legal(state, player, source):
                continue
            front = local >> 1
            rank = local & 1
            if front > 0:
                dest = slot_index(player, front - 1, rank)
                if self.maneuver_destination_legal(state, dest):
                    n = _append_action(
                        actions,
                        n,
                        encode_action(TYPE_MANEUVER, -1, source, dest, player),
                    )
            if front < 3:
                dest = slot_index(player, front + 1, rank)
                if self.maneuver_destination_legal(state, dest):
                    n = _append_action(
                        actions,
                        n,
                        encode_action(TYPE_MANEUVER, -1, source, dest, player),
                    )

        available = state.command[player]
        kept = 0
        for i in range(n):
            action = actions[i]
            if self.command_cost_fast(state, action) <= available:
                actions[kept] = action
                kept += 1
        n = kept

        can_pass = (
            state.operations_this_battle[0] > 0
            and state.operations_this_battle[1] > 0
        )
        if can_pass or n == 0:
            for i in range(n, 0, -1):
                actions[i] = actions[i - 1]
            actions[0] = encode_action(TYPE_PASS, -1, -1, -1, 0)
            n += 1

        return n

    cpdef list legal_actions(self, FastState state):
        cdef uint64_t actions[MAX_ACTIONS]
        cdef int n = self.legal_actions_into(state, &actions[0])
        cdef int i
        return [actions[i] for i in range(n)]

    cdef inline void append_discard(self, FastState state, int player, int card, bint battle_count=True) noexcept:
        state.discard[player][state.discard_len[player]] = card
        state.discard_len[player] += 1
        if battle_count:
            state.discarded_this_battle[player] += 1

    cdef inline void return_to_hand(self, FastState state, int player, int card) noexcept:
        state.hand[player][card] += 1
        state.hand_len[player] += 1
        state.known_hidden[1 - player][player][card] += 1

    cdef inline void take_from_hand(self, FastState state, int player, int card, int hidden_kind) noexcept:
        cdef int viewer = 1 - player
        cdef int known
        if hidden_kind == 0:
            if state.known_hidden[viewer][player][card] > 0:
                state.known_hidden[viewer][player][card] -= 1
        else:
            for known in range(self.n_cards):
                if state.known_hidden[viewer][player][known] == 0:
                    continue
                if hidden_kind == 1:
                    if self.card_type[known] == CARD_PLOT and self.veiled[known]:
                        state.known_hidden[viewer][player][known] -= 1
                elif hidden_kind == 2:
                    if self.card_type[known] == CARD_STRATAGEM:
                        state.known_hidden[viewer][player][known] -= 1
        state.hand[player][card] -= 1
        state.hand_len[player] -= 1

    cdef inline bint front_has_subject(self, FastState state, int player, int front) noexcept:
        return state.subject[slot_index(player, front, 0)] >= 0 or state.subject[slot_index(player, front, 1)] >= 0

    cdef inline int preferred_slot(self, FastState state, int player, int front) noexcept:
        cdef int slot = slot_index(player, front, 0)
        if state.subject[slot] >= 0:
            return slot
        slot = slot_index(player, front, 1)
        return slot if state.subject[slot] >= 0 else -1

    cdef void remove_link(self, FastState state, int player, int slot):
        cdef int link = state.link[slot]
        cdef int name = state.name[slot]
        state.link[slot] = -1
        state.name[slot] = -1
        if link >= 0:
            self.append_discard(state, player, link, True)
        if name >= 0:
            self.return_to_hand(state, player, name)

    cdef void compact_ongoing_stories(
        self,
        FastState state,
        int player,
    ) noexcept:
        """Keep packed Story storage aligned with GameState's compact list."""
        cdef int read_slot, write_slot, src, dst
        write_slot = 0
        for read_slot in range(self.ongoing_story_limit):
            src = player * 4 + read_slot
            if state.scheme[src] < 0:
                continue
            if read_slot != write_slot:
                dst = player * 4 + write_slot
                state.scheme[dst] = state.scheme[src]
                state.scheme_revealed[dst] = state.scheme_revealed[src]
                state.scheme_front_mask[dst] = state.scheme_front_mask[src]
                state.scheme_target_slot[dst] = state.scheme_target_slot[src]
                state.scheme_used[dst] = state.scheme_used[src]
                state.scheme[src] = -1
                state.scheme_revealed[src] = 0
                state.scheme_front_mask[src] = 0
                state.scheme_target_slot[src] = -1
                state.scheme_used[src] = 0
            write_slot += 1

    cdef void reveal_scheme(self, FastState state, int controller, int front, int actor, int trigger_slot=-1):
        cdef int ix = controller * 4 + front
        cdef int card = state.scheme[ix]
        cdef int effect, amount, target
        if card < 0:
            return
        state.scheme_revealed[ix] = 1
        effect = self.scheme_effect[card]
        amount = self.scheme_amount[card]
        if effect == SCHEME_PENALIZE_SUBJECT and trigger_slot >= 0 and state.subject[trigger_slot] >= 0:
            state.temporary[trigger_slot] -= amount
        elif effect == SCHEME_DISCARD_LINK and trigger_slot >= 0 and state.link[trigger_slot] >= 0:
            self.remove_link(state, actor, trigger_slot)
        elif effect == SCHEME_REINFORCE:
            target = self.preferred_slot(state, controller, front)
            if target >= 0:
                state.temporary[target] += amount
        state.scheme[ix] = -1
        state.scheme_revealed[ix] = 0
        state.scheme_front_mask[ix] = 0
        state.scheme_target_slot[ix] = -1
        self.compact_ongoing_stories(state, controller)
        self.append_discard(state, controller, card, True)

    cdef void resolve_scheme_event(self, FastState state, int actor, int event, int front, int trigger_slot=-1):
        cdef int controller, ix, card
        for controller in (actor, 1 - actor):
            ix = controller * 4 + front
            card = state.scheme[ix]
            if card < 0:
                continue
            if self.scheme_trigger[card] != event or actor == controller:
                continue
            if self.scheme_requires_subject[card] and not self.front_has_subject(state, controller, front):
                continue
            self.reveal_scheme(state, controller, front, actor, trigger_slot)

    cdef bint strat_trigger_matches(self, FastState state, int controller, int card, int event, int actor, int played_card=-1, int pos=-1) noexcept:
        cdef int role, rank, scope
        if self.strat_trigger_event[card] != event:
            return False
        scope = self.strat_actor[card]
        if scope == ACTOR_OPPONENT and actor == controller:
            return False
        if scope == ACTOR_CONTROLLER and actor != controller:
            return False
        if self.strat_role_mask[card]:
            if played_card < 0:
                return False
            role = self.role[played_card]
            if not (self.strat_role_mask[card] & (1 << role)):
                return False
        if self.strat_rank_mask[card]:
            if pos < 0:
                return False
            rank = rank_from_slot(pos)
            if not (self.strat_rank_mask[card] & (1 << rank)):
                return False
        return True

    cdef void resolve_strat_event(self, FastState state, int event, int actor, int played_card=-1, int pos=-1):
        cdef int controller, card
        for controller in (actor, 1 - actor):
            card = state.stratagem[controller]
            if card < 0 or state.stratagem_revealed[controller]:
                continue
            if not self.strat_trigger_matches(state, controller, card, event, actor, played_card, pos):
                continue
            state.stratagem_revealed[controller] = 1
            if self.strat_reveal_effect[card] == STRAT_REVEAL_PENALIZE and pos >= 0 and state.subject[pos] >= 0:
                state.temporary[pos] -= self.strat_reveal_amount[card]

    cdef bint pre_story_cancel(self, FastState state, int actor):
        cdef int controller = 1 - actor
        cdef int card = state.stratagem[controller]
        if card < 0 or state.stratagem_revealed[controller]:
            return False
        if not self.strat_trigger_matches(state, controller, card, EVENT_IMMEDIATE_STORY, actor):
            return False
        state.stratagem_revealed[controller] = 1
        return self.strat_cancel_story[card]

    cdef void move_slot(self, FastState state, int source, int dest) noexcept:
        cdef int ix
        for ix in range(SCHEME_COUNT):
            if state.scheme_target_slot[ix] == source:
                state.scheme_target_slot[ix] = dest
        state.subject[dest] = state.subject[source]
        state.link[dest] = state.link[source]
        state.name[dest] = state.name[source]
        state.temporary[dest] = state.temporary[source]
        state.maneuver_count[dest] = state.maneuver_count[source]
        state.subject[source] = -1
        state.link[source] = -1
        state.name[source] = -1
        state.temporary[source] = 0
        state.maneuver_count[source] = 0

    cdef void swap_slots(self, FastState state, int a, int b) noexcept:
        cdef int ix
        for ix in range(SCHEME_COUNT):
            if state.scheme_target_slot[ix] == a:
                state.scheme_target_slot[ix] = b
            elif state.scheme_target_slot[ix] == b:
                state.scheme_target_slot[ix] = a
        cdef int8_t force = state.subject[a]
        cdef int8_t bond = state.link[a]
        cdef int8_t name = state.name[a]
        cdef int16_t temporary = state.temporary[a]
        cdef uint8_t maneuvers = state.maneuver_count[a]
        state.subject[a] = state.subject[b]
        state.link[a] = state.link[b]
        state.name[a] = state.name[b]
        state.temporary[a] = state.temporary[b]
        state.maneuver_count[a] = state.maneuver_count[b]
        state.subject[b] = force
        state.link[b] = bond
        state.name[b] = name
        state.temporary[b] = temporary
        state.maneuver_count[b] = maneuvers

    cdef void resolve_plot(self, FastState state, int actor, int card, int pos, int dest):
        cdef int effect = self.plot_effect[card]
        cdef int owner
        if effect == PLOT_DISCREDIT:
            owner = owner_from_slot(pos)
            if state.link[pos] >= 0:
                self.remove_link(state, owner, pos)
            elif state.subject[pos] >= 0:
                state.temporary[pos] -= 2
        elif effect == PLOT_RETURN_NAME:
            owner = owner_from_slot(pos)
            if state.name[pos] >= 0:
                card = state.name[pos]
                state.name[pos] = -1
                self.return_to_hand(state, owner, card)
            elif state.subject[pos] >= 0:
                state.temporary[pos] -= 2
        elif effect == PLOT_MOVE_SUBJECT:
            self.move_slot(state, pos, dest)

    cdef void discard_ongoing_narrative(
        self,
        FastState state,
        int controller,
        int story_slot,
    ) noexcept:
        cdef int ix = controller * 4 + story_slot
        cdef int card = state.scheme[ix]
        if card < 0:
            return
        state.scheme[ix] = -1
        state.scheme_revealed[ix] = 0
        state.scheme_front_mask[ix] = 0
        state.scheme_target_slot[ix] = -1
        state.scheme_used[ix] = 0
        self.compact_ongoing_stories(state, controller)
        self.append_discard(state, controller, card, True)

    cdef void resolve_named_narratives(
        self,
        FastState state,
        int named_player,
    ) noexcept:
        cdef int controller, story_slot, ix, card, trigger, amount
        for controller in range(2):
            story_slot = self.ongoing_story_limit - 1
            while story_slot >= 0:
                ix = controller * 4 + story_slot
                card = state.scheme[ix]
                if card >= 0:
                    trigger = self.narrative_trigger[card]
                    if (
                        (controller == named_player and trigger == NARR_TRIGGER_FRIENDLY_NAMED)
                        or (
                            controller != named_player
                            and trigger == NARR_TRIGGER_OPPONENT_NAMED
                        )
                    ):
                        amount = self.narrative_trigger_gain[card]
                        if amount:
                            self.gain_command_fast(state, controller, amount)
                        if self.narrative_trigger_discard[card]:
                            self.discard_ongoing_narrative(
                                state, controller, story_slot
                            )
                story_slot -= 1

    cdef void resolve_retreat_narratives(
        self,
        FastState state,
        int player,
    ) noexcept:
        cdef int story_slot, ix, card, amount
        story_slot = self.ongoing_story_limit - 1
        while story_slot >= 0:
            ix = player * 4 + story_slot
            card = state.scheme[ix]
            if (
                card >= 0
                and self.narrative_trigger[card] == NARR_TRIGGER_FRIENDLY_RETREAT
            ):
                amount = self.narrative_trigger_gain[card]
                if amount:
                    self.gain_command_fast(state, player, amount)
                if self.narrative_trigger_discard[card]:
                    self.discard_ongoing_narrative(
                        state, player, story_slot
                    )
            story_slot -= 1

    cdef void resolve_force_pair_narratives(
        self,
        FastState state,
        int force_player,
    ) noexcept:
        cdef int controller = 1 - force_player
        cdef int front, story_slot, ix, card, amount
        cdef bint pair_exists = False
        for front in range(4):
            if (
                state.subject[slot_index(force_player, front, 0)] >= 0
                and state.subject[slot_index(force_player, front, 1)] >= 0
            ):
                pair_exists = True
                break
        if not pair_exists:
            return
        story_slot = self.ongoing_story_limit - 1
        while story_slot >= 0:
            ix = controller * 4 + story_slot
            card = state.scheme[ix]
            if (
                card >= 0
                and self.narrative_trigger[card]
                == NARR_TRIGGER_OPPONENT_BOTH_RANKS
            ):
                amount = self.narrative_trigger_gain[card]
                if amount:
                    self.gain_command_fast(state, controller, amount)
                if self.narrative_trigger_discard[card]:
                    self.discard_ongoing_narrative(
                        state, controller, story_slot
                    )
            story_slot -= 1

    cdef void resolve_maneuver_into_empty_narratives(
        self,
        FastState state,
        int player,
    ) noexcept:
        cdef int story_slot, ix, card, amount
        for story_slot in range(self.ongoing_story_limit):
            ix = player * 4 + story_slot
            card = state.scheme[ix]
            if card < 0 or state.scheme_used[ix]:
                continue
            amount = self.narrative_maneuver_empty_gain[card]
            if amount <= 0:
                continue
            state.scheme_used[ix] = 1
            self.gain_command_fast(state, player, amount)

    cdef void resolve_plot_target_scheme(self, FastState state, int actor, int pos):
        cdef int opponent = 1 - actor
        cdef int front, ix, card
        if pos < 0 or owner_from_slot(pos) != opponent:
            return
        front = front_from_slot(pos)
        ix = opponent * 4 + front
        card = state.scheme[ix]
        if card < 0 or self.scheme_trigger[card] != EVENT_PLOT_TARGET:
            return
        if self.scheme_requires_subject[card] and not self.front_has_subject(state, opponent, front):
            return
        self.reveal_scheme(state, opponent, front, actor, -1)

    cdef void reshuffle_discard_into_deck(
        self,
        FastState state,
        int player,
    ) noexcept:
        cdef int i, j, card
        cdef uint32_t seed
        if (
            state.deck_len[player] > 0
            or state.discard_len[player] == 0
        ):
            return
        state.deck_reshuffles[player] += 1
        state.reshuffle_card_totals[player] += state.discard_len[player]
        state.reshuffle_hand_card_totals[player] += state.hand_len[player]
        for i in range(state.discard_len[player]):
            card = state.discard[player][i]
            state.deck[player][state.deck_len[player]] = card
            state.deck_len[player] += 1
            state.deck_counts[player][card] += 1
        state.discard_len[player] = 0
        seed = state.shuffle_seed
        i = state.deck_len[player] - 1
        while i > 0:
            seed = self.next_shuffle_seed(seed)
            j = seed % (i + 1)
            card = state.deck[player][i]
            state.deck[player][i] = state.deck[player][j]
            state.deck[player][j] = card
            i -= 1
        state.shuffle_seed = seed

    cdef void draw(self, FastState state, int player, int count) noexcept:
        cdef int card
        while count > 0:
            if state.deck_len[player] == 0:
                self.reshuffle_discard_into_deck(state, player)
            if state.deck_len[player] == 0:
                break
            state.deck_len[player] -= 1
            card = state.deck[player][state.deck_len[player]]
            state.deck_counts[player][card] -= 1
            state.hand[player][card] += 1
            state.hand_len[player] += 1
            count -= 1

    cdef void draw_for_battle(
        self,
        FastState state,
        int player,
        int count,
    ) noexcept:
        cdef int before = state.hand_len[player]
        self.draw(state, player, count)
        state.cards_drawn_this_battle[player] += state.hand_len[player] - before

    cdef void queue_battle_draws(
        self,
        FastState state,
        int player,
        int count,
    ) noexcept:
        """Process draws one at a time and pause for discard at hand limit."""
        if count <= 0:
            return
        if state.cleanup_pending:
            state.pending_draw_count += count
            return
        state.pending_draw_count = 0
        while count > 0 and self.can_draw_fast(state, player):
            if state.hand_len[player] >= self.hand_limit:
                state.active_player = player
                state.cleanup_pending = 1
                state.pending_draw_count = count
                return
            self.draw_for_battle(state, player, 1)
            count -= 1

    cdef void start_turn_fast(self, FastState state, int player) noexcept:
        state.active_player = player
        state.cards_played_this_turn_front_mask[player] = 0
        state.cleanup_pending = 0
        state.pending_draw_count = 0
        state.pending_draw_finish_operation = 0
        if state.phase == PHASE_BATTLE:
            self.queue_battle_draws(state, player, 1)

    cpdef initialize_opening_turn(
        self,
        FastState state,
        int active_player,
        bint opening_bonus=True,
    ):
        state.active_player = active_player
        if not opening_bonus:
            return
        self.start_turn_fast(state, active_player)

    cdef inline void clear_pass_sequence_fast(
        self,
        FastState state,
    ) noexcept:
        state.passed[0] = 0
        state.passed[1] = 0
        state.pass_len = 0
        state.pass_order[0] = -1
        state.pass_order[1] = -1

    cdef void finish_operation_fast(self, FastState state, int actor):
        cdef int opponent = 1 - actor
        state.operations_this_battle[actor] += 1

        # Any non-Pass operation breaks a pending consecutive-Pass sequence.
        if state.pass_len > 0:
            self.clear_pass_sequence_fast(state)

        self.start_turn_fast(state, opponent)
        state.turn_number += 1

    cdef inline uint32_t next_shuffle_seed(self, uint32_t seed) noexcept:
        return seed * <uint32_t>1664525 + <uint32_t>1013904223

    cdef void discard_slot_components(
        self,
        FastState state,
        int player,
        int slot,
    ) noexcept:
        cdef int card
        card = state.subject[slot]
        if card >= 0:
            self.append_discard(state, player, card, False)
        card = state.link[slot]
        if card >= 0:
            self.append_discard(state, player, card, False)
        card = state.name[slot]
        if card >= 0:
            self.append_discard(state, player, card, False)
        state.subject[slot] = -1
        state.link[slot] = -1
        state.name[slot] = -1
        state.temporary[slot] = 0
        state.maneuver_count[slot] = 0

    cdef void drive_off_slot(
        self,
        FastState state,
        int player,
        int slot,
    ) noexcept:
        """Drive off one complete formation, applying printed persistence text."""
        cdef int force = state.subject[slot]
        cdef int bond = state.link[slot]
        cdef int name = state.name[slot]

        if force >= 0:
            self.append_discard(state, player, force, False)

        if bond >= 0:
            if self.driven_bond_stays[bond]:
                # Stayed Behind For remains as a prepared Bond after the Force
                # is driven off; its Name is returned rather than discarded.
                state.subject[slot] = -1
                if name >= 0:
                    self.return_to_hand(state, player, name)
                state.name[slot] = -1
                state.temporary[slot] = 0
                state.maneuver_count[slot] = 0
                return
            if self.driven_bond_returns[bond]:
                self.return_to_hand(state, player, bond)
            else:
                self.append_discard(state, player, bond, False)

        if name >= 0:
            if self.driven_name_returns[name]:
                self.return_to_hand(state, player, name)
            else:
                self.append_discard(state, player, name, False)

        state.subject[slot] = -1
        state.link[slot] = -1
        state.name[slot] = -1
        state.temporary[slot] = 0
        state.maneuver_count[slot] = 0

    cdef void retreat_slot(
        self,
        FastState state,
        int player,
        int source,
        int destination,
    ) noexcept:
        """Move a formation by Retreat and apply mandatory Retreat text."""
        cdef int bond = state.link[source]
        self.move_slot(state, source, destination)
        self.resolve_retreat_narratives(state, player)
        if bond >= 0 and self.retreat_command_gain[bond] > 0:
            self.gain_command_fast(
                state,
                player,
                self.retreat_command_gain[bond],
            )

    cdef void discard_incomplete_formations(self, FastState state) noexcept:
        cdef int player, slot
        for player in range(2):
            for slot in range(player * 8, player * 8 + 8):
                if (
                    state.subject[slot] >= 0
                    or state.link[slot] >= 0
                    or state.name[slot] >= 0
                ) and not self.slot_complete(state, slot):
                    self.discard_slot_components(state, player, slot)

    cdef void resolve_retreats(
        self,
        FastState state,
        int losses0,
        int losses1,
        int drive0,
        int drive1,
    ) noexcept:
        cdef int player, front, front_slot, rear_slot
        cdef bint lost
        for player in range(2):
            for front in range(4):
                lost = (
                    (player == 0 and (losses0 & (1 << front)) != 0)
                    or (player == 1 and (losses1 & (1 << front)) != 0)
                )
                if not lost:
                    continue
                front_slot = slot_index(player, front, 0)
                rear_slot = slot_index(player, front, 1)

                # Rear is driven off first, then a surviving Frontline Named
                # Formation retreats into the now-empty Rear.
                if self.slot_complete(state, rear_slot):
                    self.drive_off_slot(state, player, rear_slot)
                if self.slot_complete(state, front_slot):
                    if (
                        (player == 0 and (drive0 & (1 << front)) != 0)
                        or (player == 1 and (drive1 & (1 << front)) != 0)
                    ):
                        self.drive_off_slot(state, player, front_slot)
                    else:
                        self.retreat_slot(state, player, front_slot, rear_slot)

    cdef void discard_battle_stratagems(self, FastState state) noexcept:
        cdef int player, card
        for player in range(2):
            card = state.stratagem[player]
            if card >= 0:
                self.append_discard(state, player, card, False)
            state.stratagem[player] = -1
            state.stratagem_revealed[player] = 0
            state.stratagem_front_mask[player] = 0
            state.stratagem_direction[player] = 0
            state.stratagem_target_mask[player] = 0

    cdef inline void clear_battle_temporary_strength(
        self,
        FastState state,
    ) noexcept:
        cdef int slot
        for slot in range(SLOT_COUNT):
            state.temporary[slot] = 0

    cdef inline int command_recovery_fast(
        self,
        int battle,
    ) noexcept:
        cdef int index = battle - 1
        if index < 0 or index >= self.command_recovery_len:
            return 0
        return self.command_recovery_values[index]

    cdef int command_recovery_for_battle(
        self,
        int battle,
    ):
        return self.command_recovery_fast(battle)

    cdef void begin_next_battle_fast(
        self,
        FastState state,
        int starter,
    ) noexcept:
        cdef int p
        state.cleanup_pending = 0
        state.phase = PHASE_BATTLE
        for p in range(2):
            state.battle_start_hand_size[p] = state.hand_len[p]
        self.start_turn_fast(state, starter)

    cdef void score_battle(self, FastState state):
        """Resolve four independent Fronts and the Battle-end sequence."""
        cdef int front, a, b, p, first_passer, strat, protected, card
        cdef int controller, mask, combined0, combined1
        cdef int lost_mask0=0, lost_mask1=0
        cdef int drive_mask0=0, drive_mask1=0
        cdef int losses0=0, losses1=0
        cdef int recovery_losses0=0, recovery_losses1=0
        cdef int base_recovery, actual, target
        cdef bint tie_control = self.tie_control_active(state)

        state.last_battle_valid = 1
        state.last_battle = state.battle
        state.last_pass_len = state.pass_len

        for p in range(2):
            state.last_pass_order[p] = (
                state.pass_order[p] if p < state.pass_len else -1
            )
            state.last_command_start[p] = state.battle_start_command[p]
            state.last_command_spent[p] = state.command_spent_this_battle[p]
            state.last_command_refunded[p] = state.command_refunded_this_battle[p]
            state.last_battle_start_hand_size[p] = state.battle_start_hand_size[p]
            state.last_cards_drawn[p] = state.cards_drawn_this_battle[p]
            state.last_completion_count[p] = state.completion_count_this_battle[p]
            state.last_operations[p] = state.operations_this_battle[p]

        # Front results are fixed before any cleanup or Retreat changes board
        # Strength. There is intentionally no overall Battle winner.
        for front in range(4):
            a = self.resolution_front_strength_fast(state, 0, front)
            b = self.resolution_front_strength_fast(state, 1, front)
            state.last_front_scores[front][0] = a
            state.last_front_scores[front][1] = b
            if a < b:
                lost_mask0 |= 1 << front
                losses0 += 1
            elif b < a:
                lost_mask1 |= 1 << front
                losses1 += 1
            elif tie_control:
                if self.slot_complete(state, slot_index(0, front, 0)) != self.slot_complete(state, slot_index(1, front, 0)):
                    if self.slot_complete(state, slot_index(0, front, 0)):
                        lost_mask1 |= 1 << front
                        losses1 += 1
                    else:
                        lost_mask0 |= 1 << front
                        losses0 += 1

        # The Center Must Hold resolves its chosen adjacent pair as one
        # combined Strength comparison.
        for controller in range(2):
            strat = state.stratagem[controller]
            if strat < 0 or not self.strat_combine_fronts[strat]:
                continue
            mask = state.stratagem_front_mask[controller] & 15
            if popcount16(mask) != 2:
                continue
            combined0 = 0
            combined1 = 0
            for front in range(4):
                if mask & (1 << front):
                    combined0 += self.resolution_front_strength_fast(
                        state, 0, front
                    )
                    combined1 += self.resolution_front_strength_fast(
                        state, 1, front
                    )
            lost_mask0 &= ~mask
            lost_mask1 &= ~mask
            if combined0 < combined1:
                lost_mask0 |= mask
            elif combined1 < combined0:
                lost_mask1 |= mask

        losses0 = popcount16(lost_mask0 & 15)
        losses1 = popcount16(lost_mask1 & 15)

        # Breakthrough effects replace the losing Frontline Named
        # Formation's Retreat when the winner has the printed effect and the
        # loser has no Rear Force in that Front.
        for front in range(4):
            if (
                lost_mask0 & (1 << front)
                and state.subject[slot_index(0, front, 1)] < 0
                and self.breakthrough_active(state, 1, front)
            ):
                drive_mask0 |= 1 << front
            if (
                lost_mask1 & (1 << front)
                and state.subject[slot_index(1, front, 1)] < 0
                and self.breakthrough_active(state, 0, front)
            ):
                drive_mask1 |= 1 << front

        # No Step Back drives off the losing Frontline Named Formation on its
        # chosen Front for either player.
        for controller in range(2):
            strat = state.stratagem[controller]
            if strat >= 0 and self.strat_no_retreat[strat]:
                mask = state.stratagem_front_mask[controller] & 15
                drive_mask0 |= lost_mask0 & mask
                drive_mask1 |= lost_mask1 & mask

        # The Trap Closed replaces Retreat on the middle Front of a won
        # three-Front encirclement.
        strat = state.stratagem[0]
        if strat >= 0 and self.strat_encirclement[strat]:
            if (lost_mask1 & 7) == 7:
                drive_mask1 |= 1 << 1
            if (lost_mask1 & 14) == 14:
                drive_mask1 |= 1 << 2
        strat = state.stratagem[1]
        if strat >= 0 and self.strat_encirclement[strat]:
            if (lost_mask0 & 7) == 7:
                drive_mask0 |= 1 << 1
            if (lost_mask0 & 14) == 14:
                drive_mask0 |= 1 << 2

        # Lock in recovery-loss modifiers from the board and public
        # Stratagems that existed when the Front results were determined.
        # Retreat/drive-off and Stratagem discard happen afterwards.
        recovery_losses0 = losses0
        recovery_losses1 = losses1
        for front in range(4):
            if lost_mask0 & (1 << front):
                protected = 0
                for p in range(2):
                    card = state.subject[slot_index(0, front, p)]
                    if card >= 0 and self.recovery_protected_front[card]:
                        protected = 1
                if protected and recovery_losses0 > 0:
                    recovery_losses0 -= 1
            if lost_mask1 & (1 << front):
                protected = 0
                for p in range(2):
                    card = state.subject[slot_index(1, front, p)]
                    if card >= 0 and self.recovery_protected_front[card]:
                        protected = 1
                if protected and recovery_losses1 > 0:
                    recovery_losses1 -= 1

        strat = state.stratagem[0]
        if strat >= 0 and self.strat_recovery_loss_reduction[strat]:
            recovery_losses0 -= min(
                recovery_losses0,
                self.strat_recovery_loss_reduction[strat],
            )
        strat = state.stratagem[1]
        if strat >= 0 and self.strat_recovery_loss_reduction[strat]:
            recovery_losses1 -= min(
                recovery_losses1,
                self.strat_recovery_loss_reduction[strat],
            )

        self.discard_incomplete_formations(state)
        self.resolve_retreats(
            state,
            lost_mask0,
            lost_mask1,
            drive_mask0,
            drive_mask1,
        )
        self.discard_battle_stratagems(state)
        self.clear_battle_temporary_strength(state)

        # Ongoing Narratives remain in play unless their own Battle-end text
        # has ended them.

        base_recovery = self.command_recovery_for_battle(state.battle)
        for p in range(2):
            actual = base_recovery - (
                recovery_losses0 if p == 0 else recovery_losses1
            )
            if actual < 0:
                actual = 0
            state.command[p] += actual
            if state.command[p] > self.command_cap:
                state.command[p] = self.command_cap
            state.last_command_remaining[p] = state.command[p]
            state.last_deck_remaining[p] = state.deck_len[p]
            state.last_hand_size[p] = state.hand_len[p]

        # Command Collapse: if either side is below the threshold, the lower
        # Command total loses. Equal totals continue exactly as written.
        if (
            state.command[0] < self.command_collapse_threshold
            or state.command[1] < self.command_collapse_threshold
        ):
            if state.command[0] < state.command[1]:
                state.phase = PHASE_COMPLETE
                state.winner = 1
            elif state.command[1] < state.command[0]:
                state.phase = PHASE_COMPLETE
                state.winner = 0
            if state.phase == PHASE_COMPLETE:
                state.cleanup_pending = 0
                return

        first_passer = (
            state.pass_order[0]
            if state.pass_len > 0
            else state.active_player
        )

        state.battle += 1
        state.cleanup_pending = 0
        state.pass_len = 0
        state.pass_order[0] = -1
        state.pass_order[1] = -1

        for p in range(2):
            state.passed[p] = 0
            state.discarded_this_battle[p] = 0
            state.operations_this_battle[p] = 0
            state.cards_played_this_turn_front_mask[p] = 0
            state.cards_played_this_battle_front_mask[p] = 0
            state.narratives_played_this_battle[p] = 0
            state.command_spent_this_battle[p] = 0
            state.command_refunded_this_battle[p] = 0
            state.cards_drawn_this_battle[p] = 0
            state.completion_count_this_battle[p] = 0
            state.stratagem_used[p] = 0
            state.hero_used[p] = 0
            for front in range(self.ongoing_story_limit):
                state.scheme_used[p * 4 + front] = 0
            for front in range(8):
                state.maneuver_count[p * 8 + front] = 0

            # Hand/deck/discard persist. Refill only to 10; draw() reshuffles
            # discard only if the draw pile is actually empty.
            target = self.hand_limit - state.hand_len[p]
            if target > 0:
                self.draw(state, p, target)
            state.battle_start_command[p] = state.command[p]

        self.begin_next_battle_fast(state, first_passer)

    cdef void pass_action(self, FastState state, int player):
        cdef int opponent = 1 - player

        state.passed[player] = 1
        state.pass_order[state.pass_len] = player
        state.pass_len += 1
        self.resolve_strat_event(state, EVENT_PASS, player)

        if state.pass_len >= 2:
            self.score_battle(state)
        else:
            # A first Pass hands the opponent a completely normal turn.
            self.start_turn_fast(state, opponent)

        state.turn_number += 1

    cdef void apply_fast(self, FastState state, uint64_t action):
        cdef int kind = action_kind(action)
        cdef int card = action_card(action)
        cdef int pos = action_pos(action)
        cdef int dest = action_dest(action)
        cdef int actor = state.active_player
        cdef int front, before_mask = 0, cost = 0, source, target, local, choice
        cdef uint32_t extra = action_extra(action)
        cdef bint cancelled

        if kind == TYPE_PASS:
            self.pass_action(state, actor)
            return

        if kind == TYPE_DISCARD:
            if not state.cleanup_pending:
                raise ValueError("Discard is only legal before a mandatory draw")
            self.take_from_hand(state, actor, card, 0)
            self.append_discard(state, actor, card, False)
            state.cleanup_pending = 0
            if state.pending_draw_count > 0:
                state.pending_draw_count -= 1
            self.draw_for_battle(state, actor, 1)
            if state.pending_draw_count > 0:
                self.queue_battle_draws(
                    state,
                    actor,
                    state.pending_draw_count,
                )
                if state.cleanup_pending:
                    return
            if state.pending_draw_finish_operation:
                state.pending_draw_finish_operation = 0
                self.finish_operation_fast(state, actor)
            return

        cost = self.command_cost_fast(state, action)
        self.spend_command_fast(state, actor, cost)

        if kind == TYPE_MANEUVER:
            target = 1 if state.subject[dest] < 0 else 0
            self.swap_slots(state, pos, dest)
            state.maneuver_count[dest] += 1
            if target:
                self.resolve_maneuver_into_empty_narratives(state, actor)
            self.resolve_force_pair_narratives(state, actor)
            self.finish_operation_fast(state, actor)
            return

        if kind == TYPE_SUBJECT or kind == TYPE_LINK or kind == TYPE_NAME:
            before_mask = self.complete_mask(state, actor)
            front = front_from_slot(pos)
            state.cards_played_this_turn_front_mask[actor] |= 1 << front
            state.cards_played_this_battle_front_mask[actor] |= 1 << front
        if (kind == TYPE_SUBJECT or kind == TYPE_NAME) and card >= 0 and self.hero[card]:
            state.hero_used[actor] = 1

        if kind == TYPE_SUBJECT:
            self.take_from_hand(state, actor, card, 0)
            state.subject[pos] = card
            self.resolve_force_pair_narratives(state, actor)
            front = front_from_slot(pos)
            self.resolve_scheme_event(state, actor, EVENT_SUBJECT, front, pos)
            self.resolve_strat_event(state, EVENT_SUBJECT, actor, card, pos)

        elif kind == TYPE_LINK:
            self.take_from_hand(state, actor, card, 0)
            state.link[pos] = card
            if state.subject[pos] >= 0:
                state.temporary[pos] += self.on_link_bonus[state.subject[pos]]
            if dest >= 0:
                self.move_slot(state, pos, dest)
                pos = dest
                self.resolve_force_pair_narratives(state, actor)
            if extra and self.bond_optional_draw_count[card] > 0:
                self.queue_battle_draws(
                    state,
                    actor,
                    self.bond_optional_draw_count[card],
                )
            front = front_from_slot(pos)
            self.resolve_scheme_event(state, actor, EVENT_LINK, front, pos)

        elif kind == TYPE_NAME:
            self.take_from_hand(state, actor, card, 0)
            state.name[pos] = card
            if self.name_effect[card] == NAME_REVEAL_SCHEME:
                front = front_from_slot(pos)
                if state.scheme[(1 - actor) * 4 + front] >= 0:
                    state.scheme_revealed[(1 - actor) * 4 + front] = 1
            elif self.name_effect[card] == NAME_MOVE_ADJACENT and dest >= 0:
                self.move_slot(state, pos, dest)
                pos = dest
            self.resolve_strat_event(state, EVENT_NAME, actor, card, pos)

        elif kind == TYPE_PLOT:
            self.take_from_hand(state, actor, card, 0)
            state.narratives_played_this_battle[actor] += 1
            if extra and self.story_discard_count[card] == 1:
                target = <int>extra - 1
                if target >= 0 and state.hand[actor][target] > 0:
                    self.take_from_hand(state, actor, target, 0)
                    self.append_discard(state, actor, target, True)
                    self.gain_command_fast(
                        state,
                        actor,
                        self.story_discard_gain_command[card],
                    )
            cancelled = self.pre_story_cancel(state, actor)
            if not cancelled:
                self.resolve_plot(state, actor, card, pos, dest)
                self.resolve_plot_target_scheme(state, actor, pos)
            self.append_discard(state, actor, card, True)

        elif kind == TYPE_SCHEME:
            self.take_from_hand(state, actor, card, 0)
            state.narratives_played_this_battle[actor] += 1
            state.scheme[actor * 4 + pos] = card
            state.scheme_revealed[actor * 4 + pos] = 1
            state.scheme_front_mask[actor * 4 + pos] = <uint8_t>(extra & 15)
            state.scheme_target_slot[actor * 4 + pos] = dest

        elif kind == TYPE_STRATAGEM:
            self.take_from_hand(state, actor, card, 0)
            state.stratagem[actor] = card
            state.stratagem_revealed[actor] = 1
            state.stratagem_front_mask[actor] = (
                <uint8_t>pos if pos >= 0 else 0
            )
            state.stratagem_direction[actor] = (
                <uint8_t>(dest + 1) if dest >= 0 else 0
            )
            state.stratagem_target_mask[actor] = <uint16_t>(extra & 0xFFFF)
            state.stratagem_used[actor] = 1

            choice = self.strat_choice_kind[card]
            if choice == STRAT_CHOICE_WHEEL and dest >= 0:
                for source in range(actor * 8, actor * 8 + 8):
                    if not (extra & (<uint32_t>1 << source)):
                        continue
                    local = local_slot(source)
                    front = local >> 1
                    if dest == 0:
                        target = slot_index(actor, front - 1, local & 1)
                    else:
                        target = slot_index(actor, front + 1, local & 1)
                    self.move_slot(state, source, target)
                self.resolve_force_pair_narratives(state, actor)
            elif choice == STRAT_CHOICE_RESERVES:
                for front in range(4):
                    source = slot_index(actor, front, 1)
                    if extra & (<uint32_t>1 << source):
                        target = slot_index(actor, front, 0)
                        self.move_slot(state, source, target)
                self.resolve_force_pair_narratives(state, actor)

            self.finish_operation_fast(state, actor)
            return

        if kind == TYPE_SUBJECT or kind == TYPE_LINK or kind == TYPE_NAME:
            self.resolve_new_completions_fast(state, actor, before_mask)

        if state.cleanup_pending:
            state.pending_draw_finish_operation = 1
            return
        self.finish_operation_fast(state, actor)

    cpdef FastState next_state(self, FastState state, uint64_t action):
        cdef FastState child = state.clone_fast()
        self.apply_fast(child, action)
        return child

    cpdef apply(self, FastState state, uint64_t action):
        self.apply_fast(state, action)

    cdef InfoHash128 state_hash_fast(self, FastState state) noexcept:
        """128-bit hash of all rule/search-relevant perfect-state data."""
        cdef InfoHash128 h
        cdef int p, i, card, slot, ix
        _info_hash_init(&h)
        _info_hash_feed(&h, <uint8_t>(state.phase + 1))
        _info_hash_feed_u16(&h, <uint16_t>state.battle)
        _info_hash_feed(&h, <uint8_t>(state.active_player + 1))
        _info_hash_feed(&h, <uint8_t>(state.winner + 1))
        _info_hash_feed_u32(&h, <uint32_t>state.shuffle_seed)

        for p in range(2):
            _info_hash_feed(&h, state.deck_len[p])
            for i in range(state.deck_len[p]):
                _info_hash_feed(&h, <uint8_t>(state.deck[p][i] + 1))
            for card in range(self.n_cards):
                _info_hash_feed(&h, state.hand[p][card])
            _info_hash_feed(&h, state.hand_len[p])
            _info_hash_feed(&h, state.discard_len[p])
            for i in range(state.discard_len[p]):
                _info_hash_feed(
                    &h,
                    <uint8_t>(state.discard[p][i] + 1),
                )
            _info_hash_feed(&h, state.passed[p])
            _info_hash_feed_u16(&h, <uint16_t>state.command[p])
            _info_hash_feed(&h, state.hero_used[p])
            _info_hash_feed_u16(
                &h,
                state.operations_this_battle[p],
            )
            _info_hash_feed(&h, state.cards_played_this_turn_front_mask[p])
            _info_hash_feed(&h, state.cards_played_this_battle_front_mask[p])
            _info_hash_feed(&h, state.narratives_played_this_battle[p])
            for card in range(self.n_cards):
                _info_hash_feed(
                    &h,
                    state.known_hidden[0][p][card],
                )
                _info_hash_feed(
                    &h,
                    state.known_hidden[1][p][card],
                )

        _info_hash_feed(&h, state.pass_len)
        for i in range(state.pass_len):
            _info_hash_feed(&h, <uint8_t>(state.pass_order[i] + 1))
        for p in range(2):
            _info_hash_feed(&h, state.discarded_this_battle[p])

        for slot in range(SLOT_COUNT):
            _info_hash_feed(&h, <uint8_t>(state.subject[slot] + 1))
            _info_hash_feed(&h, <uint8_t>(state.link[slot] + 1))
            _info_hash_feed(&h, <uint8_t>(state.name[slot] + 1))
            _info_hash_feed_u16(
                &h,
                <uint16_t>state.temporary[slot],
            )
            _info_hash_feed(&h, state.maneuver_count[slot])

        for ix in range(SCHEME_COUNT):
            _info_hash_feed(&h, <uint8_t>(state.scheme[ix] + 1))
            _info_hash_feed(&h, state.scheme_revealed[ix])
            _info_hash_feed(&h, state.scheme_front_mask[ix])
            _info_hash_feed(&h, state.scheme_used[ix])
            _info_hash_feed(&h, <uint8_t>(state.scheme_target_slot[ix] + 1))
        for p in range(2):
            _info_hash_feed(&h, <uint8_t>(state.stratagem[p] + 1))
            _info_hash_feed(&h, state.stratagem_revealed[p])
            _info_hash_feed(&h, state.stratagem_front_mask[p])
            _info_hash_feed(&h, state.stratagem_direction[p])
            _info_hash_feed_u16(&h, state.stratagem_target_mask[p])
            _info_hash_feed(&h, state.stratagem_used[p])

        _info_hash_feed(&h, state.cleanup_pending)
        _info_hash_feed(&h, state.pending_draw_count)
        _info_hash_feed(&h, state.pending_draw_finish_operation)
        return h

    cpdef tuple state_hash(self, FastState state):
        cdef InfoHash128 h = self.state_hash_fast(state)
        return (h.a, h.b)

    cdef int _information_state_encode(
        self,
        FastState state,
        int player,
        unsigned char* buf,
        InfoHash128* h,
    ) noexcept:
        """Single canonical observable-state encoding for imperfect-info AI."""
        cdef int n=0, i, owner, slot, card, story_slot, story_count
        cdef int opponent = 1 - player
        cdef int pending_draw = (
            state.active_player + 1
            if state.cleanup_pending
            else 0
        )

        _info_emit(buf, &n, h, 5)
        _info_emit(buf, &n, h, <uint8_t>player)
        _info_emit(buf, &n, h, <uint8_t>(state.phase + 1))
        _info_emit_u16(buf, &n, h, <uint16_t>state.battle)
        _info_emit(buf, &n, h, <uint8_t>(state.active_player + 1))

        for i in range(2):
            _info_emit(buf, &n, h, state.passed[i])

        _info_emit(buf, &n, h, state.pass_len)
        for i in range(state.pass_len):
            _info_emit(
                buf,
                &n,
                h,
                <uint8_t>(state.pass_order[i] + 1),
            )

        for i in range(2):
            _info_emit(buf, &n, h, state.discarded_this_battle[i])
            _info_emit_u16(
                buf,
                &n,
                h,
                <uint16_t>state.command[i],
            )
            _info_emit(buf, &n, h, state.hero_used[i])
            _info_emit_u16(
                buf,
                &n,
                h,
                state.operations_this_battle[i],
            )
            _info_emit(buf, &n, h, state.cards_played_this_turn_front_mask[i])
            _info_emit(buf, &n, h, state.cards_played_this_battle_front_mask[i])
            _info_emit(buf, &n, h, state.narratives_played_this_battle[i])

        _info_emit(buf, &n, h, <uint8_t>pending_draw)
        _info_emit(buf, &n, h, state.pending_draw_count)
        _info_emit(buf, &n, h, state.pending_draw_finish_operation)

        for owner in range(2):
            for slot in range(owner * 8, owner * 8 + 8):
                _info_emit(
                    buf,
                    &n,
                    h,
                    <uint8_t>(state.subject[slot] + 1),
                )
                _info_emit(
                    buf,
                    &n,
                    h,
                    <uint8_t>(state.link[slot] + 1),
                )
                _info_emit(
                    buf,
                    &n,
                    h,
                    <uint8_t>(state.name[slot] + 1),
                )
                _info_emit_u16(
                    buf,
                    &n,
                    h,
                    <uint16_t>state.temporary[slot],
                )
                _info_emit(buf, &n, h, state.maneuver_count[slot])

        # Ongoing Stories and Stratagems are public in the canonical rules.
        for owner in range(2):
            story_count = 0
            for story_slot in range(self.ongoing_story_limit):
                if state.scheme[owner * 4 + story_slot] >= 0:
                    story_count += 1
            _info_emit(buf, &n, h, <uint8_t>story_count)
            for story_slot in range(self.ongoing_story_limit):
                card = state.scheme[owner * 4 + story_slot]
                if card >= 0:
                    _info_emit(buf, &n, h, <uint8_t>(card + 1))
                    _info_emit(
                        buf,
                        &n,
                        h,
                        state.scheme_front_mask[owner * 4 + story_slot],
                    )
                    _info_emit(
                        buf,
                        &n,
                        h,
                        state.scheme_used[owner * 4 + story_slot],
                    )
                    _info_emit(
                        buf,
                        &n,
                        h,
                        <uint8_t>(
                            state.scheme_target_slot[owner * 4 + story_slot] + 1
                        ),
                    )

        for owner in range(2):
            card = state.stratagem[owner]
            if card < 0:
                _info_emit(buf, &n, h, 0)
            else:
                _info_emit(buf, &n, h, <uint8_t>(card + 1))
                _info_emit(buf, &n, h, state.stratagem_front_mask[owner])
                _info_emit(buf, &n, h, state.stratagem_direction[owner])
                _info_emit_u16(buf, &n, h, state.stratagem_target_mask[owner])

        for owner in range(2):
            _info_emit(buf, &n, h, state.stratagem_used[owner])

        # Own hidden resources are visible to the acting player.
        for card in range(self.n_cards):
            _info_emit(buf, &n, h, state.hand[player][card])
        for card in range(self.n_cards):
            _info_emit(buf, &n, h, state.deck_counts[player][card])

        _info_emit(buf, &n, h, state.discard_len[player])
        for i in range(state.discard_len[player]):
            _info_emit(
                buf,
                &n,
                h,
                <uint8_t>(state.discard[player][i] + 1),
            )

        # Opponent hidden resources are represented only by observable counts
        # and cards explicitly known to this player.
        _info_emit(buf, &n, h, state.hand_len[opponent])
        for card in range(self.n_cards):
            _info_emit(
                buf,
                &n,
                h,
                state.known_hidden[player][opponent][card],
            )
        _info_emit(buf, &n, h, state.deck_len[opponent])
        _info_emit(buf, &n, h, state.discard_len[opponent])
        for i in range(state.discard_len[opponent]):
            _info_emit(
                buf,
                &n,
                h,
                <uint8_t>(state.discard[opponent][i] + 1),
            )
        return n

    cdef InfoHash128 information_hash_fast(
        self,
        FastState state,
        int player,
    ) noexcept:
        cdef InfoHash128 h
        cdef int n
        _info_hash_init(&h)
        n = self._information_state_encode(
            state,
            player,
            NULL,
            &h,
        )
        return h

    cpdef tuple information_hash(self, FastState state, int player):
        cdef InfoHash128 h = self.information_hash_fast(state, player)
        return (h.a, h.b)

    cdef bytes information_key_fast(self, FastState state, int player):
        cdef unsigned char buf[3 * MAX_CARDS + 2 * MAX_DECK + 128]
        cdef int n = self._information_state_encode(
            state,
            player,
            &buf[0],
            NULL,
        )
        return <bytes>PyBytes_FromStringAndSize(<char*>buf, n)

    cpdef bytes information_key(self, FastState state, int player):
        return self.information_key_fast(state, player)

    cpdef str information_id(self, FastState state, int player):
        return hashlib.sha256(self.information_key_fast(state, player)).hexdigest()

    cpdef str action_key(self, uint64_t action):
        cdef int kind = action_kind(action)
        cdef int card = action_card(action)
        cdef int pos = action_pos(action)
        cdef int dest = action_dest(action)
        cdef int player = action_player(action)
        cdef int choice, mask, slot, front
        cdef uint32_t extra = action_extra(action)
        cdef object key, fronts, targets

        if kind == TYPE_PASS:
            return "pass"
        if kind == TYPE_DISCARD:
            return f"discard:{self.card_ids[card]}"
        if kind == TYPE_MANEUVER:
            return (
                f"maneuver:{front_from_slot(pos)}:"
                f"{'front' if rank_from_slot(pos) == 0 else 'rear'}:"
                f"{front_from_slot(dest)}:"
                f"{'front' if rank_from_slot(dest) == 0 else 'rear'}"
            )
        if kind == TYPE_SUBJECT:
            return (
                f"force:{self.card_ids[card]}:{front_from_slot(pos)}:"
                f"{'front' if rank_from_slot(pos) == 0 else 'rear'}"
            )
        if kind == TYPE_LINK:
            key = (
                f"bond:{self.card_ids[card]}:{front_from_slot(pos)}:"
                f"{'front' if rank_from_slot(pos) == 0 else 'rear'}"
            )
            if dest >= 0:
                key += (
                    f":move:{front_from_slot(dest)}:"
                    f"{'front' if rank_from_slot(dest) == 0 else 'rear'}"
                )
            if extra:
                key += f":extra:{self.bond_optional_extra_cost[card]}"
            return key
        if kind == TYPE_NAME:
            return (
                f"name:{self.card_ids[card]}:{front_from_slot(pos)}:"
                f"{'front' if rank_from_slot(pos) == 0 else 'rear'}"
            )
        if kind == TYPE_SCHEME:
            key = f"story:{self.card_ids[card]}:ongoing:{pos}"
            choice = self.story_choice_kind[card]
            if choice == STORY_CHOICE_FRONT:
                fronts = ""
                for front in range(4):
                    if extra & (1 << front):
                        if fronts:
                            fronts += ","
                        fronts += str(front)
                key += f":fronts:{fronts}"
            elif choice == STORY_CHOICE_NAMED_FORMATION and dest >= 0:
                key += (
                    f":targets:{owner_from_slot(dest)},"
                    f"{front_from_slot(dest)},"
                    f"{'front' if rank_from_slot(dest) == 0 else 'rear'}"
                )
            return key
        if kind == TYPE_STRATAGEM:
            key = f"stratagem:{self.card_ids[card]}"
            choice = self.strat_choice_kind[card]
            if (
                choice == STRAT_CHOICE_FRONT
                or choice == STRAT_CHOICE_ADJACENT_FRONTS
                or choice == STRAT_CHOICE_EDGE_FRONT
            ) and pos >= 0:
                fronts = ""
                for front in range(4):
                    if pos & (1 << front):
                        if fronts:
                            fronts += ","
                        fronts += str(front)
                key += f":fronts:{fronts}"
            if (
                choice == STRAT_CHOICE_DIRECTION
                or choice == STRAT_CHOICE_WHEEL
            ) and dest >= 0:
                key += f":direction:{'left' if dest == 0 else 'right'}"
            if (
                choice == STRAT_CHOICE_WHEEL
                or choice == STRAT_CHOICE_RESERVES
            ) and extra:
                targets = []
                for slot in range(SLOT_COUNT):
                    if extra & (<uint32_t>1 << slot):
                        targets.append(
                            f"{owner_from_slot(slot)},"
                            f"{front_from_slot(slot)},"
                            f"{'front' if rank_from_slot(slot) == 0 else 'rear'}"
                        )
                key += ":targets:" + ";".join(targets)
            return key
        if kind == TYPE_PLOT:
            if extra and self.story_discard_count[card] == 1:
                return (
                    f"story:{self.card_ids[card]}:discard:"
                    f"{self.card_ids[<int>extra - 1]}"
                )
            if dest >= 0:
                return (
                    f"story:{self.card_ids[card]}:"
                    f"{player}:{front_from_slot(pos)}:"
                    f"{'front' if rank_from_slot(pos) == 0 else 'rear'};"
                    f"{player}:{front_from_slot(dest)}:"
                    f"{'front' if rank_from_slot(dest) == 0 else 'rear'}"
                )
            if pos >= 0:
                return (
                    f"story:{self.card_ids[card]}:"
                    f"{player}:{front_from_slot(pos)}:"
                    f"{'front' if rank_from_slot(pos) == 0 else 'rear'}"
                )
            return f"story:{self.card_ids[card]}:"
        raise ValueError("Unknown fast action")

    cpdef dict export_state(self, FastState state):
        cdef int p, f, r, i, card, viewer, owner, ix
        cdef int lost0 = 0
        cdef int lost1 = 0
        cdef object last_snapshot = None

        if state.last_battle_valid:
            for f in range(4):
                if (
                    state.last_front_scores[f][0]
                    < state.last_front_scores[f][1]
                ):
                    lost0 += 1
                elif (
                    state.last_front_scores[f][1]
                    < state.last_front_scores[f][0]
                ):
                    lost1 += 1
            last_snapshot = {
                "battle": state.last_battle,
                "front_scores": [
                    [
                        state.last_front_scores[f][0],
                        state.last_front_scores[f][1],
                    ]
                    for f in range(4)
                ],
                "front_results": [
                    (
                        0
                        if state.last_front_scores[f][0]
                        > state.last_front_scores[f][1]
                        else 1
                        if state.last_front_scores[f][1]
                        > state.last_front_scores[f][0]
                        else None
                    )
                    for f in range(4)
                ],
                "fronts_lost": [lost0, lost1],
                "command_start": [
                    state.last_command_start[0],
                    state.last_command_start[1],
                ],
                "command_spent": [
                    state.last_command_spent[0],
                    state.last_command_spent[1],
                ],
                "command_refunded": [
                    state.last_command_refunded[0],
                    state.last_command_refunded[1],
                ],
                "command_remaining": [
                    state.last_command_remaining[0],
                    state.last_command_remaining[1],
                ],
                "deck_remaining": [
                    state.last_deck_remaining[0],
                    state.last_deck_remaining[1],
                ],
                "hand_size": [
                    state.last_hand_size[0],
                    state.last_hand_size[1],
                ],
                "battle_start_hand_size": [
                    state.last_battle_start_hand_size[0],
                    state.last_battle_start_hand_size[1],
                ],
                "cards_drawn": [
                    state.last_cards_drawn[0],
                    state.last_cards_drawn[1],
                ],
                "completion_count": [
                    state.last_completion_count[0],
                    state.last_completion_count[1],
                ],
                "operations": [
                    state.last_operations[0],
                    state.last_operations[1],
                ],
                "pass_order": [
                    state.last_pass_order[i]
                    for i in range(state.last_pass_len)
                ],
            }

        return {
            "phase": (
                "battle"
                if state.phase == PHASE_BATTLE
                else "complete"
            ),
            "battle": state.battle,
            "active_player": state.active_player,
            "winner": None if state.winner < 0 else state.winner,
            "turn_number": state.turn_number,
            "shuffle_seed": state.shuffle_seed,
            "players": [
                {
                    "deck": [
                        self.card_ids[state.deck[p][i]]
                        for i in range(state.deck_len[p])
                    ],
                    "hand": [
                        self.card_ids[card]
                        for card in range(self.n_cards)
                        for _ in range(state.hand[p][card])
                    ],
                    "discard": [
                        self.card_ids[state.discard[p][i]]
                        for i in range(state.discard_len[p])
                    ],
                    "passed": bool(state.passed[p]),
                    "command": state.command[p],
                }
                for p in range(2)
            ],
            "board": [
                [
                    [
                        {
                            "force": (
                                None
                                if state.subject[slot_index(p, f, r)] < 0
                                else self.card_ids[
                                    state.subject[slot_index(p, f, r)]
                                ]
                            ),
                            "bond": (
                                None
                                if state.link[slot_index(p, f, r)] < 0
                                else self.card_ids[
                                    state.link[slot_index(p, f, r)]
                                ]
                            ),
                            "name": (
                                None
                                if state.name[slot_index(p, f, r)] < 0
                                else self.card_ids[
                                    state.name[slot_index(p, f, r)]
                                ]
                            ),
                            "temporary_strength": (
                                state.temporary[slot_index(p, f, r)]
                            ),
                            "maneuvers_this_battle": (
                                state.maneuver_count[slot_index(p, f, r)]
                            ),
                        }
                        for r in range(2)
                    ]
                    for f in range(4)
                ]
                for p in range(2)
            ],
            "stories": [
                [
                    {
                        "card_id": self.card_ids[state.scheme[p * 4 + i]],
                        "front_mask": state.scheme_front_mask[p * 4 + i],
                        "triggered_this_battle": bool(state.scheme_used[p * 4 + i]),
                        "target_slot": (
                            None
                            if state.scheme_target_slot[p * 4 + i] < 0
                            else state.scheme_target_slot[p * 4 + i]
                        ),
                    }
                    for i in range(self.ongoing_story_limit)
                    if state.scheme[p * 4 + i] >= 0
                ]
                for p in range(2)
            ],
            "stratagems": [
                (
                    None
                    if state.stratagem[p] < 0
                    else {
                        "card_id": self.card_ids[state.stratagem[p]],
                        "front_mask": state.stratagem_front_mask[p],
                        "direction": state.stratagem_direction[p],
                        "target_mask": state.stratagem_target_mask[p],
                    }
                )
                for p in range(2)
            ],
            "stratagem_used": [
                bool(state.stratagem_used[0]),
                bool(state.stratagem_used[1]),
            ],
            "hero_used": [
                bool(state.hero_used[0]),
                bool(state.hero_used[1]),
            ],
            "discarded_this_battle": [
                state.discarded_this_battle[0],
                state.discarded_this_battle[1],
            ],
            "command_spent_this_battle": [
                state.command_spent_this_battle[0],
                state.command_spent_this_battle[1],
            ],
            "command_refunded_this_battle": [
                state.command_refunded_this_battle[0],
                state.command_refunded_this_battle[1],
            ],
            "battle_start_command": [
                state.battle_start_command[0],
                state.battle_start_command[1],
            ],
            "battle_start_hand_size": [
                state.battle_start_hand_size[0],
                state.battle_start_hand_size[1],
            ],
            "cards_drawn_this_battle": [
                state.cards_drawn_this_battle[0],
                state.cards_drawn_this_battle[1],
            ],
            "completion_count_this_battle": [
                state.completion_count_this_battle[0],
                state.completion_count_this_battle[1],
            ],
            "operations_this_battle": [
                state.operations_this_battle[0],
                state.operations_this_battle[1],
            ],
            "cards_played_this_turn_front_mask": [
                state.cards_played_this_turn_front_mask[0],
                state.cards_played_this_turn_front_mask[1],
            ],
            "cards_played_this_battle_front_mask": [
                state.cards_played_this_battle_front_mask[0],
                state.cards_played_this_battle_front_mask[1],
            ],
            "narratives_played_this_battle": [
                state.narratives_played_this_battle[0],
                state.narratives_played_this_battle[1],
            ],
            "deck_reshuffles": [
                state.deck_reshuffles[0],
                state.deck_reshuffles[1],
            ],
            "reshuffle_card_totals": [
                state.reshuffle_card_totals[0],
                state.reshuffle_card_totals[1],
            ],
            "reshuffle_hand_card_totals": [
                state.reshuffle_hand_card_totals[0],
                state.reshuffle_hand_card_totals[1],
            ],
            "pending_draw_discard_for": (
                state.active_player if state.cleanup_pending else None
            ),
            "pending_draw_count": state.pending_draw_count,
            "pending_draw_finish_operation": bool(
                state.pending_draw_finish_operation
            ),
            "pass_order": [
                state.pass_order[i]
                for i in range(state.pass_len)
            ],
            "known_hidden_hand": [
                [
                    {
                        self.card_ids[card]:
                            state.known_hidden[viewer][owner][card]
                        for card in range(self.n_cards)
                        if state.known_hidden[viewer][owner][card]
                    }
                    for owner in range(2)
                ]
                for viewer in range(2)
            ],
            "last_battle_snapshot": last_snapshot,
        }

    cpdef dict debug_snapshot(self, FastState state):
        cdef int p, f, r, slot, i, card
        return {
            "phase": state.phase,
            "battle": state.battle,
            "active_player": state.active_player,
            "winner": state.winner,
            "turn_number": state.turn_number,
            "passed": [bool(state.passed[0]), bool(state.passed[1])],
            "pass_order": [state.pass_order[i] for i in range(state.pass_len)],
            "discarded_this_battle": [state.discarded_this_battle[0], state.discarded_this_battle[1]],
            "command": [state.command[0], state.command[1]],
            "operations_this_battle": [state.operations_this_battle[0], state.operations_this_battle[1]],
            "pending_draw_discard_for": state.active_player if state.cleanup_pending else None,
            "pending_draw_count": state.pending_draw_count,
            "pending_draw_finish_operation": bool(state.pending_draw_finish_operation),
            "hands": [
                {self.card_ids[card]: state.hand[p][card] for card in range(self.n_cards) if state.hand[p][card]}
                for p in range(2)
            ],
            "decks": [
                [self.card_ids[state.deck[p][i]] for i in range(state.deck_len[p])]
                for p in range(2)
            ],
            "discards": [
                [self.card_ids[state.discard[p][i]] for i in range(state.discard_len[p])]
                for p in range(2)
            ],
            "board": [
                [
                    (
                        None if state.subject[slot_index(p, f, r)] < 0 else self.card_ids[state.subject[slot_index(p, f, r)]],
                        None if state.link[slot_index(p, f, r)] < 0 else self.card_ids[state.link[slot_index(p, f, r)]],
                        None if state.name[slot_index(p, f, r)] < 0 else self.card_ids[state.name[slot_index(p, f, r)]],
                        state.temporary[slot_index(p, f, r)],
                    )
                    for f in range(4) for r in range(2)
                ]
                for p in range(2)
            ],
            "schemes": [
                [
                    None if state.scheme[p * 4 + f] < 0 else (self.card_ids[state.scheme[p * 4 + f]], bool(state.scheme_revealed[p * 4 + f]))
                    for f in range(4)
                ]
                for p in range(2)
            ],
            "stratagems": [
                None if state.stratagem[p] < 0 else (self.card_ids[state.stratagem[p]], bool(state.stratagem_revealed[p]))
                for p in range(2)
            ],
            "stratagem_used": [bool(state.stratagem_used[0]), bool(state.stratagem_used[1])],
            "hero_used": [bool(state.hero_used[0]), bool(state.hero_used[1])],
        }

# Keep one compiled extension/shared packed state, but separate policies and
# algorithms physically so rule changes do not invite heuristic/search edits.
include "_heuristic_core.pxi"
include "_alpha_beta_core.pxi"
include "_ismcts_core.pxi"
include "_mccfr_core.pxi"
