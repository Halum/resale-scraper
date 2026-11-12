#!/usr/bin/env python3
"""fetch.py [--products a,b] [--like text] [--limit 500] [--size 100]
Pull the not-yet-sold Kleinanzeigen ads from the scraper host, one entry per
ad id (an ad can sit in several product DBs), least-recently-checked first,
keep --limit of them, and split those into work groups G1..Gn of --size ads in
the work dir. Starts a fresh run: old group files go. The next sweep picks up
where this one stopped, because every pushed ad gets a fresh checked_at."""
import argparse, json, os, pathlib, subprocess

W = pathlib.Path(os.environ.get("SOLD_SWEEP_DIR", pathlib.Path.home() / ".cache/sold-sweep"))
ap = argparse.ArgumentParser()
ap.add_argument("--products", default="macbook,macbookm4,m2,m3,m5")
ap.add_argument("--like", help="only titles containing this text (case-insensitive)")
ap.add_argument("--limit", type=int, default=500, help="ads per sweep (5 agents of 100)")
ap.add_argument("--size", type=int, default=100)
a = ap.parse_args()

remote = r"""
import sqlite3, json, sys
for p in sys.argv[1].split(','):
    c = sqlite3.connect(f'/opt/scraper/products/{p}/hunt.db')
    for i, t, h, ck in c.execute("SELECT id, title, href, json_extract(meta, '$.checked_at') FROM ads "
                                 "WHERE href LIKE '%kleinanzeigen.de%' "
                                 "AND (meta IS NULL OR json_extract(meta, '$.sold') IS NULL)"):
        print(json.dumps([p, str(i), t, h, ck or '']))
"""
out = subprocess.run(["ssh", "scraper", "python3", "-", a.products], input=remote,
                     capture_output=True, text=True, check=True).stdout
ads = {}
for line in out.splitlines():
    p, i, t, h, ck = json.loads(line)
    if a.like and a.like.lower() not in t.lower():
        continue
    ad = ads.setdefault(i, {"id": i, "title": t, "href": h, "products": [], "checked_at": ck})
    ad["products"].append(p)
    ad["checked_at"] = min(ad["checked_at"], ck)  # never-checked ("") sorts first

W.mkdir(parents=True, exist_ok=True)
for f in list(W.glob("G*.json")) + list(W.glob("G*.db")):
    f.unlink()
everything = sorted(ads.values(), key=lambda ad: ad["checked_at"])
L = everything[:a.limit]
for n in range(0, len(L), a.size):
    (W / f"G{n // a.size + 1}.json").write_text(json.dumps(L[n:n + a.size], ensure_ascii=False))
print(f"{len(L)} of {len(everything)} unsold ads -> {-(-len(L) // a.size)} groups of up to {a.size} in {W}; "
      f"{len(everything) - len(L)} left for later sweeps")
