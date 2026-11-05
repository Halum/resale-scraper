"""Classify/combos for Roborock/Dreame/Xiaomi lidar robot vacuums, 15-60EUR.
Plugs into common/kleinanzeigen_engine.py + common/vinted_engine.py, which own
the scrape loop, DB and export.

spec_label = brand, spec_num = model string (text in the INTEGER-affinity
column is fine in SQLite). Models live in config.json; the search is by brand
plus a vacuum word and classify() does the model filtering.

Vinted: no brand_ids are configured (ids not verified), so there is no native
brand filter and Vinted uses the same title-based classify() and queries. When
real ids are added to config["vinted"]["brand_ids"], VINTED_EXTRA_QS picks them
up, but a classify_vinted() that tolerates brand-less titles is then needed.
"""
import re, json, pathlib

HERE = pathlib.Path(__file__).parent
CFG = json.loads((HERE / "config.json").read_text())

MIN_PRICE = CFG["min_price"]
MAX_PRICE = CFG["max_price"]
CAT = CFG["kleinanzeigen"]["cat"]
QUERIES = CFG["queries"]

BRAND_IDS = list(CFG["vinted"]["brand_ids"].values())
VINTED_EXTRA_QS = "".join(f"&brand_ids[]={b}" for b in BRAND_IDS)

# Brand check order matters: "Xiaomi Roborock S7" is a Roborock.
BRAND_ORDER = [("Roborock", re.compile(r"\broborock\b", re.I)),
               ("Dreame", re.compile(r"\bdreame\b", re.I)),
               ("Xiaomi", re.compile(r"\b(xiaomi|mi)\b", re.I))]


def _model_re(m):
    return re.compile(r"(?<!\w)" + r"\s*".join(map(re.escape, m.split())) + r"(?!\w)", re.I)


# longest model string first, so "Q7 Max+" wins over "Q7"
MODELS = {b: sorted(((m, _model_re(m)) for m in ms), key=lambda x: -len(x[0]))
          for b, ms in CFG["brands"].items()}

EXCLUDED = re.compile(
    r"(?<!\w)(d9|s5|s50|s55|s6|e4|e5|e10|e12|t12|1s|lefant)(?!\w)", re.I)

BAD = re.compile(r"\b(suche|gesucht|ankauf|kaufe|tausch|defekt|kaputt|ersatzteil|bastler|mainboard)\b", re.I)

_ACC = (r"\w*b[üu]rste\w*|filter\w*|mopp?-?\s*pads?|wischt[üu]cher|beutel|akku|batterie|"
        r"absaugstation|ladestation|wassertank|lds|laser|zubeh[öo]r")
ACC_LEAD = re.compile(rf"^\W*(?:{_ACC})(?!\w)", re.I)
ACC_FOR = re.compile(rf"(?<!\w)(?:{_ACC})\s+(?:f[üu]r|passend|kompatibel)(?!\w)", re.I)
ACC_OK_BEFORE = re.compile(r"(?:\bmit|\binkl\.?|\bund|\+)\s*$", re.I)


def _is_accessory(title):
    if ACC_LEAD.search(title):
        return True
    return any(not ACC_OK_BEFORE.search(title[:m.start()]) for m in ACC_FOR.finditer(title))


def combos():
    return list(QUERIES)


def combos_vinted():
    return list(QUERIES)


def classify(ad):
    """-> (verdict, model, brand, reason); verdict in hit / skip. Title-only.
    reason set only for skip, for negative-space analysis."""
    title = ad["title"]
    if BAD.search(title):
        return "skip", None, None, "bad_title"
    if _is_accessory(title):
        return "skip", None, None, "accessory"
    brand = next((b for b, rx in BRAND_ORDER if rx.search(title)), None)
    if not brand:
        return "skip", None, None, "no_brand"
    for model, rx in MODELS[brand]:
        if rx.search(title):
            return "hit", model, brand, None
    if EXCLUDED.search(title):
        return "skip", None, brand, "excluded_model"
    return "skip", None, brand, "model_not_in_title"
