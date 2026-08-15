"""Classify/combos for Anker/Ugreen/Baseus chargers, <=20EUR.
Plugs into common/kleinanzeigen_engine.py + common/vinted_engine.py, which own
the actual scrape loop, browser setup, DB, and export.

Kleinanzeigen and Vinted need DIFFERENT classify()/combos() here: Vinted's
native brand_ids filter already guarantees the brand, so its combos only pair
watt+keyword (no brand in the search text) and its classify skips the
brand-in-title check that Kleinanzeigen needs.
"""
import re, json, pathlib

HERE = pathlib.Path(__file__).parent
CFG = json.loads((HERE / "config.json").read_text())

MIN_PRICE = CFG["min_price"]
MAX_PRICE = CFG["max_price"]
WANT_WATT = tuple(CFG["watts"])
BRANDS = CFG["brands"]
KEYWORDS = CFG["keywords_kleinanzeigen"]
KEYWORD_VINTED = CFG["keyword_vinted"]
CAT = ""   # no category restriction for charger

BRAND = re.compile(r"\b(anker|ugreen|baseus)\b", re.I)
CHARGER_KW = re.compile(r"\b(netzteil|ladeger[äa]t|ladeadapter|ladestation|"
                         r"netzstecker|charger|steckernetzteil|chargeur|"
                         r"caricatore|caricabatterie|oplader|adaptador)\b", re.I)
WATT = re.compile(r"\b(\d{2,3})\s*w(?:att)?\b", re.I)
BAD = re.compile(r"\b(suche|gesucht|ankauf|kaufe|tausch|defekt|"
                 r"ohne\s+(?:netzteil|ladeger(?:ä|ae)t|ladekabel|charger)|"
                 r"nur\s+kabel|kein\s+netzteil|ersatzteil)\b", re.I)

BRAND_IDS = list(CFG["vinted"]["brand_ids"].values())
VINTED_EXTRA_QS = "&" + "&".join(f"brand_ids[]={b}" for b in BRAND_IDS)


def combos():
    return [f"{brand} {watt}w {kw}" for brand in BRANDS for watt in WANT_WATT for kw in KEYWORDS]


def combos_vinted():
    return [f"{watt}w {KEYWORD_VINTED}" for watt in WANT_WATT]


def classify(ad):
    """-> (verdict, watt, brand, reason); verdict in hit / skip. Title-only.
    reason set only for skip, for negative-space analysis."""
    title = ad["title"]
    if BAD.search(title):
        return "skip", None, None, "bad_title"
    b = BRAND.search(title)
    if not b:
        return "skip", None, None, "no_brand"
    if not CHARGER_KW.search(title):
        return "skip", None, b.group(1).capitalize(), "not_charger"
    brand = b.group(1).capitalize()
    watts = [int(w) for w in WATT.findall(title)]
    hits = [w for w in watts if w in WANT_WATT]
    if hits:
        return "hit", max(hits), brand, None
    return "skip", (max(watts) if watts else None), brand, ("off_target_watt" if watts else "watt_not_in_title")


def classify_vinted(ad):
    """-> (verdict, watt, brand, reason); verdict in hit / skip. Title-only,
    no brand check here -- native brand_ids already guarantees the ad is
    Anker/Ugreen/Baseus, so requiring the brand name IN the title too (like
    Kleinanzeigen needs) would wrongly skip real hits whose seller just
    didn't type the brand into the title."""
    title = ad["title"]
    if BAD.search(title):
        return "skip", None, None, "bad_title"
    if not CHARGER_KW.search(title):
        return "skip", None, None, "not_charger"
    watts = [int(w) for w in WATT.findall(title)]
    hits = [w for w in watts if w in WANT_WATT]
    if hits:
        return "hit", max(hits), None, None
    return "skip", (max(watts) if watts else None), None, ("off_target_watt" if watts else "watt_not_in_title")
