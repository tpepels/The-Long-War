from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Any, Iterable

from .agents.online_mccfr_agent import OnlineMCCFRAgent
from .belief import CardPoolDeckPrior, DeckHypothesis, HypothesisDeckPrior
from .cards import card_index
from .counterfactual import (
    EffectEstimate,
    ExperimentSample,
    _severity,
    build_experiment_card_data,
    build_samples,
    estimate,
    pair_contrast,
    replace_cards,
    triple_contrast,
)
from .game.engine import GameEngine
from .game.model import Phase


LEVEL_SCORE = {
    "dark_green": 0,
    "green": 1,
    "yellow": 2,
    "orange": 3,
    "red": 4,
}


@dataclass(frozen=True)
class TargetCandidate:
    kind: str
    cards: tuple[str, ...]
    title: str
    broad_effect: float
    broad_ci95: tuple[float, float]
    broad_level: str
    broad_excludes_zero: bool


def _effect_field(kind: str) -> str:
    return "delta_win_probability" if kind == "card" else "interaction_delta"


def _candidate_from_row(kind: str, row: dict[str, Any]) -> TargetCandidate:
    cards = (
        (str(row["id"]),)
        if kind == "card"
        else tuple(str(card_id) for card_id in row["cards"])
    )
    effect = float(row[_effect_field(kind)])
    ci = row.get("ci95") or [effect, effect]
    return TargetCandidate(
        kind=kind,
        cards=cards,
        title=str(row["title"]),
        broad_effect=effect,
        broad_ci95=(float(ci[0]), float(ci[1])),
        broad_level=str(row.get("level", "green")),
        broad_excludes_zero=bool(row.get("confidence_excludes_zero", False)),
    )


def _priority(candidate: TargetCandidate) -> tuple[int, int, float, str]:
    return (
        1 if candidate.broad_excludes_zero else 0,
        LEVEL_SCORE.get(candidate.broad_level, 1),
        abs(candidate.broad_effect),
        candidate.title,
    )


def _suspicious(candidate: TargetCandidate, minimum_abs_effect: float) -> bool:
    return (
        candidate.broad_excludes_zero
        or LEVEL_SCORE.get(candidate.broad_level, 1) >= LEVEL_SCORE["yellow"]
        or abs(candidate.broad_effect) >= minimum_abs_effect
    )


def select_targets(
    broad_report: dict[str, Any],
    *,
    max_cards: int = 2,
    max_pairs: int = 2,
    max_triples: int = 2,
    minimum_abs_effect: float = 0.05,
    force_top: bool = False,
) -> list[TargetCandidate]:
    specs = (
        ("card", broad_report.get("cards", []), max_cards),
        ("pair", broad_report.get("pairs", []), max_pairs),
        ("triple", broad_report.get("triples", []), max_triples),
    )

    selected: list[TargetCandidate] = []
    for kind, rows, maximum in specs:
        if maximum <= 0:
            continue
        candidates = [_candidate_from_row(kind, row) for row in rows]
        suspicious = [
            candidate
            for candidate in candidates
            if _suspicious(candidate, minimum_abs_effect)
        ]
        pool = suspicious
        if not pool and force_top and candidates:
            pool = candidates[:1]
        pool.sort(key=_priority, reverse=True)
        selected.extend(pool[:maximum])

    return selected


def _powerset(cards: tuple[str, ...]) -> list[frozenset[str]]:
    result: list[frozenset[str]] = []
    for size in range(len(cards) + 1):
        for subset in itertools.combinations(cards, size):
            result.append(frozenset(subset))
    return result


def _subset_samples(
    card_data: dict[str, Any],
    broad_report: dict[str, Any],
    *,
    contexts: int,
    games_per_context: int,
) -> list[ExperimentSample]:
    broad_contexts = int(broad_report["contexts"])
    broad_games = int(broad_report["games_per_context"])
    if contexts <= 0 or games_per_context <= 0:
        raise ValueError("contexts and games_per_context must be positive")
    if contexts > broad_contexts or games_per_context > broad_games:
        raise ValueError(
            "Targeted validation must use a subset of the broad experiment's "
            "contexts/games so the deck contexts remain directly comparable"
        )

    all_samples = build_samples(
        card_data,
        contexts=broad_contexts,
        games_per_context=broad_games,
        seed=int(broad_report["seed"]),
    )
    return [
        sample
        for sample in all_samples
        if sample.context_id < contexts
        and (sample.sample_id % broad_games) < games_per_context
    ]


def _family_prior(
    engine: GameEngine,
    base_deck: Iterable[str],
    cards: tuple[str, ...],
) -> HypothesisDeckPrior:
    hypotheses: list[DeckHypothesis] = []
    seen: set[tuple[str, ...]] = set()
    for index, condition in enumerate(_powerset(cards)):
        deck = tuple(replace_cards(base_deck, condition))
        signature = tuple(sorted(deck))
        if signature in seen:
            continue
        seen.add(signature)
        hypotheses.append(
            DeckHypothesis(
                cards=deck,
                weight=1.0,
                label=f"factorial-{index}",
            )
        )
    return HypothesisDeckPrior(engine, hypotheses)


def _play_online_outcome(
    engine: GameEngine,
    sample: ExperimentSample,
    focal_deck: list[str],
    *,
    target_cards: tuple[str, ...],
    online_iterations: int,
    online_depth: int,
    max_actions: int = 500,
) -> int:
    if sample.focal_player == 0:
        deck_a, deck_b = focal_deck, list(sample.opponent_deck)
    else:
        deck_a, deck_b = list(sample.opponent_deck), focal_deck

    state = engine.new_game(
        deck_a,
        deck_b,
        seed=sample.game_seed,
        first_player=0,
    )

    # The non-focal player never gets to know which factorial condition is
    # active. Its prior over the focal owner's deck is the same uniform family
    # in every condition. The focal player's opponent prior remains a general
    # legal-card-pool prior rather than the simulator's true deck.
    focal_prior = _family_prior(engine, sample.focal_deck, target_cards)
    generic_prior = CardPoolDeckPrior(engine)
    priors = (
        (focal_prior, generic_prior)
        if sample.focal_player == 0
        else (generic_prior, focal_prior)
    )

    agents = [
        OnlineMCCFRAgent(
            engine,
            sample.game_seed * 10_000 + 1,
            priors=priors,
            iterations=online_iterations,
            max_depth=online_depth,
            deterministic=True,
        ),
        OnlineMCCFRAgent(
            engine,
            sample.game_seed * 10_000 + 2,
            priors=priors,
            iterations=online_iterations,
            max_depth=online_depth,
            deterministic=True,
        ),
    ]

    action_count = 0
    while state.phase is not Phase.COMPLETE:
        if action_count >= max_actions:
            raise RuntimeError(
                f"Targeted sample {sample.sample_id} exceeded {max_actions} actions"
            )
        actor = state.active_player
        action = agents[actor].choose(engine, state)
        engine.apply(state, action)
        action_count += 1

    if state.winner is None:
        raise RuntimeError("Completed targeted game has no winner")
    return int(state.winner == sample.focal_player)


def _contrast(
    kind: str,
    conditions: dict[frozenset[str], list[int]],
    cards: tuple[str, ...],
) -> list[float]:
    empty = conditions[frozenset()]
    if kind == "card":
        replaced = conditions[frozenset(cards)]
        return [
            base - control
            for base, control in zip(empty, replaced)
        ]

    if kind == "pair":
        a, b = cards
        return [
            pair_contrast(v0, va, vb, vab)
            for v0, va, vb, vab in zip(
                empty,
                conditions[frozenset([a])],
                conditions[frozenset([b])],
                conditions[frozenset([a, b])],
            )
        ]

    if kind == "triple":
        a, b, c = cards
        return [
            triple_contrast(v0, va, vb, vc, vab, vac, vbc, vabc)
            for v0, va, vb, vc, vab, vac, vbc, vabc in zip(
                empty,
                conditions[frozenset([a])],
                conditions[frozenset([b])],
                conditions[frozenset([c])],
                conditions[frozenset([a, b])],
                conditions[frozenset([a, c])],
                conditions[frozenset([b, c])],
                conditions[frozenset([a, b, c])],
            )
        ]

    raise ValueError(f"Unknown target kind: {kind}")


def _sign(value: float, epsilon: float = 1e-12) -> int:
    if value > epsilon:
        return 1
    if value < -epsilon:
        return -1
    return 0


def _confirmation(
    candidate: TargetCandidate,
    effect: EffectEstimate,
) -> str:
    low, high = effect.ci95
    online_excludes = low > 0 or high < 0
    broad_sign = _sign(candidate.broad_effect)
    online_sign = _sign(effect.mean)

    if online_excludes and broad_sign != 0 and online_sign == broad_sign:
        return "confirmed"
    if online_excludes and broad_sign != 0 and online_sign == -broad_sign:
        return "reversed"
    if broad_sign != 0 and online_sign == broad_sign:
        return "direction_agrees"
    return "inconclusive"


def run_targeted_online_validation(
    card_data: dict[str, Any],
    broad_report: dict[str, Any],
    *,
    contexts: int,
    games_per_context: int,
    online_iterations: int,
    online_depth: int,
    max_cards: int = 2,
    max_pairs: int = 2,
    max_triples: int = 2,
    minimum_abs_effect: float = 0.05,
    bootstrap_resamples: int = 1000,
    force_top: bool = False,
) -> dict[str, Any]:
    canonical = card_index(card_data)
    selected = select_targets(
        broad_report,
        max_cards=max_cards,
        max_pairs=max_pairs,
        max_triples=max_triples,
        minimum_abs_effect=minimum_abs_effect,
        force_top=force_top,
    )
    samples = _subset_samples(
        card_data,
        broad_report,
        contexts=contexts,
        games_per_context=games_per_context,
    )
    engine = GameEngine(build_experiment_card_data(card_data))

    results: list[dict[str, Any]] = []
    total_matches = 0

    for target_index, candidate in enumerate(selected):
        conditions = _powerset(candidate.cards)
        outcomes: dict[frozenset[str], list[int]] = {
            condition: [] for condition in conditions
        }

        for sample in samples:
            for condition in conditions:
                focal_deck = replace_cards(sample.focal_deck, condition)
                outcomes[condition].append(
                    _play_online_outcome(
                        engine,
                        sample,
                        focal_deck,
                        target_cards=candidate.cards,
                        online_iterations=online_iterations,
                        online_depth=online_depth,
                    )
                )
                total_matches += 1

        values = _contrast(candidate.kind, outcomes, candidate.cards)
        effect = estimate(
            values,
            seed=int(broad_report["seed"]) + 70_000 + target_index,
            bootstrap_resamples=bootstrap_resamples,
        )
        severity = _severity(effect)
        results.append({
            "kind": candidate.kind,
            "cards": list(candidate.cards),
            "title": candidate.title,
            "broad": {
                "effect": candidate.broad_effect,
                "ci95": list(candidate.broad_ci95),
                "level": candidate.broad_level,
                "confidence_excludes_zero": candidate.broad_excludes_zero,
                "policy": broad_report.get("policy"),
                "samples": broad_report.get("samples"),
            },
            "online": {
                "effect": effect.mean,
                "ci95": list(effect.ci95),
                "standard_error": effect.standard_error,
                "samples": effect.samples,
                **severity,
            },
            "confirmation": _confirmation(candidate, effect),
            "direction_agreement": (
                _sign(candidate.broad_effect) != 0
                and _sign(candidate.broad_effect) == _sign(effect.mean)
            ),
            "factorial_conditions": len(conditions),
        })

    by_kind = {
        kind: [row for row in results if row["kind"] == kind]
        for kind in ("card", "pair", "triple")
    }

    return {
        "schema_version": 1,
        "method": "targeted_paired_online_mccfr_factorial_validation",
        "source_broad_method": broad_report.get("method"),
        "source_broad_policy": broad_report.get("policy"),
        "source_seed": broad_report.get("seed"),
        "selection": {
            "minimum_abs_effect": minimum_abs_effect,
            "max_cards": max_cards,
            "max_pairs": max_pairs,
            "max_triples": max_triples,
            "force_top": force_top,
            "targets_selected": len(selected),
        },
        "contexts": contexts,
        "games_per_context": games_per_context,
        "samples": len(samples),
        "online_iterations": online_iterations,
        "online_depth": online_depth,
        "total_matches": total_matches,
        "targets": results,
        "cards": by_kind["card"],
        "pairs": by_kind["pair"],
        "triples": by_kind["triple"],
        "methodology": {
            "selection": (
                "Targets are nominated by broad heuristic causal magnitude, "
                "severity, and whether the paired interval excludes zero."
            ),
            "pairing": (
                "Uses a subset of the exact broad experiment deck contexts, "
                "game seeds, focal seats, and intervention definitions."
            ),
            "epistemic_fairness": (
                "The opponent receives the same uniform hypothesis prior over "
                "all factorial focal-deck variants in every intervention condition; "
                "it is never told which condition is active."
            ),
            "other_deck_prior": (
                "The focal player's belief over the opponent deck uses the general "
                "legal card-pool prior, not simulator truth."
            ),
            "interpretation": (
                "Confirmed means the online-MCCFR interval excludes zero in the same "
                "direction as the broad heuristic signal. Reversed means it excludes "
                "zero in the opposite direction."
            ),
        },
    }
