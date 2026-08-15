"""Shared logging setup -- one standard timestamped format for every scraper
log line, so run_all.sh's per-run log files stay grep/correlate-able across
products and platforms instead of each module inventing its own print shape.
"""
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("scraper")
