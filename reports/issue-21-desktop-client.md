# Issue #21 — desktop game client

Implemented locally on 2026-09-24 for [issue #21](https://github.com/tpepels/The-Long-War/issues/21). The earlier issue #20 work was preserved; during this pass it became commit `f936c84`. Desktop verification ran against `f9d7fdf`; the subsequent benchmark-output commits through `c3f3dee` were also preserved. This report records the desktop implementation before the separately requested reconciliation of PR #18. No GitHub Actions runs were requested.

## What changed

The previous client retained a website masthead, stacked utility panels, lengthy action instructions, and several generations of layout overrides. Shared website CSS still imposed grid sizing on gameplay, and hand layout changed through viewport-specific overlap rules.

The client now presents a title/setup screen followed by one fixed desktop table. The HUD, opponent, three Fronts, ranks, face-down spaces, piles and own hand have persistent locations. Victory diamonds and Front control/strength remain visible. Formations join a Subject with overlapping Bond and Name tabs; the Subject keeps its geometry when components attach. Compact cards carry identity/type while the side inspector shows the complete card.

The hand uses one count-aware fan, with hover/focus lift and a raised selected copy. Every card remains reachable without a scrollbar. Large hands have bounded spacing; expanded cards stay within the viewport. Long titles have a bounded title region and adaptive typography. Initial fan layout commits before transitions begin, avoiding a flash of cards stacked at the center.

Legal-action data activates formation, Story and Stratagem destinations. Click and keyboard targeting share the same handlers. Name movement choices, cancellation, mulligans, Draw, Pass and choosing the next starter remain engine-authoritative. Full inspection is available during mulligans as well as normal play. Focus returns to the selected card when inspection closes; hot-seat handoffs close private inspection.

Rules, piles, log, fullscreen and New Match live in a side drawer. The card inspector leaves the table visible. A completed match has a result overlay and Play Again control. Routine prompts are shorter, and setup's replay seed is optional detail.

Motion communicates draw, placement, movement, return, discard, reveal and Battle/Victory changes from consecutive visible snapshots. AI has a brief thinking interval followed by visible action feedback. Battle resolution announces the authoritative Victory-count change. Reduced-motion removes travel/transitions while preserving state and feedback. Submission guards and session-generation checks prevent rapid clicks or stale AI callbacks from affecting a restarted match.

## Consolidation

- Replaced the layered `play.css` overrides with one desktop scene layout and fixed card interiors; removed mobile layout branches.
- Removed the website stylesheet dependency from `play.html` and 685 obsolete gameplay CSS lines from `style.css`. Active site, print and playmat styles remain.
- Removed the masthead, utility `<details>` panels, drag-and-drop plumbing, unused card-art helpers and duplicated banner timing.
- Kept one full-card renderer, one compact formation renderer, shared semantic rule markup and one interaction state. The overflow guard remains a diagnostic; it does not resize cards to conceal bad geometry.
- Replaced the layout check's hand-authored imitation UI with production HTML/JS/CSS fed native presentation snapshots. Only the temporary QA transport is replaced. Live interaction tests still load the actual WebAssembly engine.

No rules, cards, Python/Cython engine code or browser-engine transport changes were needed for this issue.

## Verification

Run commands with the project virtualenv active. Final local results:

| Command | Result |
| --- | --- |
| `make test-fast` | 284 passed |
| `make native-build` | Host extensions verified after the shared checkout received upstream native changes |
| `make browser-parity` | 2 engine scenarios and 107 native/WebAssembly session snapshots passed |
| `python tools/check_card_layout.py --require-browser` | All 48 browser cards and 48 print cards fit their information regions |
| `python tools/check_game_layout.py --require-browser` | 32 production-client cases passed across four desktop viewports |
| `python tools/check_play_start.py --require-browser --viewport 1280x720` | Live WebAssembly interaction smoke passed |
| `python tools/check_play_start.py --require-browser --viewport 1440x900 --reduced-motion` | Same live flow passed with reduced motion |
| `node --check web/play.js` and `git diff --check` | Passed |

The layout matrix covers 1280×720, 1366×768, 1440×900 and 1920×1080, each with a crowded battlefield/18-card hand, targeting, inspector, AI turn, Choose First, completed match, mulligan and drawer. It verifies stable zone geometry, no page scrolling, visible controls, no card overflow and hidden-card privacy. Exact-size Playwright screenshots additionally check pointer access and keyboard focus at both ends of the crowded fan. Screenshots were visually inspected at laptop and larger desktop sizes, including full formations, inspection, targeting, AI and completion.

The live smoke covers mulligan keyboard inspection, menu/Escape, card selection/cancellation, legal placement, public inspection, paced AI and Draw. A separate local Playwright audit against the real engine completed 39 checks with zero console/page errors: hot-seat privacy, mulligan selection/cancel/redraw, Name movement, Pass → Choose First → next Battle → match completion → Play Again, and spatial face-down Stratagem/Story placement with opponent identity redaction. Its script/results are under `artifacts/issue21/interaction-audit.*`; screenshots are under `artifacts/issue21-desktop/`. These stress fixtures are presentation coverage, not evidence that arbitrary full-board fixture compositions are legal decks.

## Human playtesting

The remaining questions are subjective: whether the brief AI delay gives enough time to follow actions, how quickly new players learn the assembled formation layout, and whether crowded-hand spacing feels comfortable during a full match on a 720px-tall laptop. Hover/focus and the inspector provide full reading, but this pass does not establish those preferences for every player. Mobile remains outside scope.
