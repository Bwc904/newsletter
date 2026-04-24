"""
newsletter.py — Fetches trending X posts + web news per column using Grok API.

Writes `newsletter.json` consumed by render.py.

Run locally:
    pip install -r requirements.txt
    cp .env.example .env   # then fill in XAI_API_KEY
    python newsletter.py

Cost: ~$0.10–$0.60 per run (3 columns, non-reasoning model, trimmed prompts).
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

# Must be set BEFORE importing xai_sdk (which pulls in grpc).
#
# 1. If the sandbox's proxy uses a custom CA bundle (common in corp / Claude
#    Code cloud envs), honor REQUESTS_CA_BUNDLE / SSL_CERT_FILE by pointing
#    grpc at the same bundle.
_ca = os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("SSL_CERT_FILE")
if _ca and not os.environ.get("GRPC_DEFAULT_SSL_ROOTS_FILE_PATH"):
    os.environ["GRPC_DEFAULT_SSL_ROOTS_FILE_PATH"] = _ca

# 2. Force grpc to use the OS's native DNS resolver (getaddrinfo) instead of
#    c-ares. c-ares hits "DNS cache overflow" errors in sandboxed environments
#    where background DNS traffic is blocked / throttled.
os.environ.setdefault("GRPC_DNS_RESOLVER", "native")

import grpc
from xai_sdk import Client
from xai_sdk.chat import system, user
from xai_sdk.tools import web_search, x_search

# grpc status codes that are transient per gRPC spec — worth retrying.
_RETRYABLE_GRPC_CODES = {
    grpc.StatusCode.UNAVAILABLE,         # e.g. "DNS cache overflow", network blip
    grpc.StatusCode.DEADLINE_EXCEEDED,    # timeout
    grpc.StatusCode.RESOURCE_EXHAUSTED,   # upstream rate limit
    grpc.StatusCode.INTERNAL,             # transient server-side issue
    grpc.StatusCode.ABORTED,              # upstream retry hint
}


def _is_retryable(exc: BaseException) -> bool:
    """True if the error looks like a transient network/server issue worth retrying."""
    if isinstance(exc, grpc.RpcError):
        try:
            return exc.code() in _RETRYABLE_GRPC_CODES
        except Exception:
            return True
    # Fallback for non-grpc wrapped errors with transient-looking messages.
    msg = str(exc).lower()
    return any(tok in msg for tok in (
        "unavailable", "deadline", "cache overflow", "reset by peer",
        "connection reset", "temporarily unavailable", "timed out",
    ))


ROOT = Path(__file__).parent
TOPICS_FILE = ROOT / "topics.json"
OUTPUT_FILE = ROOT / "newsletter.json"
MODEL = "grok-4-1-fast-non-reasoning"  # cheaper; skip thinking tokens


def build_system_prompt(col: dict, rules: dict, since_date: str) -> str:
    """Compact system prompt — encodes two-bucket algorithm + exclusion rules."""
    n_final = rules["final_posts_per_column"]
    n_small = rules["min_small_account_posts"]
    cutoff = rules["small_account_follower_cutoff"]
    min_faves = rules["mainstream_min_faves"]
    news_count = rules["news_articles_per_column"]
    max_calls = rules["max_tool_calls_per_column"]
    virality = rules["virality_formula"]
    exclude_cat = "; ".join(rules["exclude_categories"])
    hints = " | ".join(col["x_semantic_hints"])
    keywords = ", ".join(col["x_keywords"])

    return f"""You curate the "{col['name']}" column of a daily newsletter. Focus: {col['description']}

TIME WINDOW: posts/articles from since:{since_date} only (last {rules['time_window_hours']}h).

TOOL BUDGET (STRICT — exceeding wastes money):
  - Max {max_calls} search tool calls TOTAL across x_search and web_search combined.
  - DO NOT call x_thread_fetch — we don't need thread context, only the original post.
  - DO NOT run "disambiguation" follow-up searches for specific names you encounter. Use whatever you got from the initial searches; if you're unsure about a name, just quote what the post says.
  - Maximum ONE web_search call. Use a single broad query for the news section, not multiple narrow ones.
  - Plan your searches before calling — aim for 3 calls total: one x_keyword_search (mainstream), one x_semantic_search (gems), one web_search (news).

TWO-BUCKET RETRIEVAL:
  A) Mainstream ({rules['mainstream_slots_pct']}%): x_keyword_search Top mode, min_faves:{min_faves}. Keywords: {keywords}.
  B) Hidden gems ({rules['hidden_gem_slots_pct']}%, more important): x_semantic_search on long-tail phrases like: {hints}. Score by virality = {virality}. Prefer builder posts / novel tools / small accounts with high engagement-to-follower ratio.

HARD RULES:
1. SKIP these categories entirely: {exclude_cat}.
2. At least {n_small} of the final {n_final} posts from accounts with <{cutoff:,} followers.
3. Dedupe near-duplicate stories.
4. No spam, low-effort replies, or karma-farming.

SIGNAL TAGS (exactly one per post):
  mainstream | hidden_gem | novel_tool | community_buzz

WEB NEWS: use web_search for {news_count} high-quality articles on: {col['news_query']}. Prefer primary sources.

OUTPUT: return ONLY valid JSON (no prose, no code fences):
{{
  "column": "{col['name']}", "slug": "{col['slug']}",
  "x_posts": [{{
    "author":"", "handle":"", "post_url":"https://x.com/h/status/id",
    "text":"", "likes":0, "retweets":0, "replies":0,
    "follower_count":0, "virality_score":0.0, "timestamp":"ISO",
    "summary":"one line", "why_it_matters":"one line",
    "signal_type":"mainstream|hidden_gem|novel_tool|community_buzz",
    "importance":1-10
  }}],
  "news":[{{"title":"", "source":"", "url":"", "published":"ISO", "summary":"one line", "importance":1-10}}],
  "commentary":"1-2 sentence editor note — concise, slightly witty"
}}

Include `importance` (1-10) on every post/article: how universally significant is it? 10 = everyone should know; 1 = niche. Keep summaries TIGHT (max 15 words each). Return {n_final} posts + {news_count} news. JSON ONLY."""


def fetch_column(client: Client, col: dict, rules: dict, since_date: str) -> dict:
    """One Grok call per column with server-side X + web search."""
    sys_prompt = build_system_prompt(col, rules, since_date)
    from_date = datetime.now(timezone.utc) - timedelta(hours=rules["time_window_hours"])

    # x_search caps excluded_x_handles at 10; truncate and push the overflow
    # into the system prompt so Grok still filters them client-side.
    all_excludes = col.get("exclude_handles", []) or []
    x_excludes = all_excludes[:10]
    tools = [
        x_search(
            from_date=from_date,
            excluded_x_handles=x_excludes,
        ),
        web_search(),
    ]

    chat = client.chat.create(
        model=MODEL,
        tools=tools,
        temperature=0.3,
    )
    chat.append(system(sys_prompt))
    chat.append(user(f"Assemble today's '{col['name']}' column. Return JSON only."))

    response = chat.sample()
    raw = response.content.strip()

    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rstrip("`").strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[WARN] JSON parse failed for {col['name']}: {e}", file=sys.stderr)
        print(f"[WARN] Raw: {raw[:400]}...", file=sys.stderr)
        return {
            "column": col["name"], "slug": col["slug"],
            "x_posts": [], "news": [],
            "commentary": "(Parse error — see logs)",
            "_parse_error": str(e), "_raw": raw,
        }

    parsed["accent"] = col.get("accent", "#64748b")

    # Attach usage info for cost tracking if available.
    try:
        u = response.usage
        parsed["_usage"] = {
            "prompt_tokens": getattr(u, "prompt_tokens", None),
            "completion_tokens": getattr(u, "completion_tokens", None),
            "total_tokens": getattr(u, "total_tokens", None),
        }
    except Exception:
        pass

    return parsed


def fetch_column_with_retry(client: Client, col: dict, rules: dict, since_date: str,
                            max_attempts: int = 3) -> dict:
    """Run fetch_column with exponential backoff on transient errors.

    Backoffs: 5s, 20s, 60s between attempts. On final failure, the exception
    propagates to the caller (main loop handles it and marks the column as
    failed so other columns can still publish)."""
    backoffs = [5, 20, 60]
    for attempt in range(max_attempts):
        try:
            return fetch_column(client, col, rules, since_date)
        except Exception as e:
            is_last = attempt == max_attempts - 1
            if is_last or not _is_retryable(e):
                raise
            wait = backoffs[attempt] if attempt < len(backoffs) else backoffs[-1]
            short = str(e)[:140].replace("\n", " ")
            print(f"[retry] {col['name']} attempt {attempt + 1}/{max_attempts} failed: {short}",
                  file=sys.stderr)
            print(f"[retry] retrying in {wait}s...", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError("unreachable — loop should have returned or raised")


def pick_hero(columns: list[dict]) -> dict | None:
    """Pick the single most important post/article across all columns as the hero.
    Free — pure local selection, no extra LLM call."""
    candidates = []
    for col in columns:
        for p in col.get("x_posts", []):
            candidates.append({
                "kind": "post",
                "importance": p.get("importance", 0) or 0,
                "virality": p.get("virality_score", 0) or 0,
                "column_name": col.get("column"),
                "column_slug": col.get("slug"),
                "accent": col.get("accent"),
                "data": p,
            })
        for a in col.get("news", []):
            candidates.append({
                "kind": "news",
                "importance": a.get("importance", 0) or 0,
                "virality": 0,
                "column_name": col.get("column"),
                "column_slug": col.get("slug"),
                "accent": col.get("accent"),
                "data": a,
            })
    if not candidates:
        return None
    # Sort by importance desc, break ties with virality
    candidates.sort(key=lambda c: (c["importance"], c["virality"]), reverse=True)
    hero = candidates[0]
    # Remove chosen hero from its column so it doesn't appear twice
    for col in columns:
        if col.get("slug") == hero["column_slug"]:
            if hero["kind"] == "post":
                col["x_posts"] = [p for p in col.get("x_posts", []) if p is not hero["data"]]
            else:
                col["news"] = [a for a in col.get("news", []) if a is not hero["data"]]
            break
    return hero


def main() -> int:
    load_dotenv(ROOT / ".env")
    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        print("ERROR: XAI_API_KEY not set (check .env or routine env secrets)", file=sys.stderr)
        return 1

    with open(TOPICS_FILE, encoding="utf-8") as f:
        config = json.load(f)
    columns_cfg = config["columns"]
    rules = config["selection_rules"]

    since_date = (datetime.now(timezone.utc) - timedelta(hours=rules["time_window_hours"])).strftime("%Y-%m-%d")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    client = Client(api_key=api_key, timeout=600)

    columns = []
    total_tokens = 0
    for col in columns_cfg:
        print(f"[fetch] {col['name']}...", file=sys.stderr)
        try:
            result = fetch_column_with_retry(client, col, rules, since_date)
        except Exception as e:
            print(f"[ERROR] {col['name']} failed after all retries: {e}", file=sys.stderr)
            result = {
                "column": col["name"],
                "slug": col["slug"],
                "accent": col.get("accent", "#64748b"),
                "x_posts": [],
                "news": [],
                "commentary": "(Data unavailable today — fetch failed after retries.)",
                "_fetch_error": str(e)[:500],
            }
        columns.append(result)
        u = result.get("_usage") or {}
        if u.get("total_tokens"):
            total_tokens += u["total_tokens"]

    # Only abort the whole run if EVERY column failed. Otherwise publish
    # whatever we got — a partial newsletter beats no newsletter.
    successful = [c for c in columns if not c.get("_fetch_error")]
    if not successful:
        print("[FATAL] all columns failed to fetch — aborting", file=sys.stderr)
        return 1

    hero = pick_hero(columns)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "date": today,
        "hero": hero,
        "columns": columns,
        "_total_tokens": total_tokens,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)

    print(f"[done] wrote {OUTPUT_FILE} (tokens: {total_tokens:,})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
