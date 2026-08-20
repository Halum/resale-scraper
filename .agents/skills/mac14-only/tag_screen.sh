#!/usr/bin/env bash
# Set meta.screen_in for specific ad ids in a specific product's DB.
# Usage: tag_screen.sh <product> <id>:<size> [<id>:<size> ...]
# e.g. tag_screen.sh macbookm4 3363613834:15 3446321251:14
# Merges into any existing meta JSON, same shape common/store.py's
# set_meta() writes. Never touches bucket -- purely informational, the
# viewer's screen-size toggle does the actual filtering.
set -euo pipefail

product="$1"; shift
pairs_py=$(printf "'%s'," "$@")

ssh scraper "cd /opt/scraper/products/$product && python3 -c \"
import sqlite3, json
pairs = [$pairs_py]
conn = sqlite3.connect('hunt.db')
n = 0
for pair in pairs:
    ad_id, size = pair.split(':')
    row = conn.execute('SELECT meta FROM ads WHERE id=?', (ad_id,)).fetchone()
    if row is None:
        print('  ! not found:', ad_id)
        continue
    meta = json.loads(row[0]) if row[0] else {}
    meta['screen_in'] = int(size)
    conn.execute('UPDATE ads SET meta=? WHERE id=?', (json.dumps(meta), ad_id))
    n += 1
conn.commit()
print('$product tagged', n)
\""
