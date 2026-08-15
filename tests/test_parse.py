import pathlib
import pytest
from common.parse import (parse_kleinanzeigen_cards, parse_vinted_cards,
                          is_sold_html, kleinanzeigen_posted_date, vinted_posted_date)

FIX = pathlib.Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def kl_listing():
    return (FIX / "kl_listing.html").read_text(encoding="utf-8", errors="replace")


@pytest.fixture(scope="module")
def vi_listing():
    return (FIX / "vi_listing.html").read_text(encoding="utf-8", errors="replace")


def test_kleinanzeigen_cards_extracted(kl_listing):
    cards = parse_kleinanzeigen_cards(kl_listing)
    assert len(cards) >= 20, f"expected a full page of cards, got {len(cards)}"
    for c in cards:
        assert set(c) == {"id", "href", "title", "text"}
        assert c["id"].isdigit()
        assert c["href"].startswith("https://www.kleinanzeigen.de")
        assert c["title"].strip()


def test_kleinanzeigen_card_text_carries_price_and_location(kl_listing):
    # price_of()/where_of() in the engine parse these out of ad["text"].
    from common.kleinanzeigen_engine import price_of, where_of
    cards = parse_kleinanzeigen_cards(kl_listing)
    assert sum(price_of(c["text"]) is not None for c in cards) == len(cards)
    assert sum(where_of(c["text"]) != "?" for c in cards) == len(cards)


def test_vinted_cards_extracted(vi_listing):
    cards = parse_vinted_cards(vi_listing)
    assert len(cards) >= 20
    for c in cards:
        assert set(c) == {"href", "title"}
        assert "/items/" in c["href"]


def test_vinted_cards_feed_parse_card_unchanged(vi_listing):
    from common.vinted_engine import parse_card
    cards = parse_vinted_cards(vi_listing)
    parsed = [parse_card(c["href"], c["title"]) for c in cards]
    assert sum(p["price"] is not None for p in parsed) > len(parsed) // 2
    assert all(p["id"].isdigit() for p in parsed)


def test_sold_detection_distinguishes_sold_from_live():
    sold = (FIX / "kl_detail_sold.html").read_text(encoding="utf-8", errors="replace")
    live = (FIX / "kl_detail_live.html").read_text(encoding="utf-8", errors="replace")
    assert is_sold_html(sold) is True
    assert is_sold_html(live) is False


def test_posted_date_is_the_real_date_not_just_any_date():
    # Asserting the EXACT date from the fixture. `d is None or len(d) == 10`
    # would pass even if the function always returned None, and would also pass
    # on a footer date from elsewhere in the 500 KB page.
    live = (FIX / "kl_detail_live.html").read_text(encoding="utf-8", errors="replace")
    sold = (FIX / "kl_detail_sold.html").read_text(encoding="utf-8", errors="replace")
    # These are the dates in the fixtures captured on 2026-08-15. If you
    # re-captured fixtures (because an ad expired), substitute the dates your
    # own files contain -- but keep the assertion EXACT, not a length check.
    assert kleinanzeigen_posted_date(live) == "10.08.2026"
    assert kleinanzeigen_posted_date(sold) == "28.07.2026"


def test_sold_detector_fails_loud_when_markup_changes():
    # Must NOT silently return False -- that would make the sweep report
    # "0 sold" forever with no error if Kleinanzeigen renames the class.
    with pytest.raises(ValueError):
        is_sold_html("<html><span class='unrelated'>nothing here</span></html>")


def test_vinted_posted_date_survives_tag_stripping():
    # itemprop="upload_date" wraps the value in a sibling <div> from the
    # "Hochgeladen" label -- turning tags into newlines (_visible_text) puts
    # them on separate lines, so a same-line regex over stripped text finds
    # nothing. Caught on a real item page on 2026-08-15.
    detail = (FIX / "vi_detail.html").read_text(encoding="utf-8", errors="replace")
    assert vinted_posted_date(detail) == "2 Tagen"


def test_sold_detector_is_not_fooled_by_a_prefixed_class():
    # A prefix match on "pvap-reserved-title" would treat this as sold and
    # silently hide a live ad from the viewer.
    evil = ('<span class="pvap-reserved-title-mobile">x</span>'
            '<span class="pvap-reserved-title is-hidden">y</span>')
    assert is_sold_html(evil) is False
