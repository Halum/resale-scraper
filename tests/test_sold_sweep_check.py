import json, os, pathlib, sqlite3, subprocess, sys

CHECK = pathlib.Path(__file__).parent.parent / ".agents/skills/sold-sweep/check.py"


def run_next(tmp_path):
    env = {**os.environ, "SOLD_SWEEP_DIR": str(tmp_path)}
    return subprocess.run([sys.executable, str(CHECK), "G1", "next"], env=env,
                          capture_output=True, text=True, check=True).stdout.strip()


def make_group(tmp_path, ids, results):
    (tmp_path / "G1.json").write_text(json.dumps([{"id": i, "href": "", "products": ["p"]} for i in ids]))
    db = sqlite3.connect(tmp_path / "G1.db")
    db.execute("CREATE TABLE results (id TEXT PRIMARY KEY, products TEXT, href TEXT, "
               "status TEXT, detail TEXT, checked_at TEXT)")
    db.executemany("INSERT INTO results VALUES (?,'p','',?,'','')", results)
    db.commit()


def test_unknown_and_error_are_retried_after_unchecked_ads(tmp_path):
    make_group(tmp_path, ["1", "2", "3", "4"], [("1", "unknown"), ("2", "sold"), ("3", "error")])
    assert run_next(tmp_path) == "4"  # unchecked first, so a stuck ad can't block the rest


def test_unknown_is_handed_out_again(tmp_path):
    make_group(tmp_path, ["1", "2"], [("1", "unknown"), ("2", "live")])
    assert run_next(tmp_path) == "1"


def test_done_when_only_sold_and_live(tmp_path):
    make_group(tmp_path, ["1", "2"], [("1", "sold"), ("2", "live")])
    assert run_next(tmp_path) == "DONE"
