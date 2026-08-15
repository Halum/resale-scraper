"""Classify/combos for MacBook Pro/Max/Ultra Apple Silicon, 32-64GB, <=1400EUR.
Plugs into common/kleinanzeigen_engine.py + common/vinted_engine.py, which own
the actual scrape loop, browser setup, DB, and export.
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
    """-> (verdict, ram, chip, reason); verdict in hit / skip. Title-only --
    no description, no detail-page text. reason set only for skip.

    32/36/48/64GB only exists on Pro/Max/Ultra Apple Silicon -- base M-chips
    top out at 24GB, so the chip *variant* is the signal, not "MacBook Pro"
    (the model name, which also covers 2018-2020 Intel machines)."""
    title = ad["title"]
    if BAD.search(title):
        return "skip", None, None, "bad_title"
    m = CHIP.search(title)
    variant = m.group(2).lower() if m and m.group(2) else None
    if not m or variant not in ("pro", "max", "ultra"):
        return "skip", None, (f"M{m.group(1)}" if m else None), "no_pro_max_chip_in_title"
    chip = f"M{m.group(1)} {variant.capitalize()}"
    rams = [int(g) for pair in RAM.findall(title) for g in pair if g]
    hits = [r for r in rams if r in WANT_RAM]
    if hits:
        return "hit", max(hits), chip, None
    return "skip", (max(rams) if rams else None), chip, ("off_target_ram" if rams else "ram_not_in_title")
