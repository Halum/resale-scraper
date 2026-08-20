#!/usr/bin/env bash
# Cron entry point -- Kleinanzeigen only. See run_all_vinted.sh for Vinted,
# which runs on its own lower-frequency schedule (fragile session, needs a
# Cloudflare re-solve before each product).
set -uo pipefail
cd "$(dirname "$0")/.."

# FLARESOLVERR_URL / NOTIFY_WEBHOOK_URL live here, not in source -- see
# .env.example. Deployed by the GitHub Actions runner from the ENV_FILE
# secret; optional so a host without it yet doesn't fail the whole batch.
if [ -f .env ]; then set -a; . ./.env; set +a; fi

mkdir -p logs
LOG="logs/run-$(date +%F-%H%M).log"

# Keep only the last 30 days of logs (both platforms land here, plus the
# sold-ad sweep's own log dir) -- run once per invocation, cheap, no cron
# entry of its own needed.
find logs -name '*.log' -mtime +30 -delete
find /var/log/scraper -name '*.log' -mtime +30 -delete 2>/dev/null

# Hard wall-clock cap per product -- a stuck HTTP call still has a real
# socket timeout (see common/fetch.py), this is the coarser outer backstop.
PRODUCT_TIMEOUT="45m"

# Cron fires at exact clock ticks, which is itself a bot signature -- jitter
# the actual start time so request timestamps vary day to day.
sleep $((RANDOM % 1800))

FAILURES=()
{
  for product in macbook charger macbookm4 m2 m3 m5 router ipad; do
    echo "== $(date +%T) $product/kleinanzeigen =="
    (cd "products/$product" && timeout -k 30 "$PRODUCT_TIMEOUT" uv run python kleinanzeigen.py)
    rc=$?
    if [ $rc -eq 124 ]; then
      echo "[$product] kleinanzeigen TIMED OUT after $PRODUCT_TIMEOUT -- killed"
      FAILURES+=("$product: kleinanzeigen timed out after $PRODUCT_TIMEOUT")
    elif [ $rc -ne 0 ]; then
      echo "[$product] kleinanzeigen FAILED rc=$rc (see traceback above)"
      FAILURES+=("$product: kleinanzeigen failed rc=$rc")
    fi
  done
} >> "$LOG" 2>&1

# Failures always alert regardless of per-product notify config -- a scrape
# that silently stopped running is worse than a muted product's normal hits.
if [ ${#FAILURES[@]} -gt 0 ]; then
  uv run python -c "
from common.notify import send_lines
import sys
send_lines(sys.argv[1:], header='<b>Scrape failures:</b>')
" "${FAILURES[@]}"
fi

echo "run complete, log: $LOG"
