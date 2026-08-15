"""Classify/combos for Xiaomi/Mi/Redmi AX1800 + AX3000 routers, 5-25EUR.
Plugs into common/kleinanzeigen_engine.py + common/vinted_engine.py, which own
the actual scrape loop, browser setup, DB, and export.

classify() is shared, but combos() (Kleinanzeigen) and combos_vinted() differ --
Vinted's own search is stricter about matching every query word against the
title, so "brand keyword model" (e.g. "xiaomi router ax1800") misses listings
titled "mesh system"/"routeur"/"répéteur" that never say "router". Dropping
the keyword and searching just "brand model" lets Vinted's own relevance
surface those; classify() below still filters the results.
"""
import re, json, pathlib

HERE = pathlib.Path(__file__).parent
CFG = json.loads((HERE / "config.json").read_text())

MIN_PRICE = CFG["min_price"]
MAX_PRICE = CFG["max_price"]
MODELS = CFG["models"]
BRANDS = CFG["brands"]
KEYWORDS = CFG["keywords_kleinanzeigen"]
CAT = CFG["kleinanzeigen"]["cat"]

BRAND = re.compile(r"\b(xiaomi|redmi|mi)\b", re.I)
ROUTER_KW = re.compile(r"\b(router|routeur|wlan|repeater|répéteur|mesh|access\s*point)\b", re.I)
MODEL = re.compile(r"\bax\s*(1800|3000)\b", re.I)
BAD = re.compile(r"\b(suche|gesucht|ankauf|kaufe|tausch|defekt|kaputt|ersatzteil|bastler)\b", re.I)


def combos():
    return [f"{brand} {kw} {model}" for brand in BRANDS for model in MODELS for kw in KEYWORDS]


def combos_vinted():
    return [f"{brand} {model}" for brand in BRANDS for model in MODELS]


def classify(ad):
    """-> (verdict, model_num, brand, reason); verdict in hit / skip. Title-only.
    reason set only for skip, for negative-space analysis."""
    title = ad["title"]
    if BAD.search(title):
        return "skip", None, None, "bad_title"
    b = BRAND.search(title)
    if not b:
        return "skip", None, None, "no_brand"
    brand = b.group(1).capitalize()
    if not ROUTER_KW.search(title):
        return "skip", None, brand, "not_router"
    m = MODEL.search(title)
    if not m:
        return "skip", None, brand, "model_not_in_title"
    return "hit", int(m.group(1)), brand, None
