# AGENTS.md

Guidance for an agent working in this repo. See `README.md` for the project overview, architecture, and commands — this file only covers what the agent can't infer from the code or README.

## Gotchas

- **Kleinanzeigen vs Vinted search strategy differs per product** (except MacBooks). Vinted's search wants query words to roughly match the title; a Kleinanzeigen-safe keyword can silently miss real listings on Vinted (different wording, different language). Check for a `combos_vinted()` in `spec.py` before assuming `combos()` is shared — see `router/spec.py` for why (French "routeur"/"mesh system" titles were being missed entirely).
- **`classify()` is title-only, no field access beyond `ad["title"]`.** Returns `("hit"|"skip", spec_num_or_None, spec_label_or_None, reason_or_None)`. When tuning a regex, check the `reason` counts printed at end of run, not just the hit count — a spike in one skip reason is usually the actual signal.
- **Don't build a hide/filter feature with regex or keyword matching when the ask is "judge by reading the title."** Read titles and reason about them directly (see `.agents/skills/mac14-only/` for the pattern: a fetch-only script + a hide-by-id script, with zero classification logic in either — the judgment happens in the conversation, not in code).
- **Page fetching goes through FlareSolverr** (`common/fetch.py`), not a local browser. `FLARESOLVERR_URL` is read from the environment (see `.env.example`) — the scraper host runs no Chrome/patchright at all.
- **Deploy is manual, not automatic.** After editing anything under `common/`, a product's `spec.py`/`config.json`, or `deploy/`, changes must be `scp`'d to the host and copied into place as the `scraper` user before they take effect. Editing a local file does nothing on its own.
- **`deploy/viewer_server.py` needs a restart** after changes to itself or `common/store.py`. `index.html` needs none (static, fetched fresh each load).
