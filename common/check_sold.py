#!/usr/bin/env python3
"""Daily sweep across every product's DB: visit each not-yet-checked
Kleinanzeigen ad, check for the sold marker (data-soldlabel="Verkauft" on the
title element), tag sold ones with meta.sold=true (bucket untouched -- the
viewer's Sold filter chip handles hiding, same pattern as meta.screen_in),
and send one combined Telegram message listing what got pulled.

Run:  uv run python common/check_sold.py
Vinted ads are skipped -- the sold marker is Kleinanzeigen-specific and
unconfirmed on Vinted.
"""
import datetime, json, os, pathlib, sqlite3, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from common.browser import pace
from common.fetch import fetch_html, FetchError
from common.parse import is_sold_html
from common.notify import _esc, send_lines
from common.store import set_meta
from common.log import log

ROOT = pathlib.Path(__file__).parent.parent


def is_sold_from_html(href):
    """The 'Reserviert'/'Verkauft'/'Gelöscht' badge renders as two spans; the
    inactive one carries `is-hidden`. On a live ad BOTH carry it. An earlier
    version of this file claimed static HTML could not tell them apart -- that
    is true only of a naive substring search for the words. The `is-hidden`
    class IS in the markup, so the distinction is static.

    Every failure path returns False. Reporting "not sold" leaves an ad
    visible, which is recoverable on the next sweep; reporting "sold" hides it
    from the viewer, which the user may never notice."""
    try:
        return is_sold_html(fetch_html(href, timeout_ms=30000))
    except (FetchError, ValueError):
        return False


# Max ads checked per run. Bounds runtime so the sweep always finishes inside
# the cron's 90m cap instead of running for hours (the full unsold-ad set is
# ~3500 and grows). Ads are picked least-recently-checked first, so successive
# runs cycle through the whole backlog. Override with CHECK_SOLD_CAP, or
# --limit N for a one-off.
CAP = int(os.environ.get("CHECK_SOLD_CAP", "400"))


def main():
    cap = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else CAP

    conns, notify, cands = {}, {}, []
    for db_path in sorted(ROOT.glob("products/*/hunt.db")):
        product = db_path.parent.name
        cfg_path = db_path.parent / "config.json"
        notify[product] = json.loads(cfg_path.read_text()).get("notify", True) if cfg_path.exists() else True
        conn = sqlite3.connect(db_path)
        conns[product] = conn
        for id_, price, spec_num, spec_label, title, href, meta in conn.execute(
            "SELECT id, price, spec_num, spec_label, title, href, meta FROM ads "
            "WHERE bucket != 'hidden' AND href LIKE '%kleinanzeigen.de%' "
            "AND (meta IS NULL OR json_extract(meta, '$.sold') IS NULL)"
        ):
            checked_at = (json.loads(meta).get("checked_at") if meta else None) or ""
            cands.append((checked_at, product, id_, price, spec_num, spec_label, title, href))

    # Least-recently-checked first: never-checked ("") sort ahead of everything,
    # so brand-new listings (which churn fastest) get priority; older live ads
    # cycle round over subsequent days.
    cands.sort(key=lambda c: c[0])
    batch = cands[:cap]

    sold = []
    now = datetime.datetime.now().isoformat(timespec="seconds")
    for checked_at, product, id_, price, spec_num, spec_label, title, href in batch:
        conn = conns[product]
        if is_sold_from_html(href):
            # sold_at drives the daily digest's Sold count -- without it a marked
            # ad is invisible to digest.py.
            set_meta(conn, id_, {"sold": True, "sold_at": now, "checked_at": now})
            sold.append((product, price, spec_num, spec_label, title, href))
            log.info(f"[sold] {product} {price}EUR {title[:50]}")
        else:
            set_meta(conn, id_, {"checked_at": now})
        # Commit per ad so a timeout kill keeps progress + the updated
        # checked_at (the old end-of-product commit lost a whole product's work
        # when ipad never finished, and re-checked the same ads next run).
        conn.commit()
        pace("detail")

    for c in conns.values():
        c.commit()
        c.close()

    log.info(f"{len(sold)} sold of {len(batch)} checked ({len(cands)} unsold total)")
    lines = [
        f'{product} · {price}€ · {spec_num}{spec_label or ""} · <a href="{href}">{_esc(title)}</a>'
        for product, price, spec_num, spec_label, title, href in sold
        if notify.get(product, True)
    ]
    send_lines(lines, header="<b>Sold:</b>")


if __name__ == "__main__":
    main()
