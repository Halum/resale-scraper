import importlib.util, pathlib

_p = pathlib.Path(__file__).parent.parent / "products" / "macbook" / "spec.py"
_s = importlib.util.spec_from_file_location("macbook_spec", _p)
spec = importlib.util.module_from_spec(_s)
_s.loader.exec_module(spec)


def c(title):
    return spec.classify({"title": title})


def test_m1_pro_max_hit():
    assert c("MacBook Pro 14 M1 Pro 32GB 1TB")[0] == "skip"
    assert c("MacBook Pro 16 M1 Max 64 GB")[:3] == ("hit", 64, "M1 Max")


def test_m2_to_m5_belong_to_their_own_products():
    for t in ("MacBook Pro M2 Pro 32GB", "MacBook Pro M3 Max 64GB",
              "MacBook Pro M4 Pro 48GB", "MacBook Pro M5 Max 64GB"):
        assert c(t)[0] == "skip", t


def test_combos_search_m1_only():
    assert all(" m1" in q for q in spec.combos() if q not in spec.FALLBACK_QUERIES)


def _load(p):
    path = pathlib.Path(__file__).parent.parent / "products" / p / "spec.py"
    s = importlib.util.spec_from_file_location(f"{p}_spec", path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def test_m1_m2_m3_only_max():
    for p, n, ram in (("macbook", 1, 32), ("m2", 2, 32), ("m3", 3, 36)):
        s = _load(p)
        assert s.classify({"title": f"MacBook Pro M{n} Max {ram}GB"})[0] == "hit", p
        for t in (f"MacBook Pro M{n} Pro {ram}GB", f"MacBook Air M{n} {ram}GB"):
            assert s.classify({"title": t})[0] == "skip", (p, t)
        assert all("max" in q for q in s.combos()), p
