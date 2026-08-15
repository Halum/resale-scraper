#!/usr/bin/env python3
"""Kleinanzeigen MacBook Pro/Max M3 family price-floor scout. classify()/
combos() live in spec.py; the scrape loop, fetching, DB and export are
common/kleinanzeigen_engine.py.

Run:  uv run python kleinanzeigen.py [--all] [--test]
"""
import sys, pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))
from common.kleinanzeigen_engine import run  # noqa: E402
import spec  # noqa: E402

HERE = pathlib.Path(__file__).parent

if __name__ == "__main__":
    run(here=HERE, cfg=spec.CFG, min_price=spec.MIN_PRICE, max_price=spec.MAX_PRICE,
        cat=spec.CAT, classify=spec.classify, combos=spec.combos, spec_suffix="GB")
