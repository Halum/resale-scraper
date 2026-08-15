"""HTTP client for FlareSolverr -- replaces in-process Chrome entirely.

Why this exists: Playwright enforces its timeouts inside the Node driver, so
when that driver stops answering, the Python client blocks on the pipe with no
deadline (see the 2026-08-14 outage: check_sold.py wedged 10h, charger/vinted.py
5h40m, both futex_do_wait, each pinning a Chrome tree until the container hit
its 4GB cap). An HTTP call has a real socket timeout that the OS enforces, so
that whole failure class disappears.
"""
import json
import os
import urllib.error
import urllib.request

ENDPOINT = os.environ.get("FLARESOLVERR_URL", "")


class FetchError(Exception):
    pass


def fetch_html(url, *, timeout_ms=60000, endpoint=None):
    """Return the fully-rendered HTML for `url`, via FlareSolverr.

    timeout_ms is FlareSolverr's own per-page budget. The socket timeout is
    deliberately larger (timeout_ms + 30s) so the server's own timeout fires
    first and returns a useful error, rather than us tearing down the socket
    and leaving a browser tab live on its side.
    """
    endpoint = endpoint or ENDPOINT
    if not endpoint:
        raise FetchError("FLARESOLVERR_URL not set -- see .env.example")
    payload = json.dumps({
        "cmd": "request.get",
        "url": url,
        "maxTimeout": timeout_ms,
    }).encode()
    req = urllib.request.Request(
        endpoint, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=(timeout_ms / 1000) + 30) as r:
            body = json.load(r)
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
        raise FetchError(f"{url}: transport failure: {e}") from e

    if body.get("status") != "ok":
        raise FetchError(f"{url}: flaresolverr status={body.get('status')} msg={body.get('message')}")
    solution = body.get("solution") or {}
    http_status = solution.get("status")
    if http_status != 200:
        raise FetchError(f"{url}: http {http_status}")
    html = solution.get("response") or ""
    if not html:
        raise FetchError(f"{url}: empty response body")
    return html
