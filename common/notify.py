"""Telegram alert for every new hit found in a run, via the n8n 'Scraper
Alert' webhook. One grouped message per run (not per hit) -- Telegram
rate-limits repeated sends to the same chat, and a run can surface several
hits at once."""
import json, os, time, urllib.request

from common.log import log

WEBHOOK_URL = os.environ.get("NOTIFY_WEBHOOK_URL", "")
TELEGRAM_MAX_CHARS = 4096


def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def notify_hits(hits, spec_suffix="GB"):
    """hits: list of (pr, spec_num, spec_label, ad) tuples from one run."""
    lines = [
        f'<b>{spec_label or "?"} {spec_num or "?"}{spec_suffix}</b> · {pr}€ · <a href="{ad["href"]}">{_esc(ad["title"])}</a>'
        for pr, spec_num, spec_label, ad in hits
    ]
    send_lines(lines, header="<b>Found:</b>")


def send_lines(lines, header=None):
    """One or more grouped messages (Telegram rate-limits repeated sends to
    the same chat) -- chunked under TELEGRAM_MAX_CHARS. header, if given, is
    prepended only to the first chunk."""
    if not lines:
        return
    chunks, buf, buf_len = [], [], 0
    for line in lines:
        if buf and buf_len + 1 + len(line) > TELEGRAM_MAX_CHARS:
            chunks.append(buf)
            buf, buf_len = [], 0
        buf.append(line)
        buf_len += 1 + len(line)
    chunks.append(buf)
    for i, buf in enumerate(chunks):
        text = "\n".join(buf)
        if header and i == 0:
            text = f"{header}\n{text}"
        _send(text)


def _send(text):
    if not WEBHOOK_URL:
        log.warning(f"[notify] NOTIFY_WEBHOOK_URL not set, skipping send\n{text}")
        return
    req = urllib.request.Request(
        WEBHOOK_URL,
        data=json.dumps({"text": text}).encode(),
        headers={
            "Content-Type": "application/json",
            # Cloudflare blocks the default Python-urllib UA with error 1010.
            "User-Agent": "Mozilla/5.0 (compatible; klanenzeigen-scraper)",
        },
    )
    last_err = None
    for attempt in range(2):
        try:
            urllib.request.urlopen(req, timeout=10)
            return
        except Exception as e:
            last_err = e
            if attempt == 0:
                time.sleep(3)
    log.warning(f"[notify] failed after retry: {last_err}\n{text}")
