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

Per-card artwork is named by canonical V2 card ID and lives in `web/art/v2/cards/`. The filename is the mapping: a newly added `<card-id>.png` must be included in the renderer's `CARD_ART` manifest.

Current mapped artwork: **67 cards**.

- `a-hundred-shields.png` → `a-hundred-shields`
- `a-volley-before-dawn.png` → `a-volley-before-dawn`
- `arel.png` → `arel`
- `asha-the-shield-bearer.png` → `asha-the-shield-bearer`
- `avaros-the-bronze-king.png` → `avaros-the-bronze-king`
- `blocked-the-road-for.png` → `blocked-the-road-for`
- `brannoc.png` → `brannoc`
- `carried-messages-for.png` → `carried-messages-for`
- `corin-of-the-high-wall.png` → `corin-of-the-high-wall`
- `covered-the-withdrawal-of.png` → `covered-the-withdrawal-of`
- `doros-the-last-spear.png` → `doros-the-last-spear`
- `edrin.png` → `edrin`
- `eira.png` → `eira`
- `elian.png` → `elian`
- `every-bow-was-strung.png` → `every-bow-was-strung`
- `followed.png` → `followed`
- `guarded.png` → `guarded`
- `iria.png` → `iria`
- `iven.png` → `iven`
- `kael-the-roadless.png` → `kael-the-roadless`
- `kept-pace-with.png` → `kept-pace-with`
- `kept-the-gate-for.png` → `kept-the-gate-for`
- `lysa-the-listener.png` → `lysa-the-listener`
- `maelin.png` → `maelin`
- `mara.png` → `mara`
- `marched-with.png` → `marched-with`
- `meren.png` → `meren`
- `namar.png` → `namar`
- `oren.png` → `oren`
- `rovan-the-gatebreaker.png` → `rovan-the-gatebreaker`
- `sela.png` → `sela`
- `serai-queen-of-crows.png` → `serai-queen-of-crows`
- `shared-the-spoils-with.png` → `shared-the-spoils-with`
- `sorin.png` → `sorin`
- `stood-fast-with.png` → `stood-fast-with`
- `tala.png` → `tala`
- `teren.png` → `teren`
- `the-aradai.png` → `the-aradai`
- `the-archers-were-ready.png` → `the-archers-were-ready`
- `the-ash-bowmen.png` → `the-ash-bowmen`
- `the-banner-singers.png` → `the-banner-singers`
- `the-center-must-hold.png` → `the-center-must-hold`
- `the-crow-archers.png` → `the-crow-archers`
- `the-damar.png` → `the-damar`
- `the-fifty-men.png` → `the-fifty-men`
- `the-ilyri.png` → `the-ilyri`
- `the-kings-spears.png` → `the-kings-spears`
- `the-lantern-scouts.png` → `the-lantern-scouts`
- `the-late-banner.png` → `the-late-banner`
- `the-line-was-baited.png` → `the-line-was-baited`
- `the-raiders-came-home-loaded.png` → `the-raiders-came-home-loaded`
- `the-river-raiders.png` → `the-river-raiders`
- `the-salt-road-fleet.png` → `the-salt-road-fleet`
- `the-scouts-found-the-gap.png` → `the-scouts-found-the-gap`
- `the-scouts-had-warned-them.png` → `the-scouts-had-warned-them`
- `the-serekh.png` → `the-serekh`
- `the-stores-were-taken.png` → `the-stores-were-taken`
- `the-thornbow-hunters.png` → `the-thornbow-hunters`
- `the-trap-closed.png` → `the-trap-closed`
- `the-unnamed-host.png` → `the-unnamed-host`
- `the-vardai.png` → `the-vardai`
- `the-watchtowers-of-eren.png` → `the-watchtowers-of-eren`
- `the-white-hands-of-elara.png` → `the-white-hands-of-elara`
- `they-knew-the-ground.png` → `they-knew-the-ground`
- `thirty-spears.png` → `thirty-spears`
- `torren.png` → `torren`
- `watched-the-skies-for.png` → `watched-the-skies-for`

Cards without a matching per-card image continue to use the appropriate family fallback.
