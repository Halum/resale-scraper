# Decisions

## robotvac product

- Scope: used lidar robot vacuums from Roborock, Dreame and Xiaomi (incl. Mijia), 15-60 €, Kleinanzeigen and Vinted. Models live in `products/robotvac/config.json`.
- Models older than the Dreame D9 generation are excluded (Roborock S5, S5 Max, S50, S55, S6, S6 Pure, Xiaomi 1S), as are the Dreame D9 family, gyro/camera budget models (Xiaomi E-series, T12, Roborock E4/E5, Lefant) and the Roborock Q7 M5.
- Working units only: defekt/Bastler/Ersatzteil/wanted ads skip, and an accessory word anywhere in the title skips the listing unless it follows mit/inkl/und/+/plus.
- Search by brand, not by model: Kleinanzeigen queries `<brand> saugroboter`, Vinted bare brand queries (Vinted wants every query word in the title). `classify_vinted` falls back to the card's `marke:` text when the title has no brand. No Vinted brand ids yet.
- robotvac runs first in both run loops, so the fastest-selling target is fetched first.
- Alerts start only after the first server run has recorded the existing listings (agent-made, 2026-11-06): the 2026-11-06 trial found 56 in-window hits, which Telegram's 4096-character limit would split into several messages. The existing listings are in the viewer tab.
- The viewer returns empty rows for a product whose `hunt.db` does not exist yet and never creates the file (the viewer runs as root; a root-owned db would block the scraper user).
- Branching: this repo has only `main` (push deploys). Features branch from `main` and merge back with `--no-ff`.
