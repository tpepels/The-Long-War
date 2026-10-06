# V2 family artwork

These seven production images were recovered from the interrupted physical-card design pass. The original cache filenames were opaque `exec-*.png` names; the images were visually inspected and mapped to the card family they were clearly composed for.

| Production asset | Recovered source | Card family | Visual |
|---|---|---|---|
| `force-march.png` | `exec-801584ee-0524-4328-942b-ba02092d6478.png` | Force | marching spear line and banners over a valley |
| `bond-bound-spears.png` | `exec-814ee772-04a0-47b0-b687-bc782a3774ae.png` | Bond | two spear shafts lashed together |
| `name-tattered-banner.png` | `exec-4f01bf91-9fd8-4f11-918b-8642de7462b5.png` | Name | lone weathered red standard |
| `hero-helmet-laurel.png` | `exec-7dd1fd94-7a52-41ef-bbfd-50c042292486.png` | Hero | crested helmet and laurel |
| `tactic-archer-volley.png` | `exec-d0dd4835-d062-477d-9cb5-256653c269a0.png` | Tactic | archers loosing a volley |
| `stratagem-war-map.png` | `exec-4f2e85ff-4096-488d-ae95-2a39ef77b02f.png` | Stratagem | campaign map inside a command tent |
| `narrative-roadside-memorial.png` | `exec-a5f6c086-558f-4e38-b289-9df2ba23f90c.png` | Narrative | memorial stone, shield and road |

The seven recovered family images are fallback artwork only. When a matching file exists under `web/art/v2/cards/<card-id>.png`, the renderer uses that per-card illustration instead. No second illustration or vector heraldry is overlaid on the art field; symbols remain confined to the card interface.


## Representative QA previews

- `previews/v2-formation-stacks.png` - Force alone, Force + Bond, Force + Bond + Name, and Hero-as-Name physical overlap.
- `previews/v2-card-families.png` - short through dense rules and the major visual families side by side.

Regenerate both from the production renderer with:

```sh
python tools/render_v2_previews.py --output-dir web/art/v2/previews --require-browser
```

The older recovered renderer screenshots were inspected during recovery and replaced by these current-production proofs.

## Per-card illustrations

Per-card artwork is named by canonical V2 card ID and lives in `web/art/v2/cards/`. The filename is the mapping: a newly added `<card-id>.png` is picked up automatically by the renderer.

Current mapped artwork: **128 cards**.

- `a-hundred-shields.png` → `a-hundred-shields.png`
- `a-volley-before-dawn.png` → `a-volley-before-dawn.png`
- `alda-keeper-of-the-ford.png` → `alda-keeper-of-the-ford.png`
- `all-banners-forward.png` → `all-banners-forward.png`
- `all-reserves-forward.png` → `all-reserves-forward.png`
- `arel.png` → `arel.png`
- `asha-the-shield-bearer.png` → `asha-the-shield-bearer.png`
- `avaros-the-bronze-king.png` → `avaros-the-bronze-king.png`
- `before-sunset-the-ford-would-be-ours.png` → `before-sunset-the-ford-would-be-ours.png`
- `bind-the-wound.png` → `bind-the-wound.png`
- `blocked-the-road-for.png` → `blocked-the-road-for.png`
- `bought-time-for.png` → `bought-time-for.png`
- `brannoc.png` → `brannoc.png`
- `carried-messages-for.png` → `carried-messages-for.png`
- `carried-the-oath-of.png` → `carried-the-oath-of.png`
- `catch-your-breath.png` → `catch-your-breath.png`
- `corin-of-the-high-wall.png` → `corin-of-the-high-wall.png`
- `covered-the-withdrawal-of.png` → `covered-the-withdrawal-of.png`
- `doros-the-last-spear.png` → `doros-the-last-spear.png`
- `edrin.png` → `edrin.png`
- `eira.png` → `eira.png`
- `elian.png` → `elian.png`
- `endured-with.png` → `endured-with.png`
- `every-banner-turned-toward-them.png` → `every-banner-turned-toward-them.png`
- `every-bow-was-strung.png` → `every-bow-was-strung.png`
- `followed.png` → `followed.png`
- `fresh-orders.png` → `fresh-orders.png`
- `guarded.png` → `guarded.png`
- `had-been-ordered-forward.png` → `had-been-ordered-forward.png`
- `held-the-line-for.png` → `held-the-line-for.png`
- `iria.png` → `iria.png`
- `iven.png` → `iven.png`
- `kael-the-roadless.png` → `kael-the-roadless.png`
- `kept-pace-with.png` → `kept-pace-with.png`
- `kept-the-gate-for.png` → `kept-the-gate-for.png`
- `lysa-the-listener.png` → `lysa-the-listener.png`
- `maelin.png` → `maelin.png`
- `mara.png` → `mara.png`
- `marched-beneath-the-banner-of.png` → `marched-beneath-the-banner-of.png`
- `marched-with.png` → `marched-with.png`
- `meren.png` → `meren.png`
- `namar.png` → `namar.png`
- `nara-builder-of-walls.png` → `nara-builder-of-walls.png`
- `neris-the-ferryman.png` → `neris-the-ferryman.png`
- `no-one-would-be-first-to-leave.png` → `no-one-would-be-first-to-leave.png`
- `no-road-was-too-long.png` → `no-road-was-too-long.png`
- `no-step-back.png` → `no-step-back.png`
- `oren.png` → `oren.png`
- `rallied-behind.png` → `rallied-behind.png`
- `re-form-the-line.png` → `re-form-the-line.png`
- `rovan-the-gatebreaker.png` → `rovan-the-gatebreaker.png`
- `seized-the-standard-of.png` → `seized-the-standard-of.png`
- `sela.png` → `sela.png`
- `send-a-runner.png` → `send-a-runner.png`
- `serai-queen-of-crows.png` → `serai-queen-of-crows.png`
- `seven-black-ships.png` → `seven-black-ships.png`
- `shared-the-spoils-with.png` → `shared-the-spoils-with.png`
- `sorin.png` → `sorin.png`
- `stayed-behind-for.png` → `stayed-behind-for.png`
- `stood-fast-with.png` → `stood-fast-with.png`
- `supplied-by.png` → `supplied-by.png`
- `supported-by.png` → `supported-by.png`
- `swore-again-to.png` → `swore-again-to.png`
- `take-stock.png` → `take-stock.png`
- `tala.png` → `tala.png`
- `teren.png` → `teren.png`
- `the-aradai.png` → `the-aradai.png`
- `the-archers-were-ready.png` → `the-archers-were-ready.png`
- `the-ash-bowmen.png` → `the-ash-bowmen.png`
- `the-baggage-was-abandoned.png` → `the-baggage-was-abandoned.png`
- `the-banner-singers.png` → `the-banner-singers.png`
- `the-battle-had-chosen-them.png` → `the-battle-had-chosen-them.png`
- `the-battle-turned-east.png` → `the-battle-turned-east.png`
- `the-black-company.png` → `the-black-company.png`
- `the-center-must-hold.png` → `the-center-must-hold.png`
- `the-crow-archers.png` → `the-crow-archers.png`
- `the-crows-came-down.png` → `the-crows-came-down.png`
- `the-damar.png` → `the-damar.png`
- `the-dust-riders.png` → `the-dust-riders.png`
- `the-fifty-men.png` → `the-fifty-men.png`
- `the-first-spear.png` → `the-first-spear.png`
- `the-flank-was-refused.png` → `the-flank-was-refused.png`
- `the-grey-riders.png` → `the-grey-riders.png`
- `the-ground-was-held.png` → `the-ground-was-held.png`
- `the-house-of-reed.png` → `the-house-of-reed.png`
- `the-ilyri.png` → `the-ilyri.png`
- `the-iron-boars.png` → `the-iron-boars.png`
- `the-king-had-given-the-order.png` → `the-king-had-given-the-order.png`
- `the-kings-spears.png` → `the-kings-spears.png`
- `the-lantern-scouts.png` → `the-lantern-scouts.png`
- `the-late-banner.png` → `the-late-banner.png`
- `the-line-had-begun-to-move.png` → `the-line-had-begun-to-move.png`
- `the-line-was-baited.png` → `the-line-was-baited.png`
- `the-line-wheeled.png` → `the-line-wheeled.png`
- `the-lines-held.png` → `the-lines-held.png`
- `the-long-march.png` → `the-long-march.png`
- `the-muster-was-false.png` → `the-muster-was-false.png`
- `the-old-guard.png` → `the-old-guard.png`
- `the-raiders-came-home-loaded.png` → `the-raiders-came-home-loaded.png`
- `the-red-duelists.png` → `the-red-duelists.png`
- `the-red-shields.png` → `the-red-shields.png`
- `the-river-raiders.png` → `the-river-raiders.png`
- `the-salt-road-fleet.png` → `the-salt-road-fleet.png`
- `the-scouts-found-the-gap.png` → `the-scouts-found-the-gap.png`
- `the-scouts-had-warned-them.png` → `the-scouts-had-warned-them.png`
- `the-serekh.png` → `the-serekh.png`
- `the-stores-were-taken.png` → `the-stores-were-taken.png`
- `the-thornbow-hunters.png` → `the-thornbow-hunters.png`
- `the-trap-closed.png` → `the-trap-closed.png`
- `the-unnamed-host.png` → `the-unnamed-host.png`
- `the-vardai.png` → `the-vardai.png`
- `the-wall-did-not-break.png` → `the-wall-did-not-break.png`
- `the-watchtowers-of-eren.png` → `the-watchtowers-of-eren.png`
- `the-white-hands-of-elara.png` → `the-white-hands-of-elara.png`
- `there-was-no-road-back.png` → `there-was-no-road-back.png`
- `they-had-gone-too-far.png` → `they-had-gone-too-far.png`
- `they-knew-the-ground.png` → `they-knew-the-ground.png`
- `they-let-them-through.png` → `they-let-them-through.png`
- `they-lived-to-tell-it.png` → `they-lived-to-tell-it.png`
- `they-returned-with-names.png` → `they-returned-with-names.png`
- `they-were-gathering-there.png` → `they-were-gathering-there.png`
- `thirty-spears.png` → `thirty-spears.png`
- `torren.png` → `torren.png`
- `tovan-the-quartermaster.png` → `tovan-the-quartermaster.png`
- `trusted.png` → `trusted.png`
- `veyra-keeper-of-oaths.png` → `veyra-keeper-of-oaths.png`
- `watched-the-skies-for.png` → `watched-the-skies-for.png`
- `yara-the-chronicler.png` → `yara-the-chronicler.png`

Cards without a matching per-card image continue to use the appropriate family fallback.
