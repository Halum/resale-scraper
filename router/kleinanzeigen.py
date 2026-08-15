#!/usr/bin/env python3
"""Kleinanzeigen Xiaomi/Mi/Redmi AX1800+AX3000 router hunter. classify()/
combos() live in spec.py; the scrape loop, fetching, DB and export are
common/kleinanzeigen_engine.py.

Run:  uv run python kleinanzeigen.py [--all] [--test]
  --all   reclassify every ad ever seen (INSERT OR REPLACE), not just new ones
  --test  tiny run: 2 combos, 1 page each -- for verifying changes quickly
"""
import sys, pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from common.kleinanzeigen_engine import run  # noqa: E402
import spec  # noqa: E402

HERE = pathlib.Path(__file__).parent

if __name__ == "__main__":
    run(here=HERE, cfg=spec.CFG, min_price=spec.MIN_PRICE, max_price=spec.MAX_PRICE,
        cat=spec.CAT, classify=spec.classify, combos=spec.combos, spec_suffix="")
