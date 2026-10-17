"""Session wiring for the FlareSolverr client -- the parts that can silently
break fetching: whether a session name is attached, and recovery when the
named session is broken. No network; _post is stubbed."""
import common.fetch as fetch

OK = {"status": "ok", "solution": {"status": 200, "response": "<html>hi</html>"}}
REDIRECTED = {"status": "ok", "solution": {
    "status": 200, "response": "<html>hi</html>", "url": "http://elsewhere"}}
MISSING = {"status": "error", "message": "Session does not exist"}
# Real payload seen live 2026-09-19: a crashed browser tab inside an existing,
# still-listed session. Doesn't mention "session" at all -- the bug that let a
# named session fail every request for ~2h until fixed by hand.
CRASHED = {"status": "error", "message": 'Error: Error solving the challenge. '
           'Message: tab crashed\n  (Session info: chrome=148.0.7778.178)'}


def _stub_post(responses, calls):
    """Return a _post that yields queued responses and records each payload."""
    it = iter(responses)
    def _post(endpoint, payload, timeout_ms):
        calls.append(payload)
        return next(it)
    return _post


def test_session_attached_when_named(monkeypatch):
    calls = []
    monkeypatch.setenv("FLARESOLVERR_SESSIONS", "1")
    monkeypatch.setattr(fetch, "_post", _stub_post([OK], calls))
    html = fetch.fetch_html("http://x", endpoint="http://fs", session="klein")
    assert html == "<html>hi</html>"
    assert calls[0].get("session") == "klein"


def test_kill_switch_forces_sessionless(monkeypatch):
    calls = []
    monkeypatch.setenv("FLARESOLVERR_SESSIONS", "0")
    monkeypatch.setattr(fetch, "_post", _stub_post([OK], calls))
    fetch.fetch_html("http://x", endpoint="http://fs", session="klein")
    assert "session" not in calls[0]   # kill-switch wins over the name


def test_resets_and_retries_on_missing_session(monkeypatch):
    calls, reset = [], []
    monkeypatch.setenv("FLARESOLVERR_SESSIONS", "1")
    monkeypatch.setattr(fetch, "_post", _stub_post([MISSING, OK], calls))
    monkeypatch.setattr(fetch, "_reset_session", lambda ep, name: reset.append(name))
    html = fetch.fetch_html("http://x", endpoint="http://fs", session="vinted")
    assert html == "<html>hi</html>"   # second attempt succeeds
    assert reset == ["vinted"]         # session was reset once
    assert len(calls) == 2             # exactly one retry, no loop


def test_resets_and_retries_on_crashed_tab(monkeypatch):
    """The bug this fixes: a crashed-tab failure doesn't mention 'session' in
    its message, so a narrower message-content check never caught it."""
    calls, reset = [], []
    monkeypatch.setenv("FLARESOLVERR_SESSIONS", "1")
    monkeypatch.setattr(fetch, "_post", _stub_post([CRASHED, OK], calls))
    monkeypatch.setattr(fetch, "_reset_session", lambda ep, name: reset.append(name))
    html = fetch.fetch_html("http://x", endpoint="http://fs", session="klein")
    assert html == "<html>hi</html>"
    assert reset == ["klein"]
    assert len(calls) == 2


def test_fetch_html_followed_returns_final_url(monkeypatch):
    calls = []
    monkeypatch.setattr(fetch, "_post", _stub_post([REDIRECTED], calls))
    html, final_url = fetch.fetch_html_followed("http://x", endpoint="http://fs")
    assert html == "<html>hi</html>"
    assert final_url == "http://elsewhere"


def test_reset_session_destroys_before_recreating(monkeypatch):
    """create alone doesn't fix a crashed-but-still-listed session (reproduced
    live: sessions.create on it no-ops). destroy must run first."""
    calls = []
    monkeypatch.setattr(fetch, "_post", _stub_post([OK, OK], calls))
    fetch._reset_session("http://fs", "klein")
    assert calls[0] == {"cmd": "sessions.destroy", "session": "klein"}
    assert calls[1] == {"cmd": "sessions.create", "session": "klein"}


def test_post_returns_json_body_of_http_500(monkeypatch):
    """FlareSolverr signals errors as HTTP 500 + JSON; _post must return the
    body (status 'error') instead of raising, or the session reset never runs."""
    import io, urllib.error
    def _urlopen(req, timeout):
        raise urllib.error.HTTPError("http://fs", 500, "err", {}, io.BytesIO(b'{"status": "error", "message": "tab crashed"}'))
    monkeypatch.setattr(fetch.urllib.request, "urlopen", _urlopen)
    assert fetch._post("http://fs", {"cmd": "request.get"}, 1000)["message"] == "tab crashed"
