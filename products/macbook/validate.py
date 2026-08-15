#!/usr/bin/env python3
"""Sanity-check combined_results.json (the DB export -- Kleinanzeigen + Vinted,
whichever script last ran) against the invariants that broke before:
  - every MATCH row has an Apple Silicon Pro/Max/Ultra chip (no Intel slipping in)
  - every MATCH row's RAM is actually in WANT_RAM
  - every MAYBE row has a chip too (Pro/Max/Ultra), just no RAM stated
  - the known-missed regression ad is present
  - no row's title trips BAD when re-checked title-only
  - no row's title mentions 16-inch (14" only)
  - prices are within [MIN_PRICE, MAX_PRICE]
Exits non-zero with a printed reason on first violation.

Run: python3 validate.py
"""
import json, sys, pathlib
from kleinanzeigen import WANT_RAM, MIN_PRICE, MAX_PRICE, BAD, CHIP, RAM, SIZE16

KNOWN_MISSED = {"3469841101"}  # regression check from user reports

path = pathlib.Path(__file__).with_name("combined_results.json")
data = json.loads(path.read_text())

errors = []

for bucket, rows in data.items():
    for price, ram, chip, title, href, date in rows:
        if not (MIN_PRICE <= price <= MAX_PRICE):
            errors.append(f"[{bucket}] price {price} out of range: {title}")
        if not chip:
            errors.append(f"[{bucket}] no chip on kept row: {title}")
        elif not any(v in chip for v in ("Pro", "Max", "Ultra")):
            errors.append(f"[{bucket}] chip '{chip}' not Pro/Max/Ultra: {title}")
        if bucket == "match" and ram not in WANT_RAM:
            errors.append(f"[match] ram {ram} not in WANT_RAM: {title}")
        if BAD.search(title):
            errors.append(f"[{bucket}] title trips BAD filter but was kept: {title}")
        if SIZE16.search(title):
            errors.append(f"[{bucket}] 16-inch title slipped through: {title}")
        if bucket == "maybe":
            title_rams = [int(g) for pair in RAM.findall(title) for g in pair if g]
            if any(r in WANT_RAM for r in title_rams):
                errors.append(f"[maybe] title states RAM {title_rams} we should've caught: {title}")

all_ids = {href.rstrip("/").split("/")[-1].split("-")[0] for rows in data.values() for *_, href, _ in rows}
missing = KNOWN_MISSED - all_ids
if missing:
    errors.append(f"regression: known-good ad IDs still missing: {missing}")

if errors:
    print(f"FAIL — {len(errors)} problem(s):")
    for e in errors[:30]:
        print(" -", e)
    sys.exit(1)

print(f"OK — match={len(data['match'])} maybe={len(data['maybe'])}, all invariants hold, regression ad present.")
