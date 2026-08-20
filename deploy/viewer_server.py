#!/usr/bin/env python3
"""Static viewer + a small DB-backed API. GET /api/results/<product> reads
straight from that product's hunt.db and returns {'match': [...], 'maybe':
[...]} -- no export/JSON-file step, the page fetches fresh on every load.
POST /api/hide marks an ad 'hidden', which drops it out of that same query
and keeps it out of future scrape runs (still present by id, so seen_ids()
skips it).
"""
import datetime, http.server, json, pathlib, sqlite3, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from common.store import rows_by_bucket, set_meta

ROOT = pathlib.Path(__file__).resolve().parent.parent
DBS = {
    "macbook": ROOT / "products" / "macbook" / "hunt.db",
    "charger": ROOT / "products" / "charger" / "hunt.db",
    "macbookm4": ROOT / "products" / "macbookm4" / "hunt.db",
    "m2": ROOT / "products" / "m2" / "hunt.db",
    "m3": ROOT / "products" / "m3" / "hunt.db",
    "m5": ROOT / "products" / "m5" / "hunt.db",
    "router": ROOT / "products" / "router" / "hunt.db",
    "ipad": ROOT / "products" / "ipad" / "hunt.db",
}


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT / "frontend"), **kw)

    def do_GET(self):
        if self.path.startswith("/api/results/"):
            product = self.path[len("/api/results/"):]
            if product not in DBS:
                self.send_error(404)
                return
            conn = sqlite3.connect(DBS[product])
            try:
                rows = rows_by_bucket(conn)
            finally:
                conn.close()
            body = json.dumps(rows, ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def do_POST(self):
        if self.path not in ("/api/hide", "/api/sold", "/api/price"):
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            data = json.loads(self.rfile.read(length))
            db_path = DBS[data["product"]]
            ad_id = str(data["id"])
            if self.path == "/api/price":
                price = int(data["price"])
        except (KeyError, ValueError, json.JSONDecodeError):
            self.send_error(400)
            return
        conn = sqlite3.connect(db_path)
        if self.path == "/api/hide":
            conn.execute("UPDATE ads SET bucket='hidden' WHERE id=?", (ad_id,))
            verb = "HIDE"
        elif self.path == "/api/price":
            conn.execute("UPDATE ads SET price=? WHERE id=?", (price, ad_id))
            verb = f"PRICE={price}"
        else:
            set_meta(conn, ad_id, {"sold": True})
            verb = "SOLD"
        conn.commit()
        conn.close()
        ts = datetime.datetime.now().isoformat(timespec="seconds")
        print(f"{ts} {verb} {data['product']} {ad_id} from {self.client_address[0]}", flush=True)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def log_message(self, fmt, *args):
        pass   # static GET traffic isn't worth journal noise; /api/hide logs itself explicitly above


if __name__ == "__main__":
    http.server.HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
