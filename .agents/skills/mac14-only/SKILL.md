---
name: mac14-only
description: Tag every MacBook listing (across all product DBs on the scraper host) with its screen size in meta.screen_in, judged by reading titles (no regex). Does NOT hide anything -- the viewer's screen-size filter chips handle showing/hiding. Use when asked to tag/classify screen sizes, or when new MacBook listings are showing up without a screen-size tag in the viewer.
---

No regex, no keyword matching. Read every title yourself and reason about screen size.

Rules of thumb:
- MacBook Pro comes in 14" and 16" -- explicit "16"/16 Zoll/16 inch/16 pollici, or bare "16" with no unit (e.g. "MacBook Pro M4 16 48gb 1TB") -> 16. Explicit 14 (14"/14 Zoll/bare "14") -> 14.
- MacBook Air comes in 13" and 15" only -- never 14". Tag 13 or 15 per the stated size.
- Bare "MacBook Pro"/"MacBook Air" with no size mentioned at all, or a chip that ships in multiple sizes with nothing else to go on: genuinely ambiguous, leave untagged (don't guess) -- it'll show up again next run, no harm.
- Non-MacBook items (Mac Mini, Mac Studio, iMac, Mac Pro) have no screen size -- leave untagged.
- Chargers/routers: not in scope, `fetch_titles.sh` doesn't include them.

Steps:

1. `bash .claude/skills/mac14-only/fetch_titles.sh` -- lists every `<product> <id> <title>` across macbook/macbookm4/m2/m3/m5 still missing `meta.screen_in`.
2. Read the full list. For each title, decide 14/15/16/13 or leave untagged.
3. For each product with judged ids, run `bash .claude/skills/mac14-only/tag_screen.sh <product> <id>:<size> [<id>:<size> ...]` -- one call per product, all its judged ids in one go (e.g. `tag_screen.sh macbookm4 3363613834:15 3446321251:14`).
4. Report counts tagged per product, and how many were left ambiguous.

Idempotent -- re-tagging an already-tagged id just overwrites with the same value.
