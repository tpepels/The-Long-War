from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass

from .game.engine import GameEngine, all_positions
from .game.model import Front, GameState


class BeliefStateError(ValueError):
    pass


@dataclass(frozen=True)
class BeliefDiagnostics:
    viewer: int
    opponent: int
    public_opponent_cards: int
    hidden_hand_cards: int
    hidden_deck_cards: int
    hidden_schemes: int


class BeliefSampler:
    """Sample hidden states consistent with one player's observable state.

    The opponent's registered deck list is treated as known. Public opponent
    cards are subtracted from that deck, then the remaining multiset is sampled
    across hidden hand, deck, and unrevealed Scheme slots. The viewer's future
    deck order is also resampled because its order is unknown.

    This deliberately does not inspect the actual opponent hand or deck stored
    in GameState. It therefore cannot accidentally determinize from privileged
    simulator information.
    """

    def __init__(
        self,
        engine: GameEngine,
        decklists: tuple[list[str], list[str]],
    ):
        self.engine = engine
        self.decklists = (list(decklists[0]), list(decklists[1]))
        self.engine.validate_deck(self.decklists[0])
        self.engine.validate_deck(self.decklists[1])

    def diagnostics(self, state: GameState, viewer: int) -> BeliefDiagnostics:
        self._validate_viewer(viewer)
        opponent = 1 - viewer
        hidden_schemes = sum(
            1
            for front in Front
            if (
                state.scheme(opponent, front) is not None
                and not state.scheme(opponent, front).revealed
            )
        )
        public = self._public_opponent_cards(state, opponent)
        return BeliefDiagnostics(
            viewer=viewer,
            opponent=opponent,
            public_opponent_cards=len(public),
            hidden_hand_cards=len(state.players[opponent].hand),
            hidden_deck_cards=len(state.players[opponent].deck),
            hidden_schemes=hidden_schemes,
        )

    def sample(
        self,
        state: GameState,
        viewer: int,
        rng: random.Random,
    ) -> GameState:
        self._validate_viewer(viewer)
        opponent = 1 - viewer
        sampled = state.clone()

        # The viewer knows the remaining cards in their own deck, but not order.
        rng.shuffle(sampled.players[viewer].deck)

        public_cards = self._public_opponent_cards(state, opponent)
        remaining = Counter(self.decklists[opponent])
        for card_id in public_cards:
            remaining[card_id] -= 1
            if remaining[card_id] < 0:
                raise BeliefStateError(
                    f"Public opponent card {card_id!r} exceeds known deck copies"
                )

        unknown_pool: list[str] = []
        for card_id, count in sorted(remaining.items()):
            if count < 0:
                raise BeliefStateError(f"Negative remaining count for {card_id}")
            unknown_pool.extend([card_id] * count)

        hidden_scheme_fronts = [
            front
            for front in Front
            if (
                state.scheme(opponent, front) is not None
                and not state.scheme(opponent, front).revealed
            )
        ]
        hand_count = len(state.players[opponent].hand)
        deck_count = len(state.players[opponent].deck)
        expected = hand_count + deck_count + len(hidden_scheme_fronts)
        if len(unknown_pool) != expected:
            raise BeliefStateError(
                "Observed public/hidden zone counts are inconsistent with the "
                f"known opponent deck: remaining={len(unknown_pool)} expected={expected}"
            )

        # Hidden Scheme identities are constrained to cards that can legally be
        # Schemes. Sample them before the unconstrained hand/deck partition.
        for front in hidden_scheme_fronts:
            eligible = [
                index
                for index, card_id in enumerate(unknown_pool)
                if self._is_scheme_card(card_id)
            ]
            if not eligible:
                raise BeliefStateError(
                    "Hidden Scheme slot exists but no Scheme-capable card "
                    "remains in the opponent belief pool"
                )
            index = rng.choice(eligible)
            card_id = unknown_pool.pop(index)
            sampled.schemes[opponent][int(front)].card_id = card_id

        rng.shuffle(unknown_pool)
        sampled.players[opponent].hand = list(unknown_pool[:hand_count])
        sampled.players[opponent].deck = list(unknown_pool[hand_count:])
        if len(sampled.players[opponent].deck) != deck_count:
            raise BeliefStateError("Belief deck partition produced wrong size")

        return sampled

    def _public_opponent_cards(
        self,
        state: GameState,
        opponent: int,
    ) -> list[str]:
        cards = list(state.players[opponent].discard)

        for position in all_positions():
            slot = state.slot(opponent, position)
            cards.extend(
                card_id
                for card_id in (slot.subject, slot.link, slot.name)
                if card_id is not None
            )

        for front in Front:
            scheme = state.scheme(opponent, front)
            if scheme is not None and scheme.revealed:
                cards.append(scheme.card_id)

        return cards

    def _is_scheme_card(self, card_id: str) -> bool:
        card = self.engine.cards[card_id]
        return card["type"] == "plot" and "scheme" in card.get("keywords", [])

    @staticmethod
    def _validate_viewer(viewer: int) -> None:
        if viewer not in (0, 1):
            raise ValueError("viewer must be 0 or 1")
