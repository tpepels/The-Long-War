# Architecture

The Long War is a game first. The architecture exists to make rules easy to
change, cards and decks easy to extend, and every consumer play exactly the
same game.

## Dependency map

```text
content / construction
  cards/cards.json
  decks/*.json
  decks.py
  rules/rulebook.md
        |
        v
game core
  cards.py
  rules.py
  game/model.py
  game/actions.py
  game/engine.py
        |
        +-------------------+-------------------+
        v                   v                   v
AI/search               browser play        simulation
agents/*                web_api.py           simulate.py
belief.py               web/*                tools/simulate.py
heuristics.py
algorithms/*
native search cores
        \                   |                   /
         \                  |                  /
          +------------------+-----------------+
                             v
                    analysis / design tools
                    telemetry.py
                    human_flow.py
                    balance.py
                    health.py
                    playability.py
                    counterfactual.py
                    tools/*
```

Dependencies point downward in this diagram. Analysis and search may consume the
game core. The game core must never depend on them.

## 1. Game core

The game core is the sole semantic authority.

It owns:

- state;
- legal actions;
- applying actions;
- Battle and match transitions;
- visibility and hidden information;
- card effect interpretation;
- scoring;
- configurable match rules.

`GameRules` is deliberately a plain configuration object. Rule experiments
should change values through `with_overrides(...)`, so a rule can be tested
without creating another engine, mode, or implementation.

The browser, simulations, and every AI algorithm must ask the same engine for
legal actions and transitions. They must not reproduce rule logic.

## 2. Cards

Cards are data interpreted by the game core.

Adding ordinary cards should require data changes, not search/UI changes.
Reusable effect primitives belong to the game core; algorithms must not contain
card-specific behavior.

**No runtime implementation may special-case a card identity.** The engine,
heuristics, and search agents may understand capabilities such as "Hero",
"move a formation", "gain Command", or "play in more than one role", but they
must not branch on a particular card id or title. A card that needs a new kind
of behavior requires a reusable capability/effect primitive in the card schema
and engine, not an `if card_id == ...` patch.

This is especially important for future rule-breaking cards: exceptions remain
data-driven and visible to every consumer through the same engine.

The card catalogue is independent from any particular deck.

## 3. Decks

A deck is input to a match, not part of the rules engine.

The engine accepts two deck compositions when creating a game. Reference decks
are examples/playtest content, not engine constants. Future decks may contain
different cards and may be larger than today's playtest decks.

`decks.py` owns optional construction policy. The current shipped playtest
format is 34 cards with the current copy limits, but those constraints are not
fields of `GameRules` and are not required by `GameEngine`. The engine only
checks that supplied card ids exist and that the deck fits native storage.

AI beliefs must likewise take deck size from the supplied game/deck context,
not from match rules. A future deck format may change size or copy limits
without changing the engine or search algorithms.

## 4. AI/search

Agents and search algorithms are consumers of the game core.

Browser play exposes product modes (`computer` and `hotseat`), not solver
identities. The current production computer opponent is `HeuristicAgent`.
Changing the production opponent must not change the browser protocol or create
a new play mode. ISMCTS, alpha-beta, MCCFR and online MCCFR are research/search
implementations unless explicitly promoted by a separate product decision.

They may own:

- search trees;
- beliefs;
- evaluation functions;
- transposition tables;
- rollout policies;
- performance optimizations.

They may not own:

- turn/Battle transitions;
- card legality;
- Command rules;
- card effects;
- deck assumptions;
- alternate state semantics.

An algorithm should continue working when a `GameRules` constant changes
unless the algorithm's own search parameters are intentionally changed.

## 5. Application adapters

`web_api.py` adapts the game to browser sessions. It may depend on the core
and the chosen production play agent. It must not depend on balance,
counterfactual, telemetry, training, or solver-research modules.

`simulate.py` is the one programmatic match loop for AI-vs-AI play. Analysis
may consume its output rather than creating alternate game loops.

## 6. Analysis and developer tooling

Analysis exists to help design the game. It sits outside the browser runtime
and may be deleted or replaced without changing game semantics.

Canonical verification covers the current standard rules. Historical/non-standard
rule variants may retain explicit tests for design archaeology, but those tests
are expressed as ordinary `GameRules.standard().with_overrides(...)` values,
marked `legacy_rule_experiment`, and are not part of `make verify` or
`make verify-algorithms`.

Tools may compose simulations and reports, but a new experiment is not a reason
to add:

- another rules engine;
- another simulation loop;
- another browser mode;
- another named rules profile;
- another Make target.

Experiment variation belongs in data/configuration and command arguments.

## 7. Command surface

Make is a small human-facing convenience layer, not an API for every script or
experiment.

New experimental variations should use arguments to an existing command.
Adding a Make target requires a new lifecycle operation, not merely a new
parameter combination.

## Enforced invariants

Architecture tests must enforce these properties:

1. Core modules do not import agents, search, simulation, analysis, or web code.
2. Browser runtime adapters do not import analysis/training modules.
3. Search algorithms do not inspect individual `GameRules` fields.
4. Action serialization belongs to `game.actions`, not to an algorithm.
5. Deck files/names are not referenced by the game core.
6. Python game transitions are not duplicated outside the canonical engine.
7. Experiment-specific command combinations do not become new Make targets.
8. Engine, heuristic, and search implementation files contain no canonical card ids.
9. `GameRules` contains no deck-construction fields such as deck size or copy limits.

Tests should enforce dependency direction and ownership, not incidental file
layout or a particular search implementation.

## Current cleanup debt

The following existing structures predate this contract and should be reduced
carefully rather than duplicated further:

- `_fast_search.pyx` physically bundles the engine and several native search
  cores into one extension;
- the browser's `_fast_search` extension still physically contains native
  search cores that browser play does not use because the engine/search split
  has not yet been performed.

These are migration items, not patterns to copy.
