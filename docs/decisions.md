# Decisions

## robotvac product

- Scope: used lidar robot vacuums from Roborock, Dreame and Xiaomi (incl. Mijia), 15-60 €, Kleinanzeigen and Vinted. Models live in `products/robotvac/config.json`.
- Models older than the Dreame D9 generation are excluded (Roborock S5, S5 Max, S50, S55, S6, S6 Pure, Xiaomi 1S), as are the Dreame D9 family, gyro/camera budget models (Xiaomi E-series, T12, Roborock E4/E5, Lefant), the Roborock Q7 M5, the Xiaomi Mop P and Mop Pro (2,100 Pa, 3,200 mAh, weaker than the D9 Pro Sajjad owns), and the Dreame D10 and D10 Plus (same 4,000 Pa as the D9 Pro; their only gain is a self-emptying station).
- The deals skill passes only models that clearly beat the D9 Pro: more suction (above 4,000 Pa), better mopping (sonic or rotating mop, mop-washing station) or camera obstacle avoidance. A self-emptying station alone is not enough; Sajjad empties the bin by hand.
- The deals skill passes only fully working units: any named defect fails, even one small part (a leaking water tank, a broken mop), never "buy a new part and it works".
- Working units only: defekt/Bastler/Ersatzteil/wanted ads skip, and an accessory word anywhere in the title skips the listing unless it follows mit/inkl/und/+/plus.
- Search by brand, not by model: Kleinanzeigen queries `<brand> saugroboter`, Vinted bare brand queries (Vinted wants every query word in the title). `classify_vinted` falls back to the card's `marke:` text when the title has no brand. No Vinted brand ids yet.
- robotvac runs first in both run loops, so the fastest-selling target is fetched first.
- Alerts are on since the first server run recorded the existing listings on 2026-11-06 (agent-made, 2026-11-06), so only listings that appear after that run are sent. Turning alerts on before that run would have sent the whole backlog, which Telegram's 4096-character limit splits into several messages.
- Vinted alerts for robotvac are off (`vinted.notify: false`, agent-made on Sajjad's request, 2026-11-06): the first Vinted run's matches were mostly French, Italian and Dutch spare-part listings that the German accessory words miss. Vinted is still scraped into the viewer. Turn alerts back on once the filter knows those part words.
- The viewer returns empty rows for a product whose `hunt.db` does not exist yet and never creates the file (the viewer runs as root; a root-owned db would block the scraper user).
- Branching: this repo has only `main` (push deploys). Features branch from `main` and merge back with `--no-ff`.
