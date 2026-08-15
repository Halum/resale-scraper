#!/usr/bin/env python3
"""Sanity-check combined_results.json (the DB export -- Kleinanzeigen + Vinted,
whichever script last ran):
  - every kept row has a brand (Anker/Ugreen/Baseus)
  - every MATCH row's watt is actually in WANT_WATT
  - no row's title trips BAD when re-checked title-only
  - prices are within [MIN_PRICE, MAX_PRICE]
  - no MAYBE row's title states a qualifying watt we should've caught outright
Exits non-zero with a printed reason on first violation.

Run: python3 validate.py
"""
import json, sys, pathlib
from kleinanzeigen import WANT_WATT, MIN_PRICE, MAX_PRICE, BAD, WATT

path = pathlib.Path(__file__).with_name("combined_results.json")
data = json.loads(path.read_text())

errors = []

for bucket, rows in data.items():
    for price, watt, brand, title, href, date in rows:
        if not (MIN_PRICE <= price <= MAX_PRICE):
            errors.append(f"[{bucket}] price {price} out of range: {title}")
        if not brand:
            errors.append(f"[{bucket}] no brand on kept row: {title}")
        if bucket == "match" and watt not in WANT_WATT:
            errors.append(f"[match] watt {watt} not in WANT_WATT: {title}")
        if BAD.search(title):
            errors.append(f"[{bucket}] title trips BAD filter but was kept: {title}")
        if bucket == "maybe":
            title_watts = [int(w) for w in WATT.findall(title)]
            if any(w in WANT_WATT for w in title_watts):
                errors.append(f"[maybe] title states watt {title_watts} we should've caught: {title}")

if errors:
    print(f"FAIL — {len(errors)} problem(s):")
    for e in errors[:30]:
        print(" -", e)
    sys.exit(1)

print(f"OK — match={len(data['match'])} maybe={len(data['maybe'])}, all invariants hold.")
