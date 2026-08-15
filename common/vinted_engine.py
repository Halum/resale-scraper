"""Generic Vinted combo-search engine, shared by every product.

Per-product code supplies only classify()/combos()/config (see e.g.
macbook/spec.py); this module owns fetching (via common/fetch.py,
FlareSolverr), pacing, the scrape/collect loop, price filtering, DB upsert,
and the skip-flag gate. The viewer reads straight from the DB (see
deploy/viewer_server.py) -- no JSON export step.
"""
import re, sys, json
from collections import Counter

from common.browser import pace
from common.store import db, seen_ids, upsert, rows_by_bucket
from common.skipflag import platform_enabled
from common.notify import notify_hits
from common.log import log
from common.fetch import fetch_html, FetchError
from common.parse import parse_vinted_cards, vinted_posted_date

PRICE = re.compile(r"(\d+)[.,]\d+\s*€")

# Give up on posted dates after this many consecutive fetch failures. Without
# it, a dead FlareSolverr costs a full socket timeout + pace("detail") PER HIT;
# at ~30 hits that exceeds run_all_vinted.sh's 45m PRODUCT_TIMEOUT and the
# process gets SIGKILLed before run() ever reaches its upsert() loop -- losing
# the entire run's finds.
DETAIL_FAIL_LIMIT = 5


def catalog_url(q, page, min_price, max_price, extra_qs=""):
    from urllib.parse import quote
    return (f"https://www.vinted.de/catalog?search_text={quote(q)}"
            f"&price_from={min_price}&price_to={max_price}&page={page}&order=newest_first{extra_qs}")


def parse_card(href, title_attr):
    """title attr shape: '<name>, marke: X, modell: Y, zustand: Z, 299,99 €, ...'"""
    name = title_attr.split(",")[0].strip()
    m = PRICE.search(title_attr)
    price = int(m.group(1)) if m else None
    item_id = href.rstrip("/").split("/items/")[-1].split("-")[0]
    return {"id": item_id, "href": href.split("?")[0], "title": name, "text": title_attr, "price": price}


def fetch_date_html(href):
    """Posted date for a confirmed hit. Returns None rather than raising:
    a missing date is cosmetic, and one bad ad must not kill the run."""
    try:
        return vinted_posted_date(fetch_html(href, timeout_ms=30000))
    except FetchError:
        return None


def collect_flaresolverr(seen, only_new, queries, pages, *, min_price, max_price,
                         extra_qs, classify):
    """Scrape all queries via FlareSolverr, filter, then fetch posted dates
    for confirmed hits. Returns (ads, hits, skipped)."""
    ads = {}
    try:
        for q in queries:
            for n in range(1, pages + 1):
                try:
                    html = fetch_html(catalog_url(q, n, min_price, max_price, extra_qs))
                except FetchError as e:
                    log.warning(f"[list] {q!r} page {n}: fetch failed ({e})")
                    break
                cards = parse_vinted_cards(html)
                if not cards:
                    log.info(f"[list] {q!r} page {n}: 0 ads (no-results)")
                    break
                for c in cards:
                    a = parse_card(c["href"], c["title"])
                    if a["price"] is not None:
                        ads.setdefault(a["id"], a)
                log.info(f"[list] {q!r} page {n}: +{len(cards)} ({len(ads)} total)")
                pace("listing")
                if len(cards) < 20:
                    break
    except Exception as e:
        # Deliberately broad -- a parse bug or KeyError here must not discard
        # everything already found. run()'s upsert() loop is downstream of
        # this return.
        log.warning(f"[warn] Vinted scrape died mid-run, keeping partial results: {e}")

    hits, skipped = [], []
    for a in ads.values():
        pr = a["price"]
        if pr is None or not (min_price <= pr <= max_price):
            skipped.append({"reason": "price_range", "price": pr, "title": a["title"], "href": a["href"]})
            continue
        verdict, spec_num, spec_label, reason = classify(a)
        if only_new and a["id"] in seen:
            continue
        if verdict == "skip":
            skipped.append({"reason": reason, "price": pr, "spec_num": spec_num,
                            "spec_label": spec_label, "title": a["title"], "href": a["href"]})
            continue
        hits.append((pr, spec_num, spec_label, a))
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
        log.info(f"[detail hit {i}/{len(hits)}] {pr}EUR {spec_num}{spec_label or ''} {a['title'][:50]}")

    return ads, hits, skipped


def run(*, here, cfg, min_price, max_price, classify, combos, extra_qs="", spec_suffix="GB"):
    if not platform_enabled(cfg, "vinted") and "--force" not in sys.argv:
        log.info("vinted disabled in global_config.json, skipping (use --force to override)")
        return

    only_new = "--all" not in sys.argv
    test = "--test" in sys.argv
    queries = combos()[:2] if test else combos()
    pages = 1 if test else cfg["vinted"]["pages"]

    db_path = here / "hunt.db"
    with db(db_path) as conn:
        known = seen_ids(conn)  # always the true pre-run set, for notify -- independent of --all
        seen = known if only_new else set()
        ads, hits, skipped = collect_flaresolverr(
            seen, only_new, queries, pages, min_price=min_price,
            max_price=max_price, extra_qs=extra_qs, classify=classify)

        for pr, spec_num, spec_label, a in hits:
            upsert(conn, a["id"], "vinted", "match", pr, spec_num, spec_label,
                   a["title"], a["href"], a.get("date"), replace=not only_new)
        new_hits = [h for h in hits if h[3]["id"] not in known]
        if cfg.get("notify", True):
            notify_hits(new_hits, spec_suffix)

        match_total = len(rows_by_bucket(conn)["match"])

    (here / "skipped_vinted.json").write_text(json.dumps(skipped, indent=2, ensure_ascii=False))
    reasons = Counter(s["reason"] for s in skipped)
    log.info(f"scanned {len(ads)} ads, {len(hits)} match this run, {len(skipped)} skipped this run {dict(reasons)} "
             f"(db totals: match={match_total})")
