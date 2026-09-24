from __future__ import annotations

import copy
import itertools
import math
import random
from dataclasses import dataclass
from statistics import mean, stdev
from typing import Any, Iterable

from .cards import card_index, validate_card_data
from .game.engine import GameEngine
from .game.model import Phase
from .simulate import make_agent
from .rules import GameRules


BASELINE_PREFIX = "__cf_baseline__"


@dataclass(frozen=True)
class ExperimentSample:
    sample_id: int
    context_id: int
    focal_player: int
    game_seed: int
    focal_deck: tuple[str, ...]
    opponent_deck: tuple[str, ...]


@dataclass(frozen=True)
class EffectEstimate:
    mean: float
    ci95: tuple[float, float]
    standard_error: float | None
    samples: int
    ci_method: str = "paired_percentile_bootstrap"


def baseline_id(card_id: str) -> str:
    return f"{BASELINE_PREFIX}{card_id}"


def baseline_card(card: dict[str, Any]) -> dict[str, Any]:
    card_type = card["type"]
    result: dict[str, Any] = {
        "id": baseline_id(card["id"]),
        "title": f"Counterfactual baseline — {card['title']}",
        "type": card_type,
        "unique": bool(card["unique"]),
        "classes": list(card.get("classes", ["experimental"])),
        "text": "Experimental matched baseline.",
        "rules": {},
        "rule_blocks": [],
        "balance": {},
        "experimental": True,
        "baseline_for": card["id"],
    }
    if "command_cost" in card:
        result["command_cost"] = card["command_cost"]

    if card_type == "subject":
        result["role"] = card["role"]
        result["hero"] = bool(card.get("hero", False))
        result["strength"] = 6 if result["hero"] else 4
    elif card_type == "link":
        result["text"] = (
            "Experimental matched baseline. Its **Subject** gets +1 **Strength**. "
            "While this **Bond** has a **Name**, its **Subject** gets +2 additional **Strength**."
        )
        result["rules"] = {
            "strength_bonus": 1,
            "named_strength_bonus": 2,
        }
        result["balance"] = {
            "strength_bonus": 1,
            "named_strength_bonus": 2,
        }
    elif card_type == "name":
        result["strength"] = 2
    elif card_type == "plot":
        result["story_form"] = card["story_form"]
        result["veiled"] = bool(card.get("veiled", False))
        if result["veiled"]:
            # Preserve the face-down Story commitment/bluff structure while
            # removing the specific trigger/effect.
            result["text"] = (
                "*Veiled.* Experimental matched baseline. While this is face-down, "
                "you have +1 **Strength** in this **Front**. It has no trigger."
            )
            result["rules"] = {
                "scheme": {
                    "trigger": "never",
                    "effect": "none",
                    "face_down_front_bonus": 1,
                }
            }
        else:
            # A no-op Story preserves the card/turn cost and universal
            # playability while removing the card-specific effect.
            result["rules"] = {}
    elif card_type == "stratagem":
        # Preserve the paid public one-per-Battle slot while removing all
        # card-specific payoff.
        result["text"] = (
            "Experimental matched baseline. Play this face-up in your "
            "**Stratagem** area. It has no continuing effect."
        )
        result["rules"] = {
            "stratagem": {
                "trigger": {"event": "played", "actor": "controller"},
                "continuous": {},
            }
        }
    else:
        raise ValueError(f"Unsupported card type: {card_type}")

    return result


def build_experiment_card_data(card_data: dict[str, Any]) -> dict[str, Any]:
    data = copy.deepcopy(card_data)
    original_cards = list(data["cards"])
    data["cards"].extend(baseline_card(card) for card in original_cards)
    validate_card_data(data)
    return data


def replace_cards(
    deck: Iterable[str],
    replacements: Iterable[str],
) -> list[str]:
    result = list(deck)
    for card_id in sorted(set(replacements)):
        try:
            index = result.index(card_id)
        except ValueError as exc:
            raise ValueError(f"Deck does not contain card required for replacement: {card_id}") from exc
        result[index] = baseline_id(card_id)
    return result


def generate_context_decks(
    card_data: dict[str, Any],
    *,
    count: int,
    seed: int,
    required_cards: Iterable[str] = (),
) -> list[list[str]]:
    """Generate legal canonical-size contexts for an expandable card pool.

    ``required_cards`` are included in every generated deck. Without required
    cards, the generator rotates coverage so the union of contexts reaches the
    whole canonical pool. A deck always contains exactly one Hero.
    """
    if count <= 0:
        raise ValueError("count must be positive")

    cards = card_data["cards"]
    meta = card_index(card_data)
    all_ids = [card["id"] for card in cards]
    required = sorted(set(required_cards))
    unknown = [card_id for card_id in required if card_id not in meta]
    if unknown:
        raise ValueError(f"Unknown required cards: {unknown}")
    deck_size = GameRules.standard().deck_size
    if len(required) > deck_size:
        raise ValueError(
            f"At most {deck_size} distinct cards can be required in a deck context"
        )

    heroes = [card["id"] for card in cards if card.get("hero", False)]
    required_heroes = [card_id for card_id in required if meta[card_id].get("hero", False)]
    if len(required_heroes) > 1:
        raise ValueError(
            "A legal context cannot require more than one Hero; "
            "evaluate alternative Heroes in separate counterfactual runs"
        )
    if not heroes:
        raise ValueError("Card pool must contain at least one Hero")

    rng = random.Random(seed)
    uncovered = set(all_ids) - set(required)
    contexts: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()

    for context_index in range(count):
        chosen_hero = (
            required_heroes[0]
            if required_heroes
            else heroes[context_index % len(heroes)]
        )
        deck = list(required)
        if chosen_hero not in deck:
            deck.append(chosen_hero)

        eligible_unique = [
            card_id
            for card_id in all_ids
            if card_id not in deck
            and (not meta[card_id].get("hero", False) or card_id == chosen_hero)
        ]
        coverage = [card_id for card_id in eligible_unique if card_id in uncovered]
        rng.shuffle(coverage)
        remainder = [card_id for card_id in eligible_unique if card_id not in uncovered]
        rng.shuffle(remainder)
        for card_id in coverage + remainder:
            if len(deck) >= deck_size:
                break
            deck.append(card_id)

        if len(deck) < deck_size:
            duplicate_candidates = [
                card["id"]
                for card in cards
                if not card["unique"]
                and not card.get("hero", False)
                and deck.count(card["id"]) < 2
            ]
            rng.shuffle(duplicate_candidates)
            for card_id in duplicate_candidates:
                if len(deck) >= deck_size:
                    break
                deck.append(card_id)

        if len(deck) != deck_size:
            raise ValueError(
                f"Card pool cannot generate a legal {deck_size}-card context from "
                f"the requested cards (built {len(deck)})"
            )

        signature = tuple(sorted(deck))
        if signature in seen:
            alternatives = [card_id for card_id in eligible_unique if card_id not in deck]
            if alternatives:
                replaced = next(
                    (
                        index
                        for index in range(len(deck) - 1, -1, -1)
                        if deck[index] not in required
                        and deck[index] != chosen_hero
                    ),
                    None,
                )
                if replaced is not None:
                    deck[replaced] = rng.choice(alternatives)
                    signature = tuple(sorted(deck))

        seen.add(signature)
        uncovered.difference_update(deck)
        contexts.append(deck)

    return contexts


def build_samples(
    card_data: dict[str, Any],
    *,
    contexts: int,
    games_per_context: int,
    seed: int,
    required_cards: Iterable[str] = (),
) -> list[ExperimentSample]:
    if games_per_context <= 0:
        raise ValueError("games_per_context must be positive")

    focal_contexts = generate_context_decks(
        card_data,
        count=contexts,
        seed=seed,
        required_cards=required_cards,
    )
    opponent_contexts = generate_context_decks(
        card_data,
        count=contexts,
        seed=seed + 7919,
    )

    samples: list[ExperimentSample] = []
    sample_id = 0
    for context_id in range(contexts):
        for local_game in range(games_per_context):
            samples.append(
                ExperimentSample(
                    sample_id=sample_id,
                    context_id=context_id,
                    focal_player=sample_id % 2,
                    game_seed=seed + 100_003 + sample_id * 97,
                    focal_deck=tuple(focal_contexts[context_id]),
                    opponent_deck=tuple(
                        opponent_contexts[(context_id + local_game) % contexts]
                    ),
                )
            )
            sample_id += 1
    return samples


def _play_focal_outcome(
    engine: GameEngine,
    sample: ExperimentSample,
    focal_deck: list[str],
    *,
    agent_name: str,
    max_actions: int = 500,
) -> int:
    if agent_name not in {"heuristic", "random"}:
        raise ValueError(
            "Counterfactual experiments currently support heuristic or random "
            "policies; use heuristic for balance estimates."
        )

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
    agents = [
        make_agent(
            agent_name,
            engine,
            sample.game_seed * 10_000 + 1,
        ),
        make_agent(
            agent_name,
            engine,
            sample.game_seed * 10_000 + 2,
        ),
    ]
    mulligan_indices = tuple(
        agent.choose_mulligan(engine, preview.players[player].hand)
        if hasattr(agent, "choose_mulligan")
        else ()
        for player, agent in enumerate(agents)
    )
    state = engine.new_game(
        deck_a,
        deck_b,
        seed=sample.game_seed,
        first_player=0,
        mulligan_indices=mulligan_indices,
    )

    actions = 0
    while state.phase is not Phase.COMPLETE:
        if actions >= max_actions:
            raise RuntimeError(
                f"Counterfactual sample {sample.sample_id} exceeded {max_actions} actions"
            )
        actor = state.active_player
        action = agents[actor].choose(engine, state)
        engine.apply(state, action)
        actions += 1

    if state.winner is None:
        raise RuntimeError("Completed counterfactual game has no winner")
    return int(state.winner == sample.focal_player)


def _bootstrap_ci(
    values: list[float],
    *,
    seed: int,
    resamples: int = 2000,
) -> tuple[float, float]:
    if not values:
        raise ValueError("Cannot estimate an empty sample")
    if resamples <= 0:
        raise ValueError("bootstrap_resamples must be positive")

    rng = random.Random(seed)
    n = len(values)
    means = []
    for _ in range(resamples):
        means.append(
            sum(values[rng.randrange(n)] for _ in range(n)) / n
        )
    means.sort()
    low_index = max(0, math.floor(0.025 * (resamples - 1)))
    high_index = min(resamples - 1, math.ceil(0.975 * (resamples - 1)))
    return (means[low_index], means[high_index])


def estimate(
    values: list[float],
    *,
    seed: int,
    bootstrap_resamples: int = 2000,
    contrast_bound: float = 1.0,
) -> EffectEstimate:
    if not values:
        raise ValueError("Cannot estimate an empty sample")
    if bootstrap_resamples <= 0:
        raise ValueError("bootstrap_resamples must be positive")
    if not math.isfinite(contrast_bound) or contrast_bound <= 0:
        raise ValueError("contrast_bound must be finite and positive")
    if any(not math.isfinite(value) or abs(value) > contrast_bound for value in values):
        raise ValueError("Contrasts must be finite and within contrast_bound")
    avg = mean(values)
    se = stdev(values) / math.sqrt(len(values)) if len(values) > 1 else None
    # Resampling an observed constant only reproduces that constant. A
    # zero-width interval would falsely imply certainty, even for one game.
    # Factorial Bernoulli contrasts are bounded, so a Hoeffding interval
    # remains informative about the uncertainty without inventing variation.
    if len(set(values)) == 1:
        radius = contrast_bound * math.sqrt(2 * math.log(40) / len(values))
        ci = (max(-contrast_bound, avg - radius), min(contrast_bound, avg + radius))
        ci_method = "bounded_hoeffding_degenerate_sample"
    else:
        ci = _bootstrap_ci(values, seed=seed, resamples=bootstrap_resamples)
        ci_method = "paired_percentile_bootstrap"
    return EffectEstimate(
        mean=avg,
        ci95=ci,
        standard_error=se,
        samples=len(values),
        ci_method=ci_method,
    )


def pair_contrast(
    base: float,
    replace_a: float,
    replace_b: float,
    replace_ab: float,
) -> float:
    return base - replace_a - replace_b + replace_ab


def triple_contrast(
    base: float,
    replace_a: float,
    replace_b: float,
    replace_c: float,
    replace_ab: float,
    replace_ac: float,
    replace_bc: float,
    replace_abc: float,
) -> float:
    return (
        base
        - replace_a
        - replace_b
        - replace_c
        + replace_ab
        + replace_ac
        + replace_bc
        - replace_abc
    )


def _severity(estimate_value: EffectEstimate) -> dict[str, Any]:
    low, high = estimate_value.ci95
    excludes_zero = low > 0 or high < 0
    magnitude = abs(estimate_value.mean)

    if excludes_zero and magnitude >= 0.08:
        level = "red"
    elif excludes_zero and magnitude >= 0.04:
        level = "orange"
    elif excludes_zero or magnitude >= 0.05:
        level = "yellow"
    elif estimate_value.samples >= 24 and (high - low) <= 0.15:
        level = "dark_green"
    else:
        level = "green"

    if estimate_value.mean > 0:
        direction = "stronger_than_baseline"
    elif estimate_value.mean < 0:
        direction = "weaker_than_baseline"
    else:
        direction = "neutral"

    return {
        "level": level,
        "direction": direction,
        "confidence_excludes_zero": excludes_zero,
    }


def run_counterfactual_card_sweep(
    card_data: dict[str, Any],
    *,
    contexts: int,
    games_per_context: int,
    seed: int,
    agent_name: str = "heuristic",
    bootstrap_resamples: int = 2000,
    card_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Evaluate card main effects across a pool larger than one legal deck.

    Each card is evaluated in its own legal paired contexts. This preserves
    the causal replacement interpretation without pretending 48 titles can
    coexist in a 30-card deck. Pair/triple interactions require an explicit
    compatible subset and remain the responsibility of the grouped runner.
    """
    canonical = card_index(card_data)
    selected = (
        list(dict.fromkeys(card_ids))
        if card_ids is not None
        else [card["id"] for card in card_data["cards"]]
    )
    unknown = [card_id for card_id in selected if card_id not in canonical]
    if unknown:
        raise ValueError(f"Unknown selected cards: {unknown}")
    if not selected:
        raise ValueError("At least one selected card is required")

    rows: list[dict[str, Any]] = []
    total_matches = 0
    reports: list[dict[str, Any]] = []
    for index, card_id in enumerate(selected):
        report = run_counterfactual_experiment(
            card_data,
            contexts=contexts,
            games_per_context=games_per_context,
            seed=seed + index * 104729,
            agent_name=agent_name,
            include_pairs=False,
            include_legend_triples=False,
            bootstrap_resamples=bootstrap_resamples,
            card_ids=[card_id],
        )
        reports.append(report)
        rows.extend({**row, "sample_generation": report["sample_generation"]} for row in report["cards"])
        total_matches += int(report["total_matches"])

    rows.sort(
        key=lambda row: (
            -abs(row["delta_win_probability"]),
            row["title"],
        )
    )
    first = reports[0] if reports else None
    return {
        "schema_version": 1,
        "method": "paired_common_random_numbers_per_card_context_sweep",
        "policy": agent_name,
        "seed": seed,
        "contexts": contexts,
        "games_per_context": games_per_context,
        "bootstrap_resamples": bootstrap_resamples,
        "samples": contexts * games_per_context,
        "samples_per_card": contexts * games_per_context,
        "conditions_evaluated_per_sample": 2,
        "total_matches": total_matches,
        "baseline_definition": first["baseline_definition"] if first else {},
        "pairing": first["pairing"] if first else {},
        "cards": rows,
        "pairs": [],
        "triples": [],
        "methodology": {
            "card_effect": (
                "base outcome - same legal deck context with the focal card "
                "replaced by its matched baseline"
            ),
            "pair_interaction": (
                "Not evaluated in full-pool sweep; select a compatible card "
                "subset to evaluate interactions."
            ),
            "triple_interaction": (
                "Not evaluated in full-pool sweep; select a compatible card "
                "subset to evaluate interactions."
            ),
            "ci95": "paired percentile bootstrap over per-card matched samples; bounded Hoeffding interval when observed contrasts are constant",
            "interpretation": (
                "Each card is tested in legal contexts containing that card. "
                "Effects are policy- and context-distribution-specific, not "
                "universal equilibrium values."
            ),
        },
    }


def run_counterfactual_experiment(
    card_data: dict[str, Any],
    *,
    contexts: int,
    games_per_context: int,
    seed: int,
    agent_name: str = "heuristic",
    include_pairs: bool = True,
    include_legend_triples: bool = True,
    bootstrap_resamples: int = 2000,
    card_ids: list[str] | None = None,
) -> dict[str, Any]:
    canonical_cards = card_index(card_data)
    selected_cards = (
        list(dict.fromkeys(card_ids))
        if card_ids is not None
        else [card["id"] for card in card_data["cards"]]
    )
    unknown = [card_id for card_id in selected_cards if card_id not in canonical_cards]
    if unknown:
        raise ValueError(f"Unknown selected cards: {unknown}")
    if not selected_cards:
        raise ValueError("At least one selected card is required")
    if bootstrap_resamples <= 0:
        raise ValueError("bootstrap_resamples must be positive")

    experiment_data = build_experiment_card_data(card_data)
    engine = GameEngine(experiment_data)
    selected_heroes = [
        card_id
        for card_id in selected_cards
        if canonical_cards[card_id].get("hero", False)
    ]
    if len(selected_cards) > 30 or len(selected_heroes) > 1:
        raise ValueError(
            "A single paired counterfactual run requires at most 30 selected "
            "cards and at most one Hero. Split a larger pool into candidate "
            "groups; alternative Heroes must be evaluated separately."
        )

    samples = build_samples(
        card_data,
        contexts=contexts,
        games_per_context=games_per_context,
        seed=seed,
        required_cards=selected_cards,
    )

    pair_ids = (
        list(itertools.combinations(selected_cards, 2))
        if include_pairs
        else []
    )

    subjects = [
        card_id for card_id in selected_cards
        if canonical_cards[card_id]["type"] == "subject"
    ]
    links = [
        card_id for card_id in selected_cards
        if canonical_cards[card_id]["type"] == "link"
    ]
    names = [
        card_id for card_id in selected_cards
        if canonical_cards[card_id]["type"] == "name"
    ]
    triple_ids = (
        list(itertools.product(subjects, links, names))
        if include_legend_triples
        else []
    )

    required_conditions: set[frozenset[str]] = {frozenset()}
    required_conditions.update(frozenset([card_id]) for card_id in selected_cards)
    required_conditions.update(frozenset(pair) for pair in pair_ids)
    if include_legend_triples:
        required_conditions.update(frozenset(triple) for triple in triple_ids)
        # Triple contrasts require every lower-order intervention even when
        # the caller does not request pair rows in the output.
        required_conditions.update(
            frozenset(pair)
            for triple in triple_ids
            for pair in itertools.combinations(triple, 2)
        )

    per_condition: dict[frozenset[str], list[int]] = {
        condition: [] for condition in required_conditions
    }

    for sample in samples:
        for condition in sorted(
            required_conditions,
            key=lambda item: (len(item), tuple(sorted(item))),
        ):
            focal_deck = replace_cards(sample.focal_deck, condition)
            outcome = _play_focal_outcome(
                engine,
                sample,
                focal_deck,
                agent_name=agent_name,
            )
            per_condition[condition].append(outcome)

    base = per_condition[frozenset()]

    cards: list[dict[str, Any]] = []
    for index, card_id in enumerate(selected_cards):
        replaced = per_condition[frozenset([card_id])]
        differences = [
            original - control
            for original, control in zip(base, replaced)
        ]
        effect = estimate(
            differences,
            seed=seed + 10_000 + index,
            bootstrap_resamples=bootstrap_resamples,
        )
        row = {
            "id": card_id,
            "title": canonical_cards[card_id]["title"],
            "type": canonical_cards[card_id]["type"],
            "baseline_id": baseline_id(card_id),
            "baseline": baseline_card(canonical_cards[card_id]),
            "delta_win_probability": effect.mean,
            "ci95": list(effect.ci95),
            "ci_method": effect.ci_method,
            "standard_error": effect.standard_error,
            "samples": effect.samples,
            "original_wins": sum(base),
            "replacement_wins": sum(replaced),
            "discordant_original_better": sum(
                1 for value in differences if value > 0
            ),
            "discordant_replacement_better": sum(
                1 for value in differences if value < 0
            ),
            "ties": sum(1 for value in differences if value == 0),
            **_severity(effect),
        }
        cards.append(row)

    pairs: list[dict[str, Any]] = []
    for index, (a, b) in enumerate(pair_ids):
        ra = per_condition[frozenset([a])]
        rb = per_condition[frozenset([b])]
        rab = per_condition[frozenset([a, b])]
        values = [
            pair_contrast(v0, va, vb, vab)
            for v0, va, vb, vab in zip(base, ra, rb, rab)
        ]
        effect = estimate(
            values,
            seed=seed + 20_000 + index,
            bootstrap_resamples=bootstrap_resamples,
            contrast_bound=2.0,
        )
        pairs.append({
            "cards": [a, b],
            "title": f"{canonical_cards[a]['title']} × {canonical_cards[b]['title']}",
            "types": [
                canonical_cards[a]["type"],
                canonical_cards[b]["type"],
            ],
            "interaction_delta": effect.mean,
            "ci95": list(effect.ci95),
            "ci_method": effect.ci_method,
            "standard_error": effect.standard_error,
            "samples": effect.samples,
            **_severity(effect),
        })

    triples: list[dict[str, Any]] = []
    for index, (a, b, c) in enumerate(triple_ids):
        ra = per_condition[frozenset([a])]
        rb = per_condition[frozenset([b])]
        rc = per_condition[frozenset([c])]
        rab = per_condition[frozenset([a, b])]
        rac = per_condition[frozenset([a, c])]
        rbc = per_condition[frozenset([b, c])]
        rabc = per_condition[frozenset([a, b, c])]
        values = [
            triple_contrast(v0, va, vb, vc, vab, vac, vbc, vabc)
            for v0, va, vb, vc, vab, vac, vbc, vabc in zip(
                base, ra, rb, rc, rab, rac, rbc, rabc
            )
        ]
        effect = estimate(
            values,
            seed=seed + 30_000 + index,
            bootstrap_resamples=bootstrap_resamples,
            contrast_bound=4.0,
        )
        triples.append({
            "cards": [a, b, c],
            "title": (
                f"{canonical_cards[a]['title']} — "
                f"{canonical_cards[b]['title']} — "
                f"{canonical_cards[c]['title']}"
            ),
            "interaction_delta": effect.mean,
            "ci95": list(effect.ci95),
            "ci_method": effect.ci_method,
            "standard_error": effect.standard_error,
            "samples": effect.samples,
            **_severity(effect),
        })

    cards.sort(
        key=lambda row: (
            -abs(row["delta_win_probability"]),
            row["title"],
        )
    )
    pairs.sort(
        key=lambda row: (
            -abs(row["interaction_delta"]),
            row["title"],
        )
    )
    triples.sort(
        key=lambda row: (
            -abs(row["interaction_delta"]),
            row["title"],
        )
    )

    return {
        "schema_version": 1,
        "method": "paired_common_random_numbers_factorial_replacement",
        "policy": agent_name,
        "seed": seed,
        "contexts": contexts,
        "games_per_context": games_per_context,
        "bootstrap_resamples": bootstrap_resamples,
        "sample_generation": {"seed": seed, "required_cards": selected_cards},
        "samples": len(samples),
        "conditions_evaluated_per_sample": len(required_conditions),
        "total_matches": len(samples) * len(required_conditions),
        "baseline_definition": {
            "subject": "Vanilla Subject, 4 Strength",
            "link": "Vanilla Link, +1 Strength immediately and +2 more while it has a Name",
            "name": "Vanilla Name, 2 Strength",
            "plot": "Universally playable no-op Story",
            "stratagem": "Face-down inert Stratagem with no trigger or effect",
        },
        "pairing": {
            "common_game_seed": True,
            "common_starting_player": True,
            "common_agent_seed": True,
            "same_deck_index_permutation": True,
            "focal_seat_alternates": True,
        },
        "cards": cards,
        "pairs": pairs,
        "triples": triples,
        "methodology": {
            "card_effect": "base outcome - same deck with one copy replaced by its matched baseline",
            "pair_interaction": "f(AB)-f(A0)-f(0B)+f(00)",
            "triple_interaction": "third-order factorial contrast over original/baseline states",
            "ci95": "paired percentile bootstrap over per-sample contrasts; bounded Hoeffding interval when observed contrasts are constant",
            "uncertainty_limits": "Intervals are unadjusted for multiple comparisons and condition on the generated deck contexts; targeted reuse of those contexts is not an independent replication.",
            "interpretation": (
                "Effects are causal for the evaluated policy and generated deck-context "
                "distribution, not universal equilibrium card values."
            ),
        },
    }
