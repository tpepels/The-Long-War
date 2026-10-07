# Repository cleanup audit

Audited from remote `main` at `b94da6a4` on 2026-10-07. Cleanup branch: `maintenance/repository-cleanup`. No engine/research integration PR was merged.

The active source flow is:

```text
physical game -> print presentation
physical game -> runtime engine -> AI/research
```

## Removed and superseded

| Removed material | Replacement / reason |
| --- | --- |
| `web/cards-v2.html` redirect | `web/cards.html` is the sole public catalogue; no migration alias is needed. |
| `web/cards-v2-force-style-lab.{html,js,css}` | Shared physical renderer plus the canonical-pool, stack, numeric-stress and overflow checks in `tools/check_card_layout.py`. |
| Unused filter/search/legend/lab controller and its CSS in the shared renderer | Public catalogue and deck controllers consume `PhysicalCards`; developer stack and overflow inspection remain. |
| `web/v2-reminders.js` | Current authored effect/exposed text is rendered directly; no active renderer imported this old sentence map. |
| Seven family-art fallback PNGs and CSS fallback layers | All 128 cards have canonical card-ID PNGs; Pages now requires those files. |
| `web/art/v2/candidates/batch-06/` and its manifest | Every one of its 64 PNGs duplicated an authoring original; unique originals remain in `cards/art-sources/`. |
| Ten unused `web/art/v2/ui/` shells/textures | Shared CSS card geometry and functional SVG symbols; no active references to the shell assets existed. |
| Two generated preview PNGs, old artwork audits/manifests and artwork README | Live layout/PDF checks, per-card coverage tests and the current source map in `cards/README.md` / `cards/art-sources/README.md`. |
| `tools/render_v2_previews.py` | Current layout checker retains all six formation stack proofs and card/PDF checks; the preview tool loaded a deleted card pool. |
| `tools/normalize_v2_art.py` | Completed one-time crop migration. Canonical normalized PNGs are preserved; build-time derivative generation never crops or overwrites those originals. |
| Twelve historical `web/assets/rulebook-*` illustrations | Current `rules/rulebook.md` has no illustration references. The old teaching-plate decorator, CSS, JPEG/FFmpeg shim and special ASCII-to-art substitution are removed; ordinary Markdown images and fenced code remain supported. |
| `cards/approved-card-mechanics.md` and the two `first-80-*` documents | Current 128-card JSON, catalogue, mechanics guide and authored design audits supersede their 80/95-card wording and rules. |
| Old deck-inclusion statistics in `cards/reference-decks.md` | Current deck index/source guide; historical statistics are not current balance evidence. Deck JSON is unchanged. |
| `.github/workflows/ci.yml`, Pages pytest/layout-test jobs | Local `make verify`, test and print checks. Actions only compile/check deployment inputs and publish Pages. |
| `make web-protocol` convenience alias | Explicit local generator `python tools/build_web_protocol.py`; lifecycle builds retain `--check`. |
| Tests tied solely to deleted labs, migration artwork and a second card pool | Canonical-pool/render/deployment contracts. Valuable runtime, card validation, search and research tests remain, including failing ones. |

## Retained and clarified

- `cards/cards.json`, `rules/rulebook.md`, all shipped decks and the exploratory playtest deck JSON are byte-identical to the audit baseline.
- All 128 high-resolution canonical PNGs are byte-identical, moved to `web/art/cards/`. All raw per-card authoring originals are retained as 125 unique files outside deployment in `cards/art-sources/`.
- Physical support documents/decks moved from `cards/v2/` to `cards/`; the renderer/styles/symbols use neutral `physical-cards` / `card-symbols` names. Producer and consumer paths changed together.
- Public navigation is **Webgame · Cards · Decks · Reference · Rules · Balance Lab**, expanded from one small static fragment. Existing home-button styling and current-page accessibility are preserved. Markers remain accessible from the print/reference package.
- Historical engineering/evidence reports remain under `reports/` with an explicit historical index. They are neither deployed nor active rules authorities.
- Current authored valuation/effect/coverage documents remain design diagnostics, not runtime schemas or measured balance evidence.
- Generated native protocol/weight/fingerprint inputs and browser protocol JS remain required compile/transport inputs. Their generators are the authorities; Actions check rather than regenerate source files.
- Browser/runtime adapters, active research runners, native facades and simulation orchestration remain. No new compatibility wrapper, framework or alternate game implementation was introduced.

## Local verification

- Native rebuild and generated-input checks passed; undefined-name lint passed.
- Focused presentation/build/navigation/workflow/content checks passed. All 128 printed render outputs were independently compared with baseline after normalizing intentional path/class renames.
- Physical layout validation passed for 128 cards, six stacks, numeric stress and deliberate oversized-text detection. The card PDF contains sixteen eight-card sheets with complete IDs/revision stamps.
- `make pages` passed with pinned Typst 0.15.1; the rulebook PDF contains five validated pages. Authored/built browser static checks passed. `dist/` contains eight public HTML pages and 128 optimized card images, with no design labs or original artwork.
- Browser inspection covered Cards, Decks and Reference: complete artwork, working navigation, ready-to-print state and no content/asset errors. The catalogue's unrelated missing favicon produces a browser 404.
- Final fast suite: **485 passed, 135 failed**, versus **484 passed, 140 failed** on baseline. There are **zero new failures**; changed totals also reflect obsolete-test replacement. Five stale assertions were corrected: duplicate catalogue, vanilla empty rules, artwork URL spelling, zero-cost cards and authored physical deck minima.
- `make verify` still stops in research command-cost validation, which rejects six canonical zero-cost cards. Browser/native parity still fails the `deterministic-standard-trace` legal-action comparison. Neither gate was weakened or disabled.

Detailed local logs and the complete remaining test names are under `artifacts/repository-cleanup/`; build/parity logs remain under their normal artifact paths. No CI monitoring or expensive evidence pipeline was run.

## Deferred debt

- **#81:** executable card mechanics, current physical deck-construction parity, native/browser legal-action parity and the existing engine/session failures. The Webgame is explicitly experimental on its setup screen.
- **#82:** search, simulation, telemetry, counterfactual and balance-consumer migration, including acceptance/analysis of authored zero-cost cards. No AI defaults, balance results or policies were changed.
- Active native `v2_*` identifiers, the included `_fast_engine_v2.pxi`, protocol payload identifiers and card-schema metadata remain internal integration dependencies. Renaming these during unfinished integration would churn source fingerprints and stacked work; they are not public version surfaces. The game fingerprint remains `f43633ff61efe22a`.
- The preserved rulebook/runtime integration test still exposes physical Force/Name minima differing from runtime configuration. That is engine-sync debt, not permission to rewrite authored rules.
- No current evidence was regenerated or promoted. Broader historical CSS and genuinely reusable Markdown support were retained where removal would require a separate presentation change or wider behavioural proof.
