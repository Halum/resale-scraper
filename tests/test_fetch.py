import os
import pytest
from common.fetch import fetch_html, FetchError

live = pytest.mark.skipif(
    not os.environ.get("FLARESOLVERR_LIVE_TEST"),
    reason="set FLARESOLVERR_LIVE_TEST=1 to hit the live service")


@live
def test_fetch_returns_html_for_a_real_page():
    html = fetch_html("https://www.kleinanzeigen.de/s-anzeige:angebote/preis:100:2000/ipad-pro-m1/k0")
    assert "article" in html
    assert len(html) > 100_000


def test_fetch_raises_on_unreachable_endpoint():
    # Port 9 (discard) is closed -- no network dependency beyond localhost.
    with pytest.raises(FetchError):
        fetch_html("https://example.com/", endpoint="http://127.0.0.1:9/v1")
