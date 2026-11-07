---
name: robotvac-deals
description: Find Sajjad the best robot vacuum deal among the scraper's Kleinanzeigen robotvac listings by reading each one in the Orca browser and checking shipping, seller age and rating, buyer protection and condition. Hides listings that fail his rules and any he dismisses. Use when he says "lookup", "any new robot for me", "any new deal for me", "best robovac deal", or dismisses a listing from a previous run.
---

Judge by reading each listing page yourself, no regex scoring. Kleinanzeigen only: Vinted robotvac rows stay on the deals page but are out of scope here.

## 1. Get the candidates

```bash
curl -s https://deals.shossain.tech/api/results/robotvac | python3 -c "
import json,sys; d=json.load(sys.stdin)
for x in sorted(d['match'], key=lambda x: x[1]):
    if 'kleinanzeigen' in x[5] and not (x[8] or {}).get('sold'):
        print(x[0], x[1], x[2], '|', x[4], '|', x[5])"
```

Columns: id, price, model, title, url. Hidden rows are already left out by the API.

## 2. Read each listing in Orca

Use the `orca-cli` skill. Per listing:

```bash
p=$(orca tab create --url "<url>" --json | python3 -c "import json,sys; print(json.load(sys.stdin)['result']['browserPageId'])")
orca wait --page $p --load load --json
orca exec --page $p --command "read" --json
orca tab close --page $p --json
```

Close every tab right after reading it, whatever the verdict: Sajjad opens the ones he wants from the links in the report. Before reporting, check `orca tab list --json` shows none of the listing tabs this run opened.

The page text between "Bild in Vollbild" and "Nachricht schreiben" holds the price, shipping line, condition (`Zustand`) and description; the seller block follows it. A deleted or reserved listing says so near the top.

## 3. Rules (all must pass)

| Rule | Pass when the page shows |
|---|---|
| Shipping | `Versand ab ...` or `Versand möglich`. `Nur Abholung` fails: Sajjad cannot pick up. |
| Buyer protection | `Käuferschutz` or `Direkt kaufen`. Both show when logged out. |
| Seller age | `Aktiv seit <date>` at least 3 years before today. |
| Seller rating | At least one positive badge: `TOP Zufriedenheit`, `Freundlich`, `Zuverlässig` or `Sehr zuverlässig`. |
| Condition | Fully working, nothing to fix. Fails when `Zustand` is `Defekt` or the description names any defect, however small: faulty, for parts, stops working, a broken, leaking or missing part (water tank, mop, brush, sensor, station), a feature that does not work, or anything the buyer must replace or repair. A weaker battery from normal age is fine; mention it. |
| Available | Not deleted, `Reserviert` or sold. |
| Upgrade | The model clearly beats the Dreame D9 Pro Sajjad already owns (4,000 Pa, 5,200 mAh, basic mop, no station): clearly more suction (above 4,000 Pa, e.g. the Dreame D10s at 5,000 Pa), better mopping (a vibrating or sonic mop, rotating mop pads, a mop-washing station), or camera obstacle avoidance. A self-emptying station alone is not enough: Sajjad is fine emptying the bin by hand (so the Dreame D10 and D10 Plus fail), and same suction with a smaller battery (Xiaomi S12) fails. Check the spec with a web search when unsure. |

## 4. Act on the result

- Fails a rule: hide it.
  ```bash
  curl -s -X POST https://deals.shossain.tech/api/hide -H 'Content-Type: application/json' -d '{"product":"robotvac","id":"<id>"}'
  ```
- Deleted or sold: mark it sold instead (`/api/sold`, same body).
- Passes: goes in the report.

## 5. Report

Always list every listing that passes, old and new together, so Sajjad never has to remember earlier reports. Mark a listing new when its `first_seen` (column 8 of the API row) is after the previous update. Rank the passing listings, best first. Model ranking, best first: Dreame L10s Ultra (self-emptying, mop-washing station), Roborock S7 MaxV (camera obstacle avoidance), Roborock S7 (sonic mop), Roborock Q7 Max / Q7 L5+ (strong vacuum, basic mop), then the rest. Within a model, rank by total price: price + shipping + buyer-protection fee. Included spare parts (side or main brushes, mop cloths, filters, dust bags, a spare battery) raise a listing above a similar one without them, since Sajjad then does not need to buy them; a few euros more is worth it. Name the included parts in the report.

Always show the deals as one table with exactly these 5 columns: `#`, `Model`, `Total` (e.g. `71.74 €`), `Note`, `Link` (the exact listing URL from step 1, never retyped from memory). `Note` is one short line: "new" first when it is new, then the included spare parts, then anything worth asking the seller (no dock mentioned, ad-copy text that never says it was tested, battery age). Leave out seller years, badges and condition: every listed deal already passed those rules. Then a short list of what was hidden and why, one line each. Do not name sellers.

## 6. Dismissals

When Sajjad dismisses a listing ("dismiss 2", "skip the S7"), hide it with the same `/api/hide` call. It then leaves the deals page and is not offered again.
