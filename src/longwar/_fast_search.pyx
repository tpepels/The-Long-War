# cython: language_level=3, boundscheck=False, wraparound=False, initializedcheck=False, cdivision=True
from libc.stdint cimport int8_t, int16_t, uint8_t, uint16_t, uint32_t, int32_t, uint64_t
from libc.stddef cimport size_t
from libc.string cimport memcpy, memset
from libc.stdlib cimport malloc, free
from libc.math cimport tanh
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
    cdef int8_t pending_final_operation_for

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
        self.pending_final_operation_for = -1
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
        self.pending_final_operation_for = other.pending_final_operation_for
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
    cdef bint recycle_between_battles
    cdef bint command_enabled
    cdef int battle_command_gain
    cdef int command_cap
    cdef bint reshuffle_on_empty
    cdef bint automatic_draw
    cdef bint paid_draw_enabled
    cdef int paid_draw_command_cost
    cdef bint cycle_enabled
    cdef bint pass_final_operation
    cdef bint pass_requires_both_acted
    cdef bint first_passer_starts_next_battle
    cdef int completion_command_refund
    cdef bint public_stratagems

    cdef int8_t card_type[MAX_CARDS]
    cdef int8_t command_cost[MAX_CARDS]
    cdef int8_t adjacent_command_discount[MAX_CARDS]
    cdef int8_t completion_effect[MAX_CARDS]
    cdef int8_t completion_amount[MAX_CARDS]
    cdef uint8_t complete_plot_protection[MAX_CARDS]
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
        memset(self.command_cost, 0, sizeof(self.command_cost))
        memset(self.adjacent_command_discount, 0, sizeof(self.adjacent_command_discount))
        memset(self.completion_effect, 0, sizeof(self.completion_effect))
        memset(self.completion_amount, 0, sizeof(self.completion_amount))
        memset(self.complete_plot_protection, 0, sizeof(self.complete_plot_protection))
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
        self.recycle_between_battles = bool(engine.recycle_between_battles)
        self.command_enabled = bool(engine.command_enabled)
        self.battle_command_gain = int(engine.battle_command_gain)
        self.command_cap = int(engine.command_cap)
        self.reshuffle_on_empty = bool(engine.reshuffle_on_empty)
        self.automatic_draw = bool(engine.automatic_draw)
        self.paid_draw_enabled = bool(engine.paid_draw_enabled)
        self.paid_draw_command_cost = int(engine.paid_draw_command_cost)
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
            self.command_cost[code] = int(card.get("command_cost", 0))
            self.adjacent_command_discount[code] = int(rules.get("adjacent_command_discount", 0))
            completion = rules.get("on_completion") or {}
            self.completion_effect[code] = completion_effect_map.get(completion.get("effect"), COMPLETE_NONE)
            self.completion_amount[code] = int(completion.get("amount", 1))
            self.complete_plot_protection[code] = bool(rules.get("complete_protection_from_opponent_plot"))
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
        for i, p in enumerate(state.pass_order):
            fast.pass_order[i] = p

        for viewer in range(2):
            for owner in range(2):
                counter = state.known_hidden_counter(viewer, owner, "hand")
                for card_id, count in counter.items():
                    fast.known_hidden[viewer][owner][self.id_to_code[card_id]] = count

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
        card = action_card(action)
        if card < 0:
            return 0
        cost = self.command_cost[card]
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

    cdef inline void spend_command_fast(
        self,
        FastState state,
        int player,
        int amount,
    ) noexcept:
        state.command[player] -= amount

    cdef inline void gain_command_fast(
        self,
        FastState state,
        int player,
        int amount,
    ) noexcept:
        state.command[player] += amount
        if state.command[player] > self.command_cap:
            state.command[player] = self.command_cap

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
        cdef int local, slot, name, effect, amount, front, enemy_ix
        cdef int after_mask = self.complete_mask(state, player)
        cdef int new_mask = after_mask & ~before_mask
        if new_mask == 0:
            return
        for local in range(6):
            if not (new_mask & (1 << local)):
                continue
            slot = player * 6 + local
            if self.command_enabled and self.completion_command_refund:
                self.gain_command_fast(
                    state,
                    player,
                    self.completion_command_refund,
                )
            name = state.name[slot]
            if name < 0:
                continue
            effect = self.completion_effect[name]
            amount = self.completion_amount[name]
            if effect == COMPLETE_GAIN_COMMAND:
                if self.command_enabled:
                    self.gain_command_fast(state, player, amount)
            elif effect == COMPLETE_FREE_CYCLE:
                if self.command_enabled and self.cycle_enabled:
                    state.free_cycle[player] = 1
            elif effect == COMPLETE_DRAW:
                self.draw(state, player, amount)
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
        opponent = 1 - player

        if (
            (not self.command_enabled)
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

    cdef void start_turn_fast(self, FastState state, int player) noexcept:
        state.active_player = player
        if (
            self.automatic_draw
            and state.phase == PHASE_BATTLE
            and not state.passed[player]
        ):
            self.draw(state, player, 1)

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

    cdef void score_battle(self, FastState state):
        cdef int front, a, b, controls0=0, controls1=0, total0=0, total1=0
        cdef int winner, loser, p, first_passer=-1, target
        for front in range(3):
            a = self.front_strength_fast(state, 0, front)
            b = self.front_strength_fast(state, 1, front)
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
            state.stratagem_used[p] = 0
            state.draw_used[p] = 0
            state.free_cycle[p] = 0
            if self.command_enabled:
                state.command[p] += self.battle_command_gain
                if state.command[p] > self.command_cap:
                    state.command[p] = self.command_cap
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

        if self.first_passer_starts_next_battle and first_passer >= 0:
            state.phase = PHASE_BATTLE
            state.chooser = -1
            self.start_turn_fast(state, first_passer)
        else:
            state.phase = PHASE_CHOOSE
            state.chooser = loser
            state.active_player = loser

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
            self.draw(state, actor, 1)
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

    cdef double evaluate_fast(self, FastState state, int player) noexcept:
        cdef int opponent = 1 - player
        cdef int front, margin, controls=0, enemy_controls=0, hand_delta
        cdef int named_delta=0, scheme_delta=0, strat_delta=0
        cdef int exposed=0, reachable=0, slot, name_card, before, after, best
        cdef int card, own_forces=0, own_board_subjects=0
        cdef double score = 0.0, option = 0.0

        if state.phase == PHASE_COMPLETE:
            return 10000.0 if state.winner == player else -10000.0

        score += 80.0 * (state.victories[player] - state.victories[opponent])

        for front in range(3):
            margin = (
                self.front_strength_fast(state, player, front)
                - self.front_strength_fast(state, opponent, front)
            )
            if margin > 0:
                controls += 1
                if margin <= 3:
                    score += 1.25
                if margin <= 4:
                    exposed += 1
            elif margin < 0:
                enemy_controls += 1
                if margin >= -3:
                    score -= 1.25
                if margin >= -4:
                    reachable += 1
            else:
                reachable += 1

            if margin > 10:
                margin = 10
            elif margin < -10:
                margin = -10
            score += 0.75 * margin

        score += 10.0 * (controls - enemy_controls)
        if controls >= 2:
            score += 14.0
        if enemy_controls >= 2:
            score -= 14.0

        hand_delta = state.hand_len[player] - state.hand_len[opponent]
        score += 1.25 * hand_delta

        for card in range(self.n_cards):
            if self.card_type[card] == CARD_SUBJECT:
                own_forces += state.hand[player][card]
        if own_forces > 3:
            own_forces = 3
        score += 0.35 * own_forces

        for slot in range(player * 6, player * 6 + 6):
            if state.subject[slot] >= 0:
                own_board_subjects += 1
        if own_forces == 0 and own_board_subjects == 0:
            score -= 2.0

        if self.command_enabled:
            score += 0.45 * (
                state.command[player] - state.command[opponent]
            )
            score += 0.35 * (
                state.free_cycle[player] - state.free_cycle[opponent]
            )

        if (
            state.phase == PHASE_BATTLE
            and state.passed[player] != state.passed[opponent]
        ):
            if state.passed[player]:
                score -= (
                    1.5
                    + min(7.0, 0.55 * state.hand_len[opponent])
                    + 1.1 * exposed
                )
            else:
                score += (
                    1.0
                    + min(5.0, 0.4 * state.hand_len[player])
                    + 0.9 * reachable
                )

        for slot in range(player * 6, player * 6 + 6):
            if state.subject[slot] >= 0 and state.name[slot] >= 0:
                named_delta += 1
        for slot in range(opponent * 6, opponent * 6 + 6):
            if state.subject[slot] >= 0 and state.name[slot] >= 0:
                named_delta -= 1
        score += 1.5 * named_delta

        for front in range(3):
            if state.scheme[player * 3 + front] >= 0:
                scheme_delta += 1
            if state.scheme[opponent * 3 + front] >= 0:
                scheme_delta -= 1
        score += 0.75 * scheme_delta

        strat_delta = (
            (1 if state.stratagem[player] >= 0 else 0)
            - (1 if state.stratagem[opponent] >= 0 else 0)
        )
        score += 0.45 * strat_delta

        for slot in range(player * 6, player * 6 + 6):
            if state.subject[slot] < 0 or state.name[slot] >= 0:
                continue
            before = self.position_strength_fast(state, slot)
            best = -32768
            for name_card in range(self.n_cards):
                if (
                    state.hand[player][name_card] == 0
                    or self.card_type[name_card] != CARD_NAME
                ):
                    continue
                state.name[slot] = name_card
                after = self.position_strength_fast(state, slot)
                if after - before > best:
                    best = after - before
                state.name[slot] = -1
            if best > 0:
                option += 0.45 * best
        score += option

        if state.passed[player] and state.phase == PHASE_BATTLE:
            score -= 2.0

        return score

    cdef double formation_progress_fast(
        self,
        FastState state,
        int player,
    ) noexcept:
        cdef int local, slot, components
        cdef double value = 0.0
        for local in range(6):
            slot = player * 6 + local
            components = (
                (1 if state.subject[slot] >= 0 else 0)
                + (1 if state.link[slot] >= 0 else 0)
                + (1 if state.name[slot] >= 0 else 0)
            )
            if components == 1:
                value += 0.35
            elif components == 2:
                value += 1.35
            elif components == 3:
                value += 2.25
        return value

    cdef double hand_construction_value_fast(
        self,
        FastState state,
        int player,
    ) noexcept:
        cdef bint needs_subject=False, needs_link=False, needs_name=False
        cdef int local, slot, card, count, typ
        cdef double value=0.0
        for local in range(6):
            slot = player * 6 + local
            if state.subject[slot] < 0 and (
                state.link[slot] >= 0 or state.name[slot] >= 0
            ):
                needs_subject = True
            if state.link[slot] < 0 and (
                state.subject[slot] >= 0 or state.name[slot] >= 0
            ):
                needs_link = True
            if state.name[slot] < 0 and (
                state.subject[slot] >= 0 or state.link[slot] >= 0
            ):
                needs_name = True

        for card in range(self.n_cards):
            count = state.hand[player][card]
            if count == 0:
                continue
            typ = self.card_type[card]
            if typ == CARD_SUBJECT:
                value += count * (0.45 + (0.95 if needs_subject else 0.0))
            elif typ == CARD_LINK:
                value += count * (0.35 + (0.95 if needs_link else 0.0))
            elif typ == CARD_NAME:
                value += count * (0.35 + (1.05 if needs_name else 0.0))
            elif typ == CARD_PLOT:
                value += count * 0.40
            elif typ == CARD_STRATAGEM:
                value += count * 0.30
        return value

    cdef int future_formation_sets_fast(
        self,
        FastState state,
        int player,
    ) noexcept:
        cdef int card, count, subjects=0, links=0, names=0
        cdef int value
        for card in range(self.n_cards):
            count = state.hand[player][card] + state.deck_counts[player][card]
            if self.card_type[card] == CARD_SUBJECT:
                subjects += count
            elif self.card_type[card] == CARD_LINK:
                links += count
            elif self.card_type[card] == CARD_NAME:
                names += count
        value = subjects
        if links < value:
            value = links
        if names < value:
            value = names
        return value

    cdef double future_force_availability_fast(
        self,
        FastState state,
        int player,
    ) noexcept:
        cdef int card, i, immediate=0, discarded=0
        for card in range(self.n_cards):
            if self.card_type[card] == CARD_SUBJECT:
                immediate += (
                    state.hand[player][card]
                    + state.deck_counts[player][card]
                )
        for i in range(state.discard_len[player]):
            card = state.discard[player][i]
            if self.card_type[card] == CARD_SUBJECT:
                discarded += 1
        return immediate + 0.35 * discarded

    cdef int affordable_hand_count_fast(
        self,
        FastState state,
        int player,
    ) noexcept:
        cdef int card, total=0
        if not self.command_enabled:
            return state.hand_len[player]
        for card in range(self.n_cards):
            if (
                state.hand[player][card]
                and self.command_cost[card] <= state.command[player]
            ):
                total += state.hand[player][card]
        return total

    cdef double strategic_evaluate_fast(
        self,
        FastState state,
        int player,
    ) noexcept:
        cdef int opponent = 1 - player
        cdef double value = self.evaluate_fast(state, player)
        if state.phase == PHASE_COMPLETE:
            return value

        value += 0.85 * (
            self.formation_progress_fast(state, player)
            - self.formation_progress_fast(state, opponent)
        )
        value += 0.30 * (
            self.hand_construction_value_fast(state, player)
            - self.hand_construction_value_fast(state, opponent)
        )

        if not self.recycle_between_battles:
            value += 0.18 * (
                state.deck_len[player] - state.deck_len[opponent]
            )
            value += 0.55 * (
                self.future_formation_sets_fast(state, player)
                - self.future_formation_sets_fast(state, opponent)
            )
            value += 0.40 * (
                self.future_force_availability_fast(state, player)
                - self.future_force_availability_fast(state, opponent)
            )

        if self.command_enabled:
            value += 0.12 * (
                self.affordable_hand_count_fast(state, player)
                - self.affordable_hand_count_fast(state, opponent)
            )

        return value

    cdef double pass_score_fast(
        self,
        FastState state,
        int player,
    ):
        cdef FastState child = FastState()
        cdef int front, margin, controls=0, tied=0, total_margin=0
        cdef int weakest_control=32767
        cdef int opponent = 1 - player
        cdef double pressure_scale = 0.45 if self.pass_final_operation else 1.0
        cdef double score

        child.copy_from_fast(state)
        self.pass_action(child, player)
        if child.phase != PHASE_BATTLE or child.battle != state.battle:
            return self.evaluate_fast(child, player)

        score = self.evaluate_fast(state, player)
        for front in range(3):
            margin = (
                self.front_strength_fast(state, player, front)
                - self.front_strength_fast(state, opponent, front)
            )
            total_margin += margin
            if margin > 0:
                controls += 1
                if margin < weakest_control:
                    weakest_control = margin
            elif margin == 0:
                tied += 1

        if controls >= 2:
            if weakest_control == 32767:
                weakest_control = 0
            score += (
                10.0
                + 0.65 * total_margin
                + 0.9 * weakest_control
                + 0.8 * state.hand_len[player]
                - pressure_scale * 1.6 * state.hand_len[opponent]
            )
        elif controls == 1 and tied >= 1 and total_margin >= 0:
            score -= 7.0 + pressure_scale * 1.2 * state.hand_len[opponent]
        else:
            score -= 25.0 + pressure_scale * 1.5 * state.hand_len[opponent]

        if self.first_passer_starts_next_battle and state.pass_len == 0:
            score += 1.5

        if (
            self.front_strength_fast(state, player, 0)
            == self.front_strength_fast(state, opponent, 0)
            and self.front_strength_fast(state, player, 1)
            == self.front_strength_fast(state, opponent, 1)
            and self.front_strength_fast(state, player, 2)
            == self.front_strength_fast(state, opponent, 2)
        ):
            score += 5.0
        return score

    cdef double action_order_score_fast(
        self,
        FastState state,
        int player,
        uint64_t action,
        FastState child,
    ):
        cdef int kind = action_kind(action)
        cdef int pos = action_pos(action)
        cdef int force_count=0, card
        cdef double score

        if kind == TYPE_PASS:
            return self.pass_score_fast(state, player)

        child.copy_from_fast(state)
        self.apply_fast(child, action)
        score = self.evaluate_fast(child, player)

        if kind == TYPE_DRAW:
            for card in range(self.n_cards):
                if self.card_type[card] == CARD_SUBJECT:
                    force_count += state.hand[player][card]
            score -= 0.35 if self.paid_draw_enabled else 0.8
            if force_count == 0:
                score += 1.4
        elif kind == TYPE_LINK:
            score += 0.10 if state.subject[pos] >= 0 else 1.35
        elif kind == TYPE_NAME:
            score += 0.35 if state.subject[pos] >= 0 else 1.50
        elif kind == TYPE_SCHEME:
            score += 0.20

        return score

    cpdef double evaluate(self, FastState state, int player):
        return self.evaluate_fast(state, player)

    cpdef double evaluate(self, FastState state, int player):
        return self.evaluate_fast(state, player)

    cdef bytes information_key_fast(self, FastState state, int player):
        cdef unsigned char buf[512]
        cdef int n=0, i, owner, slot, card, count, front, ix, opponent=1-player
        # version byte makes the binary representation explicitly evolvable
        buf[n] = 2; n += 1
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
            "operations_this_battle": [state.operations_this_battle[0], state.operations_this_battle[1]],
            "pending_final_operation_for": None if state.pending_final_operation_for < 0 else state.pending_final_operation_for,
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



class NativeSearchLimit(RuntimeError):
    pass


cdef class NativeSearchBudget:
    cdef public long limit
    cdef public long nodes

    def __init__(self, long limit):
        if limit <= 0:
            raise ValueError("limit must be positive")
        self.limit = limit
        self.nodes = 0


cdef int ordered_actions_into(
    FastEngine engine,
    FastState state,
    int actor,
    int width,
    uint64_t* selected,
    FastState order_scratch,
) except -1:
    cdef uint64_t actions[MAX_ACTIONS]
    cdef double scores[MAX_ACTIONS]
    cdef int n, i, j, selected_n, kind
    cdef uint64_t action, tmp_action
    cdef double score, tmp_score
    cdef bint have_pass=False, have_draw=False

    n = engine.legal_actions_into(state, &actions[0])
    if n <= 0:
        return 0

    for i in range(n):
        scores[i] = engine.action_order_score_fast(
            state,
            actor,
            actions[i],
            order_scratch,
        )

    # Stable insertion sort: highest one-ply actor score first.
    for i in range(1, n):
        tmp_action = actions[i]
        tmp_score = scores[i]
        j = i - 1
        while j >= 0 and scores[j] < tmp_score:
            actions[j + 1] = actions[j]
            scores[j + 1] = scores[j]
            j -= 1
        actions[j + 1] = tmp_action
        scores[j + 1] = tmp_score

    selected_n = n if n <= width else width
    for i in range(selected_n):
        selected[i] = actions[i]
        kind = action_kind(actions[i])
        if kind == TYPE_PASS:
            have_pass = True
        elif kind == TYPE_DRAW:
            have_draw = True

    # Match the Python beam policy: Pass and Draw always survive pruning.
    if selected_n < n:
        for i in range(selected_n, n):
            kind = action_kind(actions[i])
            if kind == TYPE_PASS and not have_pass:
                selected[selected_n] = actions[i]
                selected_n += 1
                have_pass = True
            elif kind == TYPE_DRAW and not have_draw:
                selected[selected_n] = actions[i]
                selected_n += 1
                have_draw = True

    return selected_n


cdef double native_alphabeta(
    FastEngine engine,
    FastState state,
    int root_player,
    int depth,
    double alpha,
    double beta,
    NativeSearchBudget budget,
    int width,
    object scratch,
    int level,
) except *:
    cdef uint64_t actions[MAX_ACTIONS]
    cdef int n, i, actor
    cdef bint maximizing
    cdef double value, child_value
    cdef FastState child
    cdef FastState order_scratch

    budget.nodes += 1
    if budget.nodes > budget.limit:
        raise NativeSearchLimit()

    if state.phase == PHASE_COMPLETE or depth <= 0:
        return engine.strategic_evaluate_fast(state, root_player)

    actor = state.active_player
    order_scratch = <FastState>scratch[level * 2]
    child = <FastState>scratch[level * 2 + 1]
    n = ordered_actions_into(
        engine,
        state,
        actor,
        width,
        &actions[0],
        order_scratch,
    )
    if n <= 0:
        return engine.strategic_evaluate_fast(state, root_player)

    maximizing = actor == root_player
    value = -1.0e300 if maximizing else 1.0e300

    for i in range(n):
        child.copy_from_fast(state)
        engine.apply_fast(child, actions[i])
        child_value = native_alphabeta(
            engine,
            child,
            root_player,
            depth - 1,
            alpha,
            beta,
            budget,
            width,
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
            break

    return value


cpdef double native_search_value(
    FastEngine engine,
    object game_state,
    int root_player,
    int depth,
    double alpha,
    double beta,
    NativeSearchBudget budget,
    int candidate_width,
):
    cdef FastState state = engine.from_game_state(game_state)
    cdef int levels = depth + 2
    cdef object scratch = [
        FastState()
        for _ in range(levels * 2)
    ]
    return native_alphabeta(
        engine,
        state,
        root_player,
        depth,
        alpha,
        beta,
        budget,
        candidate_width,
        scratch,
        0,
    )

cdef class FastCFRNode:
    cdef void* action_storage
    cdef uint64_t* action_codes
    cdef double* regrets
    cdef double* strategy_sums
    cdef int action_count
    cdef public long visits
    cdef public long average_visits

    def __cinit__(self):
        self.action_storage = NULL
        self.action_codes = NULL
        self.regrets = NULL
        self.strategy_sums = NULL
        self.action_count = 0
        self.visits = 0
        self.average_visits = 0

    def __dealloc__(self):
        if self.action_storage != NULL:
            free(self.action_storage)

    cdef void initialize_actions(
        self,
        uint64_t* actions,
        int n,
    ) except *:
        cdef int i
        cdef size_t bytes_needed

        if self.action_count != 0:
            return

        bytes_needed = n * (
            sizeof(uint64_t)
            + sizeof(double)
            + sizeof(double)
        )
        self.action_storage = malloc(bytes_needed)
        if self.action_storage == NULL:
            raise MemoryError("Unable to allocate fast CFR node actions")

        self.action_codes = <uint64_t*>self.action_storage
        self.regrets = <double*>(self.action_codes + n)
        self.strategy_sums = self.regrets + n
        self.action_count = n

        for i in range(n):
            self.action_codes[i] = actions[i]
            self.regrets[i] = 0.0
            self.strategy_sums[i] = 0.0

    cdef void strategy_into(
        self,
        uint64_t* actions,
        int n,
        double* probabilities,
    ) except *:
        cdef int i
        cdef double total = 0.0
        cdef double value

        if self.action_count == 0:
            self.initialize_actions(actions, n)
        elif self.action_count != n:
            raise RuntimeError(
                f"Action count changed inside information set: "
                f"{self.action_count} != {n}"
            )

        for i in range(n):
            if self.action_codes[i] != actions[i]:
                raise RuntimeError(
                    "Action ordering changed inside information set"
                )
            value = self.regrets[i]
            if value > 0.0:
                probabilities[i] = value
                total += value
            else:
                probabilities[i] = 0.0

        if total > 0.0:
            for i in range(n):
                probabilities[i] /= total
        else:
            value = 1.0 / n
            for i in range(n):
                probabilities[i] = value

    cdef void accumulate_into(
        self,
        double* probabilities,
        int n,
        double reach_weight,
    ) noexcept:
        cdef int i
        for i in range(n):
            self.strategy_sums[i] += reach_weight * probabilities[i]
        self.average_visits += 1

    cdef void update_regrets(
        self,
        double* utilities,
        int n,
        double node_utility,
    ) noexcept:
        cdef int i
        for i in range(n):
            self.regrets[i] += utilities[i] - node_utility

    cdef int find_action(self, uint64_t action) noexcept:
        cdef int i
        for i in range(self.action_count):
            if self.action_codes[i] == action:
                return i
        return -1

    property regret_sum:
        def __get__(self):
            return {
                self.action_codes[i]: self.regrets[i]
                for i in range(self.action_count)
            }

    property strategy_sum:
        def __get__(self):
            return {
                self.action_codes[i]: self.strategy_sums[i]
                for i in range(self.action_count)
            }

    property allocated_action_bytes:
        def __get__(self):
            return self.action_count * (
                sizeof(uint64_t)
                + sizeof(double)
                + sizeof(double)
            )

    def strategy(self, actions=None):
        cdef list keys
        cdef int i, ix
        cdef double total = 0.0
        cdef double value
        cdef dict result = {}

        keys = (
            [self.action_codes[i] for i in range(self.action_count)]
            if actions is None
            else list(actions)
        )
        for key in keys:
            ix = self.find_action(<uint64_t>key)
            if ix >= 0 and self.regrets[ix] > 0.0:
                total += self.regrets[ix]
        if total <= 0.0:
            if not keys:
                return {}
            value = 1.0 / len(keys)
            return {key: value for key in keys}
        for key in keys:
            ix = self.find_action(<uint64_t>key)
            value = self.regrets[ix] if ix >= 0 else 0.0
            result[key] = (value if value > 0.0 else 0.0) / total
        return result

    def average_strategy(self, actions=None):
        cdef list keys
        cdef int i, ix
        cdef double total = 0.0
        cdef double value
        cdef dict result = {}

        keys = (
            [self.action_codes[i] for i in range(self.action_count)]
            if actions is None
            else list(actions)
        )
        for key in keys:
            ix = self.find_action(<uint64_t>key)
            if ix >= 0 and self.strategy_sums[ix] > 0.0:
                total += self.strategy_sums[ix]
        if total <= 0.0:
            return self.strategy(keys)
        for key in keys:
            ix = self.find_action(<uint64_t>key)
            value = self.strategy_sums[ix] if ix >= 0 else 0.0
            result[key] = (value if value > 0.0 else 0.0) / total
        return result


cdef double _packed_traverse(
    FastEngine engine,
    FastState state,
    int traverser,
    int depth,
    int max_depth,
    object nodes,
    object rng,
    double leaf_scale,
    double reach0,
    double reach1,
    list scratch,
):
    cdef int actor, child_depth, n, i, sampled_index
    cdef uint64_t actions[MAX_ACTIONS]
    cdef double probabilities[MAX_ACTIONS]
    cdef double utilities[MAX_ACTIONS]
    cdef bytes info_key
    cdef object raw_node
    cdef FastCFRNode node
    cdef FastState child
    cdef double probability
    cdef double utility
    cdef double node_utility = 0.0
    cdef double threshold
    cdef double cumulative = 0.0

    if state.phase == PHASE_COMPLETE:
        return 1.0 if state.winner == traverser else -1.0

    if depth >= max_depth:
        return tanh(engine.evaluate_fast(state, traverser) / leaf_scale)

    actor = state.active_player
    n = engine.legal_actions_into(state, &actions[0])
    if n <= 0:
        raise RuntimeError("Packed non-terminal state has no legal actions")

    info_key = engine.information_key_fast(state, actor)
    raw_node = nodes.get(info_key)
    if raw_node is None:
        node = FastCFRNode()
        nodes[info_key] = node
    else:
        node = <FastCFRNode>raw_node

    node.visits += 1
    node.strategy_into(&actions[0], n, &probabilities[0])
    child_depth = depth + 1

    if actor == traverser:
        for i in range(n):
            probability = probabilities[i]
            child = <FastState>scratch[child_depth]
            child.copy_from_fast(state)
            engine.apply_fast(child, actions[i])
            if actor == 0:
                utility = _packed_traverse(
                    engine, child, traverser, child_depth, max_depth,
                    nodes, rng, leaf_scale,
                    reach0 * probability, reach1, scratch,
                )
            else:
                utility = _packed_traverse(
                    engine, child, traverser, child_depth, max_depth,
                    nodes, rng, leaf_scale,
                    reach0, reach1 * probability, scratch,
                )
            utilities[i] = utility
            node_utility += probability * utility

        node.update_regrets(&utilities[0], n, node_utility)
        return node_utility

    node.accumulate_into(
        &probabilities[0],
        n,
        reach0 if actor == 0 else reach1,
    )
    threshold = rng.random()
    sampled_index = n - 1
    for i in range(n):
        cumulative += probabilities[i]
        if threshold <= cumulative:
            sampled_index = i
            break

    probability = probabilities[sampled_index]
    child = <FastState>scratch[child_depth]
    child.copy_from_fast(state)
    engine.apply_fast(child, actions[sampled_index])
    if actor == 0:
        return _packed_traverse(
            engine, child, traverser, child_depth, max_depth,
            nodes, rng, leaf_scale,
            reach0 * probability, reach1, scratch,
        )
    return _packed_traverse(
        engine, child, traverser, child_depth, max_depth,
        nodes, rng, leaf_scale,
        reach0, reach1 * probability, scratch,
    )


def packed_external_sampling_traverse(
    FastEngine engine,
    FastState state,
    int traverser,
    *,
    int depth,
    int max_depth,
    nodes,
    rng,
    double leaf_scale=100.0,
    scratch=None,
):
    if scratch is None:
        scratch = [FastState() for _ in range(max_depth + 1)]
    return _packed_traverse(
        engine,
        state,
        traverser,
        depth,
        max_depth,
        nodes,
        rng,
        leaf_scale,
        1.0,
        1.0,
        scratch,
    )


def make_scratch(int max_depth):
    return [FastState() for _ in range(max_depth + 1)]



cdef double _fast_external_sampling_traverse(
    FastEngine engine,
    FastState state,
    int traverser,
    int depth,
    int max_depth,
    dict nodes,
    object rng,
    object node_factory,
    double leaf_scale,
    double reach0,
    double reach1,
) except *:
    cdef int actor, n, i, sampled_index
    cdef uint64_t action
    cdef object actions
    cdef object info_key
    cdef object node
    cdef object pykey
    cdef double regret, positive_total = 0.0
    cdef double probability, threshold, cumulative
    cdef double node_utility = 0.0
    cdef double sampled_probability
    cdef double probs[MAX_ACTIONS]
    cdef double utilities[MAX_ACTIONS]
    cdef FastState child

    if state.phase == PHASE_COMPLETE:
        return 1.0 if state.winner == traverser else -1.0

    if depth >= max_depth:
        return tanh(engine.evaluate_fast(state, traverser) / leaf_scale)

    actor = state.active_player
    actions = engine.legal_actions_fast(state)
    n = len(actions)
    if n <= 0:
        raise RuntimeError("Non-terminal fast state has no legal actions")
    if n > MAX_ACTIONS:
        raise RuntimeError(
            f"Fast MCCFR action buffer exceeded: {n} > {MAX_ACTIONS}"
        )

    info_key = engine.information_key_fast(state, actor)
    node = nodes.get(info_key)
    if node is None:
        node = node_factory()
        nodes[info_key] = node

    node.visits += 1

    for i in range(n):
        pykey = actions[i]
        if pykey not in node.regret_sum:
            node.regret_sum[pykey] = 0.0
            node.strategy_sum[pykey] = 0.0
        regret = node.regret_sum[pykey]
        if regret > 0.0:
            probs[i] = regret
            positive_total += regret
        else:
            probs[i] = 0.0

    if positive_total > 0.0:
        for i in range(n):
            probs[i] /= positive_total
    else:
        probability = 1.0 / n
        for i in range(n):
            probs[i] = probability

    if actor == traverser:
        child = FastState()
        for i in range(n):
            action = <uint64_t>actions[i]
            child = state.clone_fast()
            engine.apply_fast(child, action)
            if actor == 0:
                utilities[i] = _fast_external_sampling_traverse(
                    engine,
                    child,
                    traverser,
                    depth + 1,
                    max_depth,
                    nodes,
                    rng,
                    node_factory,
                    leaf_scale,
                    reach0 * probs[i],
                    reach1,
                )
            else:
                utilities[i] = _fast_external_sampling_traverse(
                    engine,
                    child,
                    traverser,
                    depth + 1,
                    max_depth,
                    nodes,
                    rng,
                    node_factory,
                    leaf_scale,
                    reach0,
                    reach1 * probs[i],
                )
            node_utility += probs[i] * utilities[i]

        for i in range(n):
            pykey = actions[i]
            node.regret_sum[pykey] += utilities[i] - node_utility
        return node_utility

    node.average_visits += 1
    if actor == 0:
        probability = reach0
    else:
        probability = reach1
    for i in range(n):
        pykey = actions[i]
        node.strategy_sum[pykey] += probability * probs[i]

    threshold = rng.random()
    cumulative = 0.0
    sampled_index = n - 1
    for i in range(n):
        cumulative += probs[i]
        if threshold <= cumulative:
            sampled_index = i
            break

    sampled_probability = probs[sampled_index]
    action = <uint64_t>actions[sampled_index]
    child = state.clone_fast()
    engine.apply_fast(child, action)
    if actor == 0:
        return _fast_external_sampling_traverse(
            engine,
            child,
            traverser,
            depth + 1,
            max_depth,
            nodes,
            rng,
            node_factory,
            leaf_scale,
            reach0 * sampled_probability,
            reach1,
        )
    return _fast_external_sampling_traverse(
        engine,
        child,
        traverser,
        depth + 1,
        max_depth,
        nodes,
        rng,
        node_factory,
        leaf_scale,
        reach0,
        reach1 * sampled_probability,
    )


def fast_external_sampling_traverse(
    FastEngine engine,
    FastState state,
    int traverser,
    *,
    int max_depth,
    dict nodes,
    rng,
    node_factory,
    double leaf_scale=100.0,
    int depth=0,
):
    """External-sampling MCCFR directly on the primitive-array search state."""
    return _fast_external_sampling_traverse(
        engine,
        state,
        traverser,
        depth,
        max_depth,
        nodes,
        rng,
        node_factory,
        leaf_scale,
        1.0,
        1.0,
    )


def stable_information_id_from_fast_key(FastEngine engine, bytes key):
    """Translate a binary fast-search key to the legacy policy id.

    This runs only when exporting/looking up a policy, never inside traversal.
    """
    data = key
    i = 0
    version = data[i]
    i += 1
    if version not in (1, 2):
        raise ValueError(f"Unsupported fast information-key version: {version}")

    card_ids = engine.card_ids
    n_cards = len(card_ids)
    player = data[i]
    i += 1
    phase_code = data[i] - 1
    i += 1
    phase = ("battle", "choose_first", "complete")[phase_code]
    battle = data[i]
    i += 1
    active_player = data[i] - 1
    i += 1
    chooser_raw = data[i] - 1
    i += 1
    chooser = None if chooser_raw < 0 else chooser_raw

    victories = [data[i], data[i + 2]]
    passed = [bool(data[i + 1]), bool(data[i + 3])]
    i += 4

    pass_len = data[i]
    i += 1
    pass_order = []
    for _ in range(pass_len):
        pass_order.append(data[i] - 1)
        i += 1

    discarded_this_battle = [data[i], data[i + 1]]
    i += 2

    board = [[], []]
    for owner in range(2):
        for local in range(6):
            subject_code = data[i] - 1
            link_code = data[i + 1] - 1
            name_code = data[i + 2] - 1
            temporary = data[i + 3] - 64
            i += 4
            board[owner].append([
                local // 2,
                "front" if (local & 1) == 0 else "rear",
                None if subject_code < 0 else card_ids[subject_code],
                None if link_code < 0 else card_ids[link_code],
                None if name_code < 0 else card_ids[name_code],
                temporary,
            ])

    schemes = [[], []]
    for owner in range(2):
        for _front in range(3):
            card_code = data[i]
            revealed = bool(data[i + 1])
            i += 2
            if card_code == 0:
                schemes[owner].append(None)
            elif card_code == 255:
                schemes[owner].append(["hidden", False])
            else:
                schemes[owner].append([card_ids[card_code - 1], revealed])

    stratagems = []
    for owner in range(2):
        card_code = data[i]
        revealed = bool(data[i + 1])
        i += 2
        if card_code == 0:
            stratagems.append(None)
        elif card_code == 255:
            stratagems.append(["hidden", False])
        else:
            stratagems.append([card_ids[card_code - 1], revealed])

    stratagem_used = [bool(data[i]), bool(data[i + 1])]
    i += 2
    draw_used = [False, False]
    if version >= 2:
        draw_used = [bool(data[i]), bool(data[i + 1])]
        i += 2

    own_hand_counts = []
    for card_code in range(n_cards):
        count = data[i]
        i += 1
        if count:
            own_hand_counts.append([card_ids[card_code], count])
    own_hand_counts.sort(key=lambda row: row[0])

    own_deck_counts = []
    for card_code in range(n_cards):
        count = data[i]
        i += 1
        if count:
            own_deck_counts.append([card_ids[card_code], count])
    own_deck_counts.sort(key=lambda row: row[0])

    own_discard_len = data[i]
    i += 1
    own_discard = []
    for _ in range(own_discard_len):
        own_discard.append(card_ids[data[i] - 1])
        i += 1

    opponent_hand_count = data[i]
    i += 1

    known_counts = []
    for card_code in range(n_cards):
        count = data[i]
        i += 1
        if count:
            known_counts.append([card_ids[card_code], count])
    known_counts.sort(key=lambda row: row[0])

    opponent_deck_count = data[i]
    i += 1
    opponent_discard_len = data[i]
    i += 1
    opponent_discard = []
    for _ in range(opponent_discard_len):
        opponent_discard.append(card_ids[data[i] - 1])
        i += 1

    if i != len(data):
        raise ValueError(
            f"Fast information key decode mismatch: consumed {i}, size {len(data)}"
        )

    observation = {
        "viewer": player,
        "phase": phase,
        "battle": battle,
        "active_player": active_player,
        "chooser": chooser,
        "victories": victories,
        "passed": passed,
        "pass_order": pass_order,
        "discarded_this_battle": discarded_this_battle,
        "board": board,
        "schemes": schemes,
        "stratagems": stratagems,
        "stratagem_used": stratagem_used,
        "draw_used": draw_used,
        "own_hand": own_hand_counts,
        "own_deck": own_deck_counts,
        "own_discard": own_discard,
        "opponent_hand_count": opponent_hand_count,
        "known_opponent_hand": known_counts,
        "opponent_deck_count": opponent_deck_count,
        "opponent_discard": opponent_discard,
    }
    payload = json.dumps(
        observation,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
