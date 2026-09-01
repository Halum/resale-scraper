"""24h-window logic for the daily digest -- the one part that can silently
miscount. In-memory DB, no network, no fixtures."""
import datetime, json, sqlite3
from common.digest import counts


def test_counts_window(tmp_path):
    now = datetime.datetime.now()
    inside = (now - datetime.timedelta(hours=1)).isoformat(timespec="seconds")
    outside = (now - datetime.timedelta(hours=30)).isoformat(timespec="seconds")
    cutoff = (now - datetime.timedelta(hours=24)).isoformat(timespec="seconds")

    db = tmp_path / "hunt.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE ads (id TEXT, bucket TEXT, first_seen TEXT, meta TEXT)")
    conn.executemany(
        "INSERT INTO ads (id, bucket, first_seen, meta) VALUES (?,?,?,?)",
        [
            ("a", "match", inside, None),                                 # new: yes
            ("b", "match", outside, None),                                # new: no (old)
            ("c", "hidden", inside, None),                                # new: no (not match)
            ("d", "match", outside, json.dumps({"sold_at": inside})),     # sold: yes
            ("e", "match", outside, json.dumps({"sold_at": outside})),    # sold: no (old)
            ("f", "match", inside, json.dumps({"sold": True})),           # sold: no (no sold_at)
        ])
    conn.commit()
    conn.close()

    new, sold = counts(str(db), cutoff)
    assert new == 2   # a + f
    assert sold == 1  # d
