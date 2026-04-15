"""Run one column and dump what searches Grok actually performed. Diagnostic only."""

import json, os, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv
from xai_sdk import Client
from xai_sdk.chat import system, user
from xai_sdk.tools import web_search, x_search

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

from newsletter import build_system_prompt, MODEL

with open(ROOT / "topics.json", encoding="utf-8") as f:
    cfg = json.load(f)

# Let user pick which column via argv, default to first (AI)
idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
col = cfg["columns"][idx]
rules = cfg["selection_rules"]
since = (datetime.now(timezone.utc) - timedelta(hours=rules["time_window_hours"])).strftime("%Y-%m-%d")
from_date = datetime.now(timezone.utc) - timedelta(hours=rules["time_window_hours"])

client = Client(api_key=os.environ["XAI_API_KEY"], timeout=600)

chat = client.chat.create(
    model=MODEL,
    tools=[
        x_search(from_date=from_date, excluded_x_handles=(col.get("exclude_handles") or [])[:10]),
        web_search(),
    ],
    temperature=0.3,
)
chat.append(system(build_system_prompt(col, rules, since)))
chat.append(user(f"Assemble today's '{col['name']}' column. Return JSON only."))

print(f"=== Running: {col['name']} ===", file=sys.stderr)
resp = chat.sample()

print("\n=== USAGE ===")
u = resp.usage
print(f"prompt_tokens     = {getattr(u,'prompt_tokens',None)}")
print(f"completion_tokens = {getattr(u,'completion_tokens',None)}")
print(f"total_tokens      = {getattr(u,'total_tokens',None)}")

print("\n=== SERVER-SIDE TOOL USAGE ===")
try:
    print(resp.server_side_tool_usage)
except Exception as e:
    print(f"(n/a: {e})")

print("\n=== TOOL CALLS ===")
try:
    tc = resp.tool_calls or []
    print(f"count={len(tc)}")
    for i, c in enumerate(tc):
        print(f"[{i}] {c}")
except Exception as e:
    print(f"(n/a: {e})")

print("\n=== CITATIONS ===")
try:
    cites = resp.citations or []
    print(f"count={len(cites)}")
    for i, c in enumerate(cites[:50]):
        print(f"[{i}] {c}")
except Exception as e:
    print(f"(n/a: {e})")

print("\n=== DEBUG OUTPUT ===")
try:
    print((resp.debug_output or "(empty)")[:2000])
except Exception as e:
    print(f"(n/a: {e})")
