import importlib.util, pathlib
import pytest

_p = pathlib.Path(__file__).parent.parent / "products" / "robotvac" / "spec.py"
_s = importlib.util.spec_from_file_location("robotvac_spec", _p)
spec = importlib.util.module_from_spec(_s)
_s.loader.exec_module(spec)


def c(title):
    return spec.classify({"title": title})


HITS = [
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
    ("Dreame L10 Pro inkl. Zubehör", "L10 Pro", "Dreame"),
    ("Dreame L10s Ultra Saugroboter", "L10s Ultra", "Dreame"),
    ("Dreame L10s Saugroboter", "L10s", "Dreame"),
    ("Dreame D10s Pro Saugroboter", "D10s Pro", "Dreame"),
    ("Dreame D10 Plus Saugroboter", "D10 Plus", "Dreame"),
    ("Dreame Z10 Pro Saugroboter", "Z10 Pro", "Dreame"),
    ("Dreame L20 Ultra Saugroboter", "L20", "Dreame"),
    ("Xiaomi Robot Vacuum X10+ Saugroboter", "X10+", "Xiaomi"),
    ("Xiaomi Robot Vacuum S10+ Saugroboter", "S10+", "Xiaomi"),
    ("Xiaomi Robot Vacuum S10 Saugroboter", "S10", "Xiaomi"),
    ("Xiaomi Mi Robot Vacuum-Mop 2 Pro", "Mop 2 Pro", "Xiaomi"),
    ("Mi Robot Vacuum Mop P Saugroboter", "Mop P", "Xiaomi"),
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
    ("Dreame D9 Pro", None, "Dreame", "excluded_model"),
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
    assert spec.combos_vinted() == spec.combos()


def test_vinted_extra_qs_empty_without_brand_ids():
    assert spec.VINTED_EXTRA_QS == ""
