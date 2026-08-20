# Resale Scraper

Scrapes Kleinanzeigen + Vinted for underpriced Apple Silicon MacBooks (M1-M5, all tiers) + USB-C GaN chargers (Anker/Ugreen/Baseus) + Xiaomi/Mi/Redmi routers (AX1800/AX3000). Hits stored in per-product SQLite DB. Single static HTML page serves it, sortable/filterable tables + price-trend chart.

## How it works

Each **product** (`products/macbook/`, `products/macbookm4/`, `products/m2/`, `products/m3/`, `products/m5/`, `products/charger/`, `products/router/`, `products/ipad/`) = folder with:

- `config.json` — price range, RAM/wattage targets, chip/brand list, fallback queries, per-platform search params.
- `spec.py` — only product-specific logic. `classify(ad) -> (verdict, spec_num, spec_label, reason)` + `combos() -> [search queries]` for Kleinanzeigen. Vinted's own search wants every query word to roughly match the title, so a keyword that's fine for Kleinanzeigen (e.g. "router") can silently miss listings titled differently ("mesh system", or the same word in another language). Every product except the MacBook family defines a separate, usually narrower `combos_vinted()` (see `products/charger/spec.py`, `products/router/spec.py`) passed to `vinted.py` instead of the Kleinanzeigen `combos`.
- `kleinanzeigen.py` / `vinted.py` — ~15-line wrappers, import `spec`, call shared engine.

Actual scraping (fetching, pacing, pagination, DB upsert) lives in `common/kleinanzeigen_engine.py` / `common/vinted_engine.py`. Both fetch pages through `common/fetch.py` (FlareSolverr) and parse the returned HTML with `common/parse.py` (stdlib `re`, no browser, no DOM library). New product = config.json + spec.py + two wrappers, no duplicated logic.

### Adding a new product

1. Copy closest existing product folder (e.g. `products/m5/` for another any-chip-variant floor-price scout).
2. Adjust `config.json` (price range, RAM/watt targets, chips/brands, fallback queries).
3. Adjust regexes + `classify()`/`combos()` in `spec.py`.
4. Add `DBS` entry in `deploy/viewer_server.py`.
5. Add tab + panel + `renderPaged(...)` call in `frontend/index.html`.
6. Add product to loop in `deploy/run_all.sh`.

## Running

Set `FLARESOLVERR_URL` (and optionally `NOTIFY_WEBHOOK_URL`) — see `.env.example`.

```bash
cd products/<product>
uv run python kleinanzeigen.py --test   # 1-2 queries, quick check
uv run python kleinanzeigen.py           # full combo sweep
uv run python vinted.py [--test]
```

`--all` re-classifies every ad already in DB instead of skipping seen ids (only matters if `spec.py` classify logic changed). `--force` runs a platform even while it's off in `global_config.json` — for testing one product without flipping the switch for everyone.

Writes straight to `hunt.db` (SQLite) — no export/build step. Viewer reads live off that DB on every page load.

## Config

- **`products/<product>/config.json`** — per-product tuning, see above.
- **`global_config.json`** (repo root) — `{"kleinanzeigen": {"enabled": bool}, "vinted": {"enabled": bool}}`. Kills a platform everywhere at once (e.g. platform starts challenging requests), no cron/code touch needed. Checked by `common/skipflag.py`.

## Notifications

Telegram alerts route through one external n8n workflow ("Scraper Alert" — not tracked in this repo, id `tgJMeexLDiMG8cag`), which is a dumb `Webhook -> Telegram` pass-through: it forwards `{{ $json.body.text }}` verbatim to one hardcoded chat, no per-product filtering, no branching. All muting/routing logic lives in this repo, not in n8n:

- `common/notify.py`'s `send_lines()` (and `notify_hits()`, which calls it) POST to `NOTIFY_WEBHOOK_URL` (n8n's webhook, set in `.env`).
- Each `products/<product>/config.json` may set `"notify": false` to mute that product's hit alerts — checked in `common/kleinanzeigen_engine.py` / `common/vinted_engine.py` before calling `notify_hits()`, and in `common/check_sold.py` before the sold summary. Defaults to `true` when the key is absent.
- `deploy/run_all.sh` / `run_all_vinted.sh` send a failure alert (product timed out or exited non-zero) regardless of the per-product `notify` flag — a silently-dead scrape should never be muted.

If a product's alerts look wrong, check its `config.json`'s `notify` key first — n8n has no logic to inspect.

## Fetching

Both platforms are fetched through [FlareSolverr](https://github.com/FlareSolverr/FlareSolverr) (`common/fetch.py`, endpoint from `FLARESOLVERR_URL`) rather than a local browser — Kleinanzeigen's fingerprint check and Vinted's Cloudflare challenge are both handled on FlareSolverr's side. The scraper host itself runs no Chrome/patchright. Listing cards, prices, and the sold/reserved badge are all parsed out of the returned static HTML with stdlib regex (`common/parse.py`) — see that file's tests for the exact markup each parser depends on.

## Viewer

`deploy/viewer_server.py` — static file server (rooted at `frontend/`) + two API routes: `GET /api/results/<product>` (live DB query, what `frontend/index.html` fetches on load) and `POST /api/hide` (marks an ad `hidden`, not deleted — stays excluded from future dupe-seen checks). `frontend/index.html` = whole frontend, vanilla JS, no build step, no deps. Includes:

- Per-tab sortable/paginated tables, one per product.
- Chip/brand + RAM/wattage toggle filters (cookie-persisted, All/None bulk buttons).
- **Trends** tab — lowest observed price per generation (M1-M5), filterable by chip tier + RAM bucket, one line per (tier, RAM) pair, hover/click through to the actual listing.
- Active-tab + filter-state cookie persistence across loads.
- Skip button asks for confirmation before hiding an ad.

## Scheduling

`deploy/run_all.sh` — Kleinanzeigen, every product, sequential (one request at a time, deliberately not parallel by default, keeps request volume low), randomized startup delay so requests don't land on exact bot-like clock tick. Five times daily via cron (`deploy/crontab`, currently 8am/12pm/4pm/8pm/11pm Berlin time).

`deploy/run_all_vinted.sh` — Vinted, its own lower-frequency schedule (10:30am/10:30pm), offset from Kleinanzeigen's slots so both platforms never fire in the same burst. A scrape dying mid-run (e.g. FlareSolverr unreachable) keeps whatever was already found instead of losing the whole run — see `common/vinted_engine.py`'s `collect_flaresolverr()`.

One-time host setup: `deploy/provision.sh`.

`common/check_sold.py` — separate daily cron job (6am), sweeps every non-hidden Kleinanzeigen ad, hides ones that turned out sold/reserved/ deleted, sends one combined Telegram summary. Kleinanzeigen-only — Vinted has no equivalent sold-detection yet.
