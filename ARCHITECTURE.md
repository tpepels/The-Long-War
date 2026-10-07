# Architecture

The software architecture exists to implement the authored physical game without duplicating game semantics.

Repository work is split by `WORKSTREAMS.md`. In particular, the physical game and print presentation may merge independently of runtime implementation. This document governs the **software dependency graph** once rules are being implemented in executable form.

## Product boundary before the software graph

```text
authored physical game
  cards/cards.json
  rules/rulebook.md
  playtest decks / artwork
       |                  \
       |                   +--> print/reference presentation
       v
runtime implementation / webgame
       |
       v
AI / balance / research
```

The runtime must implement the authored game, not redefine it. A temporary gap between authored content and runtime support is allowed during active design, but that gap must be explicit and the webgame remains experimental until synchronized.

## Dependency map

```text
content / configuration
  cards/cards.json
  decks/*.json + decks/index.json
  rules.py / cards.py / decks.py
  rules/rulebook.md
            |
            v
canonical game core
  game/model.py
  game/actions.py
  game/engine.py
  _fast_engine_core.pxi
            |
   +--------+-------------------+--------------------+
   |                            |                    |
   v                            v                    v
AI/search                  application adapters   simulation
agents/*                   web_api.py             simulate.py
belief.py                  native_engine.py       tools/simulate.py
heuristics.py              browser-engine.mjs
algorithms/*                    |
native search cores             v
                           browser UI/transport
                           play.js / play.css
                           remote-peer.mjs
   \                            |                    /
    \                           |                   /
     +--------------------------+------------------+
                                |
                                v
                     analysis / research / reports
                     telemetry.py
                     progression.py
                     balance.py
                     health.py
                     playability.py
                     counterfactual.py
                     MCCFR tooling
                     tools/run_experiments.py
                     tools/full_lab.py
```

Dependencies point downward. The core must never depend on search, browser, simulation, or analysis. Browser transport must never become a second rules engine.

## 1. Canonical game core

The core is the sole semantic authority for state, legal actions, transitions, visibility, card effects, scoring, and configurable match rules.

`GameRules` is plain configuration. Experiments use `GameRules.standard().with_overrides(...)`, not alternate engines or named rule implementations.

Configurable defaults are single-source. UI hints, generated references, simulations, and tests derive values from `GameRules`; they do not re-literalize a balance candidate.

Native composition is rooted at `_fast_engine_core.pxi`. Host engine/search may share one compiled extension for packed types and performance, but that packaging is not an architectural dependency. Core Python reaches transitions through `native_engine.py`.

## 2. Cards and decks

`cards/cards.json` and the player-facing rulebook are authored game-design inputs. Cards may be updated for physical play before every mechanic is implemented in the runtime.

When runtime support is added, cards are data interpreted by the core. `design_rules` is the only executable mechanics schema; presentation text/rule blocks are not another machine-rules channel.

Runtime code may understand reusable capabilities, but must not branch on a canonical card id/title. New behavior requires a reusable schema/engine primitive.

Decks are match input:

- `decks.py` owns construction validation;
- `decks/index.json` is the only shipped/canonical deck catalogue;
- `GameEngine.new_game()` delegates construction validation;
- beliefs/search take deck shape from match context, not `GameRules`.

Experiment-only variants are copied/in-memory data with explicit provenance, not edits to canonical files.

## 3. AI and search

Agents/search algorithms consume the core.

They may own search trees, beliefs, evaluators, transposition tables, rollout policies, training tables, and performance optimizations.

They may not own turn/Battle transitions, card legality, Command semantics, card effects, deck assumptions, or alternate state semantics.

Research/search capabilities are exposed through `native_search.py`. The product browser opponent is a separate product decision; research solvers do not become browser modes merely because they exist.

## 4. Application adapters

### Browser session

`web_api.PlaySession` adapts canonical engine state/actions to JSON snapshots. It owns viewer-specific visibility, mulligan/session pacing, action serialization, production local-opponent integration, and public log formatting. It does not own alternate rules.

### Pyodide bridge

`web/browser-engine.mjs` loads the generated browser runtime and forwards JSON calls to `PlaySession`.

The browser wheel excludes analysis, telemetry, counterfactual, solver training, and research agents. It compiles the same engine core as the host plus only the production heuristic.

### Browser UI

`web/play.js` renders snapshots and submits canonical action keys. It may animate snapshot differences but must not predict action results.

`web/play.css` owns game-scene/card geometry.

## 5. Multiplayer transport

Remote browser play is host-authoritative.

The product UI exposes remote host/join setup states, while the underlying application uses one `PlaySession(mode="remote")`.

- Host owns the canonical session and performs every transition.
- Guest receives only `snapshot(1)`.
- Guest sends canonical action keys or mulligan selections.
- Host validates/applies them and returns a redacted snapshot.
- Hidden information remains protected by the viewer boundary.

`web/remote-peer.mjs` is a rule-free WebRTC transport. It may move JSON and encode signaling tokens, but must not know cards, legal actions, or engine semantics.

The current static deployment uses manual offer/answer tokens and STUN. Future signaling, room codes, or TURN belong to transport infrastructure and do not justify duplicating game semantics server-side.

## 6. Simulation

`src/longwar/simulate.py` is the one AI-vs-AI match loop.

Analysis and experiments consume its output rather than creating parallel game loops.

## 7. Analysis and research

Analysis sits outside the runtime boundary and may evolve without changing game semantics.

It includes telemetry, progression, playability, health, balance, counterfactual analysis, solver verification/training, experiment orchestration, and Lab assembly.

Non-standard rule variants belong in explicit `GameRules.with_overrides(...)` tests. They are configuration cases, not additional supported rules profiles.

A new experiment is not a reason to add another engine, simulation loop, browser rules implementation, permanent rules profile, or Make target for a parameter combination.

## 8. Full Balance Lab

`tools/full_lab.py` composes existing validation, balance, search, MCCFR, report, and Pages stages. It is lifecycle orchestration, not another analysis implementation.

A completed expensive stage is reusable when its outputs exist and its stored **game fingerprint plus stage configuration** match. The broader experiment fingerprint is retained for provenance, but unrelated presentation/tooling edits do not invalidate expensive game evidence.

The Lab preserves evidence provenance rather than reducing different methods to one score.

## 9. Browser static integrity and Pages

`tools/build_pages.py` builds the static site into `dist/`. It expands the shared six-link navigation fragment and generates optimized card artwork from preserved canonical PNGs. Authoring originals live outside the deployed tree. There is no public historical design-lab surface.

`tools/check_web_static.py` guards cross-file/build contracts that ordinary syntax checks can miss:

- authored JS/module syntax;
- HTML local assets;
- module imports;
- `play.js` DOM ids;
- built `data/*.json` references;
- runtime/Pyodide references and wheel manifest.

`make browser-parity` runs the checker before and after building Pages, then compares canonical browser/native session traces.

The Pages workflow is deployment infrastructure. It performs compile/static build-integrity checks and publishes `dist/`, but does not run research simulations, balance analysis, pytest suites, or solver training.

## 10. Rulebook and print pipeline

Player-facing rules are authored in `rules/rulebook.md`.

Two presentation paths consume them:

- `tools/build_pages.py` renders the web rulebook/reference site;
- `tools/build_rulebook_pdf.py` renders rule tokens from `GameRules.standard()`, converts the supported Markdown subset to Typst, compiles `dist/rulebook.pdf`, and verifies the PDF.

Printable pagination is therefore independent of browser print layout. `dist/rulebook.typ` is generated intermediate source, not canonical authored rules.

## 11. Command surface

Make is a small lifecycle layer, not an API for every script.

Permanent targets are:

```text
install
native-build
browser-build
verify
verify-algorithms
test
test-fast
test-integration
simulate
balance
experiments
full-lab
pages
browser-parity
```

Variations belong in arguments to those operations or to the underlying runners.

## Enforced invariants

Architecture/tests should protect durable ownership boundaries:

1. Core modules do not import agents, search, simulation, analysis, or web code.
2. Browser runtime adapters do not import analysis/training modules.
3. Search algorithms do not reimplement rules or branch on canonical card ids.
4. Action serialization belongs to game/application boundaries, not a solver.
5. Deck filenames/profile membership are not game-core constants.
6. Python game transitions are not duplicated outside the canonical engine.
7. Experiment parameter combinations do not become permanent Make targets.
8. `GameRules` contains match configuration, not deck-construction policy.
9. Remote transport contains no game semantics and is never authoritative.
10. Browser asset names referenced by consumers must exist in the built site.
11. Configurable numeric rules are not duplicated across developer docs/consumers.

Tests should protect ownership and behavior, not incidental file layout.
