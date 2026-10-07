# Workstreams

The Long War has four deliberately separate workstreams. Keeping them separate is more important than keeping every implementation layer synchronized in every commit.

## 1. Physical game and authored rules

**Purpose:** define the game that can be printed and played at a table.

Primary sources:

- `cards/cards.json` - canonical card pool and card wording/mechanics metadata
- `rules/rulebook.md` - player-facing rules
- `cards/v2/playtest-decks.json` and `decks/*.json` - playtest/shipped deck content
- `web/art/v2/cards/` - canonical card artwork

This workstream may change while the software engine is temporarily behind. That lag must be explicit; it must not be hidden by duplicating or approximating rules in UI code.

Typical branch prefix: `game/` or `cards/`.

## 2. Print/web presentation

**Purpose:** present the physical game and make it easy to print, learn, and inspect.

Primary sources:

- `web/cards.html`, `web/cards-v2.js`, `web/cards-v2.css`
- `web/playtest-kit.html`, `web/playtest-kit.js`
- `web/playmat.html`
- `web/tokens.html`
- `web/rulebook.template.html`
- `tools/build_pages.py`, `tools/build_rulebook_pdf.py`

Presentation code may render authored card/rule data but must not become a second rules engine.

Typical branch prefix: `web/` or `print/`.

## 3. Runtime engine and webgame

**Purpose:** implement the authored physical rules exactly in executable form.

Primary sources:

- `src/longwar/rules.py`
- `src/longwar/game/`
- `src/longwar/_fast_engine_*.pxi`
- `src/longwar/web_api.py`
- `web/play.html`, `web/play.js`, `web/play.css`

The engine is the sole executable authority once a mechanic is implemented. It must not invent a different game to make tests pass. If authored cards/rules are ahead of runtime support, the webgame is explicitly experimental until the engine-sync work lands.

Typical branch prefix: `engine/`. Browser-only presentation work uses `web/`.

## 4. AI, balance, and research

**Purpose:** analyze the implemented engine. This workstream does not define game rules.

Primary sources:

- `src/longwar/agents/`
- search/native-search modules
- telemetry, progression, balance, health, counterfactual modules
- `tools/run_experiments.py`, `tools/full_lab.py`

Research evidence is valid only for the engine revision it was generated from. Do not use stale evidence to rewrite current physical rules without a deliberate design decision.

Typical branch prefix: `ai/`, `balance/`, or `research/`.

## Dependency direction

```text
physical game / authored rules
            |
            +------> print & reference presentation
            |
            v
runtime engine / webgame
            |
            v
AI / balance / research
```

Print presentation and the runtime both consume the authored game. They do not depend on each other.

## Pull request policy

Keep PRs single-purpose.

- **Game PR:** cards, decks, rules, and directly related authored content.
- **Print/web PR:** presentation/build files only; no engine semantics.
- **Engine PR:** runtime implementation/tests for already-authored mechanics.
- **Research PR:** AI/search/analysis only; no rule redesign hidden inside experiments.

If a change truly requires two workstreams, prefer two linked PRs over one mixed PR.

## Branch naming

Use one of these prefixes for new work:

- `game/` - physical rules/cards/decks
- `print/` - printable website/reference/rulebook presentation
- `web/` - interactive browser UI/transport
- `engine/` - executable game semantics
- `ai/` - production/search AI
- `balance/` or `research/` - experiments and analysis
- `docs/` - documentation-only changes

Avoid generic `fix-*`, `cleanup/*`, and agent-specific branch names for new work.

## Testing policy

Tests protect durable invariants; they do not define the evolving game. Exact card balance, rulebook wording, playtest deck composition, and visual/layout choices should be reviewed directly rather than preserved as permanent regression tests unless they represent an explicitly durable contract.

Physical game and print changes may intentionally lead the engine or invalidate an old design assertion. In that case, update/remove the obsolete assertion and record follow-up engine work separately. See `TESTING.md`.

Pages deployment is independent of regression-test status and is blocked only when the site or its required artifacts cannot be built safely.

## Current status

- `main` contains the current printable physical playtest package.
- The physical game is usable independently of the webgame.
- Runtime integration is unfinished and belongs in a separate `engine/` workstream.
- The webgame should be treated as experimental whenever runtime support lags the authored cards/rules.
- Historical branches and reports are not current sources of truth.
