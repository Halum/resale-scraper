import pathlib
import pytest
from common.check_sold import is_sold_from_html

FIX = pathlib.Path(__file__).parent / "fixtures"


def test_is_sold_from_html_uses_fetch_and_parser(monkeypatch):
    sold = (FIX / "kl_detail_sold.html").read_text(encoding="utf-8", errors="replace")
    live = (FIX / "kl_detail_live.html").read_text(encoding="utf-8", errors="replace")

    monkeypatch.setattr("common.check_sold.fetch_html", lambda href, **kw: sold)
    assert is_sold_from_html("http://example/sold") is True

    monkeypatch.setattr("common.check_sold.fetch_html", lambda href, **kw: live)
    assert is_sold_from_html("http://example/live") is False


def test_unreachable_ad_is_never_reported_sold(monkeypatch):
    # Failing closed matters here: a transient fetch error must not hide an ad.
    from common.fetch import FetchError

    def boom(href, **kw):
        raise FetchError("down")

    monkeypatch.setattr("common.check_sold.fetch_html", boom)
    assert is_sold_from_html("http://example/x") is False


def test_markup_change_is_never_reported_sold(monkeypatch):
    # is_sold_html raises ValueError when the badge span is gone. That must be
    # swallowed into "not sold", never into "sold".
    monkeypatch.setattr("common.check_sold.fetch_html",
                        lambda href, **kw: "<html><span class='other'>x</span></html>")
    assert is_sold_from_html("http://example/x") is False
