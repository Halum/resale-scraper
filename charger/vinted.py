#!/usr/bin/env python3
"""Vinted charger hunter. Uses spec.py's Vinted-specific classify_vinted()/
combos_vinted() (no brand-in-title check -- native brand_ids already
guarantees brand). Scrape loop is common/vinted_engine.py.

Run:  uv run python vinted.py [--all] [--test]
"""
import sys, pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from common.vinted_engine import run  # noqa: E402
import spec  # noqa: E402

HERE = pathlib.Path(__file__).parent

if __name__ == "__main__":
    run(here=HERE, cfg=spec.CFG, min_price=spec.MIN_PRICE, max_price=spec.MAX_PRICE,
        classify=spec.classify_vinted, combos=spec.combos_vinted, extra_qs=spec.VINTED_EXTRA_QS, spec_suffix="W")
