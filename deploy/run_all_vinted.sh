#!/usr/bin/env bash
# Cron entry point -- Vinted only, on its own lower-frequency schedule
# (separate from run_all.sh's Kleinanzeigen cadence). Fetching goes through
# FlareSolverr (see common/fetch.py) -- no browser, no Cloudflare solve loop,
# no Xvfb/x11vnc needed here anymore.
set -uo pipefail
cd "$(dirname "$0")/.."

# FLARESOLVERR_URL / NOTIFY_WEBHOOK_URL live here, not in source -- see
# .env.example. Deployed by the GitHub Actions runner from the ENV_FILE
# secret; optional so a host without it yet doesn't fail the whole batch.
if [ -f .env ]; then set -a; . ./.env; set +a; fi

mkdir -p logs
LOG="logs/run-vinted-$(date +%F-%H%M).log"

# Hard wall-clock cap per product -- a stuck HTTP call still has a real
# socket timeout (see common/fetch.py), this is the coarser outer backstop.
PRODUCT_TIMEOUT="45m"

# Jitter start time, same reasoning as run_all.sh.
sleep $((RANDOM % 900))

FAILURES=()
{
  for product in macbook charger macbookm4 m2 m3 m5 router ipad; do
    echo "== $(date +%T) $product/vinted =="
    (cd "products/$product" && timeout -k 30 "$PRODUCT_TIMEOUT" uv run python vinted.py)
    rc=$?
    if [ $rc -eq 124 ]; then
      echo "[$product] vinted TIMED OUT after $PRODUCT_TIMEOUT -- killed"
      FAILURES+=("$product: vinted timed out after $PRODUCT_TIMEOUT")
    elif [ $rc -ne 0 ]; then
      echo "[$product] vinted FAILED rc=$rc (see traceback above)"
      FAILURES+=("$product: vinted failed rc=$rc")
    fi
  done
} >> "$LOG" 2>&1

# Failures always alert regardless of per-product notify config -- a scrape
# that silently stopped running is worse than a muted product's normal hits.
if [ ${#FAILURES[@]} -gt 0 ]; then
  uv run python -c "
from common.notify import send_lines
import sys
send_lines(sys.argv[1:], header='<b>Vinted scrape failures:</b>')
" "${FAILURES[@]}"
fi

echo "vinted run complete, log: $LOG"
