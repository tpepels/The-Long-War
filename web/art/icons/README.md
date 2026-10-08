# The Long War — generated PNG icon candidates

These ten transparent PNGs are **proposed replacements** for existing inline SVG icons. They are not wired into the game or physical cards and do **not** change hand-tuned card layouts. Do not remove `web/card-symbols.js` yet.

## Mapping

| Candidate | Current SVG role | Source |
|---|---|---|
| `force.png` | Type: `force` | Heraldic shield |
| `bond.png` | Type: `bond` | Interlocking chain |
| `name.png` | Type: `name` | Battle standard |
| `action.png` | Utility/timing: `action` | Forward arrow |
| `reaction.png` | Utility/timing: `reaction` | Circular arrows |
| `archer.png` | Classification: `archer` | Bow and arrow |
| `guard.png` | Classification: `guard` | Layered defensive shield |
| `rider.png` | Classification: `rider` | Horse and lance |
| `skirmisher.png` | Classification: `skirmisher` | Crossed blades |
| `raider.png` | Classification: `raider` | Torch and crossed sabers |

Each original is 1254×1254 RGBA at the root of this directory. The `sizes/` subdirectories contain downscaled transparent PNGs at 16, 24, 32, 48, 64, 128, 256, and 512 pixels. All files were resized with a high-quality Lanczos filter. The very smallest sizes require visual evaluation: heraldic details may merge when printed as tiny classification symbols.

Generated images are not proof of print-readability. Some subjects (notably Force and Guard) have similar outlines and may need simplifying after inspection. Uploading these files only provides source assets; it does not automatically replace the inline SVG markup or change GitHub Pages rendering.
