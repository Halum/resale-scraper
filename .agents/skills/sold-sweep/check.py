#!/usr/bin/env python3
"""check.py <group> next          -> next unchecked ad id, or DONE
check.py <group> <page_id> <id>   -> open the ad in that Orca tab, classify,
                                     record in <group>.db, print one line.
Sold = redirected off the ad page (deleted) or a Gelöscht/Verkauft/Reserviert
prefix in the #viewad-title heading, as Orca's browser renders the page."""
import datetime, json, os, pathlib, random, sqlite3, subprocess, sys, time

W = pathlib.Path(os.environ.get("SOLD_SWEEP_DIR", pathlib.Path.home() / ".cache/sold-sweep"))
EXPR = r"""(()=>{const u=location.href;if(!u.includes('/s-anzeige/'))return 'sold|removed->'+u;
const h=document.querySelector('#viewad-title');if(!h)return 'unknown|no title: '+document.title.slice(0,60);
const s=h.querySelector('span:not(.is-hidden)');if(s){const t=s.textContent.trim();if(/Verkauft|Reserviert|Gelöscht/.test(t))return 'sold|'+t}
return 'live|'})()"""


def orca(*a):
    r = subprocess.run(["orca", *a, "--json"], capture_output=True, text=True, timeout=90)
    try:
        return json.loads(r.stdout)
    except ValueError:
        return {"ok": False, "error": (r.stdout + r.stderr)[:200]}


group = sys.argv[1]
ads = {a["id"]: a for a in json.loads((W / f"{group}.json").read_text())}
db = sqlite3.connect(W / f"{group}.db")
db.execute("CREATE TABLE IF NOT EXISTS results (id TEXT PRIMARY KEY, products TEXT, href TEXT, "
           "status TEXT, detail TEXT, checked_at TEXT)")

if sys.argv[2] == "next":
    done = {r[0] for r in db.execute("SELECT id FROM results WHERE status != 'error'")}
    print(next((i for i in ads if i not in done), "DONE"))
    sys.exit()

page, ad_id = sys.argv[2], sys.argv[3]
a = ads[ad_id]
g = orca("goto", "--page", page, "--url", a["href"])
if not g.get("ok"):
    print(f"{ad_id} error TAB_OR_NAV_FAILED {g.get('error', g)}")
    sys.exit(2)
orca("wait", "--page", page)
e = orca("eval", "--page", page, "--expression", EXPR)
res = (e.get("result") or {}).get("result") if e.get("ok") else None
status, _, detail = (res or "error|eval failed").partition("|")
db.execute("INSERT OR REPLACE INTO results VALUES (?,?,?,?,?,?)",
           (ad_id, ",".join(a["products"]), a["href"], status, detail,
            datetime.datetime.now().isoformat(timespec="seconds")))
db.commit()
print(ad_id, status, detail)
time.sleep(random.uniform(5, 10))  # ponytail: random pace per ad; 4 s fixed with 10 tabs got the IP blocked
