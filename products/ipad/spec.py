"""Classify/combos for iPad Pro M1 (11" + 12.9"), any storage, 0-2000EUR.
Plugs into common/kleinanzeigen_engine.py + common/vinted_engine.py, which own
the actual scrape loop, browser setup, DB, and export.

Storage and screen size are both wanted in full (no target subset like
macbook's WANT_RAM) -- the only mandatory gate is the M1 chip itself, since
iPad Pro also ships as A12X/A12Z (2018/2020), M2 (2022), and M4 (2024), and
Air/mini never carry M1 in this generation-naming scheme.
"""
import re, json, pathlib

HERE = pathlib.Path(__file__).parent
CFG = json.loads((HERE / "config.json").read_text())

MIN_PRICE = CFG["min_price"]
MAX_PRICE = CFG["max_price"]
SCREENS = CFG["screens"]
FALLBACK_QUERIES = CFG["fallback_queries"]
CAT = CFG["kleinanzeigen"]["cat"]

# Vinted is EU-wide -- accessory listings show up in French/Italian/Dutch as
# often as German/English, so the accessory-word list has to cover all of
# them (a "Cover"/"Coque"/"Custodia"/"Hoesje" for 1-20EUR was the single
# biggest false-hit source in the first live Vinted run, 2026-08-07).
BAD = re.compile(r"\b(suche|gesucht|ankauf|kaufe|defekt|ersatzteil|bastler|tausch|"
                 r"display|akku|h(ü|ue)lle|case|tasche|sticker|nur teile|"
                 r"folie|panzerglas|tastatur|keyboard|pencil|stift|"
                 r"ladekabel|netzteil|ladegeraet|ladegerät|"
                 r"cover|coque|(e|é)tui|housse|custodia|fodero|hoes(je)?|"
                 r"scatola|karton|bo(i|î)te|pellicola|subcase|sleeve|folio|"
                 r"protection|bookcase|film)\b|schutzfolie|displayschutz|schutzh(ü|ue)lle", re.I)
WRONG_LINE = re.compile(r"\bipad\s*(air|mini)\b", re.I)
WRONG_CHIP = re.compile(r"\b(a12x|a12z|m2|m4)\b", re.I)
CHIP_M1 = re.compile(r"\bm1\b", re.I)
# Sellers often skip "M1" and identify the model by generation number or year
# instead (M1 is the *only* chip in gen 3 @ 11" / gen 5 @ 12.9", released
# 2021) -- these are still an unambiguous identification, not a guess.
GEN_M1 = re.compile(r"\b[35](?:st|rd|th)?\.?\s*gen(?:eration)?\b", re.I)
YEAR_2021 = re.compile(r"\b2021\b")
SCREEN = re.compile(r"\b(11|12[.,]9)\b")
STORAGE = re.compile(r"\b(128|256|512)\s*gb\b|\b(1)\s*tb\b|\b(2)\s*tb\b", re.I)


def combos():
    qs = [f"ipad pro {s} m1" for s in SCREENS]
    qs += FALLBACK_QUERIES
    return qs


def storage_of(title):
    m = STORAGE.search(title)
    if not m:
        return None
    if m.group(1):
        return int(m.group(1))
    if m.group(2):
        return 1024
    if m.group(3):
        return 2048
    return None


def classify(ad):
    """-> (verdict, storage_gb, screen_label, reason); verdict in hit / skip.
    Title-only. reason set only for skip.

    Storage and screen are both recorded whenever found but never gate the
    verdict (every tier/size wanted) -- only the M1 identity itself is
    mandatory, since it's the one thing that actually distinguishes this
    generation from every other iPad Pro on the used market. "M1" isn't
    always spelled out -- generation number or year alone is just as
    unambiguous (see GEN_M1/YEAR_2021 above), so both count as the same
    positive signal, not a fallback guess."""
    title = ad["title"]
    if BAD.search(title):
        return "skip", None, None, "bad_title"
    tl = title.lower()
    if "ipad" not in tl or "pro" not in tl:
        return "skip", None, None, "not_ipad_pro"
    if WRONG_LINE.search(title):
        return "skip", None, None, "wrong_line"
    if WRONG_CHIP.search(title):
        return "skip", None, None, "wrong_chip"
    if not (CHIP_M1.search(title) or GEN_M1.search(title) or YEAR_2021.search(title)):
        return "skip", None, None, "no_m1_signal"
    m = SCREEN.search(title)
    screen = f'{m.group(1).replace(",", ".")}"' if m else None
    storage = storage_of(title)
    return "hit", storage, screen, None
