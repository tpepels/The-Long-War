from __future__ import annotations

import random
from math import isfinite
from collections import Counter
from dataclasses import dataclass
from typing import Protocol

from .decks import NON_UNIQUE_COPY_LIMIT, UNIQUE_COPY_LIMIT
from .game.engine import GameEngine, all_positions
from .game.model import Front, GameState


class BeliefStateError(ValueError):
    pass


# Each group describes disjoint card identities eligible for hidden slots.
HiddenRequirements = tuple[tuple[frozenset[str], int], ...]


class DeckPrior(Protocol):
    def sample_deck(
        self,
        required: Counter[str],
        rng: random.Random,
        *,
        hidden_requirements: HiddenRequirements = (),
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
        *,
        hidden_requirements: HiddenRequirements = (),
    ) -> list[tuple[DeckHypothesis, float]]:
        compatible = [
            hypothesis
            for hypothesis in self.hypotheses
            if self._contains(Counter(hypothesis.cards), required)
            and all(
                sum((Counter(hypothesis.cards) - required)[card] for card in eligible) >= count
                for eligible, count in hidden_requirements
            )
        ]
        if not compatible:
            raise BeliefStateError("No deck hypothesis is compatible with observed cards")
        total = sum(h.weight for h in compatible)
        return [(h, h.weight / total) for h in compatible]

    def sample_deck(
        self,
        required: Counter[str],
        rng: random.Random,
        *,
        hidden_requirements: HiddenRequirements = (),
    ) -> list[str]:
        posterior = self.posterior(required, hidden_requirements=hidden_requirements)
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
        if deck_size < 1:
            raise ValueError("deck_size must be positive")
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
        *,
        hidden_requirements: HiddenRequirements = (),
    ) -> list[str]:
        if any(card not in self.engine.cards or count < 0 for card, count in required.items()):
            raise BeliefStateError("Observed cards contain unknown IDs or negative counts")
        if sum(required.values()) + sum(count for _, count in hidden_requirements) > self.deck_size:
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
                    f"Observed {required[card_id]} copies of {card_id}, maximum is {maximum}"
                )
            capacities[card_id] = maximum - required[card_id]

        deck = [
            card_id
            for card_id, count in required.items()
            for _ in range(count)
        ]

        # Hidden card identities are unknown, but an occupied hidden slot is
        # evidence of its type. Reserve these cards before filling other slots.
        for eligible, count in hidden_requirements:
            for _ in range(count):
                candidates = [card for card in sorted(eligible) if capacities.get(card, 0) > 0]
                weights = [capacities[card] * self.card_weights.get(card, 1.0) for card in candidates]
                if not candidates or sum(weights) <= 0:
                    raise BeliefStateError("No legal card remains for an observed hidden slot")
                selected = rng.choices(candidates, weights=weights, k=1)[0]
                deck.append(selected)
                capacities[selected] -= 1

        slots = self.deck_size - len(deck)
        if sum(capacities.values()) < slots:
            raise BeliefStateError(
                "Card pool cannot construct a legal deck consistent with observations"
            )

        for _ in range(slots):
            candidates = [
                card_id for card_id, capacity in capacities.items()
                if capacity > 0
            ]
            weights = [
                capacities[card_id] * self.card_weights.get(card_id, 1.0)
                for card_id in candidates
            ]
            if not candidates or sum(weights) <= 0:
                raise BeliefStateError("No legal card remains for deck prior")
            selected = rng.choices(candidates, weights=weights, k=1)[0]
            deck.append(selected)
            capacities[selected] -= 1

        rng.shuffle(deck)
        self.engine.validate_deck(deck)
        return deck


@dataclass(frozen=True)
class BeliefDiagnostics:
    viewer: int
    opponent: int
    public_opponent_cards: int
    known_hidden_hand_cards: int
    hidden_hand_cards: int
    hidden_deck_cards: int
    hidden_schemes: int
    hidden_stratagems: int
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
        """Hard evidence whose change invalidates root-sampled search values.

        Public deterministic moves can reuse matching information sets. A draw,
        reveal, hidden-zone change or observer change conditions a different
        belief and must not inherit values from the previous distribution.
        Opponent hidden card identities and deck order never enter this key.
        """
        self._validate_viewer(viewer)
        opponent = 1 - viewer
        diagnostics = self.diagnostics(state, viewer)
        return (
            viewer,
            self._prior_identity(state, opponent),
            tuple(sorted(state.players[viewer].deck)),
            tuple(sorted(self._public_opponent_cards(state, opponent))),
            tuple(sorted(state.known_hidden_cards(viewer, opponent, "hand"))),
            diagnostics.hidden_hand_cards,
            diagnostics.hidden_deck_cards,
            diagnostics.hidden_schemes,
            diagnostics.hidden_stratagems,
        )

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
        hidden_stratagems = int(
            state.stratagem(opponent) is not None
            and not state.stratagem(opponent).revealed
        )
        public = self._public_opponent_cards(state, opponent)
        known = state.known_hidden_cards(viewer, opponent, "hand")
        return BeliefDiagnostics(
            viewer=viewer,
            opponent=opponent,
            public_opponent_cards=len(public),
            known_hidden_hand_cards=len(known),
            hidden_hand_cards=len(state.players[opponent].hand),
            hidden_deck_cards=len(state.players[opponent].deck),
            hidden_schemes=hidden_schemes,
            hidden_stratagems=hidden_stratagems,
            prior_type=(
                type(self.priors[opponent]).__name__
                if self.priors is not None
                else "CardPoolDeckPrior"
            ),
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

        # The viewer knows their own remaining deck composition, never its order.
        rng.shuffle(sampled.players[viewer].deck)

        public_cards = self._public_opponent_cards(state, opponent)
        known_hand = state.known_hidden_cards(viewer, opponent, "hand")
        hand_count = len(state.players[opponent].hand)
        deck_count = len(state.players[opponent].deck)

        if len(known_hand) > hand_count:
            raise BeliefStateError("Known opponent hand cards exceed hand size")

        required = Counter(public_cards)
        required.update(known_hand)
        hidden_requirements = []
        diagnostics = self.diagnostics(state, viewer)
        if diagnostics.hidden_schemes:
            hidden_requirements.append((
                frozenset(card for card in self.engine.cards if self._is_scheme_card(card)),
                diagnostics.hidden_schemes,
            ))
        if diagnostics.hidden_stratagems:
            hidden_requirements.append((
                frozenset(card for card in self.engine.cards if self._is_stratagem_card(card)),
                diagnostics.hidden_stratagems,
            ))
        # Preserve the simple DeckPrior protocol for third-party priors when no
        # hidden type evidence is present.
        prior = self._prior_for_state(state, opponent)
        sampled_full_deck = (
            prior.sample_deck(required, rng, hidden_requirements=tuple(hidden_requirements))
            if hidden_requirements else prior.sample_deck(required, rng)
        )
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

        hidden_scheme_fronts = [
            front
            for front in Front
            if (
                state.scheme(opponent, front) is not None
                and not state.scheme(opponent, front).revealed
            )
        ]

        for front in hidden_scheme_fronts:
            eligible = [
                index
                for index, card_id in enumerate(unknown_pool)
                if self._is_scheme_card(card_id)
            ]
            if not eligible:
                raise BeliefStateError(
                    "Hidden Veiled Story exists but no Veiled-Story card remains "
                    "under the sampled deck hypothesis"
                )
            index = rng.choice(eligible)
            sampled.schemes[opponent][int(front)].card_id = unknown_pool.pop(index)

        hidden_stratagem = (
            state.stratagem(opponent) is not None
            and not state.stratagem(opponent).revealed
        )
        if hidden_stratagem:
            eligible = [
                index
                for index, card_id in enumerate(unknown_pool)
                if self._is_stratagem_card(card_id)
            ]
            if not eligible:
                raise BeliefStateError(
                    "Hidden Stratagem exists but no Stratagem card remains "
                    "under the sampled deck hypothesis"
                )
            index = rng.choice(eligible)
            sampled.stratagems[opponent].card_id = unknown_pool.pop(index)

        unknown_hand_slots = hand_count - len(known_hand)
        expected = unknown_hand_slots + deck_count
        if len(unknown_pool) != expected:
            raise BeliefStateError(
                "Sampled deck/public-zone accounting mismatch: "
                f"remaining={len(unknown_pool)} expected={expected}"
            )

        rng.shuffle(unknown_pool)
        sampled.players[opponent].hand = (
            list(known_hand) + list(unknown_pool[:unknown_hand_slots])
        )
        rng.shuffle(sampled.players[opponent].hand)
        sampled.players[opponent].deck = list(unknown_pool[unknown_hand_slots:])
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
                total += int(slot.subject is not None)
                total += int(slot.link is not None)
                total += int(slot.name is not None)
        total += sum(scheme is not None for scheme in state.schemes[player])
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
                for card_id in (slot.subject, slot.link, slot.name)
                if card_id is not None
            )

        for front in Front:
            scheme = state.scheme(opponent, front)
            if scheme is not None and scheme.revealed:
                cards.append(scheme.card_id)

        stratagem = state.stratagem(opponent)
        if stratagem is not None and stratagem.revealed:
            cards.append(stratagem.card_id)

        return cards

    def _is_scheme_card(self, card_id: str) -> bool:
        card = self.engine.cards[card_id]
        return card["type"] == "plot" and card.get("veiled", False)

    def _is_stratagem_card(self, card_id: str) -> bool:
        return self.engine.cards[card_id]["type"] == "stratagem"

    @staticmethod
    def _validate_viewer(viewer: int) -> None:
        if viewer not in (0, 1):
            raise ValueError("viewer must be 0 or 1")
