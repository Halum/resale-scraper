#!/usr/bin/env bash
# List every MacBook-family ad (product, id, title) still missing screen-size
# meta, across macbook/macbookm4/m2/m3/m5 DBs on the scraper host. Pure fetch,
# no classification -- the agent reads the titles and judges screen size by
# reasoning, then calls tag_screen.sh.
set -euo pipefail

ssh scraper "cd /opt/scraper && python3 -c \"
import sqlite3
for p in ('macbook','macbookm4','m2','m3','m5'):
    conn = sqlite3.connect(f'{p}/hunt.db')
    rows = conn.execute(\\\"SELECT id, title FROM ads WHERE meta IS NULL OR json_extract(meta, '\$.screen_in') IS NULL\\\").fetchall()
    for i, t in rows:
        print(p, i, t)
    conn.close()
\""
