"""Sweep selection logic: per-run cap, least-recently-checked ordering, and the
checked_at/sold_at writes the digest depends on. Network + telegram stubbed."""
import json, sqlite3
import common.check_sold as cs

KL = "https://www.kleinanzeigen.de/s-anzeige/x/1"


def _mkdb(path, rows):
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE ads (id TEXT, bucket TEXT, price INT, spec_num INT, "
              "spec_label TEXT, title TEXT, href TEXT, first_seen TEXT, meta TEXT)")
    c.executemany("INSERT INTO ads (id,bucket,price,spec_num,spec_label,title,href,"
                  "first_seen,meta) VALUES (?,?,?,?,?,?,?,?,?)", rows)
    c.commit()
    c.close()


def _meta(db, id_):
    m = sqlite3.connect(db).execute("SELECT meta FROM ads WHERE id=?", (id_,)).fetchone()[0]
    return json.loads(m) if m else None


def _setup(tmp_path, monkeypatch, sold_result):
    prod = tmp_path / "products" / "m5"
    prod.mkdir(parents=True)
    db = prod / "hunt.db"
    _mkdb(db, [
        ("a", "match", 1, 1, "", "t", KL, "f", None),                                # never checked
        ("b", "match", 1, 1, "", "t", KL, "f", json.dumps({"checked_at": "2020-01-01T00:00:00"})),  # old
        ("c", "match", 1, 1, "", "t", KL, "f", json.dumps({"checked_at": "2999-01-01T00:00:00"})),  # recent
        ("d", "match", 1, 1, "", "t", KL, "f", json.dumps({"sold": True})),          # already sold
        ("v", "match", 1, 1, "", "t", "https://www.vinted.de/x", "f", None),         # not kleinanzeigen
    ])
    monkeypatch.setattr(cs, "ROOT", tmp_path)
    monkeypatch.setattr(cs, "CAP", 2)
    monkeypatch.setattr(cs, "pace", lambda *a, **k: None)
    monkeypatch.setattr(cs, "send_lines", lambda *a, **k: None)
    monkeypatch.setattr(cs, "is_sold_from_html", lambda href: sold_result)
    return db


def test_cap_order_and_sold_write(tmp_path, monkeypatch):
    db = _setup(tmp_path, monkeypatch, sold_result=True)
    cs.main()
    # cap=2 -> only a (never) + b (oldest) checked; c (recent) and d (sold) skipped.
    for id_ in ("a", "b"):
        m = _meta(db, id_)
        assert m["sold"] is True and m["sold_at"] and m["checked_at"]
    assert _meta(db, "c") == {"checked_at": "2999-01-01T00:00:00"}   # untouched
    assert _meta(db, "d") == {"sold": True}                          # untouched
    assert _meta(db, "v") is None                                    # vinted excluded


def test_not_sold_writes_only_checked_at(tmp_path, monkeypatch):
    db = _setup(tmp_path, monkeypatch, sold_result=False)
    cs.main()
    m = _meta(db, "a")
    assert m.get("checked_at") and "sold" not in m and "sold_at" not in m
