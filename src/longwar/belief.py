from __future__ import annotations

import random
from math import isfinite
from collections import Counter
from dataclasses import dataclass
from typing import Protocol

from .decks import (
    MINIMUM_DECK_SIZE,
    MINIMUM_FORCE_COUNT,
    MINIMUM_PRINTED_NAME_COUNT,
    NON_UNIQUE_COPY_LIMIT,
    UNIQUE_COPY_LIMIT,
)
from .game.engine import GameEngine, all_positions
from .game.model import Front, GameState
from .protocol import CardField, CardType


class BeliefStateError(ValueError):
    pass


class DeckPrior(Protocol):
    def sample_deck(
        self,
        required: Counter[str],
        rng: random.Random,
    ) -> list[str]:
        ...


@dataclass(frozen=True)
class DeckHypothesis:
    cards: tuple[str, ...]
    weight: float = 1.0
    label: str | None = None


class HypothesisDeckPrior:
    """Discrete prior over candidate decklists, conditioned on hard evidence."""

    def __init__(
        self,
        engine: GameEngine,
        hypotheses: list[DeckHypothesis],
    ):
        if not hypotheses:
            raise ValueError("At least one deck hypothesis is required")
        self.engine = engine
        self.hypotheses = list(hypotheses)
        for hypothesis in self.hypotheses:
            if not isfinite(hypothesis.weight) or hypothesis.weight <= 0:
                raise ValueError("Deck hypothesis weights must be positive")
            self.engine.validate_deck(list(hypothesis.cards))

    def posterior(
        self,
        required: Counter[str],
    ) -> list[tuple[DeckHypothesis, float]]:
        compatible = [
            hypothesis
            for hypothesis in self.hypotheses
            if self._contains(Counter(hypothesis.cards), required)
        ]
        if not compatible:
            raise BeliefStateError("No deck hypothesis is compatible with observed cards")
        total = sum(h.weight for h in compatible)
        return [(h, h.weight / total) for h in compatible]

    def sample_deck(
        self,
        required: Counter[str],
        rng: random.Random,
    ) -> list[str]:
        posterior = self.posterior(required)
        threshold = rng.random()
        cumulative = 0.0
        selected = posterior[-1][0]
        for hypothesis, probability in posterior:
            cumulative += probability
            if threshold <= cumulative:
                selected = hypothesis
                break
        return list(selected.cards)

    @staticmethod
    def _contains(deck: Counter[str], required: Counter[str]) -> bool:
        return all(deck[card_id] >= count for card_id, count in required.items())


class CardPoolDeckPrior:
    """Deck-construction prior derived only from the legal card pool.

    Required observed cards are conditioned in exactly. Remaining slots are
    sampled from legal remaining copy capacity. Optional per-card weights can
    encode an external metagame prior without revealing the true decklist.
    """

    def __init__(
        self,
        engine: GameEngine,
        *,
        deck_size: int,
        non_unique_copy_limit: int = NON_UNIQUE_COPY_LIMIT,
        unique_copy_limit: int = UNIQUE_COPY_LIMIT,
        card_weights: dict[str, float] | None = None,
    ):
        self.engine = engine
        if deck_size < MINIMUM_DECK_SIZE:
            raise ValueError(
                f"deck_size must be at least {MINIMUM_DECK_SIZE} "
                "for a canonical legal deck"
            )
        if non_unique_copy_limit < 1 or unique_copy_limit < 1:
            raise ValueError("copy limits must be positive")
        self.deck_size = deck_size
        self.non_unique_copy_limit = non_unique_copy_limit
        self.unique_copy_limit = unique_copy_limit
        self.card_weights = dict(card_weights or {})
        if any(not isfinite(weight) or weight < 0 for weight in self.card_weights.values()):
            raise ValueError("Card prior weights must be finite and non-negative")

    def sample_deck(
        self,
        required: Counter[str],
        rng: random.Random,
    ) -> list[str]:
        if any(
            card not in self.engine.cards or count < 0
            for card, count in required.items()
        ):
            raise BeliefStateError(
                "Observed cards contain unknown IDs or negative counts"
            )
        if sum(required.values()) > self.deck_size:
            raise BeliefStateError("Observed cards exceed deck size")

        capacities: dict[str, int] = {}
        for card_id, card in self.engine.cards.items():
            # Counterfactual baselines are intervention-only cards. They must
            # never enter a generic metagame belief unless hard evidence
            # already requires that exact experimental identity.
            if card.get("experimental", False) and required[card_id] == 0:
                continue
            maximum = (
                self.unique_copy_limit
                if card["unique"]
                else self.non_unique_copy_limit
            )
            if required[card_id] > maximum:
                raise BeliefStateError(
                    f"Observed {required[card_id]} copies of {card_id}, "
                    f"maximum is {maximum}"
                )
            capacities[card_id] = maximum - required[card_id]

        deck = [
            card_id
            for card_id, count in required.items()
            for _ in range(count)
        ]
        slots = self.deck_size - len(deck)

        required_forces = sum(
            count
            for card_id, count in required.items()
            if self.engine.cards[card_id][CardField.TYPE] == CardType.FORCE
        )
        required_names = sum(
            count
            for card_id, count in required.items()
            if self.engine.cards[card_id][CardField.TYPE] == CardType.NAME
        )
        force_needed = max(0, MINIMUM_FORCE_COUNT - required_forces)
        name_needed = max(
            0,
            MINIMUM_PRINTED_NAME_COUNT - required_names,
        )
        if force_needed + name_needed > slots:
            raise BeliefStateError(
                "Observed cards leave too few hidden slots to satisfy "
                "canonical Force/Name deck minimums"
            )

        def draw_one(card_type: str | None = None) -> None:
            candidates = [
                card_id
                for card_id, capacity in capacities.items()
                if capacity > 0
                and (
                    card_type is None
                    or self.engine.cards[card_id]["type"] == card_type
                )
            ]
            weights = [
                capacities[card_id]
                * self.card_weights.get(card_id, 1.0)
                for card_id in candidates
            ]
            if not candidates or sum(weights) <= 0:
                label = card_type or "legal"
                raise BeliefStateError(
                    f"No weighted {label} card remains for deck prior"
                )
            selected = rng.choices(candidates, weights=weights, k=1)[0]
            deck.append(selected)
            capacities[selected] -= 1

        for _ in range(force_needed):
            draw_one("force")
        for _ in range(name_needed):
            draw_one("name")
        while len(deck) < self.deck_size:
            draw_one()

        rng.shuffle(deck)
        try:
            self.engine.validate_deck(deck)
        except ValueError as exc:
            raise BeliefStateError(
                f"Deck prior produced an invalid deck: {exc}"
            ) from exc
        return deck


@dataclass(frozen=True)
class BeliefDiagnostics:
    viewer: int
    opponent: int
    public_opponent_cards: int
    known_hidden_hand_cards: int
    hidden_hand_cards: int
    hidden_deck_cards: int
    prior_type: str


class BeliefSampler:
    """Sample hidden states consistent with the player's full observation state."""

    def __init__(
        self,
        engine: GameEngine,
        priors: tuple[DeckPrior, DeckPrior] | None = None,
    ):
        self.engine = engine
        self.priors = priors

    def reuse_context(self, state: GameState, viewer: int) -> tuple[object, ...]:
        """Global context for values that are not encoded in information sets.

        The native information hash already contains the full observable game
        state, including own hand/deck composition, public opponent cards,
        known hidden cards and hidden-zone counts. Those observations therefore
        reroot the persistent tree instead of flushing it. Only changing the
        observer or the external deck prior invalidates every stored value.
        """
        self._validate_viewer(viewer)
        opponent = 1 - viewer
        return (
            viewer,
            self._prior_identity(state, opponent),
        )

    def diagnostics(self, state: GameState, viewer: int) -> BeliefDiagnostics:
        self._validate_viewer(viewer)
        opponent = 1 - viewer
        public = self._public_opponent_cards(state, opponent)
        known = state.known_hidden_cards(viewer, opponent, "hand")
        return BeliefDiagnostics(
            viewer=viewer,
            opponent=opponent,
            public_opponent_cards=len(public),
            known_hidden_hand_cards=len(known),
            hidden_hand_cards=len(state.players[opponent].hand),
            hidden_deck_cards=len(state.players[opponent].deck),
            prior_type=(
                type(self.priors[opponent]).__name__
                if self.priors is not None
                else "CardPoolDeckPrior"
            ),
        )

    def sample_hidden_zones(
        self,
        state: GameState,
        viewer: int,
        rng: random.Random,
    ) -> tuple[list[str], list[str], list[str]]:
        """Sample only hidden card zones for one information-set determinization."""
        self._validate_viewer(viewer)
        opponent = 1 - viewer

        # The viewer knows their own remaining deck composition, never its order.
        viewer_deck = list(state.players[viewer].deck)
        rng.shuffle(viewer_deck)

        public_cards = self._public_opponent_cards(state, opponent)
        known_hand = state.known_hidden_cards(viewer, opponent, "hand")
        hand_count = len(state.players[opponent].hand)
        deck_count = len(state.players[opponent].deck)

        if len(known_hand) > hand_count:
            raise BeliefStateError("Known opponent hand cards exceed hand size")

        required = Counter(public_cards)
        required.update(known_hand)
        prior = self._prior_for_state(state, opponent)
        sampled_full_deck = prior.sample_deck(required, rng)
        remaining = Counter(sampled_full_deck)

        for card_id in public_cards:
            remaining[card_id] -= 1
            if remaining[card_id] < 0:
                raise BeliefStateError(
                    f"Sampled deck lacks observed public card {card_id!r}"
                )
        for card_id in known_hand:
            remaining[card_id] -= 1
            if remaining[card_id] < 0:
                raise BeliefStateError(
                    f"Sampled deck lacks known hidden hand card {card_id!r}"
                )

        unknown_pool = [
            card_id
            for card_id, count in sorted(remaining.items())
            for _ in range(count)
        ]

        unknown_hand_slots = hand_count - len(known_hand)
        expected = unknown_hand_slots + deck_count
        if len(unknown_pool) != expected:
            sampled_counts = Counter(sampled_full_deck)
            visible_zone_counts = Counter(public_cards)
            visible_zone_counts.update(state.players[opponent].hand)
            visible_zone_counts.update(state.players[opponent].deck)
            missing = sampled_counts - visible_zone_counts
            extra = visible_zone_counts - sampled_counts
            raise BeliefStateError(
                "Sampled deck/public-zone accounting mismatch: "
                f"remaining={len(unknown_pool)} expected={expected}; "
                f"battle={state.battle} turn={state.turn_number} "
                f"viewer={viewer} opponent={opponent}; "
                f"public={len(public_cards)} hand={hand_count} deck={deck_count}; "
                f"missing={dict(sorted(missing.items()))} "
                f"extra={dict(sorted(extra.items()))}"
            )

        rng.shuffle(unknown_pool)
        opponent_hand = (
            list(known_hand) + list(unknown_pool[:unknown_hand_slots])
        )
        rng.shuffle(opponent_hand)
        opponent_deck = list(unknown_pool[unknown_hand_slots:])
        return viewer_deck, opponent_hand, opponent_deck

    def sample(
        self,
        state: GameState,
        viewer: int,
        rng: random.Random,
    ) -> GameState:
        viewer_deck, opponent_hand, opponent_deck = self.sample_hidden_zones(
            state,
            viewer,
            rng,
        )
        sampled = state.clone()
        opponent = 1 - viewer
        sampled.players[viewer].deck = viewer_deck
        sampled.players[opponent].hand = opponent_hand
        sampled.players[opponent].deck = opponent_deck
        return sampled

    def _prior_for_state(
        self,
        state: GameState,
        player: int,
    ) -> DeckPrior:
        if self.priors is not None:
            return self.priors[player]
        return CardPoolDeckPrior(
            self.engine,
            deck_size=self._deck_size_from_state(state, player),
        )

    def _prior_identity(
        self,
        state: GameState,
        player: int,
    ) -> object:
        if self.priors is not None:
            return id(self.priors[player])
        return ("card-pool", self._deck_size_from_state(state, player))

    @staticmethod
    def _deck_size_from_state(state: GameState, player: int) -> int:
        """Recover the supplied deck size from public zone counts.

        Card identities may be hidden, but the number of cards in each zone is
        part of the observable game state. No match-rule deck-size constant is
        needed.
        """
        ps = state.players[player]
        total = len(ps.deck) + len(ps.hand) + len(ps.discard)
        for front in state.board[player]:
            for slot in front:
                total += int(slot.force is not None)
                total += int(slot.bond is not None)
                total += int(slot.name is not None)
        total += len(state.narratives[player])
        total += int(state.stratagems[player] is not None)
        return total

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
                for card_id in (slot.force, slot.bond, slot.name)
                if card_id is not None
            )

        cards.extend(narrative.card_id for narrative in state.narratives[opponent])

        stratagem = state.stratagems[opponent]
        if stratagem is not None:
            cards.append(stratagem.card_id)

        return cards

    @staticmethod
    def _validate_viewer(viewer: int) -> None:
        if viewer not in (0, 1):
            raise ValueError("viewer must be 0 or 1")
