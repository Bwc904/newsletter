"""
publish.py — Publishes the rendered newsletter to docs/ for GitHub Pages,
and renders the minimal email-summary HTML for Gmail delivery.

Outputs:
  docs/{YYYY-MM-DD}.html    full dated copy (permalink archive)
  docs/index.html           latest (redirects or displays latest)
  docs/archive.html         list of past editions
  email.html                small email body linking to today's edition

Run after newsletter.py + render.py:
    python newsletter.py
    python render.py
    python publish.py
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape


ROOT = Path(__file__).parent
DOCS = ROOT / "docs"
NEWSLETTER_HTML = ROOT / "newsletter.html"
NEWSLETTER_JSON = ROOT / "newsletter.json"
EMAIL_OUT = ROOT / "email.html"
TEMPLATE_DIR = ROOT / "templates"


def read_site_url() -> str:
    """Returns the public base URL for hosted editions. Falls back to a placeholder."""
    # Env var is the preferred source (set on the routine's cloud env).
    url = os.environ.get("NEWSLETTER_SITE_URL", "").rstrip("/")
    if url:
        return url
    # Fallback — user fills this in README after enabling GitHub Pages.
    return "https://YOUR-USER.github.io/daily-brief"


def publish() -> str:
    """Copy newsletter.html into docs/ as dated + index. Returns today's public URL."""
    if not NEWSLETTER_HTML.exists():
        print(f"ERROR: {NEWSLETTER_HTML} missing — run render.py first.", file=sys.stderr)
        sys.exit(1)

    DOCS.mkdir(exist_ok=True)

    with open(NEWSLETTER_JSON, encoding="utf-8") as f:
        data = json.load(f)
    date = data.get("date") or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    dated = DOCS / f"{date}.html"
    shutil.copy2(NEWSLETTER_HTML, dated)
    shutil.copy2(NEWSLETTER_HTML, DOCS / "index.html")

    build_archive()

    site = read_site_url()
    return f"{site}/{date}.html"


def build_archive() -> None:
    """Generate docs/archive.html listing every dated edition."""
    editions = sorted(
        [p.stem for p in DOCS.glob("????-??-??.html")],
        reverse=True,
    )
    items = "\n".join(
        f'<li><a href="{d}.html">{d}</a></li>' for d in editions
    )
    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Archive · Daily Brief</title>
<style>
body{{margin:0;padding:60px 20px;background:#09090b;color:#e4e4e7;
font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;}}
.wrap{{max-width:640px;margin:0 auto;}}
h1{{font-weight:400;font-size:36px;letter-spacing:-0.02em;margin:0 0 30px 0;font-family:'Instrument Serif',Georgia,serif;}}
ul{{list-style:none;padding:0;margin:0;}}
li{{padding:12px 16px;margin-bottom:6px;background:#16161a;border:1px solid #27272a;border-radius:8px;}}
a{{color:#fafafa;text-decoration:none;font-size:15px;font-weight:500;}}
a:hover{{color:#22d3ee;}}
</style></head><body><div class="wrap">
<h1>Daily Brief · archive</h1>
<ul>
{items}
</ul>
<p style="margin-top:30px;font-size:12px;color:#71717a;">← <a href="index.html" style="color:#71717a;">Latest edition</a></p>
</div></body></html>
"""
    (DOCS / "archive.html").write_text(html, encoding="utf-8")


def render_email(public_url: str) -> None:
    """Render templates/email-summary.html.j2 -> email.html (body for Gmail)."""
    if not NEWSLETTER_JSON.exists():
        print(f"ERROR: {NEWSLETTER_JSON} missing", file=sys.stderr)
        sys.exit(1)

    with open(NEWSLETTER_JSON, encoding="utf-8") as f:
        data = json.load(f)

    # Build TL;DR the same way render.py does — reuse the helper.
    from render import build_tldr
    tldr = build_tldr(data.get("hero"), data.get("columns", []))

    hero = data.get("hero")
    hero_text = None
    hero_col = None
    if hero:
        h = hero["data"]
        hero_text = h.get("summary") or h.get("title") or (h.get("text") or "")[:140]
        hero_col = hero.get("column_name")

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    tpl = env.get_template("email-summary.html.j2")
    html = tpl.render(
        date=data.get("date", ""),
        url=public_url,
        tldr=tldr,
        hero_text=hero_text,
        hero_col=hero_col,
    )
    EMAIL_OUT.write_text(html, encoding="utf-8")


def main() -> int:
    url = publish()
    render_email(url)
    print(f"[done] published -> {url}")
    print(f"[done] email body -> {EMAIL_OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
