"""
render.py — Reads newsletter.json, renders templates/email.html.j2 -> newsletter.html.

Dark-mode, hero + 3 columns layout. Gmail-compatible modern CSS + inline fallbacks.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape


ROOT = Path(__file__).parent
INPUT_FILE = ROOT / "newsletter.json"
OUTPUT_FILE = ROOT / "newsletter.html"
TEMPLATE_DIR = ROOT / "templates"
TEMPLATE_NAME = "email.html.j2"


SIGNAL_META = {
    "mainstream":     {"emoji": "🔥", "label": "Trending"},
    "hidden_gem":     {"emoji": "💎", "label": "Under the radar"},
    "novel_tool":     {"emoji": "🛠️", "label": "New / built"},
    "community_buzz": {"emoji": "💬", "label": "Discussion"},
}


def fmt_int(n) -> str:
    try:
        n = int(n)
    except (TypeError, ValueError):
        return "0"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def time_ago(iso_ts) -> str:
    """Convert ISO timestamp to '4h ago' / '2d ago' / 'just now'."""
    if not iso_ts:
        return ""
    try:
        s = str(iso_ts).replace("Z", "+00:00")
        # Handle missing timezone
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return ""
    delta = datetime.now(timezone.utc) - dt
    secs = int(delta.total_seconds())
    if secs < 60:
        return "just now"
    if secs < 3600:
        return f"{secs // 60}m ago"
    if secs < 86400:
        return f"{secs // 3600}h ago"
    days = secs // 86400
    return f"{days}d ago"


def build_tldr(hero, columns) -> list[dict]:
    """Pick one item per column (highest importance) for the TL;DR strip."""
    tldr = []
    hero_data = hero["data"] if hero else None
    for col in columns:
        items = []
        for p in col.get("x_posts", []):
            if p is hero_data:
                continue
            items.append({
                "column": col.get("column"),
                "accent": col.get("accent"),
                "text": p.get("summary") or (p.get("text") or "")[:100],
                "importance": p.get("importance", 0) or 0,
                "url": p.get("post_url"),
            })
        for a in col.get("news", []):
            if a is hero_data:
                continue
            items.append({
                "column": col.get("column"),
                "accent": col.get("accent"),
                "text": a.get("title"),
                "importance": a.get("importance", 0) or 0,
                "url": a.get("url"),
            })
        items.sort(key=lambda x: x["importance"], reverse=True)
        if items:
            tldr.append(items[0])
    return tldr


def sparkline(likes, retweets, replies, width=80, height=20):
    """Tiny inline SVG bar chart for engagement — Gmail-safe SVG."""
    vals = [int(likes or 0), int(retweets or 0), int(replies or 0)]
    mx = max(vals) or 1
    bar_w = (width - 6) // 3
    bars = []
    colors = ["#ef4444", "#22d3ee", "#a78bfa"]
    for i, v in enumerate(vals):
        bh = max(2, int((v / mx) * (height - 4)))
        x = i * (bar_w + 3)
        y = height - bh
        bars.append(f'<rect x="{x}" y="{y}" width="{bar_w}" height="{bh}" fill="{colors[i]}" rx="1"/>')
    return f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">{"".join(bars)}</svg>'


def main() -> int:
    if not INPUT_FILE.exists():
        print(f"ERROR: {INPUT_FILE} not found — run newsletter.py first.", file=sys.stderr)
        return 1

    with open(INPUT_FILE, encoding="utf-8") as f:
        data = json.load(f)

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.filters["fmt_int"] = fmt_int
    env.filters["time_ago"] = time_ago
    env.globals["signal_meta"] = SIGNAL_META
    env.globals["sparkline"] = sparkline

    tldr = build_tldr(data.get("hero"), data.get("columns", []))

    tpl = env.get_template(TEMPLATE_NAME)
    html = tpl.render(
        date=data.get("date", ""),
        generated_at=data.get("generated_at", ""),
        hero=data.get("hero"),
        columns=data.get("columns", []),
        tldr=tldr,
        total_tokens=data.get("_total_tokens", 0),
    )

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[done] wrote {OUTPUT_FILE}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
