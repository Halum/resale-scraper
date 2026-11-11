"""Runs ON the scraper host: python3 apply.py <payload.json> [--commit]
Payload rows: [id, "prod1,prod2", status, checked_at]. Sold -> meta.sold,
sold_at, checked_at (same keys as common/check_sold.py); live -> checked_at.
Merges into meta (other keys such as screen_in survive) and skips ads already
sold, so re-running a payload is harmless. Without --commit it is a dry run."""
import json, sqlite3, sys

rows = json.load(open(sys.argv[1]))
conns, stats = {}, {"sold": 0, "live": 0, "already_sold": 0, "missing": 0}
for ad_id, products, status, checked_at in rows:
    for p in products.split(","):
        c = conns.setdefault(p, sqlite3.connect(f"/opt/scraper/products/{p}/hunt.db"))
        r = c.execute("SELECT json_extract(meta,'$.sold') FROM ads WHERE id=?", (ad_id,)).fetchone()
        if r is None:
            stats["missing"] += 1
            continue
        if r[0]:
            stats["already_sold"] += 1
            continue
        patch = ({"sold": True, "sold_at": checked_at, "checked_at": checked_at}
                 if status == "sold" else {"checked_at": checked_at})
        c.execute("UPDATE ads SET meta=json_patch(coalesce(meta,'{}'),?) WHERE id=?", (json.dumps(patch), ad_id))
        stats[status] += 1
for c in conns.values():
    c.commit() if "--commit" in sys.argv else c.rollback()
print("COMMITTED" if "--commit" in sys.argv else "DRY RUN", stats)
