"""SQLite-backed ad store, shared by every product's kleinanzeigen.py/vinted.py.

One row per ad, keyed by its site-unique id. Already-seen ads are skipped
outright (no re-fetch, no re-classify). Both platforms (Kleinanzeigen/Vinted)
write into the same per-product DB. The viewer reads straight from this DB via
deploy/viewer_server.py's /api/results/<product> -- no export/JSON-file step.
"""
import datetime, json, sqlite3, contextlib

SCHEMA = """
CREATE TABLE IF NOT EXISTS ads (
  id TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  bucket TEXT NOT NULL,       -- 'match' | 'maybe'
  price INTEGER,
  spec_num INTEGER,           -- ram (macbook) or watt (charger)
  spec_label TEXT,            -- chip (macbook) or brand (charger)
  title TEXT,
  href TEXT,
  posted TEXT,                -- date/relative-time string as scraped
  first_seen TEXT NOT NULL,
  meta TEXT                   -- JSON blob, e.g. {"screen_in": 16} for hidden non-14in MacBooks
);
"""


@contextlib.contextmanager
def db(path):
    conn = sqlite3.connect(path)
    conn.execute(SCHEMA)
    try:
        conn.execute("ALTER TABLE ads ADD COLUMN meta TEXT")
    except sqlite3.OperationalError:
        pass   # already migrated
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def seen_ids(conn):
    return {r[0] for r in conn.execute("SELECT id FROM ads")}


def upsert(conn, ad_id, source, bucket, price, spec_num, spec_label, title, href, posted, replace=False):
    verb = "INSERT OR REPLACE" if replace else "INSERT OR IGNORE"
    conn.execute(
        f"{verb} INTO ads (id, source, bucket, price, spec_num, spec_label, title, href, posted, first_seen) "
        "VALUES (?,?,?,?,?,?,?,?,?, COALESCE((SELECT first_seen FROM ads WHERE id=?), ?))",
        (ad_id, source, bucket, price, spec_num, spec_label, title, href, posted,
         ad_id, datetime.datetime.now().isoformat(timespec="seconds")))


def hide(conn, ad_id):
    """Mark an ad 'hidden' -- drops out of rows_by_bucket()'s 'match' list
    (what the viewer reads) but its id stays in the table, so seen_ids() still
    covers it and future only_new runs never re-add it."""
    conn.execute("UPDATE ads SET bucket='hidden' WHERE id=?", (ad_id,))


def set_meta(conn, ad_id, meta):
    """Merge `meta` (dict) into the ad's existing meta JSON blob, e.g.
    set_meta(conn, id, {"screen_in": 16})."""
    row = conn.execute("SELECT meta FROM ads WHERE id=?", (ad_id,)).fetchone()
    existing = json.loads(row[0]) if row and row[0] else {}
    existing.update(meta)
    conn.execute("UPDATE ads SET meta=? WHERE id=?", (json.dumps(existing), ad_id))


def rows_by_bucket(conn):
    """{'match': [...], 'maybe': [...]}, each row [id, price, spec_num,
    spec_label, title, href, posted, first_seen, meta] -- the shape the
    viewer's /api/results/<product> serves directly, and what engines use for
    the 'db totals' count at the end of a run. meta is parsed JSON (dict) or
    None."""
    rows = {"match": [], "maybe": []}
    for id_, bucket, price, spec_num, spec_label, title, href, posted, first_seen, meta in conn.execute(
            "SELECT id, bucket, price, spec_num, spec_label, title, href, posted, first_seen, meta FROM ads "
            "ORDER BY price"):
        rows.setdefault(bucket, []).append(
            [id_, price, spec_num, spec_label, title, href, posted, first_seen, json.loads(meta) if meta else None])
    return rows
