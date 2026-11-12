---
name: sold-sweep
description: Monthly catch-up for the sold-ad backlog. Opens every not-yet-sold Kleinanzeigen ad in the Orca browser via parallel Haiku agents (one tab and one local SQLite file each), then marks the sold, reserved and deleted ones sold on the scraper host's DBs. Use when Sajjad says "sold sweep", "clear the sold pileup", "check what's sold", or runs it monthly.
---

The daily `common/check_sold.py` only gets through 400 ads a day, so sold ads pile up. This skill clears the pile from the Mac. All scripts are in this folder (call it `S`); run data goes to `$SOLD_SWEEP_DIR` (default `~/.cache/sold-sweep`, call it `W`).

1. **Scope.** Ask which products (default: all MacBook DBs `macbook,macbookm4,m2,m3,m5`; any product DB works, every Kleinanzeigen ad page has the same markup) and whether to narrow by a title word (e.g. `max`). Then `python3 S/fetch.py --products ... [--like max]`. One sweep is at most 500 ads (`--limit`), so at most 5 agents: never launch more, Kleinanzeigen blocks the IP range when too many tabs run in parallel. It skips ads checked in the last 7 days (`--skip-days`, so ads a sweep just found live are not re-checked), takes the least-recently-checked ads first, dedupes ads that sit in several DBs, writes groups `G1..G5` of 100 to `W` (wiping the previous run) and prints how many are left. If ads are left after the pushes, tell Sajjad and run another sweep only when he says so.
2. **Launch** one agent per group, all at once: `model: haiku`, `effort: high`, `subagent_type: general-purpose`, background. Prompt (swap `Gk` and the absolute paths):

   > Check whether Kleinanzeigen ads are sold using your OWN Orca tab. Group Gk. Bash only, absolute paths. (1) `orca tab create --url about:blank --json`, keep `result.browserPageId` as PAGE. Never `orca tab switch`, never touch another tab, every orca command gets `--page PAGE`. (2) Until DONE, one ad per Bash call, no loops: `python3 S/check.py Gk next` gives an id or DONE; `python3 S/check.py Gk PAGE <id>` records it. Don't judge or edit anything. On TAB_OR_NAV_FAILED make a new tab and retry once, then stop. Stop on 2 unknowns in a row mentioning a captcha/challenge, or the same id 3 times. (3) `orca tab close --page PAGE --json`. (4) Reply only: PAGE, number checked, counts per status, unknown/error ids.

   Measured 2026-11-11: about 13 s and 0.4k tokens per ad, a 100-ad agent about 22 min and 95k tokens. On 2026-11-12, 10 tabs at a fixed 4 s pace got the IP range blocked within 8 ads ("IP-Bereich vorübergehend gesperrt", blank title, recorded as unknown), so `check.py` now waits a random 5 to 10 s per ad and a sweep is capped at 5 agents.
3. **Spot check 10 ads yourself** before the first push: a mix of sold (Gelöscht, Reserviert, removed) and live from the group DBs, opened in your own tab and read from the visible page text (`document.body.innerText`, `#viewad-title`), not from `check.py`. Any mismatch: stop and tell Sajjad.
4. **Push each group as soon as its agent finishes**, don't wait for the rest: `bash S/push.sh Gk` (`--dry` first if unsure). It backs the server DBs up once a day to `/tmp/sold-sweep-bak-<date>`, then writes `sold/sold_at/checked_at` (live: `checked_at` only) to every DB holding the ad. Re-running is harmless: already-sold rows are skipped.
5. **Report** a table per group (checked, sold, live) and what the pushes wrote. Agents' own counts are sometimes off; take numbers from `W/Gk.db`.

Unknown/error rows are never pushed; `next` hands them out again on a re-run. Vinted ads are out of scope (no proven sold marker).
