import pathlib
from common.vinted_engine import collect_flaresolverr

FIX = pathlib.Path(__file__).parent / "fixtures"


def test_collect_flaresolverr_builds_ads_from_html(monkeypatch):
    html = (FIX / "vi_listing.html").read_text(encoding="utf-8", errors="replace")
    calls = []

    def fake_fetch(url, **kw):
        calls.append(url)
        return html if len(calls) == 1 else ""   # page 2 empty -> loop stops

    monkeypatch.setattr("common.vinted_engine.fetch_html", fake_fetch)
    monkeypatch.setattr("common.vinted_engine.pace", lambda *a, **k: None)

    ads, hits, skipped = collect_flaresolverr(
        seen=set(), only_new=False, queries=["ipad pro m1"], pages=2,
        min_price=100, max_price=2000, extra_qs="",
        classify=lambda ad: ("hit", 128, '11"', None))

    assert len(ads) >= 20
    assert len(hits) >= 1
    first = next(iter(ads.values()))
    assert set(first) >= {"id", "href", "title", "text", "price"}
