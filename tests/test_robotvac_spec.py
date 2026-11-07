import importlib.util, pathlib
import pytest

_p = pathlib.Path(__file__).parent.parent / "products" / "robotvac" / "spec.py"
_s = importlib.util.spec_from_file_location("robotvac_spec", _p)
spec = importlib.util.module_from_spec(_s)
_s.loader.exec_module(spec)


def c(title):
    return spec.classify({"title": title})


HITS = [
    # real hits from the 2026-11-06 live trial run
    ("Dreame Saugroboter L10s Ultra  mit Absaugstation", "L10s Ultra", "Dreame"),
    ("roborock s7 Wisch  und Saugroboter inkl. Ladestation", "S7", "Roborock"),
    ("Mi Robot Vacuum-Mop 2 Ultra  Roboter-Staubsauger", "Mop 2 Ultra", "Xiaomi"),
    ("Roborock S7 Saugroboter mit Wischfunktion", "S7", "Roborock"),
    ("Roborock S7 MaxV Ultra Saugroboter", "S7 MaxV", "Roborock"),
    ("Roborock S6 MaxV Saugroboter", "S6 MaxV", "Roborock"),
    ("Roborock S8 Saugroboter", "S8", "Roborock"),
    ("Roborock Q7 Saugroboter", "Q7", "Roborock"),
    ("Roborock Q7+ mit Absaugstation", "Q7+", "Roborock"),
    ("Roborock Q7 Max+ Saugroboter", "Q7 Max+", "Roborock"),
    ("Roborock Q7 Max Saugroboter", "Q7 Max", "Roborock"),
    ("Roborock Q5+ Saugroboter", "Q5+", "Roborock"),
    ("Roborock Q8 Max Saug- und Wischroboter", "Q8 Max", "Roborock"),
    ("Roborock S7 mit Ladestation", "S7", "Roborock"),
    ("Xiaomi Roborock S7", "S7", "Roborock"),
    ("Roborock S7 inkl. Zubehör", "S7", "Roborock"),
    ("Roborock S7 inkl. Absaugstation", "S7", "Roborock"),
    ("Roborock S7 + Zubehör", "S7", "Roborock"),
    ("Dreame L10 Ultra Saugroboter", "L10 Ultra", "Dreame"),
    ("Roborock Q5 Pro Saugroboter", "Q5 Pro", "Roborock"),
    ("Xiaomi Robot Vacuum S10 Plus", "S10 Plus", "Xiaomi"),
    ("Mijia Mop 2 Pro Saugroboter", "Mop 2 Pro", "Xiaomi"),
    ("Dreame L10 Pro inkl. Zubehör", "L10 Pro", "Dreame"),
    ("Dreame L10s Ultra Saugroboter", "L10s Ultra", "Dreame"),
    ("Dreame L10s Saugroboter", "L10s", "Dreame"),
    ("Dreame D10s Pro Saugroboter", "D10s Pro", "Dreame"),
    ("Dreame Z10 Pro Saugroboter", "Z10 Pro", "Dreame"),
    ("Dreame L20 Ultra Saugroboter", "L20", "Dreame"),
    ("Xiaomi Robot Vacuum X10+ Saugroboter", "X10+", "Xiaomi"),
    ("Xiaomi Robot Vacuum S10+ Saugroboter", "S10+", "Xiaomi"),
    ("Xiaomi Robot Vacuum S10 Saugroboter", "S10", "Xiaomi"),
    ("Xiaomi Mi Robot Vacuum-Mop 2 Pro", "Mop 2 Pro", "Xiaomi"),
    ("Xiaomi Robot Vacuum S20+", "S20+", "Xiaomi"),
]

SKIPS = [
    ("Roborock S7 defekt", None, None, "bad_title"),
    ("Suche Roborock S7", None, None, "bad_title"),
    ("Dreame L10s Ersatzteil Mainboard", None, None, "bad_title"),
    ("Akku für Roborock S7", None, None, "accessory"),
    ("Seitenbürsten für Dreame L10s", None, None, "accessory"),
    ("Ladestation Roborock Q7 Max", None, None, "accessory"),
    ("Filter Set kompatibel Xiaomi S10", None, None, "accessory"),
    ("Roborock S7 Ladestation", None, None, "accessory"),
    # misjudged in the 2026-11-06 live trial run
    ("Roborock Vaccum Accessories Kit f S7 & S8 Saugroboter - VibraRise", None, None, "accessory"),
    ("BROTECT HD-Clear Folie für Saugroboter Roborock S7 maxV", None, None, "accessory"),
    ("2 Wisch-Aufsätze für Saugroboter Roborock S8", None, None, "accessory"),
    ("Saugroboter Roborock S8 Bumper 8 mm tiefer", None, None, "accessory"),
    ("Mi Robot Vacuum Mop 2 Ultra Station", None, None, "accessory"),
    ("Xiaomi Mi Robot Vacuum-Mop 2 Ultra Auto-Empty Station", None, None, "accessory"),
    ("Xiaomi Mi Robot Vacuum-Mop 2 Ultra – Auto-Empty Station", None, None, "accessory"),
    ("Mi Robot Vacuum-Mop P Ladegerät und Wasser, Auffangbehälter", None, None, "accessory"),
    ("roborock S7 Saugroboter mit Fehler", None, None, "bad_title"),
    ("Roborock S7 Dock", None, None, "accessory"),
    ("Roborock S7 Wassertank", None, None, "accessory"),
    ("Roborock S7 Seitenbürste", None, None, "accessory"),
    ("Roborock S7 Zubehör Set", None, None, "accessory"),
    ("Roborock S7 Netzteil", None, None, "accessory"),
    ("Roborock S7 LDS Sensor", None, None, "accessory"),
    ("Roborock Dock für S7", None, None, "accessory"),
    ("Roborock S7 Saugroboter Ladestation", None, None, "accessory"),
    ("Staubbeutel für Roborock S7", None, None, "accessory"),
    ("Wischmopp für Dreame L10s", None, None, "accessory"),
    ("Zubehörset für Roborock Q7 Max", None, None, "accessory"),
    ("Roborock S7 Ersatzteile", None, None, "bad_title"),
    ("Roborock S7 Ersatzteilspender", None, None, "bad_title"),
    ("Roborock Q7 M5 Saugroboter", None, "Roborock", "excluded_model"),
    ("Dreame D9 Pro", None, "Dreame", "excluded_model"),
    # weaker than the D9 Pro Sajjad owns
    ("Mi Robot Vacuum Mop P Saugroboter", None, "Xiaomi", "excluded_model"),
    ("Xiaomi Mi Robot Vacuum-Mop P Saugroboter mit Ladestation", None, "Xiaomi", "excluded_model"),
    ("Xiaomi Mop Pro Saugroboter mit Zubehör", None, "Xiaomi", "excluded_model"),
    ("Xiaomi Mi Robot Vacuum Mop Pro", None, "Xiaomi", "excluded_model"),
    # D10 family: only a station or more suction over the D9 Pro, neither wanted
    ("Dreame D10 Plus Saugroboter mit Absaugstation", None, "Dreame", "excluded_model"),
    ("Dreame D10s Saugroboter weiß", None, "Dreame", "excluded_model"),
    ("Dreame D10s Plus Saugroboter", None, "Dreame", "excluded_model"),
    ("Dreame D10 Saugroboter", None, "Dreame", "excluded_model"),
    ("Roborock S5 Max", None, "Roborock", "excluded_model"),
    ("Roborock S5 Max mit Ladestation", None, "Roborock", "excluded_model"),
    ("Roborock S6 Pure", None, "Roborock", "excluded_model"),
    ("Xiaomi T12 Saugroboter", None, "Xiaomi", "excluded_model"),
    ("Xiaomi Mi Robot Vacuum 1S", None, "Xiaomi", "excluded_model"),
    ("Roborock E5 Saugroboter", None, "Roborock", "excluded_model"),
    ("Saugroboter ohne Marke", None, None, "no_brand"),
    ("Roborock Saugroboter mit App", None, "Roborock", "model_not_in_title"),
    ("Dreame Staubsauger", None, "Dreame", "model_not_in_title"),
]


@pytest.mark.parametrize("title,model,brand", HITS)
def test_hit(title, model, brand):
    assert c(title) == ("hit", model, brand, None)


@pytest.mark.parametrize("title,model,brand,reason", SKIPS)
def test_skip(title, model, brand, reason):
    assert c(title) == ("skip", model, brand, reason)


def test_combos():
    assert spec.combos() == ["roborock saugroboter", "dreame saugroboter",
                             "xiaomi saugroboter", "mi robot vacuum"]


def test_combos_vinted():
    assert spec.combos_vinted() == ["roborock", "dreame", "xiaomi robot", "mi robot"]


def test_classify_vinted_brand_from_card_text():
    ad = {"title": "Saugroboter S7", "text": "Saugroboter S7, marke: Roborock, zustand: gut, 40,00 €"}
    assert spec.classify_vinted(ad) == ("hit", "S7", "Roborock", None)
    assert spec.classify({"title": ad["title"]})[3] == "no_brand"


def test_classify_vinted_no_marke_stays_no_brand():
    ad = {"title": "Saugroboter S7", "text": "Saugroboter S7, zustand: gut, 40,00 €"}
    assert spec.classify_vinted(ad)[3] == "no_brand"


def test_classify_vinted_title_brand_unchanged():
    ad = {"title": "Dreame L10s", "text": "Dreame L10s, marke: Dreame, 40,00 €"}
    assert spec.classify_vinted(ad) == ("hit", "L10s", "Dreame", None)


def test_vinted_extra_qs_empty_without_brand_ids():
    assert spec.VINTED_EXTRA_QS == ""
