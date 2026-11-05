import http.server, json, sys, threading, urllib.request
from deploy import viewer_server


def test_results_missing_db_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setitem(viewer_server.DBS, "ghost", tmp_path / "hunt.db")
    srv = http.server.HTTPServer(("127.0.0.1", 0), viewer_server.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        r = urllib.request.urlopen(f"http://127.0.0.1:{srv.server_port}/api/results/ghost")
        assert r.status == 200
        assert json.loads(r.read()) == {"match": [], "maybe": []}
        assert not (tmp_path / "hunt.db").exists()   # viewer runs as root: never create a db
    finally:
        srv.shutdown()
