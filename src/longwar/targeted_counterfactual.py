from __future__ import annotations

import itertools
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from .agents.online_mccfr_agent import OnlineMCCFRAgent
from .belief import CardPoolDeckPrior, DeckHypothesis, HypothesisDeckPrior
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
    broad_samples: int
    broad_attempted_samples: int
    broad_censored_pairs: int
    sample_generation: dict[str, Any] | None = None


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
        broad_samples=int(row.get("samples", 0) or 0),
        broad_attempted_samples=int(
            row.get("attempted_samples", row.get("samples", 0)) or 0
        ),
        broad_censored_pairs=int(row.get("censored_pairs", 0) or 0),
        sample_generation=row.get("sample_generation"),
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
        candidates = [
            _candidate_from_row(kind, row)
            for row in rows
            if row.get(_effect_field(kind)) is not None
            and int(row.get("samples", 0) or 0) > 0
        ]
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
    sample_generation: dict[str, Any] | None = None,
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

    generation = sample_generation or broad_report.get("sample_generation")
    if generation is None:
        raise ValueError(
            "Broad report lacks sample-generation metadata; rerun the broad "
            "experiment before targeted validation to preserve exact pairing"
        )
    all_samples = build_samples(
        card_data,
        contexts=broad_contexts,
        games_per_context=broad_games,
        seed=int(generation["seed"]),
        required_cards=generation["required_cards"],
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
) -> float | None:
    if sample.focal_player == 0:
        deck_a, deck_b = focal_deck, list(sample.opponent_deck)
    else:
        deck_a, deck_b = list(sample.opponent_deck), focal_deck

    preview = engine.new_game(
        deck_a,
        deck_b,
        seed=sample.game_seed,
        first_player=0,
        opening_bonus=False,
    )

    # The non-focal player never gets to know which factorial condition is
    # active. Its prior over the focal owner's deck is the same uniform family
    # in every condition. The focal player's opponent prior remains a general
    # legal-card-pool prior rather than the simulator's true deck.
    focal_prior = _family_prior(engine, sample.focal_deck, target_cards)
    generic_prior = CardPoolDeckPrior(engine, deck_size=len(sample.opponent_deck))
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

    mulligan_indices = tuple(
        agent.choose_mulligan(engine, preview.players[player].hand)
        for player, agent in enumerate(agents)
    )
    state = engine.new_game(
        deck_a,
        deck_b,
        seed=sample.game_seed,
        first_player=0,
        mulligan_indices=mulligan_indices,
    )

    action_count = 0
    while state.phase is not Phase.COMPLETE:
        if action_count >= max_actions:
            return None
        actor = state.active_player
        action = agents[actor].choose(engine, state)
        engine.apply(state, action)
        action_count += 1

    if state.winner is None:
        return 0.5
    return 1.0 if state.winner == sample.focal_player else 0.0


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
    effect: EffectEstimate | None,
) -> str:
    if effect is None:
        return "inconclusive"
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


def _run_targeted_candidate(
    target_index: int,
    candidate: TargetCandidate,
    card_data: dict[str, Any],
    broad_report: dict[str, Any],
    contexts: int,
    games_per_context: int,
    online_iterations: int,
    online_depth: int,
    bootstrap_resamples: int,
) -> tuple[int, dict[str, Any], int, int, int, int, int, int]:
    # Only the focal intervention identities belong in this solver. A target
    # adds at most 1/2/3 synthetic identities to the canonical card pool.
    engine = GameEngine(build_experiment_card_data(card_data, candidate.cards))
    samples = _subset_samples(
        card_data,
        broad_report,
        contexts=contexts,
        games_per_context=games_per_context,
        sample_generation=candidate.sample_generation,
    )
    conditions = _powerset(candidate.cards)
    outcomes: dict[frozenset[str], list[float | None]] = {
        condition: [] for condition in conditions
    }
    total_matches = 0
    censored_matches = 0
    for sample in samples:
        for condition in conditions:
            focal_deck = replace_cards(sample.focal_deck, condition)
            outcome = _play_online_outcome(
                engine,
                sample,
                focal_deck,
                target_cards=candidate.cards,
                online_iterations=online_iterations,
                online_depth=online_depth,
            )
            outcomes[condition].append(outcome)
            total_matches += 1
            if outcome is None:
                censored_matches += 1

    draw_matches = sum(
        value == 0.5
        for condition_outcomes in outcomes.values()
        for value in condition_outcomes
        if value is not None
    )
    decisive_matches = sum(
        value in (0.0, 1.0)
        for condition_outcomes in outcomes.values()
        for value in condition_outcomes
        if value is not None
    )

    complete_indices = [
        index
        for index in range(len(samples))
        if all(outcomes[condition][index] is not None for condition in conditions)
    ]
    filtered: dict[frozenset[str], list[float]] = {
        condition: [
            float(outcomes[condition][index])
            for index in complete_indices
            if outcomes[condition][index] is not None
        ]
        for condition in conditions
    }
    pair_censored = len(samples) - len(complete_indices)
    values = (
        _contrast(candidate.kind, filtered, candidate.cards)
        if complete_indices
        else []
    )
    effect = (
        estimate(
            values,
            seed=int(broad_report["seed"]) + 70_000 + target_index,
            bootstrap_resamples=bootstrap_resamples,
            contrast_bound=float(2 ** (len(candidate.cards) - 1)),
        )
        if values
        else None
    )
    severity = (
        _severity(effect)
        if effect is not None
        else {
            "level": "unobserved",
            "direction": "unresolved",
            "confidence_excludes_zero": False,
        }
    )
    result = {
        "kind": candidate.kind,
        "cards": list(candidate.cards),
        "title": candidate.title,
        "sample_generation": (
            candidate.sample_generation or broad_report.get("sample_generation")
        ),
        "broad": {
            "effect": candidate.broad_effect,
            "ci95": list(candidate.broad_ci95),
            "level": candidate.broad_level,
            "confidence_excludes_zero": candidate.broad_excludes_zero,
            "policy": broad_report.get("policy"),
            "samples": candidate.broad_samples,
            "attempted_samples": candidate.broad_attempted_samples,
            "censored_pairs": candidate.broad_censored_pairs,
        },
        "online": {
            "effect": effect.mean if effect is not None else None,
            "ci95": list(effect.ci95) if effect is not None else [None, None],
            "ci_method": effect.ci_method if effect is not None else None,
            "standard_error": effect.standard_error if effect is not None else None,
            "samples": effect.samples if effect is not None else 0,
            "attempted_samples": len(samples),
            "censored_pairs": pair_censored,
            "paired_censor_rate": (
                pair_censored / len(samples) if samples else 0.0
            ),
            **severity,
        },
        "confirmation": _confirmation(candidate, effect),
        "direction_agreement": (
            effect is not None
            and _sign(candidate.broad_effect) != 0
            and _sign(candidate.broad_effect) == _sign(effect.mean)
        ),
        "factorial_conditions": len(conditions),
    }
    return (
        target_index,
        result,
        total_matches,
        censored_matches,
        draw_matches,
        decisive_matches,
        len(complete_indices),
        pair_censored,
    )


def run_targeted_online_validation(
    card_data: dict[str, Any],
    broad_report: dict[str, Any],
    *,
    contexts: int,
    games_per_context: int,
    online_iterations: int,
    online_depth: int,
    max_cards: int = 8,
    max_pairs: int = 0,
    max_triples: int = 0,
    minimum_abs_effect: float = 0.05,
    bootstrap_resamples: int = 1000,
    force_top: bool = False,
    jobs: int = 1,
    progress_callback: Callable[[int, int, dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Re-test suspicious broad A/B signals with online MCCFR.

    The exact broad deck contexts, seats, seeds and intervention definitions
    are reused. A targeted paired sample is resolved only when every condition
    required for that contrast finishes before the action horizon. Completed
    draws remain valid 0.5 outcomes.
    """
    if bootstrap_resamples <= 0:
        raise ValueError("bootstrap_resamples must be positive")
    if contexts <= 0 or games_per_context <= 0:
        raise ValueError("contexts and games_per_context must be positive")
    if contexts > int(broad_report["contexts"]) or games_per_context > int(
        broad_report["games_per_context"]
    ):
        raise ValueError(
            "Targeted validation must use a subset of the broad experiment"
        )
    selected = select_targets(
        broad_report,
        max_cards=max_cards,
        max_pairs=max_pairs,
        max_triples=max_triples,
        minimum_abs_effect=minimum_abs_effect,
        force_top=force_top,
    )
    if jobs <= 0:
        raise ValueError("jobs must be positive")

    results: list[dict[str, Any]] = []
    total_matches = 0
    censored_matches = 0
    draw_matches = 0
    decisive_matches = 0
    resolved_paired_samples = 0
    censored_paired_samples = 0

    completed_rows: list[
        tuple[int, dict[str, Any], int, int, int, int, int, int]
    ] = []
    worker_count = min(jobs, len(selected)) if selected else 0
    if worker_count <= 1:
        for target_index, candidate in enumerate(selected):
            row = _run_targeted_candidate(
                target_index,
                candidate,
                card_data,
                broad_report,
                contexts,
                games_per_context,
                online_iterations,
                online_depth,
                bootstrap_resamples,
            )
            completed_rows.append(row)
            if progress_callback is not None:
                progress_callback(target_index + 1, len(selected), row[1])
    else:
        completed = 0
        with ProcessPoolExecutor(max_workers=worker_count) as pool:
            futures = [
                pool.submit(
                    _run_targeted_candidate,
                    target_index,
                    candidate,
                    card_data,
                    broad_report,
                    contexts,
                    games_per_context,
                    online_iterations,
                    online_depth,
                    bootstrap_resamples,
                )
                for target_index, candidate in enumerate(selected)
            ]
            for future in as_completed(futures):
                row = future.result()
                completed_rows.append(row)
                completed += 1
                if progress_callback is not None:
                    progress_callback(completed, len(selected), row[1])

    completed_rows.sort(key=lambda row: row[0])
    for (
        _target_index,
        result,
        row_total_matches,
        row_censored_matches,
        row_draw_matches,
        row_decisive_matches,
        row_resolved_pairs,
        row_censored_pairs,
    ) in completed_rows:
        results.append(result)
        total_matches += row_total_matches
        censored_matches += row_censored_matches
        draw_matches += row_draw_matches
        decisive_matches += row_decisive_matches
        resolved_paired_samples += row_resolved_pairs
        censored_paired_samples += row_censored_pairs

    by_kind = {
        kind: [row for row in results if row["kind"] == kind]
        for kind in ("card", "pair", "triple")
    }
    attempted_pairs = resolved_paired_samples + censored_paired_samples

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
        "samples": contexts * games_per_context,
        "bootstrap_resamples": bootstrap_resamples,
        "online_iterations": online_iterations,
        "online_depth": online_depth,
        "total_matches": total_matches,
        "resolved_matches": total_matches - censored_matches,
        "draw_matches": draw_matches,
        "decisive_matches": decisive_matches,
        "censored_matches": censored_matches,
        "match_censor_rate": (
            censored_matches / total_matches if total_matches else 0.0
        ),
        "resolved_paired_samples": resolved_paired_samples,
        "censored_paired_samples": censored_paired_samples,
        "pair_censor_rate": (
            censored_paired_samples / attempted_pairs
            if attempted_pairs else 0.0
        ),
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
            "censoring": (
                "A targeted paired contrast is estimated only when every "
                "required intervention condition finishes before the action "
                "horizon. Censored conditions remain reported explicitly."
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
                "zero in the opposite direction. Intervals are unadjusted for target "
                "selection and multiple comparisons; reused contexts are not an "
                "independent replication."
            ),
        },
    }

