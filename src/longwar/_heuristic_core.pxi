cdef class NativeHeuristicEvaluator:
    """Compiled heuristic policy, independent of game transitions/search."""

    cdef FastEngine engine

    def __init__(self, FastEngine engine):
        self.engine = engine

    cdef double evaluate_fast(self, FastState state, int player) noexcept:
        cdef int opponent = 1 - player
        cdef int front, margin, raw_margin, controls=0, enemy_controls=0
        cdef int hand_delta, named_delta=0, scheme_delta=0, strat_delta=0
        cdef int exposed=0, reachable=0, slot, name_card, before, after, best
        cdef int card, own_forces=0, own_board_subjects=0, hero_force=0
        cdef int own_losses=0, opponent_losses=0
        cdef int own_front_slot, own_rear_slot, opp_front_slot, opp_rear_slot
        cdef int recovery=0, own_recovery=0, opponent_recovery=0
        cdef int own_projected=0, opponent_projected=0
        cdef int current_delta=0, projected_delta=0
        cdef int own_vulnerability=0, opponent_vulnerability=0
        cdef double score = 0.0, option = 0.0

        if state.phase == PHASE_COMPLETE:
            return 10000.0 if state.winner == player else -10000.0

        for front in range(4):
            raw_margin = (
                self.engine.front_strength_fast(state, player, front)
                - self.engine.front_strength_fast(state, opponent, front)
            )
            margin = raw_margin

            if raw_margin > 0:
                controls += 1
                opponent_losses += 1
                if raw_margin <= 3:
                    score += 1.25
                if raw_margin <= 4:
                    exposed += 1

                # A lost Front drives off a Rear Named Formation and only
                # Retreats a Frontline Named Formation. Value persistence,
                # not just current Strength.
                opp_front_slot = slot_index(opponent, front, 0)
                opp_rear_slot = slot_index(opponent, front, 1)
                if self.engine.slot_complete(state, opp_rear_slot):
                    score += 4.0
                if self.engine.slot_complete(state, opp_front_slot):
                    score += 0.75

                # Margin beyond a comfortable buffer has no core scoring
                # value. Keep a little value for resilience, but strongly
                # prefer Strength that can change another Front result.
                if raw_margin > 5:
                    score -= 0.45 * (raw_margin - 5)

            elif raw_margin < 0:
                enemy_controls += 1
                own_losses += 1
                if raw_margin >= -3:
                    score -= 1.25
                if raw_margin >= -4:
                    reachable += 1

                own_front_slot = slot_index(player, front, 0)
                own_rear_slot = slot_index(player, front, 1)
                if self.engine.slot_complete(state, own_rear_slot):
                    score -= 4.0
                if self.engine.slot_complete(state, own_front_slot):
                    score -= 0.75

                if raw_margin < -5:
                    score += 0.45 * ((-raw_margin) - 5)
            else:
                reachable += 1

            if margin > 10:
                margin = 10
            elif margin < -10:
                margin = -10
            score += 0.75 * margin

        score += 7.0 * (controls - enemy_controls)

        hand_delta = state.hand_len[player] - state.hand_len[opponent]
        score += 1.25 * hand_delta

        for card in range(self.engine.n_cards):
            if self.engine.card_type[card] == CARD_SUBJECT:
                if self.engine.hero[card]:
                    if (
                        not state.hero_used[player]
                        and state.hand[player][card] > 0
                    ):
                        hero_force = 1
                else:
                    own_forces += state.hand[player][card]
        own_forces += hero_force
        if own_forces > 3:
            own_forces = 3
        score += 0.35 * own_forces

        for slot in range(player * 8, player * 8 + 8):
            if state.subject[slot] >= 0:
                own_board_subjects += 1
        if own_forces == 0 and own_board_subjects == 0:
            score -= 2.0

        if self.engine.command_enabled:
            current_delta = state.command[player] - state.command[opponent]
            score += 0.45 * current_delta

            # Project the rulebook's exact recovery formula using the current
            # Front results. This makes late-war Command and likely Collapse
            # visible to shallow search and rollouts.
            recovery = self.engine.command_recovery_for_battle(state.battle)
            own_recovery = recovery - own_losses
            if own_recovery < 0:
                own_recovery = 0
            opponent_recovery = recovery - opponent_losses
            if opponent_recovery < 0:
                opponent_recovery = 0
            own_projected = state.command[player] + own_recovery
            opponent_projected = (
                state.command[opponent] + opponent_recovery
            )
            if own_projected > self.engine.command_cap:
                own_projected = self.engine.command_cap
            if opponent_projected > self.engine.command_cap:
                opponent_projected = self.engine.command_cap

            projected_delta = own_projected - opponent_projected
            score += 0.35 * (projected_delta - current_delta)

            own_vulnerability = (
                self.engine.command_collapse_threshold + 3 - own_projected
            )
            if own_vulnerability < 0:
                own_vulnerability = 0
            opponent_vulnerability = (
                self.engine.command_collapse_threshold + 3
                - opponent_projected
            )
            if opponent_vulnerability < 0:
                opponent_vulnerability = 0
            score += 0.8 * (
                opponent_vulnerability - own_vulnerability
            )

            if (
                own_projected < self.engine.command_collapse_threshold
                or opponent_projected
                < self.engine.command_collapse_threshold
            ):
                if own_projected < opponent_projected:
                    score -= 28.0
                elif own_projected > opponent_projected:
                    score += 28.0

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

        for slot in range(player * 8, player * 8 + 8):
            if self.engine.slot_complete(state, slot):
                named_delta += 1
        for slot in range(opponent * 8, opponent * 8 + 8):
            if self.engine.slot_complete(state, slot):
                named_delta -= 1
        score += 1.5 * named_delta

        for front in range(self.engine.ongoing_story_limit):
            if state.scheme[player * 4 + front] >= 0:
                scheme_delta += 1
            if state.scheme[opponent * 4 + front] >= 0:
                scheme_delta -= 1
        score += 0.75 * scheme_delta

        strat_delta = (
            (1 if state.stratagem[player] >= 0 else 0)
            - (1 if state.stratagem[opponent] >= 0 else 0)
        )
        score += 0.45 * strat_delta

        for slot in range(player * 8, player * 8 + 8):
            if state.subject[slot] < 0 or state.name[slot] >= 0:
                continue
            before = self.engine.position_strength_fast(state, slot)
            best = -32768
            for name_card in range(self.engine.n_cards):
                if state.hand[player][name_card] == 0:
                    continue
                if self.engine.card_type[name_card] != CARD_NAME:
                    if (
                        not self.engine.hero[name_card]
                        or state.hero_used[player]
                    ):
                        continue
                state.name[slot] = name_card
                after = self.engine.position_strength_fast(state, slot)
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
        for local in range(8):
            slot = player * 8 + local
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
        cdef double value=0.0, subject_value=0.0, name_value=0.0
        for local in range(8):
            slot = player * 8 + local
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

        for card in range(self.engine.n_cards):
            count = state.hand[player][card]
            if count == 0:
                continue
            typ = self.engine.card_type[card]
            if typ == CARD_SUBJECT:
                subject_value = 0.45 + (0.95 if needs_subject else 0.0)
                if self.engine.hero[card]:
                    if state.hero_used[player]:
                        continue
                    name_value = 0.35 + (1.05 if needs_name else 0.0)
                    value += count * (
                        subject_value
                        if subject_value >= name_value
                        else name_value
                    )
                else:
                    value += count * subject_value
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
        cdef int card, count, subjects=0, links=0, names=0, heroes=0
        cdef int value, candidate
        for card in range(self.engine.n_cards):
            count = state.hand[player][card] + state.deck_counts[player][card]
            if self.engine.card_type[card] == CARD_SUBJECT:
                if self.engine.hero[card]:
                    heroes += count
                else:
                    subjects += count
            elif self.engine.card_type[card] == CARD_LINK:
                links += count
            elif self.engine.card_type[card] == CARD_NAME:
                names += count
        value = subjects
        if links < value:
            value = links
        if names < value:
            value = names
        if heroes > 0 and not state.hero_used[player]:
            candidate = subjects + 1
            if links < candidate:
                candidate = links
            if names < candidate:
                candidate = names
            if candidate > value:
                value = candidate

            candidate = subjects
            if links < candidate:
                candidate = links
            if names + 1 < candidate:
                candidate = names + 1
            if candidate > value:
                value = candidate
        return value

    cdef double future_force_availability_fast(
        self,
        FastState state,
        int player,
    ) noexcept:
        cdef int card, i, immediate=0, discarded=0
        cdef bint hero_available=False, discarded_hero=False
        for card in range(self.engine.n_cards):
            if self.engine.card_type[card] == CARD_SUBJECT:
                if self.engine.hero[card]:
                    if (
                        not state.hero_used[player]
                        and (
                            state.hand[player][card]
                            + state.deck_counts[player][card]
                        ) > 0
                    ):
                        hero_available = True
                else:
                    immediate += (
                        state.hand[player][card]
                        + state.deck_counts[player][card]
                    )
        for i in range(state.discard_len[player]):
            card = state.discard[player][i]
            if self.engine.card_type[card] == CARD_SUBJECT:
                if self.engine.hero[card]:
                    if not state.hero_used[player]:
                        discarded_hero = True
                else:
                    discarded += 1
        return (
            immediate
            + (1.0 if hero_available else 0.0)
            + 0.35 * (
                discarded + (1 if discarded_hero else 0)
            )
        )

    cdef int affordable_hand_count_fast(
        self,
        FastState state,
        int player,
    ) noexcept:
        cdef int card, total=0
        if not self.engine.command_enabled:
            return state.hand_len[player]
        for card in range(self.engine.n_cards):
            if (
                state.hand[player][card]
                and self.engine.card_command_cost[card] <= state.command[player]
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

        if not self.engine.recycle_between_battles:
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

        if self.engine.command_enabled:
            value += 0.12 * (
                self.affordable_hand_count_fast(state, player)
                - self.affordable_hand_count_fast(state, opponent)
            )

        return value

    cdef double battle_boundary_evaluate_fast(
        self,
        FastState state,
        int player,
    ) noexcept:
        # Battle resolution already applied cleanup, Retreat, recovery and
        # Command Collapse. The resulting state is the correct strategic leaf.
        return self.strategic_evaluate_fast(state, player)

    cdef double pass_score_fast(
        self,
        FastState state,
        int player,
        FastState child,
    ):
        cdef int front, margin, total_margin=0, wins=0, losses=0, tied=0
        cdef int opponent = 1 - player
        cdef double score

        child.copy_from_fast(state)
        self.engine.pass_action(child, player)
        if child.phase != PHASE_BATTLE or child.battle != state.battle:
            return self.battle_boundary_evaluate_fast(child, player)

        score = self.evaluate_fast(state, player)
        for front in range(4):
            margin = (
                self.engine.front_strength_fast(state, player, front)
                - self.engine.front_strength_fast(state, opponent, front)
            )
            total_margin += margin
            if margin > 0:
                wins += 1
            elif margin < 0:
                losses += 1
            else:
                tied += 1

        # A first Pass offers the opponent a normal turn; an intervening
        # operation clears that Pass, while a consecutive Pass ends the Battle.
        score += 4.0 * (wins - losses)
        score += 0.35 * total_margin
        score += 0.4 * tied
        score -= min(8.0, 0.8 * state.hand_len[opponent])
        if state.pass_len == 0:
            score += 1.5
        return score

    cdef double rollout_prior_fast(
        self,
        FastState state,
        int player,
        uint64_t action,
    ) noexcept:
        """Cheap stochastic-rollout prior; never copies or advances state."""
        cdef int kind = action_kind(action)
        cdef int pos = action_pos(action)
        cdef double weight = 1.0

        if kind == TYPE_PASS:
            return 0.20
        if kind == TYPE_CHOOSE:
            return 1.0
        if kind == TYPE_DRAW:
            return 0.85
        if kind == TYPE_CYCLE:
            return 0.45
        if kind == TYPE_DISCARD:
            return 1.0
        if kind == TYPE_MANEUVER:
            return 0.90
        if kind == TYPE_SUBJECT:
            weight = 1.35
            if pos >= 0 and (
                state.link[pos] >= 0 or state.name[pos] >= 0
            ):
                weight += 0.90
            return weight
        if kind == TYPE_LINK:
            weight = 1.0
            if pos >= 0 and state.subject[pos] >= 0:
                weight += 0.80
            if pos >= 0 and state.name[pos] >= 0:
                weight += 0.35
            return weight
        if kind == TYPE_NAME:
            weight = 1.05
            if pos >= 0 and state.subject[pos] >= 0:
                weight += 0.85
            if pos >= 0 and state.link[pos] >= 0:
                weight += 0.65
            return weight
        if kind == TYPE_PLOT:
            return 0.75
        if kind == TYPE_SCHEME:
            return 0.70
        if kind == TYPE_STRATAGEM:
            return 0.65
        return 1.0

    cdef double action_order_score_fast(
        self,
        FastState state,
        int player,
        uint64_t action,
        FastState child,
    ):
        cdef int kind = action_kind(action)
        cdef int pos = action_pos(action)
        cdef int force_count=0, card, front, margin_before=0, margin_after=0
        cdef double score

        if kind == TYPE_PASS:
            return self.pass_score_fast(state, player, child)

        child.copy_from_fast(state)
        self.engine.apply_fast(child, action)
        score = self.evaluate_fast(child, player)

        if kind == TYPE_DISCARD:
            score += 0.55 * self.hand_construction_value_fast(
                child,
                player,
            )
        elif kind == TYPE_LINK:
            score += 0.10 if state.subject[pos] >= 0 else 1.35
        elif kind == TYPE_NAME:
            score += 0.35 if state.subject[pos] >= 0 else 1.50
        elif kind == TYPE_SCHEME:
            score += 0.20
        elif kind == TYPE_STRATAGEM:
            score += 0.20
        elif kind == TYPE_MANEUVER:
            score += 0.15

        return score

    cpdef double evaluate(self, FastState state, int player):
        return self.evaluate_fast(state, player)

    cpdef double strategic_evaluate(self, FastState state, int player):
        return self.strategic_evaluate_fast(state, player)

    cpdef double battle_boundary_evaluate(
        self,
        FastState state,
        int player,
    ):
        return self.battle_boundary_evaluate_fast(state, player)

    cpdef double hand_construction_value(
        self,
        FastState state,
        int player,
    ):
        return self.hand_construction_value_fast(state, player)

    cpdef double score_action(
        self,
        FastState state,
        int player,
        uint64_t action,
    ):
        cdef FastState scratch = FastState()
        return self.action_order_score_fast(
            state,
            player,
            action,
            scratch,
        )
