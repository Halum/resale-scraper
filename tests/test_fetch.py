"""Session wiring for the FlareSolverr client -- the parts that can silently
break fetching: whether a session name is attached, and recovery when the
named session has been GC'd. No network; _post is stubbed."""
import common.fetch as fetch

OK = {"status": "ok", "solution": {"status": 200, "response": "<html>hi</html>"}}
MISSING = {"status": "error", "message": "Session does not exist"}


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


def test_recreates_and_retries_on_missing_session(monkeypatch):
    calls, created = [], []
    monkeypatch.setenv("FLARESOLVERR_SESSIONS", "1")
    monkeypatch.setattr(fetch, "_post", _stub_post([MISSING, OK], calls))
    monkeypatch.setattr(fetch, "_create_session", lambda ep, name: created.append(name))
    html = fetch.fetch_html("http://x", endpoint="http://fs", session="vinted")
    assert html == "<html>hi</html>"   # second attempt succeeds
    assert created == ["vinted"]       # session was recreated once
    assert len(calls) == 2             # exactly one retry, no loop
