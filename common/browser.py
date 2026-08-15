"""Shared pacing/watchdog plumbing for Kleinanzeigen + Vinted hunters (any
product). Page fetching itself goes through common/fetch.py (FlareSolverr) --
this module no longer runs a browser."""
import math, os, random, sys, threading, time

# median seconds, lognormal sigma, hard cap -- per action type, right-skewed so
# most waits are short but a long tail happens naturally (real humans do this).
PACE_PROFILES = {
    "listing": (2.0, 0.5, 10),   # between search-result pages
    "detail":  (3.5, 0.6, 18),   # after opening a detail/item page ("reading")
}
DISTRACTION_CHANCE = 0.10
DISTRACTION_RANGE = (30, 90)


# --- stall watchdog ---------------------------------------------------------
# Kept from the old browser-based approach as a defense-in-depth backstop:
# common/fetch.py's socket timeout should already bound any single request,
# but this catches a stuck loop regardless of cause.
#
# A *total runtime* cap has to be generous -- macbook legitimately runs ~38min
# -- so deploy/run_all.sh's 45m timeout is a coarse outer backstop. This is the
# tight inner one: a progress cap. pace() is called after every page operation
# in all three engines, so it doubles as a heartbeat for free. Worst legitimate
# gap between beats is ~3.2min (18s detail cap + 90s distraction + 60s goto +
# 15s selector + 8s inner_text), so 8min is ~2.5x headroom and still catches a
# hang 5.6x faster than the 45m cap.
STALL_LIMIT = 8 * 60
_last_beat = time.monotonic()
_watchdog_lock = threading.Lock()
_watchdog_started = False


def _watchdog():
    while True:
        time.sleep(30)
        stalled = time.monotonic() - _last_beat
        if stalled > STALL_LIMIT:
            # os._exit, not sys.exit/raise: a stuck thread may not be joinable
            # cleanly, and normal interpreter shutdown could hang waiting on
            # it. This skips atexit/finally, which is acceptable here.
            print(f"[watchdog] no page progress for {stalled:.0f}s "
                  f"(limit {STALL_LIMIT}s) -- killing wedged run", flush=True)
            sys.stdout.flush()
            sys.stderr.flush()
            os._exit(75)  # EX_TEMPFAIL


def _beat():
    """Mark forward progress, arming the watchdog on first use. Only started
    from pace() so short-lived helpers that never scrape a page don't get a
    stray thread."""
    global _last_beat, _watchdog_started
    _last_beat = time.monotonic()
    with _watchdog_lock:
        if not _watchdog_started:
            _watchdog_started = True
            threading.Thread(target=_watchdog, daemon=True,
                             name="stall-watchdog").start()


def pace(kind="listing"):
    """Randomized delay, right-skewed (lognormal) with an occasional long
    'distraction' pause -- flat random.uniform() ranges are too regular to
    look human over a long unattended run. Also beats the stall watchdog."""
    _beat()
    median, sigma, cap = PACE_PROFILES[kind]
    time.sleep(min(random.lognormvariate(math.log(median), sigma), cap))
    if random.random() < DISTRACTION_CHANCE:
        time.sleep(random.uniform(*DISTRACTION_RANGE))
    _beat()  # again after sleeping, so the pause itself never counts as a stall
