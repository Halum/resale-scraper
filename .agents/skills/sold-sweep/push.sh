#!/usr/bin/env bash
# push.sh [--dry] <group>... : write those groups' sold/live results to the
# scraper host's DBs. Backs the product DBs up once per day before writing.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
W="${SOLD_SWEEP_DIR:-$HOME/.cache/sold-sweep}"
COMMIT=--commit
if [ "${1:-}" = "--dry" ]; then COMMIT=; shift; fi
python3 - "$W" "$@" <<'EOF'
import json, sqlite3, sys
w, rows = sys.argv[1], []
for g in sys.argv[2:]:
    rows += sqlite3.connect(f"{w}/{g}.db").execute(
        "SELECT id, products, status, checked_at FROM results WHERE status IN ('sold','live')").fetchall()
json.dump(rows, open(f"{w}/payload.json", "w"))
print("ads", len(rows), "sold", sum(r[2] == "sold" for r in rows))
EOF
scp -q "$HERE/apply.py" "$W/payload.json" scraper:/tmp/
ssh scraper "B=/tmp/sold-sweep-bak-\$(date +%F); if [ -n '$COMMIT' ] && [ ! -d \$B ]; then mkdir \$B && for d in /opt/scraper/products/*/hunt.db; do cp \$d \$B/\$(basename \$(dirname \$d)).db; done && echo backup \$B; fi; python3 /tmp/apply.py /tmp/payload.json $COMMIT"
