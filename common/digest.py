#!/usr/bin/env python3
"""Daily Telegram digest: New (found) and Sold per product over the last 24h.
Run once a day from cron. New = first_seen within 24h (match bucket). Sold =
meta.sold_at within 24h (set by the viewer's /api/sold). Cumulative totals are
deliberately omitted -- the digest is about daily movement, not the running
count.
"""
import datetime, glob, json, pathlib, sqlite3, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from common.notify import send_lines   # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Display order + labels, mirrors the viewer's product tabs.
PRODUCTS = [("macbook", "MacBook"), ("macbookm4", "M4"), ("m5", "M5"),
            ("m2", "M2"), ("m3", "M3"), ("ipad", "iPad"),
            ("charger", "Charger"), ("router", "Router")]


def counts(db, cutoff):
    """(new, sold) for one DB since `cutoff` (ISO string). New = match ads
    first seen in window; sold = ads whose meta.sold_at is in window."""
    c = sqlite3.connect(db)
    try:
        new = c.execute(
            "SELECT count(*) FROM ads WHERE bucket='match' AND first_seen>=?",
            (cutoff,)).fetchone()[0]
        sold = sum(
            1 for (m,) in c.execute("SELECT meta FROM ads WHERE meta IS NOT NULL")
            if (json.loads(m).get("sold_at") or "") >= cutoff)
    finally:
        c.close()
    return new, sold


def build_lines(cutoff, today):
    rows, tn, ts = [], 0, 0
    for key, label in PRODUCTS:
        db = ROOT / "products" / key / "hunt.db"
        if not db.exists():
            continue
        n, s = counts(db, cutoff)
        tn += n
        ts += s
        rows.append(f"{label:<8} {n:>4} {s:>5}")
    header = f"\U0001F4CA Deal Hunter: {today:%d-%m-%Y}"
    body = ["<pre>", f"{'Product':<8} {'New':>4} {'Sold':>5}", *rows,
            "-" * 19, f"{'Total':<8} {tn:>4} {ts:>5}", "</pre>"]
    return header, body


def main():
    cutoff = (datetime.datetime.now() - datetime.timedelta(hours=24)).isoformat(timespec="seconds")
    header, body = build_lines(cutoff, datetime.date.today())
    send_lines(body, header=header)


if __name__ == "__main__":
    main()
