"""
send_email.py — Send the rendered `email.html` via Resend API.

Env vars:
  RESEND_API_KEY    required — from https://resend.com/api-keys
  NEWSLETTER_TO     required — recipient address
  NEWSLETTER_FROM   optional — defaults to "Daily Brief <onboarding@resend.dev>"
                    (Resend's sandbox sender; only delivers to the Resend
                     account owner's email. Replace with a verified-domain
                     sender when you set up DNS for your own domain.)
  NEWSLETTER_SITE_URL optional — used in subject only
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import resend
from dotenv import load_dotenv


ROOT = Path(__file__).parent
EMAIL_HTML = ROOT / "email.html"
NEWSLETTER_JSON = ROOT / "newsletter.json"

# HTTP status codes worth retrying (per standard HTTP retry semantics).
_RETRYABLE_HTTP_STATUSES = {408, 425, 429, 500, 502, 503, 504}


def _is_retryable_resend(exc: BaseException) -> bool:
    """True if the Resend error looks like a transient upstream issue."""
    # Resend SDK exceptions may expose .status_code / .http_status
    status = getattr(exc, "status_code", None) or getattr(exc, "http_status", None)
    if status in _RETRYABLE_HTTP_STATUSES:
        return True
    # Fallback to message sniffing — the SDK sometimes raises generic exceptions
    # (e.g. "Expected JSON response but got: text/plain" when a proxy returns an
    # HTML error page).
    msg = str(exc).lower()
    return any(tok in msg for tok in (
        "503", "502", "504", "429",
        "service unavailable", "temporarily unavailable",
        "cache overflow", "expected json response but got: text/plain",
        "timed out", "timeout", "connection reset", "connection aborted",
        "bad gateway", "gateway timeout",
    ))


def send_with_retry(params: dict, max_attempts: int = 4) -> dict:
    """Call resend.Emails.send() with exponential backoff on transient failures.

    Backoffs: 10s, 30s, 90s between attempts. Raises the final exception if all
    attempts fail."""
    backoffs = [10, 30, 90]
    last_exc: BaseException | None = None
    for attempt in range(max_attempts):
        try:
            return resend.Emails.send(params)
        except Exception as e:
            last_exc = e
            is_last = attempt == max_attempts - 1
            if is_last or not _is_retryable_resend(e):
                raise
            wait = backoffs[attempt] if attempt < len(backoffs) else backoffs[-1]
            short = str(e)[:140].replace("\n", " ")
            print(f"[retry] Resend attempt {attempt + 1}/{max_attempts} failed: {short}",
                  file=sys.stderr)
            print(f"[retry] retrying in {wait}s...", file=sys.stderr)
            time.sleep(wait)
    raise last_exc if last_exc else RuntimeError("unreachable")


def plaintext_fallback(data: dict, url: str) -> str:
    """Build a simple plain-text fallback body from the newsletter data."""
    lines = [
        f"Daily Brief -- {data.get('date','')}",
        "",
        "Today in 30 seconds:",
    ]
    hero = data.get("hero")
    hero_data = hero["data"] if hero else None
    for col in data.get("columns", []):
        items = [p for p in col.get("x_posts", []) if p is not hero_data]
        items += [a for a in col.get("news", []) if a is not hero_data]
        items.sort(key=lambda x: x.get("importance", 0) or 0, reverse=True)
        if items:
            top = items[0]
            text = top.get("summary") or top.get("title") or (top.get("text") or "")[:100]
            lines.append(f"  * {col.get('column')}: {text}")
    lines.append("")
    if hero_data:
        lines.append(f"Top story: {hero_data.get('summary') or hero_data.get('title')}")
        lines.append("")
    lines.append(f"Read the full brief: {url}")
    return "\n".join(lines)


def main() -> int:
    load_dotenv(ROOT / ".env")

    api_key = os.environ.get("RESEND_API_KEY")
    to = os.environ.get("NEWSLETTER_TO")
    sender = os.environ.get("NEWSLETTER_FROM", "Daily Brief <onboarding@resend.dev>")

    missing = [k for k, v in {"RESEND_API_KEY": api_key, "NEWSLETTER_TO": to}.items() if not v]
    if missing:
        print(f"ERROR: missing required env vars: {', '.join(missing)}", file=sys.stderr)
        return 1

    if not EMAIL_HTML.exists():
        print(f"ERROR: {EMAIL_HTML} not found -- run publish.py first.", file=sys.stderr)
        return 1

    html = EMAIL_HTML.read_text(encoding="utf-8")

    try:
        with open(NEWSLETTER_JSON, encoding="utf-8") as f:
            data = json.load(f)
        date = data.get("date") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        site_url = os.environ.get("NEWSLETTER_SITE_URL", "").rstrip("/")
        public = f"{site_url}/{date}.html" if site_url else ""
        text = plaintext_fallback(data, public)
    except Exception as e:
        print(f"[warn] failed to build plaintext fallback: {e}", file=sys.stderr)
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        text = "See HTML version."

    resend.api_key = api_key
    params = {
        "from": sender,
        "to": [to],
        "subject": f"Daily Brief -- {date}",
        "html": html,
        "text": text,
    }

    try:
        result = send_with_retry(params)
    except Exception as e:
        print(f"ERROR: Resend send failed after retries: {e}", file=sys.stderr)
        return 1

    print(f"[done] sent to {to} via Resend (id={result.get('id','?')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
