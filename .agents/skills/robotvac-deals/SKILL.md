---
name: robotvac-deals
description: Find Sajjad the best robot vacuum deal among the scraper's Kleinanzeigen robotvac listings by opening each one in the Orca browser and checking shipping, seller age and rating, buyer protection and condition. Hides listings that fail his rules and any he dismisses. Use when he says "lookup", "any new robot for me", "any new deal for me", "best robovac deal", or dismisses a listing from a previous run.
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
```

The page text between "Bild in Vollbild" and "Nachricht schreiben" holds the price, shipping line, condition (`Zustand`) and description; the seller block follows it. A deleted or reserved listing says so near the top.

## 3. Rules (all must pass)

| Rule | Pass when the page shows |
|---|---|
| Shipping | `Versand ab ...` or `Versand möglich`. `Nur Abholung` fails: Sajjad cannot pick up. |
| Buyer protection | `Käuferschutz` or `Direkt kaufen`. Both show when logged out. |
| Seller age | `Aktiv seit <date>` at least 3 years before today. |
| Seller rating | At least one positive badge: `TOP Zufriedenheit`, `Freundlich`, `Zuverlässig` or `Sehr zuverlässig`. |
| Condition | `Zustand` is not `Defekt`, and the description does not say it is faulty, sold as faulty, for parts, or stops working. |
| Available | Not deleted, `Reserviert` or sold. |

## 4. Act on the result

- Fails a rule: hide it and close its tab.
  ```bash
  curl -s -X POST https://deals.shossain.tech/api/hide -H 'Content-Type: application/json' -d '{"product":"robotvac","id":"<id>"}'
  ```
- Deleted or sold: mark it sold instead (`/api/sold`, same body) and close its tab.
- Passes: keep its tab open in Orca for Sajjad to look at.

## 5. Report

Rank the passing listings, best first. Model ranking, best first: Dreame L10s Ultra (self-emptying, mop-washing station), Roborock S7 MaxV (camera obstacle avoidance), Roborock S7 (sonic mop), Roborock Q7 Max / Q7 L5+ (strong vacuum, basic mop), then the rest. Within a model, rank by total price: price + shipping + buyer-protection fee. Included spare parts (side or main brushes, mop cloths, filters, dust bags, a spare battery) raise a listing above a similar one without them, since Sajjad then does not need to buy them; a few euros more is worth it. Name the included parts in the report.

For each: model, total price, link, seller years and badges, condition, one line on anything worth asking the seller (no dock mentioned, ad-copy text that never says it was tested, battery age). Then a short list of what was hidden and why, one line each. Do not name sellers.

## 6. Dismissals

When Sajjad dismisses a listing ("dismiss 2", "skip the S7"), hide it with the same `/api/hide` call and close its tab. It then leaves the deals page and is not offered again.
