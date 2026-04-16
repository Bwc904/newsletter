---
name: daily-brief-builder
description: Guide the user through building a custom daily newsletter that automatically delivers curated trending X (Twitter) posts and web news to their email. Use this skill when a user says any of: "I want to build a newsletter", "build me a daily digest", "help me make a news digest", "I want a curated feed of X posts", "set up a scheduled newsletter", "build my own Morning Brew", or similar. Covers the entire stack: Grok API for content, GitHub Pages for hosting the styled edition, Resend for delivery, and Claude Code Routines for scheduling.
---

# Daily Brief Builder — Skill

You are guiding a user through building a personalized daily newsletter from scratch. This is a real, battle-tested architecture — everything in this skill has been debugged end-to-end. Follow the phases in order. Do not skip the discovery phase — the newsletter's value comes from the user's topic choices.

## Architecture

```
Daily at 7am (or user's choice):
  Claude Code Routine (cloud, runs without user's laptop)
    ├─ python newsletter.py      → Grok API: trending X posts + web news per column
    ├─ python render.py           → full dark-mode HTML edition
    ├─ python publish.py          → copies HTML to docs/{date}.html + generates email
    ├─ git commit + push          → GitHub Pages serves the edition at a public URL
    └─ python send_email.py       → Resend API delivers minimal email with "Read →" CTA
```

Why this shape: Gmail strips modern CSS, so the *full* design lives on a hosted web page and the email is a minimal preview that links to it. The whole thing costs roughly **$3–5/month** on the Grok API and is otherwise free.

---

## Phase 1: Discovery (ALWAYS do this first)

Ask the user to answer each of these with `AskUserQuestion`. Do NOT make assumptions. These choices drive every file you'll create:

### 1.1 Topics
What categories should the newsletter cover? Push for specificity — "tech news" is weak, "AI agent tooling" is strong. A good newsletter has **2–5 columns**. For each column, capture:
- Column name (for the UI)
- A one-sentence scope
- Keywords to search X for (5–10 terms)
- Long-tail phrases for semantic search ("I built…", "underrated…", "new tool just dropped", etc.)
- A list of mega-account handles to EXCLUDE per topic (so the newsletter isn't dominated by Reuters/TechCrunch-style accounts) — **max 10 per column** because the xAI API caps it there

### 1.2 Delivery
- Email address to receive it
- Frequency (daily / weekdays / weekly) and local time

### 1.3 Design preferences
- Light or dark mode (default: dark)
- Font pairing — the default that works well:
  - **Display/headline:** Instrument Serif (italic "morning" accent is signature)
  - **Body:** Space Grotesk (geometric sans)
- Column accent colors (pick 2–5 distinct, saturated but not neon):
  - Cyan `#22d3ee`, amber `#f59e0b`, violet `#a78bfa` — default triple
  - Others: emerald `#10b981`, rose `#f43f5e`, blue `#3b82f6`, fuchsia `#d946ef`

### 1.4 Signature features (ask which to include)
- **Hero block** — one "top story" with rainbow gradient accent, auto-picked by importance score. Highly recommended.
- **"Today in 30 seconds" TL;DR strip** — one top item from each column. Highly recommended.
- **Liquid glass effect** on hero + TL;DR (backdrop-blur frosted panels with ambient color glows). Looks premium in browser; degrades gracefully.
- **Signal tags** per post: 🔥 Trending / 💎 Under the radar / 🛠️ New / built / 💬 Community take — helps skimming.
- **Time-ago stamps** ("4h ago" instead of timestamps).

### 1.5 Content philosophy — CRITICAL
By default Grok's search surfaces mega-account engagement. The whole value of this newsletter is **surfacing hidden gems** from small accounts with novel content. The algorithm enforces this with a two-bucket retrieval:

- **Bucket A (40% of slots):** mainstream trending — `x_keyword_search` top mode, `min_faves: 500`
- **Bucket B (60% of slots):** hidden gems — `x_semantic_search` on long-tail phrases + engagement-to-follower ratio scoring: `(likes + 3*replies + 2*retweets) / max(follower_count, 1000)`
- **Hard floor:** at least 2 of 5 posts per column must come from accounts with <50k followers

Ask the user if this philosophy matches their taste. If they want mostly-mainstream, flip the percentages.

### 1.6 Content to EXCLUDE
Default exclude list (tell the user these will be filtered out, ask if they want to add/remove any):
- Entertainment / celebrity gossip
- Music festivals (Coachella etc.)
- Award shows / red carpet
- Sports (unless directly about business/tech)
- Partisan outrage with no business impact
- Crypto shilling / meme coins
- Astrology / horoscopes
- Lifestyle / fashion

---

## Phase 2: Prerequisites — have them set up these accounts

Walk the user through each. Do not proceed to scaffolding until all are done.

### 2.1 xAI Grok API key
1. https://console.x.ai → sign up / sign in
2. Add payment method (required even for pay-as-you-go)
3. **API Keys → Create API Key** → name it "Daily Brief"
4. **Copy the key** (starts with `xai-`) — they won't see it again
5. Recommend setting a $20/month spending limit to be safe

**Cost note:** `grok-4-1-fast-non-reasoning` is the model to use. Full daily run is ~$0.10–$0.15 including X search tool calls. ~$3–5/month for daily delivery.

### 2.2 Resend account (email delivery)
1. https://resend.com → sign up **with the same email they want to receive the newsletter at** — this is critical. The sandbox sender `onboarding@resend.dev` only delivers to the Resend account owner's email.
2. https://resend.com/api-keys → **Create API Key** → name it "Daily Brief" → copy the key (starts with `re_`)
3. Free tier: 100 emails/day, 3,000/month — plenty

**Future upgrade path:** once the newsletter is running, they can verify a custom domain in Resend (add SPF/DKIM/DMARC DNS records) and change `NEWSLETTER_FROM` to `brief@theirdomain.com`. This lands in Primary inbox instead of Spam, and looks professional. Not required for initial setup.

### 2.3 GitHub account + public repo
1. https://github.com — create account if needed
2. **New repository** — name it whatever (suggest `daily-brief` or similar). **PUBLIC** (free GitHub Pages requires public repos; private needs GitHub Pro at $4/mo).
3. Do NOT initialize with README — leave it empty.

### 2.4 Check Python availability
Have them run `python --version` (or `python3 --version`). Need Python 3.10+. If missing, direct to https://python.org/downloads/.

### 2.5 Claude Code subscription
They need **Claude Pro or higher** for Claude Code Routines access. Pro = 5 routine runs/day (more than enough for a daily newsletter). Go to https://claude.ai/upgrade if needed.

---

## Phase 3: Scaffold the project

Create a working directory the user chooses (default: `~/Newsletter` or `C:\Users\<name>\Desktop\Newsletter` on Windows). Inside, create each file below. When creating the files, **substitute their actual topic/design choices from Phase 1** — don't copy templates verbatim.

### 3.1 File structure

```
Newsletter/
├── newsletter.py              # Grok API fetch
├── render.py                  # JSON → hosted HTML
├── publish.py                 # Copy to docs/ + generate email body
├── send_email.py              # Resend API
├── topics.json                # User's columns + selection rules
├── routine-prompt.md          # Paste target for Claude Code Routine UI
├── requirements.txt
├── .env.example               # Template
├── .env                       # Local secrets (gitignored)
├── .gitignore
├── README.md
├── docs/                      # Hosted editions go here (GitHub Pages)
└── templates/
    ├── email.html.j2          # Full dark-mode edition
    └── email-summary.html.j2  # Gmail-safe mini preview
```

### 3.2 `requirements.txt`
```
xai-sdk>=0.1.0
jinja2>=3.1.0
python-dotenv>=1.0.0
resend>=2.0.0
```

### 3.3 `.gitignore`
```
.env
__pycache__/
*.pyc
newsletter.json
newsletter.html
email.html
.venv/
venv/
```

### 3.4 `.env.example`
```
# xAI Grok API key from https://console.x.ai
XAI_API_KEY=xai-your-key-here

# Where to deliver the newsletter
NEWSLETTER_TO=you@example.com

# Public base URL of your GitHub Pages site (fill after Pages is enabled)
NEWSLETTER_SITE_URL=https://YOUR-USER.github.io/YOUR-REPO

# Resend API key from https://resend.com/api-keys
RESEND_API_KEY=re_your-key-here

# Optional: force grpc DNS resolver to native (required in Claude Code routines;
# harmless locally)
GRPC_DNS_RESOLVER=native

# Optional: custom verified sender after you verify a domain in Resend
# NEWSLETTER_FROM=Daily Brief <brief@yourdomain.com>
```

### 3.5 `topics.json`

Use the user's Phase 1 answers. Template structure:

```json
{
  "columns": [
    {
      "name": "Column Display Name",
      "slug": "short-slug",
      "accent": "#HEXCOLOR",
      "description": "one sentence scope",
      "x_keywords": ["keyword1", "keyword2", "..."],
      "x_semantic_hints": ["phrase 1", "phrase 2", "..."],
      "news_query": "web search query for news articles",
      "exclude_handles": ["max10", "mega-accounts", "..."]
    }
  ],
  "selection_rules": {
    "final_posts_per_column": 5,
    "mainstream_slots_pct": 40,
    "hidden_gem_slots_pct": 60,
    "min_small_account_posts": 2,
    "small_account_follower_cutoff": 50000,
    "mainstream_min_faves": 500,
    "time_window_hours": 24,
    "news_articles_per_column": 3,
    "max_tool_calls_per_column": 3,
    "virality_formula": "(likes + 3*replies + 2*retweets) / max(follower_count, 1000)",
    "exclude_categories": [
      "entertainment / celebrity gossip",
      "music festivals",
      "award shows",
      "sports (unless directly about business/tech)",
      "partisan outrage with no business impact",
      "crypto shilling / meme coins",
      "astrology / horoscopes",
      "lifestyle / fashion"
    ]
  }
}
```

### 3.6 `newsletter.py` (Grok fetch)

Reference implementation — the key pieces to preserve when you adapt:

```python
"""Fetches trending X posts + web news per column via Grok."""
import json, os, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv

# CRITICAL: must be set BEFORE importing xai_sdk (which loads grpc).
# 1. If the sandbox uses a custom CA bundle, point grpc at it.
_ca = os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("SSL_CERT_FILE")
if _ca and not os.environ.get("GRPC_DEFAULT_SSL_ROOTS_FILE_PATH"):
    os.environ["GRPC_DEFAULT_SSL_ROOTS_FILE_PATH"] = _ca
# 2. Force grpc to use OS DNS resolver — c-ares breaks in sandboxed envs
#    with "DNS cache overflow" errors.
os.environ.setdefault("GRPC_DNS_RESOLVER", "native")

from xai_sdk import Client
from xai_sdk.chat import system, user
from xai_sdk.tools import web_search, x_search

ROOT = Path(__file__).parent
MODEL = "grok-4-1-fast-non-reasoning"  # cheaper; skip thinking tokens

def build_system_prompt(col, rules, since_date):
    # Encodes: two-bucket strategy, exclusion rules, signal tagging,
    # output schema. See full reference in this skill's "Prompt template" section below.
    ...

def fetch_column(client, col, rules, since_date):
    from_date = datetime.now(timezone.utc) - timedelta(hours=rules["time_window_hours"])
    # CRITICAL: xAI caps excluded_x_handles at 10. Truncate.
    all_excludes = (col.get("exclude_handles") or [])[:10]
    tools = [
        x_search(from_date=from_date, excluded_x_handles=all_excludes),
        web_search(),
    ]
    chat = client.chat.create(model=MODEL, tools=tools, temperature=0.3)
    chat.append(system(build_system_prompt(col, rules, since_date)))
    chat.append(user(f"Assemble today's '{col['name']}' column. Return JSON only."))
    response = chat.sample()
    # ...parse JSON, attach usage stats, return dict...

def pick_hero(columns):
    """Local free hero selection — highest importance across all items."""
    # ...picks highest-importance item; removes from its column to avoid dupe...

# main() loads topics.json, iterates columns, writes newsletter.json
```

### 3.7 System prompt template (used inside `build_system_prompt`)

This is the single most important asset. It encodes the quality algorithm. Adapt but preserve the structure:

```
You curate the "{col[name]}" column of a daily newsletter. Focus: {col[description]}

TIME WINDOW: posts/articles from since:{since_date} only (last {hours}h).

TOOL BUDGET (STRICT — exceeding wastes money):
  - Max {max_calls} search tool calls TOTAL across x_search and web_search combined.
  - DO NOT call x_thread_fetch — we don't need thread context, only the original post.
  - DO NOT run "disambiguation" follow-up searches for specific names you encounter.
    Use whatever you got from the initial searches; if unsure about a name, quote the post.
  - Maximum ONE web_search call. Use a single broad query.
  - Plan before calling — aim for 3 calls total: one x_keyword_search, one x_semantic_search,
    one web_search.

TWO-BUCKET RETRIEVAL:
  A) Mainstream (40%): x_keyword_search Top mode, min_faves:500. Keywords: {keywords}.
  B) Hidden gems (60%, MORE IMPORTANT): x_semantic_search on long-tail phrases like:
     {hints}. Score by virality = {virality_formula}. Prefer builder posts, novel tools,
     small accounts with high engagement-to-follower ratio.

HARD RULES:
1. SKIP these categories entirely: {exclude_categories}.
2. At least {n_small} of the final {n_final} posts from accounts with <{cutoff} followers.
3. Dedupe near-duplicate stories.
4. No spam, low-effort replies, karma-farming.

SIGNAL TAGS (exactly one per post):
  mainstream | hidden_gem | novel_tool | community_buzz

WEB NEWS: use web_search for {news_count} high-quality articles on: {news_query}.
Prefer primary sources.

OUTPUT: return ONLY valid JSON (no prose, no code fences) with this schema:
{
  "column": "...", "slug": "...",
  "x_posts": [{
    "author":"", "handle":"", "post_url":"https://x.com/h/status/id",
    "text":"", "likes":0, "retweets":0, "replies":0,
    "follower_count":0, "virality_score":0.0, "timestamp":"ISO",
    "summary":"one line", "why_it_matters":"one line",
    "signal_type":"mainstream|hidden_gem|novel_tool|community_buzz",
    "importance":1-10
  }],
  "news":[{"title":"", "source":"", "url":"", "published":"ISO", "summary":"one line", "importance":1-10}],
  "commentary":"1-2 sentence editor note"
}

Include `importance` (1-10) on every item: how universally significant? 10 = everyone
should know; 1 = niche. Keep summaries TIGHT (max 15 words). JSON ONLY.
```

### 3.8 `render.py` (JSON → HTML)

Loads `newsletter.json`, renders `templates/email.html.j2` via Jinja2. Provides two custom filters:
- `fmt_int` — converts 1234 → "1.2K", 1500000 → "1.5M"
- `time_ago` — converts ISO timestamp → "4h ago"

And a `build_tldr` helper that picks one highest-importance item per column (excluding whatever became hero) for the "Today in 30 seconds" strip.

### 3.9 `templates/email.html.j2` (the hosted edition)

This is where design lives. Key pieces to implement (can be tuned freely since it's rendered in a real browser, not Gmail):
- `<body>` with radial-gradient ambient glows (cyan/amber/violet positions)
- Google Fonts link for Instrument Serif + Space Grotesk
- Masthead with serif italic accent ("The *morning* edition")
- TL;DR strip with backdrop-filter frosted glass
- Hero panel with backdrop-filter + rainbow top border + radial ambient glows inside
- Responsive `<table>` 3-column layout that stacks <700px
- Per-column accent color applied to: column dot, section label, card signal tag, "Read on X →" link
- Cards: rounded block, signal tag pill, bold sans headline, muted post body with left border, author line, engagement stats, "Why:" callout with colored left border
- News cards: plain rounded block, bold title, source + time-ago, optional summary

### 3.10 `templates/email-summary.html.j2` (the Gmail-safe email body)

DIFFERENT file from the hosted edition. Must be email-safe:
- Inline styles only (no `<style>` blocks — some clients strip them)
- Table-based layout
- Light mode background (#f4f4f5) — dark mode forces break in many clients
- NO backdrop-filter, NO Google Fonts (they won't load in Gmail mobile)
- System font stack with serif fallback
- Simple structure: masthead → hero preview card with gradient bg → TL;DR list → big CTA button → footer
- One single primary CTA: "**Read the full brief →**" linking to `{{ url }}`

### 3.11 `publish.py`

```python
def publish():
    """Copy newsletter.html → docs/{date}.html + docs/index.html, rebuild archive.html"""

def render_email(public_url):
    """Render email-summary.html.j2 → email.html with the URL baked in"""

# main() runs both, passing the site URL from env
```

Also generates `docs/archive.html` — simple list of every dated edition, newest first.

### 3.12 `send_email.py`

```python
import resend, os
from dotenv import load_dotenv
load_dotenv()

resend.api_key = os.environ["RESEND_API_KEY"]
sender = os.environ.get("NEWSLETTER_FROM", "Daily Brief <onboarding@resend.dev>")

resend.Emails.send({
    "from": sender,
    "to": [os.environ["NEWSLETTER_TO"]],
    "subject": f"Daily Brief -- {date}",
    "html": open("email.html", encoding="utf-8").read(),
    "text": plaintext_fallback,
})
```

Plain-text fallback body should include the TL;DR bullets + link — both for deliverability (some spam filters downrank HTML-only emails) and for clients that don't render HTML.

### 3.13 `routine-prompt.md` — text to paste into the Routine UI later

```
You are the delivery agent for the user's daily newsletter.

Python deps are pre-installed by the environment's setup script — do NOT run pip install.

Steps (each in its own bash command):
1. python newsletter.py — if exit non-zero, abort and proceed to step 6
2. python render.py
3. python publish.py
4. git config user.email "routine@daily-brief"; git config user.name "Daily Brief Routine"
   git add docs/
   git commit -m "Daily Brief -- $(date -u +%Y-%m-%d)"
   git push origin main
5. python send_email.py
6. If any step failed, send plain-text failure email via Resend with subject
   `Daily Brief -- FAILED <date>` and last 30 lines of stderr. Do not retry.

Environment secrets required:
- XAI_API_KEY, NEWSLETTER_TO, NEWSLETTER_SITE_URL, RESEND_API_KEY, GRPC_DNS_RESOLVER=native
```

---

## Phase 4: Local test before deploying

Before touching the routine, prove the pipeline works on the user's machine:

```
cd Newsletter
pip install -r requirements.txt
cp .env.example .env
# user edits .env with their real XAI_API_KEY and NEWSLETTER_TO

python newsletter.py     # ~30–90 sec, produces newsletter.json
python render.py         # produces newsletter.html
python publish.py        # produces docs/{date}.html + email.html
```

Open `newsletter.html` in their browser. Iterate on design until it looks right — it's much faster to iterate locally than via the cloud routine. Also open `email.html` to see what Gmail will receive.

**If `newsletter.py` fails** — paste the error, debug. Common local issues:
- `XAI_API_KEY not set` → they didn't edit `.env` or forgot to save
- `InvalidArgumentError: A maximum of 10 handles can be excluded` → their `exclude_handles` for a column has >10 entries. Trim.
- `Live search is deprecated` → they're on an outdated xai-sdk. `pip install -U xai-sdk`.

---

## Phase 5: Deploy to GitHub + GitHub Pages

1. Initialize git in the folder:
   ```
   git init -b main
   git remote add origin https://github.com/<user>/<repo>.git
   git add .
   git commit -m "Initial scaffold"
   git push -u origin main
   ```
2. On GitHub: **repo → Settings → Pages** → Source: `Deploy from a branch` → Branch: `main` / folder: `/docs` → **Save**
3. Wait ~60 sec, refresh. Green banner: "Your site is live at `https://<user>.github.io/<repo>/`"
4. Visit that URL + `/YYYY-MM-DD.html` (today's date) — full edition should load.
5. Update `NEWSLETTER_SITE_URL` in their local `.env` to this real URL. Re-run `python publish.py` so `email.html` has the correct link. Commit + push.

---

## Phase 6: Create the Claude Code Routine

### 6.1 Configure the cloud environment

**Critical:** the default "Trusted" network policy blocks the APIs we need. Go to https://claude.ai/code → **Environments** → create or edit the environment the routine will use:

- **Network access:** **Custom**
- **Allowed domains** (one per line):
  ```
  api.x.ai
  api.resend.com
  pypi.org
  files.pythonhosted.org
  github.com
  ```
- **Setup script:**
  ```
  pip install --no-input --ignore-installed xai-sdk jinja2 python-dotenv resend
  ```
  Why `--ignore-installed`: Ubuntu ships `packaging` via distutils, pip refuses to overwrite without this flag.
  Why inline packages (not `-r requirements.txt`): setup script runs BEFORE the repo is cloned, so it can't read repo files.
  Why in setup script (not the routine prompt): runs before Claude starts, so the routine starts faster and uses fewer Claude tokens.

### 6.2 Create the routine

https://claude.ai/code/routines → **New routine**:

| Field | Value |
|---|---|
| Name | Daily Brief (or their choice) |
| Repository | `<user>/<repo>` · branch `main` |
| Environment | the one configured above |
| Trigger | Scheduled · Daily · 07:00 local (or their choice) |
| Connectors | **none** (delivery is via Resend API, not Gmail MCP) |
| Prompt | paste contents of `routine-prompt.md` |

**Environment variables (the routine's secrets panel — separate from the environment's setup config):**

| Name | Value |
|---|---|
| `XAI_API_KEY` | their Grok key |
| `NEWSLETTER_TO` | delivery email |
| `NEWSLETTER_SITE_URL` | GitHub Pages URL |
| `RESEND_API_KEY` | their Resend key |
| `GRPC_DNS_RESOLVER` | `native` |

### 6.3 Grant repo write access

When they select the repo, it'll ask for permissions. Grant **write access to contents** — the routine needs it to `git push` the daily edition to `main` so GitHub Pages picks it up.

### 6.4 Run now

Click **Run now**. Expected sequence (~3–4 min total first time):
1. Container spin-up (~20 sec)
2. Setup script: `pip install` (~60 sec)
3. Claude session starts
4. `python newsletter.py` runs (~90 sec — 3 columns × ~30 sec each)
5. `python render.py`, `publish.py` (each <2 sec)
6. `git push` (~5 sec)
7. `python send_email.py` (~2 sec) — Resend returns a message ID
8. Email arrives in inbox (or Spam — see 6.5)

### 6.5 First email is in Spam — this is normal

Emails from `@resend.dev` (sandbox sender) almost always land in Gmail Spam initially. Two fixes:

**Quick (30 sec, permanent):**
- Open the email in Spam → click "Report not spam"
- Click the sender name → "Add to contacts"
- All future sends land in inbox

**Proper fix (10 min, professional):** verify a custom domain in Resend
1. Resend → **Domains → Add Domain** → their domain
2. Add the provided SPF/DKIM/DMARC records to their DNS
3. Wait ~5 min for verification
4. Update routine env: `NEWSLETTER_FROM=Daily Brief <brief@theirdomain.com>`
5. Emails now come from their own domain — Primary inbox, no spam risk, professional "From" line

---

## Phase 7: Troubleshooting runbook (from real debugging)

Work through these in order if the first run fails.

### Setup script fails

| Error | Cause | Fix |
|---|---|---|
| `ERROR: Cannot uninstall 'packaging'...` | Ubuntu distutils package conflict | Add `--ignore-installed` to pip command |
| `Could not open requirements file: No such file or directory: 'requirements.txt'` | Setup script runs before repo clone | Inline package names instead of using `-r requirements.txt` |
| Setup script hangs >2 min on package downloads | Custom allowlist missing PyPI hosts | Add `pypi.org` and `files.pythonhosted.org` to allowed domains |

### `newsletter.py` fails

| Error | Cause | Fix |
|---|---|---|
| `CERTIFICATE_VERIFY_FAILED: self signed certificate in certificate chain` | Sandbox TLS interception, grpc doesn't trust proxy's CA | Code already handles via `REQUESTS_CA_BUNDLE` → `GRPC_DEFAULT_SSL_ROOTS_FILE_PATH`. If still failing, add `api.x.ai` to custom allowlist. |
| `DNS cache overflow` (grpc UNAVAILABLE) | c-ares resolver broken in sandbox | Set `GRPC_DNS_RESOLVER=native` as routine env var |
| `A maximum of 10 handles can be excluded` | Column's `exclude_handles` has >10 entries | Code truncates to first 10. Verify in `topics.json`. |
| `Live search is deprecated. Please switch to the Agent Tools API` | Old xai-sdk or old API call pattern | Use `xai_sdk.tools.x_search()` + `web_search()` in `tools=[...]`, not `SearchParameters` |
| `XAI_API_KEY not set` | Secret didn't reach the runtime | Confirm it's in the **routine's** env vars (not the environment's setup config) |

### `send_email.py` reports success but email never arrives

| Check | Fix |
|---|---|
| Resend message ID appears in dashboard Emails/Logs? | If yes → deliverability issue; check Gmail Spam and Promotions |
| If no → you're checking a different Resend account | Re-create API key under the correct account, update `RESEND_API_KEY` |
| Email in Spam from `@resend.dev`? | Expected. Report Not Spam + Add Contact, or verify custom domain |
| Bounce or reject shown in Resend dashboard? | Sandbox sender only delivers to the Resend account owner's email. Confirm `NEWSLETTER_TO` = the email that registered the Resend account |

### `git push` fails in routine

| Error | Fix |
|---|---|
| `Permission denied (push)` | Routine repo access didn't grant write. Re-select repo in routine settings with write permission. |
| `nothing to commit` | `docs/` had no changes. Either `publish.py` failed silently or first run was already committed. Check `docs/` contents. |

### Cost is higher than expected (~$0.30+/run)

The token cost is small; the tool-call cost dominates. Common culprits:
- Grok making `x_thread_fetch` calls — **forbid in prompt**, already in template
- Grok making "disambiguation" web searches — **forbid in prompt**, already in template
- Grok using reasoning tokens — **use `grok-4-1-fast-non-reasoning`** not `-reasoning`
- Too many columns — consolidate (3 is optimal)
- `max_tool_calls_per_column` too high — set to 3

Run the diagnostic once to see what Grok is actually calling:
```python
# inspect_searches.py — runs one column and dumps server_side_tool_usage + tool_calls
```

---

## Phase 8: Iteration — after the first week

Suggest the user:

1. **Tune topics.json** — if a column keeps returning weak posts, refine its `x_semantic_hints` (what phrases make great content sound like) and `exclude_handles` (which mega-accounts keep leaking through).
2. **Tune the system prompt** — edit `build_system_prompt` in `newsletter.py` if Grok isn't respecting a rule. Be very explicit.
3. **Iterate design locally** — edit `templates/email.html.j2`, run `python render.py` locally, refresh browser. Commit when happy. The next morning's routine picks it up automatically.
4. **Archive page** — `docs/archive.html` auto-regenerates each run with every dated edition linked. Bookmark it.
5. **Verify custom domain in Resend** — big upgrade, mentioned in Phase 6.5.
6. **Add a column** — add an entry to `topics.json → columns` and add its accent color to the template's rainbow gradient.
7. **Cost watchdog** — newsletter.json records `_usage` per column. If total tokens start climbing, inspect which column is exploding and tune.

---

## Key principles to preserve

If the user wants to modify aggressively, keep these intact — they're the load-bearing bits:

1. **Two-bucket retrieval** (40% mainstream + 60% hidden gems) — this is the differentiator from generic news scrapers
2. **≥2 of 5 posts from <50k-follower accounts** — the floor that prevents mega-account dominance
3. **Excluded-categories list in the system prompt** — keeps Coachella-class noise out
4. **Hosted web edition + minimal email link** — don't fight Gmail's CSS sanitizer; host the real thing and link to it
5. **`grok-4-1-fast-non-reasoning` + tool budget** — keeps daily cost under $0.20

---

## Done signal

The user has successfully shipped when:
- ✅ They've received at least one email with a working "Read the full brief →" button
- ✅ Clicking it loads the full styled edition at their GitHub Pages URL
- ✅ The hosted edition shows today's date + all their columns populated
- ✅ The routine is scheduled and enabled (not just manual-run)
- ✅ Their email is in Primary inbox (or they've moved it out of Spam with "Add Contact")

Celebrate. Remind them: the routine now fires every morning automatically. They can edit `topics.json` or the template any time, commit+push, and tomorrow's run uses the new version.
