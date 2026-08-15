# Redesign plan: title-gated combo search + human-like pacing

Status: awaiting green light. Nothing below is built yet.

## Why

Current design (broad per-brand query + regex over detail-page body/description)
has two confirmed bugs this session:

1. **Charger noise**: brand-only queries pull in every product line (headphones,
   powerbanks, docks, cables) since Anker/Ugreen/Baseus sell all of it. Fixed
   short-term with a `CHARGER_KW` gate, kept below, but the real fix is not
   querying that broadly in the first place.
2. **Macbook RAM misclassification**: `fetch_detail()` regexes the visible text
   of `#viewad-main` for a RAM number, but the ad's *actual* RAM is a separate
   structured "specifics" table (`RAM (GB): 16 GB`) that isn't reliably inside
   that scope, and isn't in the title either most of the time. Confirmed two
   real cases of ads showing 32GB in our data with no "32" anywhere in title
   or `#viewad-main` text.

Decision: stop guessing from prose. Only trust the ad's own title for the spec
number. If the title doesn't state it, skip the ad entirely — no more "maybe"
bucket, no detail-page regex-guessing.

## Core design

**Search-first narrowing, not scrape-then-filter.** Generate many specific
search-term combinations per product/platform, dedupe ad IDs across all of
them (`seen_ids` set), classify strictly from the SRP card's own title text,
and only open the detail page for ads that already passed the title check —
solely to grab the posted date.

No "maybe" bucket in the new design. An ad is either a title-confirmed match,
or it's skipped. This is a deliberate call: sellers who don't state basic
specs in the title aren't worth the back-and-forth.

## Config-driven, not hardcoded

One JSON per product: `macbook/config.json`, `charger/config.json`. Each has
a `kleinanzeigen` section and a `vinted` section, since the two platforms
support different filter capabilities (Vinted has native brand filtering,
Kleinanzeigen doesn't). Scripts become generic — combos, price bounds, and
brand filters live in the JSON, not in code, so tuning the hunt doesn't
require touching Python.

## Macbook

- **Chips**: M1, M1 Pro, M1 Max, M2, M2 Pro, M2 Max, M3, M3 Pro, M3 Max, M4,
  M4 Pro, M4 Max (12 total — no Ultra, doesn't ship in laptops).
- **RAM targets**: 32, 36, 48, 64 GB (existing `WANT_RAM`).
- **Combos**: chip × RAM → 48 search terms (e.g. `"macbook pro m1 pro 32gb"`),
  plus 2-3 broad fallback queries (e.g. `"macbook pro"`) to catch title
  phrasing the combos miss.
- **Price range**: 600€-1400€ (was unbounded on the low end before — cheap
  listings are noise/parts, not real machines).
- **Classify**: regex over `ad["title"]` only (not full card text, not
  description) for RAM number + chip name. No match in title → skip, no
  detail visit.
- **Detail visit**: only for title-confirmed ads, only to extract posted date.
  Never re-parsed for RAM/chip — removes the sidebar-leak bug class entirely,
  since spec data is never read from detail-page text again.
- **Sort**: Kleinanzeigen's default sort is already "Neueste" (newest first,
  `data-value="SORTING_DATE"`) as long as no location filter is set — no
  extra query param needed. Confirmed via a real search URL
  (`kleinanzeigen.de/s-65w-charger/k0`, no sort param, defaults to newest).

## Charger

- **Kleinanzeigen combos**: brand × watt × keyword, keywords cover both
  languages: `charger`, `ladegerät`, `netzteil` (e.g.
  `"anker 65w ladegerät"`, `"ugreen 67w charger"`). No native brand filter on
  this platform, so brand name must be in the query text itself.
- **Vinted combos**: native `brand_ids` filter
  (`304174`, `427512`, `369636` — Anker/Ugreen/Baseus, confirmed from a real
  filtered URL) **plus** search text combining watt + charger-keyword (e.g.
  `search_text="65w charger"`). Never search watt alone — confirmed today
  that a bare `"65w"` search pulls in cables/adapters rated for 65W, not just
  chargers.
- **Sort**: `order=newest_first` on Vinted (confirmed from a real URL).
  Kleinanzeigen: same default-newest behavior as macbook, no extra param.
- **Price range**: unchanged, 1€-20€.
- Existing `CHARGER_KW` gate and `skipped.json` negative-space logging
  (added this session) carry over as-is — still useful even with narrower
  searches, as a second line of defense and for tuning visibility.

## Anti-detection / pacing

Staying on sync patchright (no switch to `humanization-playwright`— it's
async-only, would force a rewrite of every script and `common/browser.py`,
and it's Alpha-stage/v0.1.2 which is a real risk for something running
unattended via cron). Instead, build the improvements directly on the
existing sync API:

1. **Mouse/scroll jitter**: before clicks/navigation, move the mouse via
   `pg.mouse.move()` in a few small jittered intermediate steps (cheap
   approximation of a Bezier path) rather than teleporting the cursor.
   Occasional `pg.mouse.wheel()` scroll on listing pages before scraping.
2. **Delay distribution**: replace flat `random.uniform(lo, hi)` in `pace()`
   with a right-skewed distribution (e.g. lognormal) — most delays short,
   occasional long tail, instead of a bounded flat range.
3. **Periodic "distraction" breaks**: small chance (tunable, start ~1-in-10)
   of a much longer pause (30-90s) between pages/ads, simulating a human
   getting distracted mid-session.
4. **Cron start jitter**: `run_all.sh` currently fires at exactly 08:00 and
   20:00 daily — add a random sleep (0-30 min) at the start of the script so
   the actual first request timestamp varies day to day.
5. **Per-action-type pacing**: different pause profiles for different actions
   — e.g. a longer "reading" pause after opening a detail page than between
   listing-page navigations, rather than one flat profile for the whole run.

## Data model impact

- No "maybe" bucket going forward — `hunt.db`'s `bucket` column only ever
  gets `"match"` from the new scripts. Existing historical `"maybe"` rows
  from the old design stay in the DB as-is (not retroactively purged unless
  asked) but nothing new writes to that bucket.
- Viewer (`index.html`) will need the "Maybe" table/section removed or hidden
  per-product once both hunters stop producing that bucket — not addressed
  in this plan yet, flagging as follow-up.

## Open items / assumptions to confirm before or during build

- Exact lognormal parameters and "distraction break" frequency/duration are
  starting guesses — will tune after a real test run, not treated as final.
- Old `"maybe"` rows sitting in `hunt.db` and the viewer's Maybe tables: leave
  alone for now, revisit once new design is live and validated.
- Will re-verify Kleinanzeigen's default-sort behavior holds across all combo
  queries (not just the one sample URL) during the test run.

## Execution order (once approved)

1. Write `macbook/config.json` and `charger/config.json`.
2. Add pacing/mouse-jitter helpers to `common/browser.py`.
3. Rewrite `macbook/kleinanzeigen.py` + `macbook/vinted.py` around combo
   generation, title-only classify, config-driven price bounds.
4. Rewrite `charger/kleinanzeigen.py` + `charger/vinted.py` around combo
   generation (brand×watt×keyword), Vinted brand-filter integration.
5. Sync to LXC, run a real test (not just syntax check) for each of the four
   scripts, verify counts/output look sane.
6. Report results, adjust based on what the test run shows.
