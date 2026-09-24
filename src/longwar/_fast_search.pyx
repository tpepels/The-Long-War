# cython: language_level=3, boundscheck=False, wraparound=False, initializedcheck=False, cdivision=True
from libc.stdint cimport int8_t, int16_t, uint8_t, uint16_t, uint32_t, int32_t, uint64_t
from libc.stddef cimport size_t
from libc.string cimport memcpy, memset
from libc.stdlib cimport malloc, free, realloc
from libc.math cimport tanh, log, sqrt
from cpython.bytes cimport PyBytes_FromStringAndSize
import hashlib
import json

DEF MAX_CARDS = 64
DEF MAX_DECK = 64
DEF SLOT_COUNT = 12
DEF SCHEME_COUNT = 6
DEF MAX_ACTIONS = 256
DEF NONE = -1

cdef int PHASE_BATTLE = 0
cdef int PHASE_CHOOSE = 1
cdef int PHASE_COMPLETE = 2

cdef int TYPE_PASS = 0
cdef int TYPE_CHOOSE = 1
cdef int TYPE_SUBJECT = 2
cdef int TYPE_LINK = 3
cdef int TYPE_NAME = 4
cdef int TYPE_PLOT = 5
cdef int TYPE_SCHEME = 6
cdef int TYPE_STRATAGEM = 7
cdef int TYPE_DRAW = 8
cdef int TYPE_CYCLE = 9
cdef int TYPE_DISCARD = 10

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

cdef int NAME_NONE = 0
cdef int NAME_MOVE_ADJACENT = 1
cdef int NAME_REVEAL_SCHEME = 2

cdef int COMPLETE_NONE = 0
cdef int COMPLETE_GAIN_COMMAND = 1
cdef int COMPLETE_FREE_CYCLE = 2
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

cdef inline int slot_index(int player, int front, int rank) noexcept:
    return player * 6 + front * 2 + rank

cdef inline int owner_from_slot(int slot) noexcept:
    return 0 if slot < 6 else 1

cdef inline int local_slot(int slot) noexcept:
    return slot if slot < 6 else slot - 6

cdef inline int front_from_slot(int slot) noexcept:
    return local_slot(slot) >> 1

cdef inline int rank_from_slot(int slot) noexcept:
    return local_slot(slot) & 1

cdef inline uint64_t encode_action(int kind, int card=-1, int pos=-1, int dest=-1, int player=0) noexcept:
    return (
        <uint64_t>(kind & 15)
        | (<uint64_t>(card + 1) << 4)
        | (<uint64_t>(pos + 1) << 11)
        | (<uint64_t>(dest + 1) << 16)
        | (<uint64_t>(player & 1) << 21)
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

    cdef int8_t scheme[SCHEME_COUNT]
    cdef uint8_t scheme_revealed[SCHEME_COUNT]
    cdef int8_t stratagem[2]
    cdef uint8_t stratagem_revealed[2]
    cdef uint8_t stratagem_used[2]
    cdef uint8_t draw_used[2]

    cdef uint8_t known_hidden[2][2][MAX_CARDS]

    cdef uint8_t victories[2]
    cdef uint8_t passed[2]
    cdef int8_t pass_order[2]
    cdef uint8_t pass_len
    cdef uint8_t discarded_this_battle[2]
    cdef int16_t command[2]
    cdef uint8_t free_cycle[2]
    cdef uint16_t operations_this_battle[2]
    cdef int16_t command_spent_this_battle[2]
    cdef int16_t command_refunded_this_battle[2]
    cdef int16_t completion_command_refunded_this_battle[2]
    cdef int16_t battle_start_command[2]
    cdef int16_t battle_start_hand_size[2]
    cdef int16_t cards_drawn_this_battle[2]
    cdef int16_t completion_count_this_battle[2]
    cdef int16_t deck_reshuffles[2]
    cdef int16_t reshuffle_card_totals[2]
    cdef int16_t reshuffle_hand_card_totals[2]
    cdef uint8_t last_battle_valid
    cdef int16_t last_battle
    cdef int8_t last_battle_winner
    cdef int16_t last_front_scores[3][2]
    cdef int16_t last_total_strength
    cdef int16_t last_abs_total_margin
    cdef int16_t last_command_start[2]
    cdef int16_t last_command_spent[2]
    cdef int16_t last_command_refunded[2]
    cdef int16_t last_completion_command_refunded[2]
    cdef int16_t last_command_remaining[2]
    cdef int16_t last_deck_remaining[2]
    cdef int16_t last_hand_size[2]
    cdef int16_t last_battle_start_hand_size[2]
    cdef int16_t last_cards_drawn[2]
    cdef int16_t last_completion_count[2]
    cdef int16_t last_operations[2]
    cdef int8_t last_pass_order[2]
    cdef uint8_t last_pass_len
    cdef int8_t pending_final_operation_for
    cdef uint8_t cleanup_pending
    cdef int8_t cleanup_next_starter
    cdef int8_t cleanup_next_chooser

    cdef int8_t active_player
    cdef int16_t battle
    cdef int8_t phase
    cdef int8_t chooser
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
        memset(self.scheme, 0xff, sizeof(self.scheme))
        memset(self.scheme_revealed, 0, sizeof(self.scheme_revealed))
        memset(self.stratagem, 0xff, sizeof(self.stratagem))
        memset(self.stratagem_revealed, 0, sizeof(self.stratagem_revealed))
        memset(self.stratagem_used, 0, sizeof(self.stratagem_used))
        memset(self.draw_used, 0, sizeof(self.draw_used))
        memset(self.known_hidden, 0, sizeof(self.known_hidden))
        memset(self.victories, 0, sizeof(self.victories))
        memset(self.passed, 0, sizeof(self.passed))
        memset(self.pass_order, 0xff, sizeof(self.pass_order))
        memset(self.discarded_this_battle, 0, sizeof(self.discarded_this_battle))
        memset(self.command, 0, sizeof(self.command))
        memset(self.free_cycle, 0, sizeof(self.free_cycle))
        memset(self.operations_this_battle, 0, sizeof(self.operations_this_battle))
        memset(self.command_spent_this_battle, 0, sizeof(self.command_spent_this_battle))
        memset(self.command_refunded_this_battle, 0, sizeof(self.command_refunded_this_battle))
        memset(self.completion_command_refunded_this_battle, 0, sizeof(self.completion_command_refunded_this_battle))
        memset(self.battle_start_command, 0, sizeof(self.battle_start_command))
        memset(self.battle_start_hand_size, 0, sizeof(self.battle_start_hand_size))
        memset(self.cards_drawn_this_battle, 0, sizeof(self.cards_drawn_this_battle))
        memset(self.completion_count_this_battle, 0, sizeof(self.completion_count_this_battle))
        memset(self.deck_reshuffles, 0, sizeof(self.deck_reshuffles))
        memset(self.reshuffle_card_totals, 0, sizeof(self.reshuffle_card_totals))
        memset(self.reshuffle_hand_card_totals, 0, sizeof(self.reshuffle_hand_card_totals))
        self.last_battle_valid = 0
        self.last_battle = 0
        self.last_battle_winner = -1
        memset(self.last_front_scores, 0, sizeof(self.last_front_scores))
        self.last_total_strength = 0
        self.last_abs_total_margin = 0
        memset(self.last_command_start, 0, sizeof(self.last_command_start))
        memset(self.last_command_spent, 0, sizeof(self.last_command_spent))
        memset(self.last_command_refunded, 0, sizeof(self.last_command_refunded))
        memset(self.last_completion_command_refunded, 0, sizeof(self.last_completion_command_refunded))
        memset(self.last_command_remaining, 0, sizeof(self.last_command_remaining))
        memset(self.last_deck_remaining, 0, sizeof(self.last_deck_remaining))
        memset(self.last_hand_size, 0, sizeof(self.last_hand_size))
        memset(self.last_battle_start_hand_size, 0, sizeof(self.last_battle_start_hand_size))
        memset(self.last_cards_drawn, 0, sizeof(self.last_cards_drawn))
        memset(self.last_completion_count, 0, sizeof(self.last_completion_count))
        memset(self.last_operations, 0, sizeof(self.last_operations))
        memset(self.last_pass_order, 0xff, sizeof(self.last_pass_order))
        self.last_pass_len = 0
        self.pending_final_operation_for = -1
        self.cleanup_pending = 0
        self.cleanup_next_starter = -1
        self.cleanup_next_chooser = -1
        self.pass_len = 0
        self.active_player = 0
        self.battle = 1
        self.phase = PHASE_BATTLE
        self.chooser = -1
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
        memcpy(self.scheme, other.scheme, sizeof(self.scheme))
        memcpy(self.scheme_revealed, other.scheme_revealed, sizeof(self.scheme_revealed))
        memcpy(self.stratagem, other.stratagem, sizeof(self.stratagem))
        memcpy(self.stratagem_revealed, other.stratagem_revealed, sizeof(self.stratagem_revealed))
        memcpy(self.stratagem_used, other.stratagem_used, sizeof(self.stratagem_used))
        memcpy(self.draw_used, other.draw_used, sizeof(self.draw_used))
        memcpy(self.known_hidden, other.known_hidden, sizeof(self.known_hidden))
        memcpy(self.victories, other.victories, sizeof(self.victories))
        memcpy(self.passed, other.passed, sizeof(self.passed))
        memcpy(self.pass_order, other.pass_order, sizeof(self.pass_order))
        memcpy(self.discarded_this_battle, other.discarded_this_battle, sizeof(self.discarded_this_battle))
        memcpy(self.command, other.command, sizeof(self.command))
        memcpy(self.free_cycle, other.free_cycle, sizeof(self.free_cycle))
        memcpy(self.operations_this_battle, other.operations_this_battle, sizeof(self.operations_this_battle))
        memcpy(self.command_spent_this_battle, other.command_spent_this_battle, sizeof(self.command_spent_this_battle))
        memcpy(self.command_refunded_this_battle, other.command_refunded_this_battle, sizeof(self.command_refunded_this_battle))
        memcpy(self.completion_command_refunded_this_battle, other.completion_command_refunded_this_battle, sizeof(self.completion_command_refunded_this_battle))
        memcpy(self.battle_start_command, other.battle_start_command, sizeof(self.battle_start_command))
        memcpy(self.battle_start_hand_size, other.battle_start_hand_size, sizeof(self.battle_start_hand_size))
        memcpy(self.cards_drawn_this_battle, other.cards_drawn_this_battle, sizeof(self.cards_drawn_this_battle))
        memcpy(self.completion_count_this_battle, other.completion_count_this_battle, sizeof(self.completion_count_this_battle))
        memcpy(self.deck_reshuffles, other.deck_reshuffles, sizeof(self.deck_reshuffles))
        memcpy(self.reshuffle_card_totals, other.reshuffle_card_totals, sizeof(self.reshuffle_card_totals))
        memcpy(self.reshuffle_hand_card_totals, other.reshuffle_hand_card_totals, sizeof(self.reshuffle_hand_card_totals))
        self.last_battle_valid = other.last_battle_valid
        self.last_battle = other.last_battle
        self.last_battle_winner = other.last_battle_winner
        memcpy(self.last_front_scores, other.last_front_scores, sizeof(self.last_front_scores))
        self.last_total_strength = other.last_total_strength
        self.last_abs_total_margin = other.last_abs_total_margin
        memcpy(self.last_command_start, other.last_command_start, sizeof(self.last_command_start))
        memcpy(self.last_command_spent, other.last_command_spent, sizeof(self.last_command_spent))
        memcpy(self.last_command_refunded, other.last_command_refunded, sizeof(self.last_command_refunded))
        memcpy(self.last_completion_command_refunded, other.last_completion_command_refunded, sizeof(self.last_completion_command_refunded))
        memcpy(self.last_command_remaining, other.last_command_remaining, sizeof(self.last_command_remaining))
        memcpy(self.last_deck_remaining, other.last_deck_remaining, sizeof(self.last_deck_remaining))
        memcpy(self.last_hand_size, other.last_hand_size, sizeof(self.last_hand_size))
        memcpy(self.last_battle_start_hand_size, other.last_battle_start_hand_size, sizeof(self.last_battle_start_hand_size))
        memcpy(self.last_cards_drawn, other.last_cards_drawn, sizeof(self.last_cards_drawn))
        memcpy(self.last_completion_count, other.last_completion_count, sizeof(self.last_completion_count))
        memcpy(self.last_operations, other.last_operations, sizeof(self.last_operations))
        memcpy(self.last_pass_order, other.last_pass_order, sizeof(self.last_pass_order))
        self.last_pass_len = other.last_pass_len
        self.pending_final_operation_for = other.pending_final_operation_for
        self.cleanup_pending = other.cleanup_pending
        self.cleanup_next_starter = other.cleanup_next_starter
        self.cleanup_next_chooser = other.cleanup_next_chooser
        self.pass_len = other.pass_len
        self.active_player = other.active_player
        self.battle = other.battle
        self.phase = other.phase
        self.chooser = other.chooser
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
    cdef bint draw_action_enabled
    cdef bint recycle_between_battles
    cdef bint command_enabled
    cdef int battle_command_gain
    cdef int command_cap
    cdef int cycle_command_cost
    cdef bint reshuffle_on_empty
    cdef bint automatic_draw
    cdef bint paid_draw_enabled
    cdef int paid_draw_command_cost
    cdef bint paid_draw_consumes_operation
    cdef int automatic_draw_hand_limit
    cdef int battle_end_hand_limit
    cdef bint cycle_enabled
    cdef bint pass_final_operation
    cdef bint pass_requires_both_acted
    cdef bint first_passer_starts_next_battle
    cdef int completion_command_refund
    cdef bint public_stratagems

    cdef int8_t card_type[MAX_CARDS]
    cdef int8_t card_command_cost[MAX_CARDS]
    cdef int8_t adjacent_command_discount[MAX_CARDS]
    cdef int8_t completion_effect[MAX_CARDS]
    cdef int8_t completion_amount[MAX_CARDS]
    cdef uint8_t complete_plot_protection[MAX_CARDS]
    cdef uint8_t legacy_completion_draw[MAX_CARDS]
    cdef int8_t role[MAX_CARDS]
    cdef int8_t strength[MAX_CARDS]
    cdef int8_t placement_rank[MAX_CARDS]
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

    cdef int8_t name_rank_bonus_rank[MAX_CARDS]
    cdef int8_t name_rank_bonus_amount[MAX_CARDS]
    cdef int8_t name_effect[MAX_CARDS]

    cdef int8_t plot_effect[MAX_CARDS]
    cdef uint8_t veiled[MAX_CARDS]
    cdef int8_t scheme_trigger[MAX_CARDS]
    cdef int8_t scheme_effect[MAX_CARDS]
    cdef int8_t scheme_amount[MAX_CARDS]
    cdef uint8_t scheme_requires_subject[MAX_CARDS]
    cdef int8_t scheme_face_bonus[MAX_CARDS]

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
    cdef uint8_t strat_disable_line[MAX_CARDS]
    cdef uint8_t strat_story_lock[MAX_CARDS]
    cdef uint8_t strat_global_story_lock[MAX_CARDS]

    def __cinit__(self):
        memset(self.card_type, 0, sizeof(self.card_type))
        memset(self.card_command_cost, 0, sizeof(self.card_command_cost))
        memset(self.adjacent_command_discount, 0, sizeof(self.adjacent_command_discount))
        memset(self.completion_effect, 0, sizeof(self.completion_effect))
        memset(self.completion_amount, 0, sizeof(self.completion_amount))
        memset(self.complete_plot_protection, 0, sizeof(self.complete_plot_protection))
        memset(self.legacy_completion_draw, 0, sizeof(self.legacy_completion_draw))
        memset(self.role, 0, sizeof(self.role))
        memset(self.strength, 0, sizeof(self.strength))
        memset(self.placement_rank, 0xff, sizeof(self.placement_rank))
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
        memset(self.name_rank_bonus_rank, 0xff, sizeof(self.name_rank_bonus_rank))
        memset(self.name_rank_bonus_amount, 0, sizeof(self.name_rank_bonus_amount))
        memset(self.name_effect, 0, sizeof(self.name_effect))
        memset(self.plot_effect, 0, sizeof(self.plot_effect))
        memset(self.veiled, 0, sizeof(self.veiled))
        memset(self.scheme_trigger, 0, sizeof(self.scheme_trigger))
        memset(self.scheme_effect, 0, sizeof(self.scheme_effect))
        memset(self.scheme_amount, 0, sizeof(self.scheme_amount))
        memset(self.scheme_requires_subject, 0, sizeof(self.scheme_requires_subject))
        memset(self.scheme_face_bonus, 0, sizeof(self.scheme_face_bonus))
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
        memset(self.strat_disable_line, 0, sizeof(self.strat_disable_line))
        memset(self.strat_story_lock, 0, sizeof(self.strat_story_lock))
        memset(self.strat_global_story_lock, 0, sizeof(self.strat_global_story_lock))

    def __init__(self, engine):
        cdef int code, r
        self.card_ids = tuple(engine.cards)
        self.n_cards = len(self.card_ids)
        self.opening_hand_size = int(engine.opening_hand_size)
        self.draw_action_enabled = bool(engine.draw_action_enabled)
        self.recycle_between_battles = bool(engine.recycle_between_battles)
        self.command_enabled = bool(engine.command_enabled)
        self.battle_command_gain = int(engine.battle_command_gain)
        self.command_cap = int(engine.command_cap)
        self.cycle_command_cost = int(engine.cycle_command_cost)
        self.reshuffle_on_empty = bool(engine.reshuffle_on_empty)
        self.automatic_draw = bool(engine.automatic_draw)
        self.paid_draw_enabled = bool(engine.paid_draw_enabled)
        self.paid_draw_command_cost = int(engine.paid_draw_command_cost)
        self.paid_draw_consumes_operation = bool(
            engine.paid_draw_consumes_operation
        )
        self.automatic_draw_hand_limit = (
            -1
            if engine.automatic_draw_hand_limit is None
            else int(engine.automatic_draw_hand_limit)
        )
        self.battle_end_hand_limit = (
            -1
            if engine.battle_end_hand_limit is None
            else int(engine.battle_end_hand_limit)
        )
        self.cycle_enabled = bool(engine.cycle_enabled)
        self.pass_final_operation = bool(engine.pass_final_operation)
        self.pass_requires_both_acted = bool(engine.pass_requires_both_acted)
        self.first_passer_starts_next_battle = bool(engine.first_passer_starts_next_battle)
        self.completion_command_refund = int(engine.completion_command_refund)
        self.public_stratagems = bool(engine.public_stratagems)
        if self.n_cards > MAX_CARDS:
            raise ValueError("Fast MCCFR supports at most 64 card identities")
        self.id_to_code = {card_id: i for i, card_id in enumerate(self.card_ids)}

        type_map = {"subject": CARD_SUBJECT, "link": CARD_LINK, "name": CARD_NAME, "plot": CARD_PLOT, "stratagem": CARD_STRATAGEM}
        role_map = {"swordsman": ROLE_SWORDSMAN, "spearman": ROLE_SPEARMAN, "archer": ROLE_ARCHER, "healer": ROLE_HEALER, "ship": ROLE_SHIP, "stronghold": ROLE_STRONGHOLD}
        name_effect_map = {"move_adjacent_optional": NAME_MOVE_ADJACENT, "reveal_enemy_scheme": NAME_REVEAL_SCHEME}
        completion_effect_map = {
            "gain_command": COMPLETE_GAIN_COMMAND,
            "grant_free_cycle": COMPLETE_FREE_CYCLE,
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

        for code, card_id in enumerate(self.card_ids):
            card = engine.cards[card_id]
            self.card_type[code] = type_map[card["type"]]
            self.role[code] = role_map.get(card.get("role"), ROLE_NONE)
            self.strength[code] = int(card.get("strength", 0))
            rules = card.get("rules", {})
            self.card_command_cost[code] = int(card.get("command_cost", 0))
            self.adjacent_command_discount[code] = int(rules.get("adjacent_command_discount", 0))
            completion = rules.get("on_completion") or {}
            self.completion_effect[code] = completion_effect_map.get(completion.get("effect"), COMPLETE_NONE)
            self.completion_amount[code] = int(completion.get("amount", 1))
            self.complete_plot_protection[code] = bool(rules.get("complete_protection_from_opponent_plot"))
            self.legacy_completion_draw[code] = card_id in engine.completion_draw_names
            placement = rules.get("placement", {}).get("rank")
            self.placement_rank[code] = rank_map.get(placement, -1)

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

            self.link_bonus[code] = int(rules.get("strength_bonus", 0))
            self.link_named_bonus[code] = int(rules.get("named_strength_bonus", 0))
            discard_bonus = rules.get("discard_strength_bonus") or {}
            self.link_discard_per[code] = int(discard_bonus.get("per_card", 0))
            self.link_discard_max[code] = int(discard_bonus.get("maximum", 0))
            self.link_opposing[code] = int(rules.get("opposing_front_modifier", 0))
            self.link_protect[code] = bool(rules.get("protect_subject_from_opponent_plot"))

            rank_bonus = rules.get("rank_strength_bonus") or {}
            self.name_rank_bonus_rank[code] = rank_map.get(rank_bonus.get("rank"), -1)
            self.name_rank_bonus_amount[code] = int(rank_bonus.get("amount", 0))
            self.name_effect[code] = name_effect_map.get(rules.get("on_name_attached"), NAME_NONE)

            self.plot_effect[code] = plot_effect_map.get(rules.get("effect"), PLOT_NONE)
            self.veiled[code] = bool(card.get("veiled", False))
            scheme = rules.get("scheme") or {}
            self.scheme_trigger[code] = scheme_trigger_map.get(scheme.get("trigger"), EVENT_NONE)
            self.scheme_effect[code] = scheme_effect_map.get(scheme.get("effect"), SCHEME_NONE)
            self.scheme_amount[code] = int(scheme.get("amount", 0))
            self.scheme_requires_subject[code] = bool(scheme.get("requires_own_subject"))
            self.scheme_face_bonus[code] = int(scheme.get("face_down_front_bonus", 0))

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
            self.strat_disable_line[code] = bool(continuous.get("disable_line_defense"))
            self.strat_story_lock[code] = bool(continuous.get("controller_immediate_story_lock"))
            self.strat_global_story_lock[code] = bool(continuous.get("global_immediate_story_lock"))

    cpdef FastState from_game_state(self, state):
        cdef FastState fast = FastState()
        cdef int p, i, f, r, slot, code, viewer, owner
        cdef object card_id, py_slot, scheme, strat, counter
        phase_map = {"battle": PHASE_BATTLE, "choose_first": PHASE_CHOOSE, "complete": PHASE_COMPLETE}

        for p in range(2):
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
            fast.victories[p] = state.players[p].victories
            fast.passed[p] = state.players[p].passed
            fast.command[p] = state.players[p].command
            fast.free_cycle[p] = state.players[p].free_cycle
            fast.operations_this_battle[p] = state.operations_this_battle[p]
            fast.command_spent_this_battle[p] = state.command_spent_this_battle[p]
            fast.command_refunded_this_battle[p] = state.command_refunded_this_battle[p]
            fast.completion_command_refunded_this_battle[p] = state.completion_command_refunded_this_battle[p]
            fast.battle_start_command[p] = state.battle_start_command[p]
            fast.battle_start_hand_size[p] = state.battle_start_hand_size[p]
            fast.cards_drawn_this_battle[p] = state.cards_drawn_this_battle[p]
            fast.completion_count_this_battle[p] = state.completion_count_this_battle[p]
            fast.deck_reshuffles[p] = state.deck_reshuffles[p]
            fast.reshuffle_card_totals[p] = state.reshuffle_card_totals[p]
            fast.reshuffle_hand_card_totals[p] = state.reshuffle_hand_card_totals[p]
            fast.discarded_this_battle[p] = state.discarded_this_battle[p]
            fast.stratagem_used[p] = state.stratagem_used[p]
            fast.draw_used[p] = state.draw_used[p]
            strat = state.stratagems[p]
            if strat is not None:
                fast.stratagem[p] = self.id_to_code[strat.card_id]
                fast.stratagem_revealed[p] = strat.revealed

            for f in range(3):
                for r in range(2):
                    slot = slot_index(p, f, r)
                    py_slot = state.board[p][f][r]
                    if py_slot.subject is not None:
                        fast.subject[slot] = self.id_to_code[py_slot.subject]
                    if py_slot.link is not None:
                        fast.link[slot] = self.id_to_code[py_slot.link]
                    if py_slot.name is not None:
                        fast.name[slot] = self.id_to_code[py_slot.name]
                    fast.temporary[slot] = py_slot.temporary_strength
                scheme = state.schemes[p][f]
                if scheme is not None:
                    fast.scheme[p * 3 + f] = self.id_to_code[scheme.card_id]
                    fast.scheme_revealed[p * 3 + f] = scheme.revealed

        fast.active_player = state.active_player
        fast.battle = state.battle
        fast.phase = phase_map[state.phase.value]
        fast.chooser = -1 if state.chooser is None else state.chooser
        fast.winner = -1 if state.winner is None else state.winner
        fast.turn_number = state.turn_number
        fast.shuffle_seed = state.shuffle_seed
        fast.pass_len = len(state.pass_order)
        fast.pending_final_operation_for = (
            -1
            if state.pending_final_operation_for is None
            else state.pending_final_operation_for
        )
        fast.cleanup_pending = bool(state.cleanup_pending)
        fast.cleanup_next_starter = (
            -1
            if state.cleanup_next_starter is None
            else state.cleanup_next_starter
        )
        fast.cleanup_next_chooser = (
            -1
            if state.cleanup_next_chooser is None
            else state.cleanup_next_chooser
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
            fast.last_battle_winner = int(snapshot.get("winner", -1))
            front_scores = snapshot.get("front_scores", ())
            for f in range(min(3, len(front_scores))):
                fast.last_front_scores[f][0] = int(front_scores[f][0])
                fast.last_front_scores[f][1] = int(front_scores[f][1])
            fast.last_total_strength = int(snapshot.get("total_strength", 0))
            fast.last_abs_total_margin = int(snapshot.get("abs_total_margin", 0))
            for p in range(2):
                fast.last_command_start[p] = int(snapshot.get("command_start", (0, 0))[p])
                fast.last_command_spent[p] = int(snapshot.get("command_spent", (0, 0))[p])
                fast.last_command_refunded[p] = int(snapshot.get("command_refunded", (0, 0))[p])
                fast.last_completion_command_refunded[p] = int(
                    snapshot.get("completion_command_refunded", (0, 0))[p]
                )
                fast.last_command_remaining[p] = int(snapshot.get("command_remaining", (0, 0))[p])
                fast.last_deck_remaining[p] = int(snapshot.get("deck_remaining", (0, 0))[p])
                fast.last_hand_size[p] = int(snapshot.get("hand_size", (0, 0))[p])
                fast.last_battle_start_hand_size[p] = int(
                    snapshot.get("battle_start_hand_size", (0, 0))[p]
                )
                fast.last_cards_drawn[p] = int(snapshot.get("cards_drawn", (0, 0))[p])
                fast.last_completion_count[p] = int(snapshot.get("completion_count", (0, 0))[p])
                fast.last_operations[p] = int(snapshot.get("operations", (0, 0))[p])
            pass_snapshot = snapshot.get("pass_order", ())
            fast.last_pass_len = min(2, len(pass_snapshot))
            for i in range(fast.last_pass_len):
                fast.last_pass_order[i] = int(pass_snapshot[i])

        return fast

    cdef inline int hand_size(self, FastState state, int player) noexcept:
        return state.hand_len[player]

    cdef inline bint line_disabled(self, FastState state) noexcept:
        cdef int p, card
        for p in range(2):
            card = state.stratagem[p]
            if card >= 0 and state.stratagem_revealed[p] and self.strat_disable_line[card]:
                return True
        return False

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

        if rank == 0 and not self.line_disabled(state):
            value += 1

        if role == ROLE_SWORDSMAN and rank == 0:
            value += 1
        elif role == ROLE_SPEARMAN and rank == 0:
            rear = slot_index(player, front, 1)
            if state.subject[rear] >= 0:
                value += 1
        elif role == ROLE_ARCHER and rank == 1:
            frontslot = slot_index(player, front, 0)
            if state.subject[frontslot] >= 0:
                value += 2
        elif (role == ROLE_SHIP or role == ROLE_STRONGHOLD) and rank == 1:
            value += 1

        if rank == 0:
            rear = slot_index(player, front, 1)
            if state.subject[rear] >= 0 and self.role[state.subject[rear]] == ROLE_HEALER:
                value += 2

        if front > 0:
            adj = slot_index(player, front - 1, rank)
            other = state.subject[adj]
            if other >= 0 and self.aura[other] and (self.aura_rank[other] < 0 or self.aura_rank[other] == rank):
                value += self.aura[other]
        if front < 2:
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
                    front < 2
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
            value += self.strength[name]
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
        scheme = state.scheme[player * 3 + front]
        if scheme >= 0 and not state.scheme_revealed[player * 3 + front]:
            value += self.scheme_face_bonus[scheme]
        enemy = 1 - player
        for slot in (slot_index(enemy, front, 0), slot_index(enemy, front, 1)):
            if state.subject[slot] >= 0 and state.link[slot] >= 0 and state.name[slot] >= 0:
                link = state.link[slot]
                value += self.link_opposing[link]
        return value

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
            or (self.reshuffle_on_empty and state.discard_len[player] > 0)
        )

    cpdef bint can_draw(self, FastState state, int player):
        return self.can_draw_fast(state, player)

    cdef inline int adjacent_discount_fast(
        self,
        FastState state,
        int player,
        int target_front,
    ) noexcept:
        cdef int local, slot, front, name, discount = 0
        for local in range(6):
            slot = player * 6 + local
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
        cdef int kind, card, pos, target_front=-1, cost, discount
        if not self.command_enabled:
            return 0
        kind = action_kind(action)
        if kind == TYPE_PASS or kind == TYPE_CHOOSE:
            return 0
        if kind == TYPE_DRAW:
            return self.paid_draw_command_cost if self.paid_draw_enabled else 0
        if kind == TYPE_CYCLE:
            return 0 if state.free_cycle[state.active_player] else self.cycle_command_cost
        card = action_card(action)
        if card < 0:
            return 0
        cost = self.card_command_cost[card]
        pos = action_pos(action)
        if kind == TYPE_SUBJECT or kind == TYPE_LINK or kind == TYPE_NAME:
            target_front = front_from_slot(pos)
        elif kind == TYPE_SCHEME:
            target_front = pos
        if target_front >= 0:
            discount = self.adjacent_discount_fast(
                state,
                state.active_player,
                target_front,
            )
            if discount:
                cost -= discount
                if cost < 1:
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
        for local in range(6):
            slot = player * 6 + local
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
        cdef int local, slot, name, effect, amount, front, enemy_ix, command_before
        cdef int after_mask = self.complete_mask(state, player)
        cdef int new_mask = after_mask & ~before_mask
        if new_mask == 0:
            return
        for local in range(6):
            if not (new_mask & (1 << local)):
                continue
            slot = player * 6 + local
            state.completion_count_this_battle[player] += 1
            if self.command_enabled and self.completion_command_refund:
                command_before = state.command[player]
                self.gain_command_fast(
                    state,
                    player,
                    self.completion_command_refund,
                )
                state.completion_command_refunded_this_battle[player] += (
                    state.command[player] - command_before
                )
            name = state.name[slot]
            if name < 0:
                continue
            if self.legacy_completion_draw[name]:
                self.draw(state, player, 1)
            effect = self.completion_effect[name]
            amount = self.completion_amount[name]
            if effect == COMPLETE_GAIN_COMMAND:
                if self.command_enabled:
                    self.gain_command_fast(state, player, amount)
            elif effect == COMPLETE_FREE_CYCLE:
                if self.command_enabled and self.cycle_enabled:
                    state.free_cycle[player] = 1
            elif effect == COMPLETE_DRAW:
                self.draw_for_battle(state, player, amount)
            elif effect == COMPLETE_REVEAL_SCHEME:
                front = local >> 1
                enemy_ix = (1 - player) * 3 + front
                if state.scheme[enemy_ix] >= 0:
                    state.scheme_revealed[enemy_ix] = 1
            elif effect == COMPLETE_RECOVER_LINK:
                self.recover_recent_link_fast(state, player)

    cdef int legal_actions_into(
        self,
        FastState state,
        uint64_t* actions,
    ) except -1:
        cdef int n = 0
        cdef int player, card, slot, local, front, rank, source, dest, req, opponent, effect
        cdef int i, kept, can_pass, available
        cdef uint64_t action

        if state.phase == PHASE_COMPLETE:
            return 0
        if state.phase == PHASE_CHOOSE:
            actions[0] = encode_action(TYPE_CHOOSE, -1, 0, -1, 0)
            actions[1] = encode_action(TYPE_CHOOSE, -1, 1, -1, 0)
            return 2

        player = state.active_player
        if state.cleanup_pending:
            for card in range(self.n_cards):
                if state.hand[player][card] > 0:
                    actions[n] = encode_action(
                        TYPE_DISCARD,
                        card,
                        -1,
                        -1,
                        player,
                    )
                    n += 1
            return n

        player = state.active_player
        opponent = 1 - player

        if (
            (not self.command_enabled)
            and self.draw_action_enabled
            and (not state.draw_used[player])
            and self.can_draw_fast(state, player)
        ):
            actions[n] = encode_action(TYPE_DRAW, -1, -1, -1, player); n += 1
        elif (
            self.command_enabled
            and self.paid_draw_enabled
            and self.can_draw_fast(state, player)
        ):
            actions[n] = encode_action(TYPE_DRAW, -1, -1, -1, player); n += 1

        for card in range(self.n_cards):
            if state.hand[player][card] == 0:
                continue

            if (
                self.command_enabled
                and self.cycle_enabled
                and self.can_draw_fast(state, player)
            ):
                actions[n] = encode_action(TYPE_CYCLE, card, -1, -1, player); n += 1

            if self.card_type[card] == CARD_SUBJECT:
                req = self.placement_rank[card]
                for local in range(6):
                    slot = player * 6 + local
                    if state.subject[slot] >= 0:
                        continue
                    rank = local & 1
                    if req >= 0 and req != rank:
                        continue
                    actions[n] = encode_action(TYPE_SUBJECT, card, slot, -1, player); n += 1

            elif self.card_type[card] == CARD_LINK:
                for local in range(6):
                    slot = player * 6 + local
                    if state.link[slot] < 0:
                        actions[n] = encode_action(TYPE_LINK, card, slot, -1, player); n += 1

            elif self.card_type[card] == CARD_NAME:
                for local in range(6):
                    slot = player * 6 + local
                    if state.name[slot] >= 0:
                        continue
                    actions[n] = encode_action(TYPE_NAME, card, slot, -1, player); n += 1
                    if self.name_effect[card] == NAME_MOVE_ADJACENT and state.subject[slot] >= 0:
                        front = local >> 1
                        rank = local & 1
                        if front > 0:
                            dest = slot_index(player, front - 1, rank)
                            if state.subject[dest] < 0 and state.link[dest] < 0 and state.name[dest] < 0:
                                actions[n] = encode_action(TYPE_NAME, card, slot, dest, player); n += 1
                        if front < 2:
                            dest = slot_index(player, front + 1, rank)
                            if state.subject[dest] < 0 and state.link[dest] < 0 and state.name[dest] < 0:
                                actions[n] = encode_action(TYPE_NAME, card, slot, dest, player); n += 1

            elif self.card_type[card] == CARD_PLOT:
                if self.veiled[card]:
                    for front in range(3):
                        if state.scheme[player * 3 + front] < 0:
                            actions[n] = encode_action(TYPE_SCHEME, card, front, -1, player); n += 1
                elif not self.story_locked(state, player):
                    effect = self.plot_effect[card]
                    if effect == PLOT_DISCREDIT or effect == PLOT_RETURN_NAME:
                        for local in range(6):
                            slot = opponent * 6 + local
                            if state.subject[slot] >= 0 and not self.subject_protected(state, slot):
                                actions[n] = encode_action(TYPE_PLOT, card, slot, -1, opponent); n += 1
                    elif effect == PLOT_MOVE_SUBJECT:
                        for source in range(player * 6, player * 6 + 6):
                            if state.subject[source] < 0:
                                continue
                            req = self.placement_rank[state.subject[source]]
                            for dest in range(player * 6, player * 6 + 6):
                                if (
                                    dest == source
                                    or state.subject[dest] >= 0
                                    or state.link[dest] >= 0
                                    or state.name[dest] >= 0
                                ):
                                    continue
                                if req >= 0 and req != rank_from_slot(dest):
                                    continue
                                actions[n] = encode_action(TYPE_PLOT, card, source, dest, player); n += 1
                    elif effect == PLOT_NONE:
                        actions[n] = encode_action(TYPE_PLOT, card, -1, -1, player); n += 1

            elif self.card_type[card] == CARD_STRATAGEM:
                if not state.stratagem_used[player] and state.stratagem[player] < 0:
                    actions[n] = encode_action(TYPE_STRATAGEM, card, -1, -1, player); n += 1

            if n >= MAX_ACTIONS - 1:
                raise RuntimeError(
                    f"Fast search action buffer exceeded: {n} >= {MAX_ACTIONS - 1}"
                )

        if self.command_enabled:
            available = state.command[player]
            kept = 0
            for i in range(n):
                action = actions[i]
                if self.command_cost_fast(state, action) <= available:
                    actions[kept] = action
                    kept += 1
            n = kept

        can_pass = (
            (not self.pass_requires_both_acted)
            or state.pass_len > 0
            or (
                state.operations_this_battle[0] > 0
                and state.operations_this_battle[1] > 0
            )
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

    cdef void reveal_scheme(self, FastState state, int controller, int front, int actor, int trigger_slot=-1):
        cdef int ix = controller * 3 + front
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
        self.append_discard(state, controller, card, True)

    cdef void resolve_scheme_event(self, FastState state, int actor, int event, int front, int trigger_slot=-1):
        cdef int controller, ix, card
        for controller in (actor, 1 - actor):
            ix = controller * 3 + front
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
        state.subject[dest] = state.subject[source]
        state.link[dest] = state.link[source]
        state.name[dest] = state.name[source]
        state.temporary[dest] = state.temporary[source]
        state.subject[source] = -1
        state.link[source] = -1
        state.name[source] = -1
        state.temporary[source] = 0

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

    cdef void resolve_plot_target_scheme(self, FastState state, int actor, int pos):
        cdef int opponent = 1 - actor
        cdef int front, ix, card
        if pos < 0 or owner_from_slot(pos) != opponent:
            return
        front = front_from_slot(pos)
        ix = opponent * 3 + front
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
            not self.reshuffle_on_empty
            or state.deck_len[player] > 0
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

    cdef void start_turn_fast(self, FastState state, int player) noexcept:
        state.active_player = player
        if (
            self.automatic_draw
            and state.phase == PHASE_BATTLE
            and not state.passed[player]
            and not state.cleanup_pending
            and (
                self.automatic_draw_hand_limit < 0
                or state.hand_len[player] < self.automatic_draw_hand_limit
            )
        ):
            self.draw_for_battle(state, player, 1)

    cpdef initialize_opening_turn(
        self,
        FastState state,
        int active_player,
        bint opening_bonus=True,
    ):
        state.active_player = active_player
        if not opening_bonus:
            return
        if self.automatic_draw:
            self.start_turn_fast(state, active_player)
        elif not self.paid_draw_enabled:
            self.draw(state, active_player, 1)

    cdef void finish_operation_fast(self, FastState state, int actor):
        cdef int opponent = 1 - actor
        state.operations_this_battle[actor] += 1
        if (
            self.pass_final_operation
            and state.pending_final_operation_for == actor
        ):
            state.pending_final_operation_for = -1
            self.score_battle(state)
        elif not state.passed[opponent]:
            self.start_turn_fast(state, opponent)
        state.turn_number += 1

    cdef inline uint32_t next_shuffle_seed(self, uint32_t seed) noexcept:
        return seed * <uint32_t>1664525 + <uint32_t>1013904223

    cdef void recycle_non_hand_cards(self, FastState state):
        cdef int player, i, j, card, target
        cdef uint32_t seed = state.shuffle_seed
        for player in range(2):
            for i in range(state.discard_len[player]):
                card = state.discard[player][i]
                state.deck[player][state.deck_len[player]] = card
                state.deck_len[player] += 1
                state.deck_counts[player][card] += 1
            state.discard_len[player] = 0

            i = state.deck_len[player] - 1
            while i > 0:
                seed = self.next_shuffle_seed(seed)
                j = seed % (i + 1)
                card = state.deck[player][i]
                state.deck[player][i] = state.deck[player][j]
                state.deck[player][j] = card
                i -= 1

            target = self.opening_hand_size - state.hand_len[player]
            if target > 0:
                self.draw(state, player, target)
        state.shuffle_seed = seed

    cdef void discard_battlefield(self, FastState state):
        cdef int player, slot, front, card
        for player in range(2):
            for slot in range(player * 6, player * 6 + 6):
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
            for front in range(3):
                card = state.scheme[player * 3 + front]
                if card >= 0:
                    self.append_discard(state, player, card, False)
                    state.scheme[player * 3 + front] = -1
                    state.scheme_revealed[player * 3 + front] = 0
            card = state.stratagem[player]
            if card >= 0:
                self.append_discard(state, player, card, False)
                state.stratagem[player] = -1
                state.stratagem_revealed[player] = 0

    cdef void begin_next_battle_fast(
        self,
        FastState state,
        int starter,
        int chooser,
    ) noexcept:
        cdef int p
        state.cleanup_pending = 0
        state.cleanup_next_starter = -1
        state.cleanup_next_chooser = -1
        for p in range(2):
            state.battle_start_hand_size[p] = state.hand_len[p]
        if starter >= 0:
            state.phase = PHASE_BATTLE
            state.chooser = -1
            self.start_turn_fast(state, starter)
        else:
            state.phase = PHASE_CHOOSE
            state.chooser = chooser
            state.active_player = chooser

    cdef void advance_cleanup_fast(self, FastState state) noexcept:
        cdef int p
        if self.battle_end_hand_limit < 0:
            self.begin_next_battle_fast(
                state,
                state.cleanup_next_starter,
                state.cleanup_next_chooser,
            )
            return
        for p in range(2):
            if state.hand_len[p] > self.battle_end_hand_limit:
                state.cleanup_pending = 1
                state.phase = PHASE_BATTLE
                state.chooser = -1
                state.active_player = p
                return
        self.begin_next_battle_fast(
            state,
            state.cleanup_next_starter,
            state.cleanup_next_chooser,
        )

    cdef void score_battle(self, FastState state):
        cdef int front, a, b, controls0=0, controls1=0, total0=0, total1=0
        cdef int winner, loser, p, first_passer=-1, target, margin

        state.last_battle_valid = 1
        state.last_battle = state.battle
        state.last_pass_len = state.pass_len
        for p in range(2):
            state.last_pass_order[p] = (
                state.pass_order[p] if p < state.pass_len else -1
            )

        for front in range(3):
            a = self.front_strength_fast(state, 0, front)
            b = self.front_strength_fast(state, 1, front)
            state.last_front_scores[front][0] = a
            state.last_front_scores[front][1] = b
            total0 += a
            total1 += b
            if a > b:
                controls0 += 1
            elif b > a:
                controls1 += 1

        if controls0 >= 2:
            winner = 0
        elif controls1 >= 2:
            winner = 1
        elif total0 > total1:
            winner = 0
        elif total1 > total0:
            winner = 1
        elif state.pass_len > 0:
            winner = state.pass_order[0]
        else:
            winner = state.active_player

        state.last_battle_winner = winner
        state.last_total_strength = total0 + total1
        margin = total0 - total1
        state.last_abs_total_margin = margin if margin >= 0 else -margin
        for p in range(2):
            state.last_command_start[p] = state.battle_start_command[p]
            state.last_command_spent[p] = state.command_spent_this_battle[p]
            state.last_command_refunded[p] = state.command_refunded_this_battle[p]
            state.last_completion_command_refunded[p] = (
                state.completion_command_refunded_this_battle[p]
            )
            state.last_command_remaining[p] = state.command[p]
            state.last_deck_remaining[p] = state.deck_len[p]
            state.last_hand_size[p] = state.hand_len[p]
            state.last_battle_start_hand_size[p] = state.battle_start_hand_size[p]
            state.last_cards_drawn[p] = state.cards_drawn_this_battle[p]
            state.last_completion_count[p] = state.completion_count_this_battle[p]
            state.last_operations[p] = state.operations_this_battle[p]

        if state.pass_len > 0:
            first_passer = state.pass_order[0]

        state.victories[winner] += 1
        loser = 1 - winner
        for p in range(2):
            if state.stratagem[p] >= 0:
                state.stratagem_revealed[p] = 1
        self.discard_battlefield(state)

        if state.victories[winner] >= 2:
            state.phase = PHASE_COMPLETE
            state.winner = winner
            state.chooser = -1
            state.pending_final_operation_for = -1
            return

        state.battle += 1
        for p in range(2):
            state.discarded_this_battle[p] = 0
            state.operations_this_battle[p] = 0
            state.command_spent_this_battle[p] = 0
            state.command_refunded_this_battle[p] = 0
            state.completion_command_refunded_this_battle[p] = 0
            state.cards_drawn_this_battle[p] = 0
            state.completion_count_this_battle[p] = 0
            state.stratagem_used[p] = 0
            state.draw_used[p] = 0
            state.free_cycle[p] = 0
            if self.command_enabled:
                state.command[p] += self.battle_command_gain
                if state.command[p] > self.command_cap:
                    state.command[p] = self.command_cap
                state.battle_start_command[p] = state.command[p]
            else:
                state.battle_start_command[p] = 0

        state.pending_final_operation_for = -1
        state.pass_len = 0
        state.pass_order[0] = -1
        state.pass_order[1] = -1

        if self.recycle_between_battles:
            self.recycle_non_hand_cards(state)
        else:
            for p in range(2):
                target = self.opening_hand_size - state.hand_len[p]
                if target > 0:
                    self.draw(state, p, target)

        for p in range(2):
            state.passed[p] = 0

        state.cleanup_next_starter = (
            first_passer
            if self.first_passer_starts_next_battle and first_passer >= 0
            else -1
        )
        state.cleanup_next_chooser = (
            -1 if state.cleanup_next_starter >= 0 else loser
        )
        if (
            self.battle_end_hand_limit >= 0
            and (
                state.hand_len[0] > self.battle_end_hand_limit
                or state.hand_len[1] > self.battle_end_hand_limit
            )
        ):
            state.cleanup_pending = 1
            self.advance_cleanup_fast(state)
        else:
            self.begin_next_battle_fast(
                state,
                state.cleanup_next_starter,
                state.cleanup_next_chooser,
            )

    cdef void pass_action(self, FastState state, int player):
        cdef int opponent = 1 - player
        cdef int front, ix, card
        state.passed[player] = 1
        state.pass_order[state.pass_len] = player
        state.pass_len += 1
        self.resolve_strat_event(state, EVENT_PASS, player)
        for front in range(3):
            ix = opponent * 3 + front
            card = state.scheme[ix]
            if card >= 0 and self.scheme_trigger[card] == EVENT_PASS:
                if not self.scheme_requires_subject[card] or self.front_has_subject(state, opponent, front):
                    self.reveal_scheme(state, opponent, front, player, -1)

        if self.pass_final_operation:
            if state.pending_final_operation_for == player:
                state.operations_this_battle[player] += 1
                state.pending_final_operation_for = -1
                self.score_battle(state)
            else:
                state.pending_final_operation_for = opponent
                self.start_turn_fast(state, opponent)
        elif state.passed[opponent]:
            self.score_battle(state)
        else:
            self.start_turn_fast(state, opponent)
        state.turn_number += 1

    cdef void apply_fast(self, FastState state, uint64_t action):
        cdef int kind = action_kind(action)
        cdef int card = action_card(action)
        cdef int pos = action_pos(action)
        cdef int dest = action_dest(action)
        cdef int actor = state.active_player
        cdef int front, before_mask = 0, cost = 0
        cdef bint cancelled

        if kind == TYPE_CHOOSE:
            state.chooser = -1
            state.phase = PHASE_BATTLE
            self.start_turn_fast(state, pos)
            state.turn_number += 1
            return

        if kind == TYPE_PASS:
            self.pass_action(state, actor)
            return

        if kind == TYPE_DRAW:
            if self.command_enabled and self.paid_draw_enabled:
                cost = self.command_cost_fast(state, action)
                self.spend_command_fast(state, actor, cost)
            else:
                state.draw_used[actor] = 1
            self.draw_for_battle(state, actor, 1)
            if self.paid_draw_enabled and not self.paid_draw_consumes_operation:
                state.turn_number += 1
                return
            self.finish_operation_fast(state, actor)
            return

        if kind == TYPE_DISCARD:
            if not state.cleanup_pending:
                raise ValueError("Discard is only legal during Battle cleanup")
            self.take_from_hand(state, actor, card, 0)
            self.append_discard(state, actor, card, False)
            state.turn_number += 1
            self.advance_cleanup_fast(state)
            return

        if kind == TYPE_CYCLE:
            cost = self.command_cost_fast(state, action)
            self.spend_command_fast(state, actor, cost)
            self.take_from_hand(state, actor, card, 0)
            self.append_discard(state, actor, card, True)
            self.draw_for_battle(state, actor, 1)
            if state.free_cycle[actor]:
                state.free_cycle[actor] = 0
            self.finish_operation_fast(state, actor)
            return

        if self.command_enabled:
            cost = self.command_cost_fast(state, action)
            self.spend_command_fast(state, actor, cost)

        if kind == TYPE_SUBJECT or kind == TYPE_LINK or kind == TYPE_NAME:
            before_mask = self.complete_mask(state, actor)

        if kind == TYPE_SUBJECT:
            self.take_from_hand(state, actor, card, 0)
            state.subject[pos] = card
            front = front_from_slot(pos)
            self.resolve_scheme_event(state, actor, EVENT_SUBJECT, front, pos)
            self.resolve_strat_event(state, EVENT_SUBJECT, actor, card, pos)

        elif kind == TYPE_LINK:
            self.take_from_hand(state, actor, card, 0)
            state.link[pos] = card
            if state.subject[pos] >= 0:
                state.temporary[pos] += self.on_link_bonus[state.subject[pos]]
            front = front_from_slot(pos)
            self.resolve_scheme_event(state, actor, EVENT_LINK, front, pos)

        elif kind == TYPE_NAME:
            self.take_from_hand(state, actor, card, 0)
            state.name[pos] = card
            if self.name_effect[card] == NAME_REVEAL_SCHEME:
                front = front_from_slot(pos)
                if state.scheme[(1 - actor) * 3 + front] >= 0:
                    state.scheme_revealed[(1 - actor) * 3 + front] = 1
            elif self.name_effect[card] == NAME_MOVE_ADJACENT and dest >= 0:
                self.move_slot(state, pos, dest)
                pos = dest
            self.resolve_strat_event(state, EVENT_NAME, actor, card, pos)

        elif kind == TYPE_PLOT:
            self.take_from_hand(state, actor, card, 0)
            cancelled = self.pre_story_cancel(state, actor)
            if not cancelled:
                self.resolve_plot(state, actor, card, pos, dest)
                self.resolve_plot_target_scheme(state, actor, pos)
            self.append_discard(state, actor, card, True)

        elif kind == TYPE_SCHEME:
            self.take_from_hand(state, actor, card, 1)
            state.scheme[actor * 3 + pos] = card
            state.scheme_revealed[actor * 3 + pos] = 0

        elif kind == TYPE_STRATAGEM:
            self.take_from_hand(
                state,
                actor,
                card,
                0 if self.public_stratagems else 2,
            )
            state.stratagem[actor] = card
            state.stratagem_revealed[actor] = 1 if self.public_stratagems else 0
            state.stratagem_used[actor] = 1
            if self.command_enabled:
                self.finish_operation_fast(state, actor)
            return

        if kind == TYPE_SUBJECT or kind == TYPE_LINK or kind == TYPE_NAME:
            self.resolve_new_completions_fast(state, actor, before_mask)

        self.finish_operation_fast(state, actor)

    cpdef FastState next_state(self, FastState state, uint64_t action):
        cdef FastState child = state.clone_fast()
        self.apply_fast(child, action)
        return child

    cpdef apply(self, FastState state, uint64_t action):
        self.apply_fast(state, action)

    cdef InfoHash128 information_hash_fast(
        self,
        FastState state,
        int player,
    ) noexcept:
        """Native 128-bit hash of the same observable state as information_key."""
        cdef InfoHash128 h
        cdef int i, owner, slot, card, front, ix, opponent=1-player
        _info_hash_init(&h)

        _info_hash_feed(&h, 3)
        _info_hash_feed(&h, <uint8_t>player)
        _info_hash_feed(&h, <uint8_t>(state.phase + 1))
        _info_hash_feed(&h, <uint8_t>(state.battle & 255))
        _info_hash_feed(&h, <uint8_t>(state.active_player + 1))
        _info_hash_feed(&h, <uint8_t>(state.chooser + 1))
        for i in range(2):
            _info_hash_feed(&h, state.victories[i])
            _info_hash_feed(&h, state.passed[i])
        _info_hash_feed(&h, state.pass_len)
        for i in range(state.pass_len):
            _info_hash_feed(&h, <uint8_t>(state.pass_order[i] + 1))
        for i in range(2):
            _info_hash_feed(&h, state.discarded_this_battle[i])
            _info_hash_feed(&h, <uint8_t>(state.command[i] & 255))
            _info_hash_feed(&h, state.free_cycle[i])
            _info_hash_feed(
                &h,
                <uint8_t>(state.operations_this_battle[i] & 255),
            )
        _info_hash_feed(
            &h,
            <uint8_t>(state.pending_final_operation_for + 1),
        )
        _info_hash_feed(&h, state.cleanup_pending)
        _info_hash_feed(&h, <uint8_t>(state.cleanup_next_starter + 1))
        _info_hash_feed(&h, <uint8_t>(state.cleanup_next_chooser + 1))

        for owner in range(2):
            for slot in range(owner * 6, owner * 6 + 6):
                _info_hash_feed(&h, <uint8_t>(state.subject[slot] + 1))
                _info_hash_feed(&h, <uint8_t>(state.link[slot] + 1))
                _info_hash_feed(&h, <uint8_t>(state.name[slot] + 1))
                _info_hash_feed(
                    &h,
                    <uint8_t>(state.temporary[slot] + 64),
                )

        for owner in range(2):
            for front in range(3):
                ix = owner * 3 + front
                card = state.scheme[ix]
                if card < 0:
                    _info_hash_feed(&h, 0)
                    _info_hash_feed(&h, 0)
                elif owner == player or state.scheme_revealed[ix]:
                    _info_hash_feed(&h, <uint8_t>(card + 1))
                    _info_hash_feed(&h, state.scheme_revealed[ix])
                else:
                    _info_hash_feed(&h, 255)
                    _info_hash_feed(&h, 0)

        for owner in range(2):
            card = state.stratagem[owner]
            if card < 0:
                _info_hash_feed(&h, 0)
                _info_hash_feed(&h, 0)
            elif owner == player or state.stratagem_revealed[owner]:
                _info_hash_feed(&h, <uint8_t>(card + 1))
                _info_hash_feed(&h, state.stratagem_revealed[owner])
            else:
                _info_hash_feed(&h, 255)
                _info_hash_feed(&h, 0)

        for owner in range(2):
            _info_hash_feed(&h, state.stratagem_used[owner])
        for owner in range(2):
            _info_hash_feed(&h, state.draw_used[owner])

        for card in range(self.n_cards):
            _info_hash_feed(&h, state.hand[player][card])
        for card in range(self.n_cards):
            _info_hash_feed(&h, state.deck_counts[player][card])

        _info_hash_feed(&h, state.discard_len[player])
        for i in range(state.discard_len[player]):
            _info_hash_feed(
                &h,
                <uint8_t>(state.discard[player][i] + 1),
            )

        _info_hash_feed(&h, state.hand_len[opponent])
        for card in range(self.n_cards):
            _info_hash_feed(
                &h,
                state.known_hidden[player][opponent][card],
            )
        _info_hash_feed(&h, state.deck_len[opponent])
        _info_hash_feed(&h, state.discard_len[opponent])
        for i in range(state.discard_len[opponent]):
            _info_hash_feed(
                &h,
                <uint8_t>(state.discard[opponent][i] + 1),
            )
        return h

    cpdef tuple information_hash(self, FastState state, int player):
        cdef InfoHash128 h = self.information_hash_fast(state, player)
        return (h.a, h.b)

    cdef bytes information_key_fast(self, FastState state, int player):
        cdef unsigned char buf[512]
        cdef int n=0, i, owner, slot, card, count, front, ix, opponent=1-player
        # version byte makes the binary representation explicitly evolvable
        buf[n] = 3; n += 1
        buf[n] = player; n += 1
        buf[n] = state.phase + 1; n += 1
        buf[n] = state.battle & 255; n += 1
        buf[n] = state.active_player + 1; n += 1
        buf[n] = state.chooser + 1; n += 1
        for i in range(2):
            buf[n] = state.victories[i]; n += 1
            buf[n] = state.passed[i]; n += 1
        buf[n] = state.pass_len; n += 1
        for i in range(state.pass_len):
            buf[n] = state.pass_order[i] + 1; n += 1
        for i in range(2):
            buf[n] = state.discarded_this_battle[i]; n += 1
            buf[n] = state.command[i] & 255; n += 1
            buf[n] = state.free_cycle[i]; n += 1
            buf[n] = state.operations_this_battle[i] & 255; n += 1
        buf[n] = state.pending_final_operation_for + 1; n += 1
        buf[n] = state.cleanup_pending; n += 1
        buf[n] = state.cleanup_next_starter + 1; n += 1
        buf[n] = state.cleanup_next_chooser + 1; n += 1

        for owner in range(2):
            for slot in range(owner * 6, owner * 6 + 6):
                buf[n] = state.subject[slot] + 1; n += 1
                buf[n] = state.link[slot] + 1; n += 1
                buf[n] = state.name[slot] + 1; n += 1
                # signed temporary strength in one byte, biased by 64
                buf[n] = state.temporary[slot] + 64; n += 1

        for owner in range(2):
            for front in range(3):
                ix = owner * 3 + front
                card = state.scheme[ix]
                if card < 0:
                    buf[n] = 0; n += 1
                    buf[n] = 0; n += 1
                elif owner == player or state.scheme_revealed[ix]:
                    buf[n] = card + 1; n += 1
                    buf[n] = state.scheme_revealed[ix]; n += 1
                else:
                    buf[n] = 255; n += 1
                    buf[n] = 0; n += 1

        for owner in range(2):
            card = state.stratagem[owner]
            if card < 0:
                buf[n] = 0; n += 1
                buf[n] = 0; n += 1
            elif owner == player or state.stratagem_revealed[owner]:
                buf[n] = card + 1; n += 1
                buf[n] = state.stratagem_revealed[owner]; n += 1
            else:
                buf[n] = 255; n += 1
                buf[n] = 0; n += 1
        for owner in range(2):
            buf[n] = state.stratagem_used[owner]; n += 1
        for owner in range(2):
            buf[n] = state.draw_used[owner]; n += 1

        # own hand and own deck multisets: fixed card-count vector
        for card in range(self.n_cards):
            buf[n] = state.hand[player][card]; n += 1
        for card in range(self.n_cards):
            buf[n] = state.deck_counts[player][card]; n += 1

        buf[n] = state.discard_len[player]; n += 1
        for i in range(state.discard_len[player]):
            buf[n] = state.discard[player][i] + 1; n += 1

        buf[n] = state.hand_len[opponent]; n += 1
        for card in range(self.n_cards):
            buf[n] = state.known_hidden[player][opponent][card]; n += 1
        buf[n] = state.deck_len[opponent]; n += 1
        buf[n] = state.discard_len[opponent]; n += 1
        for i in range(state.discard_len[opponent]):
            buf[n] = state.discard[opponent][i] + 1; n += 1

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
        cdef int front, rank
        if kind == TYPE_PASS:
            return "pass"
        if kind == TYPE_DRAW:
            return "draw"
        if kind == TYPE_CYCLE:
            return f"cycle:{self.card_ids[card]}"
        if kind == TYPE_DISCARD:
            return f"discard:{self.card_ids[card]}"
        if kind == TYPE_CHOOSE:
            return f"choose_first:{pos}"
        if kind == TYPE_SUBJECT:
            return f"subject:{self.card_ids[card]}:{front_from_slot(pos)}:{'front' if rank_from_slot(pos) == 0 else 'rear'}"
        if kind == TYPE_LINK:
            return f"link:{self.card_ids[card]}:{front_from_slot(pos)}:{'front' if rank_from_slot(pos) == 0 else 'rear'}"
        if kind == TYPE_NAME:
            if dest < 0:
                return f"name:{self.card_ids[card]}:{front_from_slot(pos)}:{'front' if rank_from_slot(pos) == 0 else 'rear'}:stay"
            return f"name:{self.card_ids[card]}:{front_from_slot(pos)}:{'front' if rank_from_slot(pos) == 0 else 'rear'}:{front_from_slot(dest)}:{'front' if rank_from_slot(dest) == 0 else 'rear'}"
        if kind == TYPE_SCHEME:
            return f"scheme:{self.card_ids[card]}:{pos}"
        if kind == TYPE_STRATAGEM:
            return f"stratagem:{self.card_ids[card]}"
        if kind == TYPE_PLOT:
            if dest >= 0:
                return f"plot:{self.card_ids[card]}:{player}:{front_from_slot(pos)}:{'front' if rank_from_slot(pos) == 0 else 'rear'};{player}:{front_from_slot(dest)}:{'front' if rank_from_slot(dest) == 0 else 'rear'}"
            if pos >= 0:
                return f"plot:{self.card_ids[card]}:{player}:{front_from_slot(pos)}:{'front' if rank_from_slot(pos) == 0 else 'rear'}"
            return f"plot:{self.card_ids[card]}:"
        raise ValueError("Unknown fast action")

    cpdef dict export_state(self, FastState state):
        cdef int p, f, r, i, card, viewer, owner
        cdef object last_snapshot = None
        if state.last_battle_valid:
            last_snapshot = {
                "battle": state.last_battle,
                "winner": state.last_battle_winner,
                "front_scores": [
                    [
                        state.last_front_scores[f][0],
                        state.last_front_scores[f][1],
                    ]
                    for f in range(3)
                ],
                "total_strength": state.last_total_strength,
                "abs_total_margin": state.last_abs_total_margin,
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
                "completion_command_refunded": [
                    state.last_completion_command_refunded[0],
                    state.last_completion_command_refunded[1],
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
                else "choose_first"
                if state.phase == PHASE_CHOOSE
                else "complete"
            ),
            "battle": state.battle,
            "active_player": state.active_player,
            "chooser": None if state.chooser < 0 else state.chooser,
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
                    "victories": state.victories[p],
                    "passed": bool(state.passed[p]),
                    "command": state.command[p],
                    "free_cycle": bool(state.free_cycle[p]),
                }
                for p in range(2)
            ],
            "board": [
                [
                    [
                        {
                            "subject": (
                                None
                                if state.subject[slot_index(p, f, r)] < 0
                                else self.card_ids[
                                    state.subject[slot_index(p, f, r)]
                                ]
                            ),
                            "link": (
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
                        }
                        for r in range(2)
                    ]
                    for f in range(3)
                ]
                for p in range(2)
            ],
            "schemes": [
                [
                    (
                        None
                        if state.scheme[p * 3 + f] < 0
                        else {
                            "card_id": self.card_ids[state.scheme[p * 3 + f]],
                            "revealed": bool(
                                state.scheme_revealed[p * 3 + f]
                            ),
                        }
                    )
                    for f in range(3)
                ]
                for p in range(2)
            ],
            "stratagems": [
                (
                    None
                    if state.stratagem[p] < 0
                    else {
                        "card_id": self.card_ids[state.stratagem[p]],
                        "revealed": bool(state.stratagem_revealed[p]),
                    }
                )
                for p in range(2)
            ],
            "stratagem_used": [
                bool(state.stratagem_used[0]),
                bool(state.stratagem_used[1]),
            ],
            "draw_used": [
                bool(state.draw_used[0]),
                bool(state.draw_used[1]),
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
            "completion_command_refunded_this_battle": [
                state.completion_command_refunded_this_battle[0],
                state.completion_command_refunded_this_battle[1],
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
            "pending_final_operation_for": (
                None
                if state.pending_final_operation_for < 0
                else state.pending_final_operation_for
            ),
            "cleanup_pending": bool(state.cleanup_pending),
            "cleanup_next_starter": (
                None
                if state.cleanup_next_starter < 0
                else state.cleanup_next_starter
            ),
            "cleanup_next_chooser": (
                None
                if state.cleanup_next_chooser < 0
                else state.cleanup_next_chooser
            ),
            "pass_order": [
                state.pass_order[i]
                for i in range(state.pass_len)
            ],
            "known_hidden_hand": [
                [
                    {
                        self.card_ids[card]: state.known_hidden[viewer][owner][card]
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
            "chooser": state.chooser,
            "winner": state.winner,
            "turn_number": state.turn_number,
            "victories": [state.victories[0], state.victories[1]],
            "passed": [bool(state.passed[0]), bool(state.passed[1])],
            "pass_order": [state.pass_order[i] for i in range(state.pass_len)],
            "discarded_this_battle": [state.discarded_this_battle[0], state.discarded_this_battle[1]],
            "command": [state.command[0], state.command[1]],
            "free_cycle": [bool(state.free_cycle[0]), bool(state.free_cycle[1])],
            "operations_this_battle": [state.operations_this_battle[0], state.operations_this_battle[1]],
            "pending_final_operation_for": None if state.pending_final_operation_for < 0 else state.pending_final_operation_for,
            "cleanup_pending": bool(state.cleanup_pending),
            "cleanup_next_starter": None if state.cleanup_next_starter < 0 else state.cleanup_next_starter,
            "cleanup_next_chooser": None if state.cleanup_next_chooser < 0 else state.cleanup_next_chooser,
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
                    for f in range(3) for r in range(2)
                ]
                for p in range(2)
            ],
            "schemes": [
                [
                    None if state.scheme[p * 3 + f] < 0 else (self.card_ids[state.scheme[p * 3 + f]], bool(state.scheme_revealed[p * 3 + f]))
                    for f in range(3)
                ]
                for p in range(2)
            ],
            "stratagems": [
                None if state.stratagem[p] < 0 else (self.card_ids[state.stratagem[p]], bool(state.stratagem_revealed[p]))
                for p in range(2)
            ],
            "stratagem_used": [bool(state.stratagem_used[0]), bool(state.stratagem_used[1])],
            "draw_used": [bool(state.draw_used[0]), bool(state.draw_used[1])],
        }

# Keep one compiled extension/shared packed state, but separate policies and
# algorithms physically so rule changes do not invite heuristic/search edits.
include "_heuristic_core.pxi"
include "_alpha_beta_core.pxi"
include "_ismcts_core.pxi"
include "_mccfr_core.pxi"
