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
import json, pathlib, sqlite3, sys

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


def main():
    sold = []
    notify = {}
    for db_path in sorted(ROOT.glob("*/hunt.db")):
        product = db_path.parent.name
        cfg_path = db_path.parent / "config.json"
        notify[product] = json.loads(cfg_path.read_text()).get("notify", True) if cfg_path.exists() else True
        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            "SELECT id, price, spec_num, spec_label, title, href FROM ads "
            "WHERE bucket != 'hidden' AND href LIKE '%kleinanzeigen.de%' "
            "AND (meta IS NULL OR json_extract(meta, '$.sold') IS NULL)"
        ).fetchall()
        for id_, price, spec_num, spec_label, title, href in rows:
            if is_sold_from_html(href):
                set_meta(conn, id_, {"sold": True})
                sold.append((product, price, spec_num, spec_label, title, href))
                log.info(f"[sold] {product} {price}EUR {title[:50]}")
            pace("detail")
        conn.commit()
        conn.close()

    log.info(f"{len(sold)} sold, tagged")
    lines = [
        f'{product} · {price}€ · {spec_num}{spec_label or ""} · <a href="{href}">{_esc(title)}</a>'
        for product, price, spec_num, spec_label, title, href in sold
        if notify.get(product, True)
    ]
    send_lines(lines, header="<b>Sold:</b>")


if __name__ == "__main__":
    main()
