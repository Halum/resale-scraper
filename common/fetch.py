"""HTTP client for FlareSolverr -- replaces in-process Chrome entirely.

Why this exists: Playwright enforces its timeouts inside the Node driver, so
when that driver stops answering, the Python client blocks on the pipe with no
deadline (see the 2026-08-14 outage: check_sold.py wedged 10h, charger/vinted.py
5h40m, both futex_do_wait, each pinning a Chrome tree until the container hit
its 4GB cap). An HTTP call has a real socket timeout that the OS enforces, so
that whole failure class disappears.

Sessions: FlareSolverr can keep a warm browser context alive between calls
(sessions.create), which skips the per-request Chrome launch -- measured ~13s
sessionless vs ~8.6s warm on a Vinted catalog page. We reuse one named session
per platform (FLARESOLVERR_SESSION=klein|vinted, set by the run scripts), shared
server-side across every product process in a run. We deliberately never
destroy it: the flaresolverr-janitor sidecar GCs sessions older than 72h, and a
named session is auto-recreated on demand -- so a janitor sweep, a FlareSolverr
restart, or a deploy costs at most one cold fetch, never a hard failure. Set
FLARESOLVERR_SESSIONS=0 (e.g. in the ENV_FILE secret) to force sessionless
without editing the run scripts.
"""
import json
import os
import urllib.error
import urllib.request

ENDPOINT = os.environ.get("FLARESOLVERR_URL", "")
# Session name for this process, set per-platform by the run scripts. Empty in
# manual/one-off runs -> sessionless, which is fine.
DEFAULT_SESSION = os.environ.get("FLARESOLVERR_SESSION", "")

_TRANSPORT_ERRORS = (urllib.error.URLError, OSError, json.JSONDecodeError)


class FetchError(Exception):
    pass


def _sessions_on():
    # Runtime kill-switch: read live so a secret change takes effect without a
    # code change. Default on.
    return os.environ.get("FLARESOLVERR_SESSIONS", "1").strip().lower() not in ("0", "false", "no")


def _post(endpoint, payload, timeout_ms):
    req = urllib.request.Request(
        endpoint, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    # socket timeout deliberately larger than FlareSolverr's own page budget so
    # the server times out first and returns a useful error (see fetch_html).
    with urllib.request.urlopen(req, timeout=(timeout_ms / 1000) + 30) as r:
        return json.load(r)


def _create_session(endpoint, name):
    """Best-effort create; the following request.get retry surfaces any real
    error. Harmless if the session already exists."""
    try:
        _post(endpoint, {"cmd": "sessions.create", "session": name}, 30000)
    except _TRANSPORT_ERRORS:
        pass


def _is_missing_session(body):
    return "session" in (body.get("message") or "").lower()


def fetch_html(url, *, timeout_ms=60000, endpoint=None, session=None):
    """Return the fully-rendered HTML for `url`, via FlareSolverr.

    timeout_ms is FlareSolverr's own per-page budget. The socket timeout is
    deliberately larger (timeout_ms + 30s) so the server's own timeout fires
    first and returns a useful error, rather than us tearing down the socket
    and leaving a browser tab live on its side.

    When a session name is active (param, else FLARESOLVERR_SESSION env, unless
    FLARESOLVERR_SESSIONS=0), the request reuses that warm browser context. If
    the session has been GC'd or lost, we recreate it once and retry -- so the
    caller never sees a spurious failure from a swept session.
    """
    endpoint = endpoint or ENDPOINT
    if not endpoint:
        raise FetchError("FLARESOLVERR_URL not set -- see .env.example")

    sess = (session or DEFAULT_SESSION) if _sessions_on() else ""
    payload = {"cmd": "request.get", "url": url, "maxTimeout": timeout_ms}
    if sess:
        payload["session"] = sess

    try:
        body = _post(endpoint, payload, timeout_ms)
    except _TRANSPORT_ERRORS as e:
        raise FetchError(f"{url}: transport failure: {e}") from e

    # Session vanished (janitor sweep / FlareSolverr restart): recreate + retry
    # once. Versions that auto-create on miss never hit this branch.
    if sess and body.get("status") != "ok" and _is_missing_session(body):
        _create_session(endpoint, sess)
        try:
            body = _post(endpoint, payload, timeout_ms)
        except _TRANSPORT_ERRORS as e:
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
