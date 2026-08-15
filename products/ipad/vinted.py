#!/usr/bin/env python3
"""Vinted iPad Pro M1 hunter. Same classify()/combos() as kleinanzeigen.py
(spec.py) -- "iPad Pro" wording doesn't have the router-style language
mismatch, so no combos_vinted() needed. Scrape loop is common/vinted_engine.py.

Run:  uv run python vinted.py [--all] [--test]
"""
import sys, pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))
from common.vinted_engine import run  # noqa: E402
import spec  # noqa: E402

HERE = pathlib.Path(__file__).parent

if __name__ == "__main__":
    run(here=HERE, cfg=spec.CFG, min_price=spec.MIN_PRICE, max_price=spec.MAX_PRICE,
        classify=spec.classify, combos=spec.combos)
