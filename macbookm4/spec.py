"""Classify/combos for MacBook Pro M4/M4 Pro/M4 Max, 48/64/128GB, 1000-3000EUR
-- price-floor scout. Plugs into common/kleinanzeigen_engine.py +
common/vinted_engine.py, which own the actual scrape loop, browser setup, DB,
and export.
"""
import re, json, pathlib

HERE = pathlib.Path(__file__).parent
CFG = json.loads((HERE / "config.json").read_text())

MIN_PRICE = CFG["min_price"]
MAX_PRICE = CFG["max_price"]
WANT_RAM = tuple(CFG["ram_targets"])
CHIPS = CFG["chips"]
FALLBACK_QUERIES = CFG["fallback_queries"]
CAT = CFG["kleinanzeigen"]["cat"]

BAD = re.compile(r"\b(suche|gesucht|ankauf|kaufe|defekt|ersatzteil|bastler|tausch|"
                 r"displays?|akkus?|netzteil|logicboard|"
                 r"h(ü|ue)lle|case|tasche|sticker|nur teile|"
                 r"mac\s*mini|mac\s*studio|imac|mac\s*pro)\b", re.I)
RAM_NUM = r"(8|16|18|24|32|36|48|64|96|128)"
RAM = re.compile(
    rf"\b{RAM_NUM}\s*(?:gb|g\b)"
    rf"|\b{RAM_NUM}\s*/\s*\d+\s*(?:gb|tb)\b",
    re.I)
CHIP = re.compile(r"\bm([1-4])\s*(pro|max|ultra)?\b", re.I)


def combos():
    qs = [f"macbook {chip} {ram}gb" for chip in CHIPS for ram in WANT_RAM]
    qs += FALLBACK_QUERIES
    return qs


def classify(ad):
    """-> (verdict, ram, chip, reason); verdict in hit / skip. Title-only.
    Any M4 family chip (base/Pro/Max) counts -- just not M1/M2/M3."""
    title = ad["title"]
    if BAD.search(title):
        return "skip", None, None, "bad_title"
    m = CHIP.search(title)
    if not m or m.group(1) != "4":
        return "skip", None, None, "not_m4"
    variant = m.group(2).lower() if m.group(2) else None
    chip = f"M4 {variant.capitalize()}" if variant else "M4"
    rams = [int(g) for pair in RAM.findall(title) for g in pair if g]
    hits = [r for r in rams if r in WANT_RAM]
    if hits:
        return "hit", max(hits), chip, None
    return "skip", (max(rams) if rams else None), chip, ("off_target_ram" if rams else "ram_not_in_title")
