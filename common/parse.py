"""HTML -> structured data, replacing the in-page JavaScript the engines used
to run via pg.evaluate()/pg.eval_on_selector_all().

Everything here is stdlib regex rather than a DOM library, deliberately: it
adds no dependency, and each of these three extractions was verified against
real saved responses (see tests/fixtures/).
"""
import html as _html
import json
import re

# --- Kleinanzeigen listing -------------------------------------------------
# Bounded by </article> deliberately. Splitting on the start tag alone lets the
# LAST block run to the end of the document -- measured at 43,411 bytes vs
# 4,162 when bounded -- so page-tail markup (pagination, footer, recommendation
# modules) lands in that card's `text`, and price_of()/where_of() take the
# FIRST match they find. That silently mis-prices the trailing card.
_ARTICLE = re.compile(r'<article[^>]*data-adid=.*?</article>', re.S)
_ADID = re.compile(r'data-adid="(\d+)"')
_HREF = re.compile(r'data-href="([^"]*)"')
_LDJSON = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
# h2, NOT h3. The JS this replaces used a.querySelector('h3'), but the static
# HTML contains no h3 inside a card -- only h2 (verified on a real page).
# "Fixing" this to h3 returns zero titles.
_H2 = re.compile(r'<h2[^>]*>\s*(?:<a[^>]*>)?\s*([^<]{3,200})')
_TAGS = re.compile(r'<[^>]+>')
_SCRIPTSTYLE = re.compile(r'<(script|style)[^>]*>.*?</\1>', re.S)
_BLANKS = re.compile(r'\n{2,}')


def _visible_text(fragment):
    """Approximate element.innerText: drop script/style, turn tags into
    newlines, unescape entities. price_of()/where_of() are line-oriented and
    tolerant, so this is close enough -- verified 27/27 on a real page."""
    f = _SCRIPTSTYLE.sub(" ", fragment)
    f = _TAGS.sub("\n", f)
    return _BLANKS.sub("\n", _html.unescape(f)).strip()


def parse_kleinanzeigen_cards(html):
    """Same output shape as kleinanzeigen_engine.SCRAPE's JavaScript."""
    out = []
    for block in _ARTICLE.findall(html):
        m_id = _ADID.search(block)
        if not m_id:
            continue
        m_href = _HREF.search(block)
        title = None
        m_ld = _LDJSON.search(block)
        if m_ld:
            try:
                title = (json.loads(m_ld.group(1)) or {}).get("title")
            except (ValueError, TypeError):
                title = None
        if not title:
            m_h2 = _H2.search(block)
            title = _html.unescape(m_h2.group(1)).strip() if m_h2 else ""
        if not title:
            continue
        out.append({
            "id": m_id.group(1),
            "href": "https://www.kleinanzeigen.de" + (m_href.group(1) if m_href else ""),
            "title": title,
            "text": _visible_text(block),
        })
    return out


# --- Vinted listing --------------------------------------------------------
# Mirrors CARD_SEL = 'a[data-testid$="--overlay-link"]'
_VI_ANCHOR = re.compile(r'<a[^>]*data-testid="[^"]*--overlay-link"[^>]*>')
_A_HREF = re.compile(r'href="([^"]+)"')
_A_TITLE = re.compile(r'title="([^"]+)"')


def parse_vinted_cards(html):
    """Same output shape as pg.eval_on_selector_all(CARD_SEL, ...) -- a list of
    {href, title}. hrefs are relative in static HTML, so absolutise them; the
    live DOM's e.href was already absolute."""
    out = []
    for tag in _VI_ANCHOR.findall(html):
        m_href = _A_HREF.search(tag)
        m_title = _A_TITLE.search(tag)
        if not (m_href and m_title):
            continue
        href = _html.unescape(m_href.group(1))
        if href.startswith("/"):
            href = "https://www.vinted.de" + href
        out.append({"href": href, "title": _html.unescape(m_title.group(1))})
    return out


# --- detail pages ----------------------------------------------------------
# The badge renders as two spans; the inactive one carries `is-hidden`. On a
# live ad BOTH carry it; on a sold ad at least one does not. That is exactly
# what the old el.is_visible() check resolved to -- visibility here is
# class-driven, so it IS in the static HTML (the old check_sold.py docstring
# claimed otherwise; it was only true of a naive substring search).
#
# Matched as a whole tag with an exact class-token check, NOT as a prefix.
# A naive `class="pvap-reserved-title(?P<cls>[^"]*)"` would also match a
# hypothetical `pvap-reserved-title-mobile` (yielding cls="-mobile", no
# "is-hidden" -> false positive -> a LIVE ad silently hidden), and would match
# nothing at all if `class` were not the first attribute -- failing closed to
# "never sold", so the sweep would report 0 sold forever with no error.
_SPAN_TAG = re.compile(r'<span\b[^>]*>')
_CLASS_ATTR = re.compile(r'\bclass\s*=\s*["\']([^"\']*)["\']')


def _span_classes(html):
    """Yield the class-token list of every <span> on the page."""
    for tag in _SPAN_TAG.findall(html):
        m = _CLASS_ATTR.search(tag)
        if m:
            yield m.group(1).split()


def is_sold_html(html):
    """True when a sold/reserved/deleted badge is actually visible.

    Fails LOUD, not closed: if no badge span is found at all, the page shape
    has changed and we raise rather than silently reporting 'not sold' for
    every ad forever."""
    seen = False
    sold = False
    for classes in _span_classes(html):
        if "pvap-reserved-title" in classes:
            seen = True
            if "is-hidden" not in classes:
                sold = True
    if not seen:
        raise ValueError("no pvap-reserved-title span found -- page markup changed")
    return sold


# Scoped to the extra-info block, matching what the old code read via
# pg.locator("#viewad-extra-info") (kleinanzeigen_engine.py:51). On the pages
# checked the first date on the page happened to be the right one, but that is
# luck: a footer, JSON-LD block, or a recommended-ad module could supply an
# earlier DD.MM.YYYY and write a wrong `posted` for every hit.
_DATE = re.compile(r'\d{2}\.\d{2}\.\d{4}')
# itemprop="upload_date" wraps the value in its own <span>, adjacent in the DOM
# to (but a separate sibling <div> from) a "Hochgeladen" label span -- e.g.
# `<div itemprop="upload_date"><span class="...">8 h</span></div>`. A
# text-scan for "Hochgeladen ([^\n]+)" (what pg.inner_text("body") supported)
# fails on static HTML: turning every tag into a newline for _visible_text()
# puts the label and value on separate lines, so nothing follows "Hochgeladen"
# on its own line. Anchoring on the itemprop instead of scanning rendered text
# sidesteps that entirely. Verified against two real item pages (2026-08-15).
_UPLOADED = re.compile(r'itemprop="upload_date"[^>]*>\s*<span[^>]*>([^<]+)</span>')


def kleinanzeigen_posted_date(html):
    i = html.find("viewad-extra-info")
    scope = html[i:i + 4000] if i >= 0 else html
    m = _DATE.search(scope)
    return m.group(0) if m else None


def vinted_posted_date(html):
    m = _UPLOADED.search(html)
    return _html.unescape(m.group(1)).strip() if m else None
