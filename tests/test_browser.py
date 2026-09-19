"""pace()'s distraction pause is detail-only -- the bug that let it eat 37% of
macbook's vinted runtime (200 listing pages x 10% x 30-90s)."""
import common.browser as browser


def test_distraction_skipped_for_listing(monkeypatch):
    monkeypatch.setattr(browser, "_beat", lambda: None)   # skip watchdog thread
    monkeypatch.setattr(browser.random, "random", lambda: 0.0)   # always "hits"
    sleeps = []
    monkeypatch.setattr(browser.time, "sleep", lambda s: sleeps.append(s))
    browser.pace("listing")
    assert len(sleeps) == 1   # only the base lognormal delay, no distraction


def test_distraction_applies_to_detail(monkeypatch):
    monkeypatch.setattr(browser, "_beat", lambda: None)
    monkeypatch.setattr(browser.random, "random", lambda: 0.0)
    sleeps = []
    monkeypatch.setattr(browser.time, "sleep", lambda s: sleeps.append(s))
    browser.pace("detail")
    assert len(sleeps) == 2   # base delay + distraction
