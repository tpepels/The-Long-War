from __future__ import annotations

import random
from collections import Counter
from itertools import combinations
from typing import Any, Iterable

from ..cards import card_index, load_card_file
from .actions import (
    Action,
    BoardTarget,
    ChooseFirst,
    Pass,
    PlayLink,
    PlayName,
    PlayPlot,
    PlayScheme,
    PlaySubject,
)
from .model import (
    Front,
    GameState,
    Phase,
    PlayerState,
    Position,
    Rank,
    SchemeState,
    Slot,
)


class IllegalAction(ValueError):
    pass


class InvalidDeck(ValueError):
    pass


def all_positions() -> tuple[Position, ...]:
    return tuple(
        Position(front, rank)
        for front in Front
        for rank in (Rank.FRONT, Rank.REAR)
    )


class GameEngine:
    def __init__(self, card_data: dict[str, Any]):
        self.card_data = card_data
        self.cards = card_index(card_data)

    @classmethod
    def from_file(cls, path: str) -> "GameEngine":
        return cls(load_card_file(path))

    def validate_deck(self, deck: list[str]) -> None:
        if len(deck) != 30:
            raise InvalidDeck(f"A deck must contain exactly 30 cards, got {len(deck)}")

        counts = Counter(deck)
        for card_id, count in counts.items():
            if card_id not in self.cards:
                raise InvalidDeck(f"Unknown card: {card_id}")
            card = self.cards[card_id]
            maximum = 1 if card["unique"] else 2
            if count > maximum:
                raise InvalidDeck(
                    f"{card['title']} appears {count} times; maximum is {maximum}"
                )

    def new_game(
        self,
        deck_a: list[str],
        deck_b: list[str],
        *,
        seed: int = 0,
        first_player: int | None = None,
        mulligan_indices: tuple[tuple[int, ...], tuple[int, ...]] = ((), ()),
    ) -> GameState:
        self.validate_deck(deck_a)
        self.validate_deck(deck_b)
        rng = random.Random(seed)

        decks = [list(deck_a), list(deck_b)]
        for deck in decks:
            rng.shuffle(deck)

        players = [
            PlayerState(deck=decks[player], hand=[])
            for player in range(2)
        ]
        state = GameState(players=players)

        for player in range(2):
            self._draw(state, player, 10)
            self._apply_mulligan(
                state,
                player,
                mulligan_indices[player],
                rng,
            )

        state.active_player = rng.randrange(2) if first_player is None else first_player
        return state

    def _apply_mulligan(
        self,
        state: GameState,
        player: int,
        indices: tuple[int, ...],
        rng: random.Random,
    ) -> None:
        if len(indices) > 2 or len(set(indices)) != len(indices):
            raise ValueError("A mulligan may contain at most two distinct hand indices")
        hand = state.players[player].hand
        if any(index < 0 or index >= len(hand) for index in indices):
            raise ValueError("Mulligan index outside opening hand")

        returned = [hand[index] for index in sorted(indices)]
        for index in sorted(indices, reverse=True):
            del hand[index]
        state.players[player].deck.extend(returned)
        rng.shuffle(state.players[player].deck)
        self._draw(state, player, len(returned))

    def legal_actions(self, state: GameState) -> list[Action]:
        if state.phase is Phase.COMPLETE:
            return []

        if state.phase is Phase.CHOOSE_FIRST:
            if state.active_player != state.chooser:
                raise RuntimeError("Chooser must be the active player")
            return [ChooseFirst(0), ChooseFirst(1)]

        player = state.active_player
        if state.players[player].passed:
            raise RuntimeError("A passed player cannot become active")

        actions: list[Action] = [Pass()]
        unique_hand = list(dict.fromkeys(state.players[player].hand))

        for card_id in unique_hand:
            card = self.cards[card_id]
            card_type = card["type"]

            if card_type == "subject":
                actions.extend(self._subject_actions(state, player, card))
            elif card_type == "link":
                actions.extend(self._link_actions(state, player, card))
            elif card_type == "name":
                actions.extend(self._name_actions(state, player, card))
            elif card_type == "plot":
                if "scheme" in card.get("keywords", []):
                    actions.extend(self._scheme_actions(state, player, card))
                else:
                    actions.extend(self._plot_actions(state, player, card))

        return actions

    def apply(self, state: GameState, action: Action) -> None:
        legal = self.legal_actions(state)
        if action not in legal:
            raise IllegalAction(f"Illegal action: {action!r}")

        if isinstance(action, ChooseFirst):
            state.active_player = action.player
            state.chooser = None
            state.phase = Phase.BATTLE
            state.turn_number += 1
            return

        actor = state.active_player

        if isinstance(action, Pass):
            self._pass(state, actor)
            return

        if isinstance(action, PlaySubject):
            self._take_from_hand(state, actor, action.card_id)
            slot = state.slot(actor, action.position)
            slot.subject = action.card_id
            self._resolve_triggered_schemes(
                state,
                actor=actor,
                event="opponent_plays_subject",
                front=action.position.front,
                position=action.position,
            )

        elif isinstance(action, PlayLink):
            self._take_from_hand(state, actor, action.card_id)
            slot = state.slot(actor, action.position)
            slot.link = action.card_id
            subject = self.cards[slot.subject]
            bonus = subject.get("rules", {}).get("on_link_attached", {}).get(
                "temporary_strength", 0
            )
            slot.temporary_strength += int(bonus)
            self._resolve_triggered_schemes(
                state,
                actor=actor,
                event="opponent_plays_link",
                front=action.position.front,
                position=action.position,
            )

        elif isinstance(action, PlayName):
            self._take_from_hand(state, actor, action.card_id)
            slot = state.slot(actor, action.position)
            slot.name = action.card_id
            self._on_name_attached(
                state,
                actor,
                action.position,
                move_to=action.move_to,
            )

        elif isinstance(action, PlayPlot):
            self._take_from_hand(state, actor, action.card_id)
            plot_targets = tuple(action.targets)
            self._resolve_plot(state, actor, action)
            self._discard_card(state, actor, action.card_id)
            self._resolve_plot_target_schemes(
                state,
                actor=actor,
                targets=plot_targets,
            )

        elif isinstance(action, PlayScheme):
            self._take_from_hand(
                state,
                actor,
                action.card_id,
                reveal_identity=False,
            )
            state.schemes[actor][int(action.front)] = SchemeState(action.card_id)

        else:
            raise TypeError(f"Unhandled action type: {type(action)!r}")

        self._advance_turn(state)
        state.turn_number += 1

    def position_strength(
        self,
        state: GameState,
        player: int,
        position: Position,
    ) -> int:
        slot = state.slot(player, position)
        if slot.subject is None:
            return 0

        subject = self.cards[slot.subject]
        value = int(subject["strength"]) + slot.temporary_strength

        for modifier in subject.get("rules", {}).get("strength_modifiers", []):
            if self._condition_matches(state, player, position, modifier.get("when", {})):
                value += int(modifier["amount"])

        if slot.link is not None:
            link = self.cards[slot.link]
            link_rules = link.get("rules", {})
            value += int(link_rules.get("strength_bonus", 0))

            if slot.name is not None:
                name = self.cards[slot.name]
                name_rules = name.get("rules", {})
                value += int(link_rules.get("named_strength_bonus", 0))

                discard_bonus = link_rules.get("discard_strength_bonus")
                if discard_bonus:
                    per_card = int(discard_bonus.get("per_card", 1))
                    maximum = int(discard_bonus.get("maximum", 0))
                    value += min(
                        state.discarded_this_battle[player] * per_card,
                        maximum,
                    )

                value += int(name["strength"])

                rank_bonus = name_rules.get("rank_strength_bonus")
                if (
                    rank_bonus
                    and position.rank.value == rank_bonus.get("rank")
                ):
                    value += int(rank_bonus.get("amount", 0))

        return max(0, value)

    def front_strength(self, state: GameState, player: int, front: Front) -> int:
        value = sum(
            self.position_strength(state, player, Position(front, rank))
            for rank in (Rank.FRONT, Rank.REAR)
        )

        opponent = 1 - player
        for rank in (Rank.FRONT, Rank.REAR):
            enemy_slot = state.slot(opponent, Position(front, rank))
            if not enemy_slot.complete:
                continue
            enemy_link = self.cards[enemy_slot.link]
            value += int(
                enemy_link.get("rules", {}).get("opposing_front_modifier", 0)
            )

        return value

    def _condition_matches(
        self,
        state: GameState,
        player: int,
        position: Position,
        condition: dict[str, Any],
    ) -> bool:
        rank = condition.get("rank")
        if rank is not None and position.rank.value != rank:
            return False

        discard_at_least = condition.get("own_discard_at_least")
        if (
            discard_at_least is not None
            and len(state.players[player].discard) < int(discard_at_least)
        ):
            return False

        if condition.get("adjacent_subject_has_name"):
            if not any(
                state.slot(player, adjacent).name is not None
                for adjacent in self._adjacent_positions(position)
            ):
                return False

        return True

    def _subject_actions(
        self,
        state: GameState,
        player: int,
        card: dict[str, Any],
    ) -> Iterable[Action]:
        required_rank = card.get("rules", {}).get("placement", {}).get("rank")
        for position in all_positions():
            if state.slot(player, position).occupied:
                continue
            if required_rank is not None and position.rank.value != required_rank:
                continue
            yield PlaySubject(card["id"], position)

    def _link_actions(
        self,
        state: GameState,
        player: int,
        card: dict[str, Any],
    ) -> Iterable[Action]:
        for position in all_positions():
            slot = state.slot(player, position)
            if slot.subject is not None and slot.link is None:
                yield PlayLink(card["id"], position)

    def _name_actions(
        self,
        state: GameState,
        player: int,
        card: dict[str, Any],
    ) -> Iterable[Action]:
        for position in all_positions():
            slot = state.slot(player, position)
            if slot.subject is None or slot.link is None or slot.name is not None:
                continue

            on_complete = card.get("rules", {}).get("on_name_attached")
            if on_complete == "move_adjacent_optional":
                yield PlayName(card["id"], position, None)
                for destination in self._adjacent_positions(position):
                    if not state.slot(player, destination).occupied:
                        yield PlayName(card["id"], position, destination)
            else:
                yield PlayName(card["id"], position)

    def _plot_actions(
        self,
        state: GameState,
        player: int,
        card: dict[str, Any],
    ) -> Iterable[Action]:
        effect = card.get("rules", {}).get("effect")

        if effect == "discard_link":
            for target_player in range(2):
                for position in all_positions():
                    if state.slot(target_player, position).link is not None:
                        yield PlayPlot(
                            card["id"],
                            (BoardTarget(target_player, position),),
                        )
            return

        if effect == "return_outer_attachment":
            for target_player in range(2):
                for position in all_positions():
                    slot = state.slot(target_player, position)
                    if slot.link is None:
                        continue
                    if slot.name is not None and self._name_protected_from_plot(slot):
                        continue
                    yield PlayPlot(
                        card["id"],
                        (BoardTarget(target_player, position),),
                    )
            return

        if effect == "move_link":
            for source in all_positions():
                source_slot = state.slot(player, source)
                if source_slot.link is None:
                    continue
                for destination in all_positions():
                    if destination == source:
                        continue
                    destination_slot = state.slot(player, destination)
                    if (
                        destination_slot.subject is not None
                        and destination_slot.link is None
                    ):
                        yield PlayPlot(
                            card["id"],
                            (
                                BoardTarget(player, source),
                                BoardTarget(player, destination),
                            ),
                        )
            return

        if effect is None:
            yield PlayPlot(card["id"])
            return

        raise NotImplementedError(f"Unsupported plot effect: {effect}")

    def _scheme_actions(
        self,
        state: GameState,
        player: int,
        card: dict[str, Any],
    ) -> Iterable[Action]:
        for front in Front:
            if state.schemes[player][int(front)] is None:
                yield PlayScheme(card["id"], front)

    def _resolve_plot(
        self,
        state: GameState,
        actor: int,
        action: PlayPlot,
    ) -> None:
        effect = self.cards[action.card_id].get("rules", {}).get("effect")

        if effect == "discard_link":
            target = action.targets[0]
            self._remove_link(state, target.player, target.position)
            return

        if effect == "return_outer_attachment":
            target = action.targets[0]
            slot = state.slot(target.player, target.position)
            if slot.name is not None:
                self._remove_name(
                    state,
                    target.player,
                    target.position,
                    to_hand=True,
                )
            else:
                self._return_link_to_hand(
                    state,
                    target.player,
                    target.position,
                )
            return

        if effect == "move_link":
            source, destination = action.targets
            self._move_link(
                state,
                actor,
                source.position,
                destination.position,
            )
            return

        if effect is None:
            return

        raise NotImplementedError(f"Unsupported plot effect: {effect}")

    def _resolve_triggered_schemes(
        self,
        state: GameState,
        *,
        actor: int,
        event: str,
        front: Front,
        position: Position | None = None,
    ) -> None:
        for controller in (actor, 1 - actor):
            scheme = state.scheme(controller, front)
            if scheme is None:
                continue
            rules = self.cards[scheme.card_id].get("rules", {}).get("scheme", {})
            if rules.get("trigger") != event:
                continue
            if actor == controller:
                continue
            if rules.get("requires_own_subject") and not self._front_has_subject(
                state, controller, front
            ):
                continue
            self._reveal_and_resolve_scheme(
                state,
                controller=controller,
                front=front,
                actor=actor,
                position=position,
            )

    def _resolve_plot_target_schemes(
        self,
        state: GameState,
        *,
        actor: int,
        targets: tuple[BoardTarget, ...],
    ) -> None:
        opponent = 1 - actor
        targeted_fronts = {
            target.position.front
            for target in targets
            if target.player == opponent
        }
        for front in sorted(targeted_fronts, key=int):
            scheme = state.scheme(opponent, front)
            if scheme is None:
                continue
            rules = self.cards[scheme.card_id].get("rules", {}).get("scheme", {})
            if rules.get("trigger") != "opponent_plot_targets_your_card":
                continue
            if rules.get("requires_own_subject") and not self._front_has_subject(
                state, opponent, front
            ):
                continue
            self._reveal_and_resolve_scheme(
                state,
                controller=opponent,
                front=front,
                actor=actor,
            )

    def _resolve_pass_schemes(
        self,
        state: GameState,
        *,
        actor: int,
    ) -> None:
        opponent = 1 - actor
        for front in Front:
            scheme = state.scheme(opponent, front)
            if scheme is None:
                continue
            rules = self.cards[scheme.card_id].get("rules", {}).get("scheme", {})
            if rules.get("trigger") != "opponent_passes":
                continue
            if rules.get("requires_own_subject") and not self._front_has_subject(
                state, opponent, front
            ):
                continue
            self._reveal_and_resolve_scheme(
                state,
                controller=opponent,
                front=front,
                actor=actor,
            )

    def _reveal_and_resolve_scheme(
        self,
        state: GameState,
        *,
        controller: int,
        front: Front,
        actor: int,
        position: Position | None = None,
    ) -> None:
        scheme = state.scheme(controller, front)
        if scheme is None:
            return

        if not scheme.revealed:
            scheme.revealed = True
            state.observe_reveal(
                viewer=1 - controller,
                owner=controller,
                card_id=scheme.card_id,
                zone="scheme",
                reason="scheme_triggered",
            )

        card_id = scheme.card_id
        rules = self.cards[card_id].get("rules", {}).get("scheme", {})
        effect = rules.get("effect")
        amount = int(rules.get("amount", 0))

        if effect == "penalize_played_subject":
            if position is not None:
                slot = state.slot(actor, position)
                if slot.subject is not None:
                    slot.temporary_strength -= amount

        elif effect == "discard_played_link":
            if position is not None:
                slot = state.slot(actor, position)
                if slot.link is not None:
                    self._remove_link(state, actor, position)

        elif effect == "reinforce_front":
            target = self._preferred_subject_position(state, controller, front)
            if target is not None:
                state.slot(controller, target).temporary_strength += amount

        elif effect in (None, "none"):
            pass

        else:
            raise NotImplementedError(f"Unsupported Scheme effect: {effect}")

        state.schemes[controller][int(front)] = None
        self._discard_card(state, controller, card_id)

    def _front_has_subject(
        self,
        state: GameState,
        player: int,
        front: Front,
    ) -> bool:
        return self._preferred_subject_position(state, player, front) is not None

    @staticmethod
    def _preferred_subject_position(
        state: GameState,
        player: int,
        front: Front,
    ) -> Position | None:
        frontline = Position(front, Rank.FRONT)
        if state.slot(player, frontline).subject is not None:
            return frontline
        rear = Position(front, Rank.REAR)
        if state.slot(player, rear).subject is not None:
            return rear
        return None

    def _name_protected_from_plot(self, slot: Slot) -> bool:
        if not slot.complete:
            return False
        link = self.cards[slot.link]
        return bool(
            link.get("rules", {}).get("protect_name_from_plot_target")
        )

    def _on_name_attached(
        self,
        state: GameState,
        player: int,
        position: Position,
        *,
        move_to: Position | None = None,
    ) -> None:
        slot = state.slot(player, position)
        if slot.name is None:
            return
        name = self.cards[slot.name]
        effect = name.get("rules", {}).get("on_name_attached")

        if effect == "reveal_enemy_scheme":
            owner = 1 - player
            enemy_scheme = state.scheme(owner, position.front)
            if enemy_scheme is not None and not enemy_scheme.revealed:
                enemy_scheme.revealed = True
                state.observe_reveal(
                    viewer=player,
                    owner=owner,
                    card_id=enemy_scheme.card_id,
                    zone="scheme",
                    reason="revealed_by_name",
                )

        if effect == "move_adjacent_optional" and move_to is not None:
            self._move_legend(state, player, position, move_to)

    def _move_legend(
        self,
        state: GameState,
        player: int,
        source: Position,
        destination: Position,
    ) -> None:
        source_slot = state.slot(player, source)
        destination_slot = state.slot(player, destination)
        if destination_slot.occupied:
            raise IllegalAction("Destination is occupied")
        if destination not in self._adjacent_positions(source):
            raise IllegalAction("Destination is not adjacent")
        self._copy_slot(source_slot, destination_slot)
        self._clear_slot(source_slot)

    def _return_link_to_hand(
        self,
        state: GameState,
        player: int,
        position: Position,
    ) -> None:
        slot = state.slot(player, position)
        link_id = slot.link
        if link_id is None:
            raise IllegalAction("Position has no Link")
        if slot.name is not None:
            raise IllegalAction("Cannot return a Link while a Name is attached")

        slot.link = None
        self._return_public_card_to_hand(
            state,
            player,
            link_id,
            reason="link_returned",
        )

    def _move_link(
        self,
        state: GameState,
        player: int,
        source: Position,
        destination: Position,
    ) -> None:
        source_slot = state.slot(player, source)
        destination_slot = state.slot(player, destination)

        if source_slot.link is None:
            raise IllegalAction("Source has no Link")
        if destination_slot.subject is None:
            raise IllegalAction("Destination has no Subject")
        if destination_slot.link is not None:
            raise IllegalAction("Destination already has a Link")

        destination_slot.link = source_slot.link
        destination_slot.name = source_slot.name
        source_slot.link = None
        source_slot.name = None

    def _remove_link(
        self,
        state: GameState,
        player: int,
        position: Position,
    ) -> None:
        slot = state.slot(player, position)
        link_id = slot.link
        name_id = slot.name
        slot.link = None
        slot.name = None

        if link_id is not None:
            self._discard_card(state, player, link_id)
        if name_id is not None:
            self._return_public_card_to_hand(
                state,
                player,
                name_id,
                reason="link_removed",
            )

    def _remove_name(
        self,
        state: GameState,
        player: int,
        position: Position,
        *,
        to_hand: bool,
    ) -> str:
        slot = state.slot(player, position)
        name_id = slot.name
        if name_id is None:
            raise IllegalAction("Position has no Name")

        slot.name = None

        if to_hand:
            self._return_public_card_to_hand(
                state,
                player,
                name_id,
                reason="name_returned",
            )
        else:
            self._discard_card(state, player, name_id)

        return name_id

    def _discard_subject(
        self,
        state: GameState,
        player: int,
        position: Position,
    ) -> None:
        slot = state.slot(player, position)
        subject_id = slot.subject
        link_id = slot.link
        name_id = slot.name

        self._clear_slot(slot)

        if subject_id is not None:
            self._discard_card(state, player, subject_id)
        if link_id is not None:
            self._discard_card(state, player, link_id)
        if name_id is not None:
            self._return_public_card_to_hand(
                state,
                player,
                name_id,
                reason="subject_removed",
            )

    def _pass(self, state: GameState, player: int) -> None:
        state.players[player].passed = True
        state.pass_order.append(player)
        self._resolve_pass_schemes(state, actor=player)

        opponent = 1 - player
        if state.players[opponent].passed:
            self._score_battle(state)
        else:
            state.active_player = opponent

        state.turn_number += 1

    def _score_battle(self, state: GameState) -> None:
        front_scores = {
            front: (
                self.front_strength(state, 0, front),
                self.front_strength(state, 1, front),
            )
            for front in Front
        }

        controls = [0, 0]
        for score_a, score_b in front_scores.values():
            if score_a > score_b:
                controls[0] += 1
            elif score_b > score_a:
                controls[1] += 1

        if controls[0] >= 2:
            winner = 0
        elif controls[1] >= 2:
            winner = 1
        else:
            totals = [
                sum(scores[player] for scores in front_scores.values())
                for player in range(2)
            ]
            if totals[0] > totals[1]:
                winner = 0
            elif totals[1] > totals[0]:
                winner = 1
            else:
                winner = state.pass_order[0]

        state.players[winner].victories += 1
        loser = 1 - winner

        self._discard_battlefield(state)

        if state.players[winner].victories >= 2:
            state.phase = Phase.COMPLETE
            state.winner = winner
            state.chooser = None
            return

        state.battle += 1
        state.discarded_this_battle = [0, 0]
        state.pass_order.clear()
        for player in range(2):
            state.players[player].passed = False
            self._draw(state, player, 3)

        state.phase = Phase.CHOOSE_FIRST
        state.chooser = loser
        state.active_player = loser

    def _discard_battlefield(self, state: GameState) -> None:
        for player in range(2):
            for position in all_positions():
                slot = state.slot(player, position)
                for card_id in (slot.subject, slot.link, slot.name):
                    if card_id is not None:
                        state.players[player].discard.append(card_id)
                self._clear_slot(slot)

            for front in Front:
                scheme = state.schemes[player][int(front)]
                if scheme is not None:
                    state.players[player].discard.append(scheme.card_id)
                    state.schemes[player][int(front)] = None

    def _advance_turn(self, state: GameState) -> None:
        opponent = 1 - state.active_player
        if not state.players[opponent].passed:
            state.active_player = opponent

    def _take_from_hand(
        self,
        state: GameState,
        player: int,
        card_id: str,
        *,
        reveal_identity: bool = True,
    ) -> None:
        viewer = 1 - player
        if reveal_identity:
            if state.known_hidden_count(viewer, player, card_id, "hand") > 0:
                state.observe_hidden_delta(
                    viewer=viewer,
                    owner=player,
                    card_id=card_id,
                    zone="hand",
                    delta=-1,
                    reason="public_play_from_known_hand",
                )
        else:
            # A face-down play cannot reveal which exact known card left.
            # Reduce only guaranteed knowledge for card identities that could
            # legally be the hidden card, without consulting simulator truth.
            known = state.known_hidden_counter(viewer, player, "hand")
            for known_id, count in list(known.items()):
                card = self.cards[known_id]
                can_be_scheme = (
                    card["type"] == "plot"
                    and "scheme" in card.get("keywords", [])
                )
                if count > 0 and can_be_scheme:
                    state.observe_hidden_delta(
                        viewer=viewer,
                        owner=player,
                        card_id=known_id,
                        zone="hand",
                        delta=-1,
                        reason="possible_face_down_play",
                    )

        state.players[player].hand.remove(card_id)

    def _return_public_card_to_hand(
        self,
        state: GameState,
        player: int,
        card_id: str,
        *,
        reason: str,
    ) -> None:
        state.players[player].hand.append(card_id)
        state.observe_hidden_delta(
            viewer=1 - player,
            owner=player,
            card_id=card_id,
            zone="hand",
            delta=1,
            reason=reason,
        )

    def _discard_card(self, state: GameState, player: int, card_id: str) -> None:
        state.players[player].discard.append(card_id)
        state.discarded_this_battle[player] += 1

    def _draw(self, state: GameState, player: int, count: int) -> None:
        player_state = state.players[player]
        for _ in range(min(count, len(player_state.deck))):
            player_state.hand.append(player_state.deck.pop())

    def _adjacent_positions(self, position: Position) -> tuple[Position, ...]:
        positions: list[Position] = []
        index = int(position.front)
        if index > 0:
            positions.append(Position(Front(index - 1), position.rank))
        if index < 2:
            positions.append(Position(Front(index + 1), position.rank))
        return tuple(positions)

    @staticmethod
    def _clear_slot(slot: Slot) -> None:
        slot.subject = None
        slot.link = None
        slot.name = None
        slot.temporary_strength = 0

    @staticmethod
    def _copy_slot(source: Slot, destination: Slot) -> None:
        destination.subject = source.subject
        destination.link = source.link
        destination.name = source.name
        destination.temporary_strength = source.temporary_strength
