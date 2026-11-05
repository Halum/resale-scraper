import json, pathlib
HERE = pathlib.Path(__file__).parent
CFG = json.loads((HERE / "config.json").read_text())
MIN_PRICE = CFG["min_price"]
MAX_PRICE = CFG["max_price"]
CAT = CFG["kleinanzeigen"]["cat"]
VINTED_EXTRA_QS = ""
def combos(): return []
def combos_vinted(): return []
def classify(ad): return "skip", None, None, "stub"
