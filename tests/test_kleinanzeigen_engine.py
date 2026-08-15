import pathlib
from common.kleinanzeigen_engine import collect_flaresolverr, empty_page_reason_html

FIX = pathlib.Path(__file__).parent / "fixtures"


def test_collect_flaresolverr_builds_ads(monkeypatch):
    html = (FIX / "kl_listing.html").read_text(encoding="utf-8", errors="replace")
    calls = []

    def fake_fetch(url, **kw):
        calls.append(url)
        return html if len(calls) == 1 else ""

    monkeypatch.setattr("common.kleinanzeigen_engine.fetch_html", fake_fetch)
    monkeypatch.setattr("common.kleinanzeigen_engine.pace", lambda *a, **k: None)

    ads, hits, skipped = collect_flaresolverr(
        seen=set(), only_new=False, queries=["ipad pro m1"], pages=2,
        min_price=100, max_price=2000, cat="",
        classify=lambda ad: ("hit", 128, '11"', None))

    assert len(ads) >= 20
    assert len(hits) >= 1


def test_empty_page_reason_not_fooled_by_omnipresent_gdpr_banner():
    # "Alle akzeptieren" markup is server-rendered on EVERY Kleinanzeigen page
    # regardless of consent state or result count (verified: present in
    # kl_listing.html, which has 27 real cards). A genuine zero-result page
    # must still resolve to "no-results", not "blocked-consent" -- confirmed
    # live on 2026-08-15 (22/105 macbook combos mislabeled, all genuinely
    # 0-result on re-fetch, none actually blocked).
    page = "<html><body>Alle akzeptieren keine Ergebnisse gefunden</body></html>"
    assert empty_page_reason_html(page) == "no-results"
