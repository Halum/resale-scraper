"""Generic Kleinanzeigen combo-search engine, shared by every product.

Per-product code supplies only classify()/combos()/config (see e.g.
macbook/spec.py); this module owns fetching (via common/fetch.py,
FlareSolverr), pacing, the scrape/collect loop, price filtering, DB upsert,
JSON export, and the skip-flag gate. A new product needs zero copy of this
file -- just a spec.py and a 3-line kleinanzeigen.py wrapper.
"""
import re, sys, json
from collections import Counter

from common.browser import pace
from common.store import db, seen_ids, upsert, rows_by_bucket
from common.skipflag import platform_enabled
from common.notify import notify_hits
from common.log import log
from common.fetch import fetch_html, FetchError
from common.parse import parse_kleinanzeigen_cards, kleinanzeigen_posted_date

PRICE = re.compile(r"([\d.]+)\s*€")

# Give up on posted dates after this many consecutive fetch failures -- same
# value and reasoning as vinted_engine.DETAIL_FAIL_LIMIT, defined separately
# here since the two engines are deliberately independent.
DETAIL_FAIL_LIMIT = 5


def price_of(text):
    m = PRICE.search(text)
    return int(m.group(1).replace(".", "")) if m else None


def where_of(text):
    m = re.search(r"\b(\d{5}\s+[^\n]{2,40})", text)
    return m.group(1).strip() if m else "?"


def fetch_date_html(href):
    try:
        return kleinanzeigen_posted_date(fetch_html(href, timeout_ms=30000))
    except FetchError:
        return None


def empty_page_reason_html(html):
    """Classify why a listing page yielded 0 ads -- distinguishes a real
    empty result from a silent block, so a broken session surfaces in the
    log instead of looking like "no listings" for days (see: router profile,
    2026-08-04).

    No "blocked-consent" check: the GDPR banner's raw markup ("Alle
    akzeptieren") is present in EVERY server-rendered response from
    FlareSolverr regardless of consent state or result count -- verified
    2026-08-15 present in a fixture that also yielded 27 real cards. A
    presence check on static HTML can't distinguish blocked from normal and
    would mislabel every genuine zero-result page (see: 22/105 macbook combos
    in the 2026-08-15 08:00 run, all confirmed genuinely 0-result on
    re-fetch, none actually blocked)."""
    if "keine Ergebnisse" in html or "keine passenden" in html.lower():
        return "no-results"
    if "Zugriff verweigert" in html or "Pardon Our Interruption" in html:
        return "blocked-captcha"
    return "unknown"


def srp_url(q, page, min_price, max_price, cat):
    from urllib.parse import quote
    slug = quote(q.replace(" ", "-"))
    p = f"seite:{page}/" if page > 1 else ""
    return (f"https://www.kleinanzeigen.de/s-{p}anzeige:angebote/"
            f"preis:{min_price}:{max_price}/{slug}/k0{cat}")


def filter_ads(ads, seen, only_new, min_price, max_price, classify):
    hits, skipped = [], []
    for a in ads.values():
        pr = price_of(a["text"])
        if pr is None or not (min_price <= pr <= max_price):
            skipped.append({"reason": "price_range", "price": pr, "title": a["title"], "href": a["href"]})
            continue
        verdict, spec_num, spec_label, reason = classify(a)
        if only_new and a["id"] in seen:
            continue
        if verdict == "skip":
            skipped.append({"reason": reason, "price": pr, "spec_num": spec_num, "spec_label": spec_label,
                             "title": a["title"], "href": a["href"]})
            continue
        hits.append((pr, spec_num, spec_label, a))
    return hits, skipped


def collect_flaresolverr(seen, only_new, queries, pages, *, min_price, max_price,
                         cat, classify):
    """Scrape all queries via FlareSolverr, filter, then fetch posted dates
    for confirmed hits. Returns (ads, hits, skipped)."""
    ads = {}
    try:
        for q in queries:
            for n in range(1, pages + 1):
                try:
                    html = fetch_html(srp_url(q, n, min_price, max_price, cat))
                except FetchError as e:
                    log.warning(f"[list] {q!r} page {n}: fetch failed ({e})")
                    break
                batch = parse_kleinanzeigen_cards(html)
                if not batch:
                    log.info(f"[list] {q!r} page {n}: 0 ads ({empty_page_reason_html(html)})")
                    break
                for a in batch:
                    ads.setdefault(a["id"], a)
                log.info(f"[list] {q!r} page {n}: +{len(batch)} ({len(ads)} total)")
                pace("listing")
                if len(batch) < 20:
                    break
    except Exception as e:
        # Deliberately broad -- a parse bug discards the whole run's finds
        # otherwise, since run()'s upsert() loop never runs.
        log.warning(f"[warn] Kleinanzeigen scrape died mid-run, keeping partial results: {e}")

    hits, skipped = filter_ads(ads, seen, only_new, min_price, max_price, classify)
    log.info(f"[filter] {len(hits)} hit, {len(skipped)} skipped (of {len(ads)} scanned)")

    consecutive_failures = 0
    for i, (pr, spec_num, spec_label, a) in enumerate(hits, 1):
        if consecutive_failures >= DETAIL_FAIL_LIMIT:
            log.warning(f"[warn] {DETAIL_FAIL_LIMIT} consecutive detail fetches failed -- "
                        f"skipping posted dates for the remaining {len(hits) - i + 1} hits. "
                        f"Hits are still returned and will be upserted.")
            break
        a["date"] = fetch_date_html(a["href"])
        consecutive_failures = 0 if a["date"] else consecutive_failures + 1
        pace("detail")
        log.info(f"[detail hit {i}/{len(hits)}] {pr}EUR {spec_num}{'?' if spec_label is None else spec_label} "
                 f"{a['title'][:50]}")

    return ads, hits, skipped


def run(*, here, cfg, min_price, max_price, cat, classify, combos, spec_suffix):
    if not platform_enabled(cfg, "kleinanzeigen") and "--force" not in sys.argv:
        log.info("kleinanzeigen disabled in global_config.json, skipping (use --force to override)")
        return

    only_new = "--all" not in sys.argv
    test = "--test" in sys.argv
    queries = combos()[:2] if test else combos()
    pages = 1 if test else cfg["kleinanzeigen"]["pages"]

    db_path = here / "hunt.db"
    with db(db_path) as conn:
        known = seen_ids(conn)  # always the true pre-run set, for notify -- independent of --all
        seen = known if only_new else set()
        ads, hits, skipped = collect_flaresolverr(
            seen, only_new, queries, pages, min_price=min_price,
            max_price=max_price, cat=cat, classify=classify)

        log.info(f"== MATCH == ({len(hits)})")
        for pr, spec_num, spec_label, a in sorted(hits, key=lambda r: r[0]):
            log.info(f"{pr:>5}EUR {str(spec_num or '?'):>3}{spec_suffix} {spec_label or '?':<8} {a['title'][:68]} "
                     f"| {a.get('date') or '?':<10} {where_of(a['text'])} | {a['href']}")

        for pr, spec_num, spec_label, a in hits:
            upsert(conn, a["id"], "kleinanzeigen", "match", pr, spec_num, spec_label,
                   a["title"], a["href"], a.get("date"), replace=not only_new)
        new_hits = [h for h in hits if h[3]["id"] not in known]
        if cfg.get("notify", True):
            notify_hits(new_hits, spec_suffix)

        match_total = len(rows_by_bucket(conn)["match"])

    (here / "skipped.json").write_text(json.dumps(skipped, indent=2, ensure_ascii=False))
    reasons = Counter(s["reason"] for s in skipped)
    log.info(f"scanned {len(ads)} ads, {len(hits)} match this run, {len(skipped)} skipped this run {dict(reasons)} "
             f"(db totals: match={match_total})")
