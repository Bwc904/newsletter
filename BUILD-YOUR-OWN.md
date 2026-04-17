# Build Your Own Daily Brief

A step-by-step guide to building a personalized daily newsletter that automatically delivers curated trending X (Twitter) posts and web news to your email. Battle-tested — every step, every bug, and every fix is here.

**What you'll ship:**
- A daily email at 7am (or whenever you want) with 3 customizable columns of handpicked content
- A full dark-mode "web magazine" edition hosted on GitHub Pages
- Total cost: ~$3–5/month (Grok API only)
- Runs on autopilot in the cloud — your laptop doesn't need to be on
- Side note, a user can avoid the x api and just have claude scrape reddit if desired
**Prerequisites:**
- Claude Pro or higher (for Claude Code Routines)
- A credit card for xAI (Grok) — set a small monthly limit
- Free accounts at GitHub and Resend
- Python 3.10+ on your machine for initial scaffolding
- Basic comfort with the command line and a text editor

If you'd rather not do this solo, paste this whole file into Claude.ai or Claude Code and say "walk me through this" — it works either way.

---

## Architecture at a glance

```
Daily at 7am (cloud — your laptop doesn't matter):
  Claude Code Routine
    ├─ newsletter.py      → Grok API: trending X posts + web news per column
    ├─ render.py           → full dark-mode HTML edition
    ├─ publish.py          → copies HTML to docs/{date}.html + generates email body
    ├─ git commit + push   → GitHub Pages serves the edition at a public URL
    └─ send_email.py       → Resend delivers minimal email with "Read →" CTA
```

**Why hosted + email link:** Gmail strips modern CSS (dark mode, backdrop-filter, Google Fonts). So the *real* design lives on a public web page, and the email is just a minimal preview with a button to open the full thing in the browser.

---

## Step 1: Figure out what you want

Before writing any code, decide these. Write them down — they drive every file you'll create.

### Columns (2–5)

For each column you want, write down:
- **Name** — e.g. "AI", "Ecommerce & Amazon", "Business & World"
- **Scope** — one sentence describing what belongs in it
- **Keywords** — 5–10 terms to search X for (e.g. `AI, LLM, agent, Claude, GPT, open source model`)
- **Semantic hints** — phrases that great content sounds like (e.g. "I built this", "new tool just dropped", "underrated", "this prompt is wild"). These surface hidden-gem posts that keyword search misses.
- **Mega-accounts to exclude** — up to 10 big handles per column so the newsletter isn't dominated by Reuters / TechCrunch / etc. The xAI API caps the exclude list at 10, so be selective.

### Delivery

- Email address
- Frequency (daily / weekdays / weekly)
- Local time (most use 7am)

### Design

- Dark or light mode (default: dark — most reliable in email)
- 2–5 column accent colors. Saturated but not neon:
  - Cyan `#22d3ee`, amber `#f59e0b`, violet `#a78bfa` (solid default triple)
  - Also good: emerald `#10b981`, rose `#f43f5e`, blue `#3b82f6`, fuchsia `#d946ef`
- Signature features you want (or not):
  - **Hero block** — one big "top story" auto-picked by importance score
  - **"Today in 30 seconds"** TL;DR strip — one top item per column at the top
  - **Liquid glass** (frosted-blur panels with ambient glows) on hero + TL;DR
  - **Signal tags** per post: 🔥 Trending / 💎 Under the radar / 🛠️ New / built / 💬 Community take

### Content philosophy (this is the big one)

Default Grok search surfaces mega-account engagement. That's boring. The algorithm this guide encodes is a **two-bucket retrieval** to solve that:

- **Bucket A (40% of slots):** mainstream trending — keyword search, Top mode, high-engagement filter
- **Bucket B (60%, more important):** hidden gems — semantic search on long-tail phrases, scored by `engagement-to-follower ratio`. A post from a 2k-follower account with 800 likes beats a 2M-follower account with 5k likes.
- **Hard floor:** at least 2 of 5 posts per column must come from accounts with <50k followers.

If you want mostly-mainstream, flip the percentages. If you want all hidden gems, crank bucket B to 80%+.

### Exclude these categories

Default list (customize as needed):
- Entertainment / celebrity gossip
- Music festivals (Coachella etc.)
- Award shows / red carpet
- Sports (unless directly about business/tech)
- Partisan outrage with no business impact
- Crypto shilling / meme coins
- Astrology / horoscopes
- Lifestyle / fashion

---

## Step 2: Create your accounts

### xAI Grok API

1. Go to https://console.x.ai
2. Sign up, add a payment method (required)
3. Set a spending limit (recommend $20/month to be safe)
4. **API Keys → Create API Key** → name it "Daily Brief" → **copy the key** (starts with `xai-`) — you won't see it again

**Cost info:** use `grok-4-1-fast-non-reasoning`. Full daily run = ~$0.10–$0.15. About $3–5/month for daily delivery.

### Resend (email delivery)

1. Go to https://resend.com
2. **Sign up with the same email you want to receive the newsletter at.** The default sandbox sender `onboarding@resend.dev` only delivers to the Resend account owner's email. If you register with `me@work.com` and send to `me@personal.com`, it silently drops.
3. https://resend.com/api-keys → **Create API Key** → name it "Daily Brief" → copy it (starts with `re_`)

Free tier: 100 emails/day, 3,000/month — plenty.

**Later upgrade:** verify your own domain with Resend (adds SPF/DKIM/DMARC DNS records). Takes ~10 min. Makes emails land in Primary inbox instead of Spam, and shows "From: Daily Brief `<brief@yourdomain.com>`" instead of Resend's domain. Worth doing once the pipeline is live.

### GitHub account + public repo

1. https://github.com — create account if needed
2. **New repository** — name it whatever (e.g. `daily-brief` or `newsletter`). **Must be PUBLIC** (free GitHub Pages requires public repos; private requires GitHub Pro at $4/mo)
3. Do NOT initialize with a README — leave it empty

### Claude Pro

If you don't have Claude Pro yet: https://claude.ai/upgrade. Pro = 5 Claude Code routine runs/day, which is plenty for daily delivery.

---

## Step 3: Scaffold the project locally

Create a folder (e.g. `~/Newsletter` or `C:\Users\<you>\Desktop\Newsletter`). Inside, create each file below. Substitute your own topic/design choices when you get to `topics.json` and the template.

### File structure

```
Newsletter/
├── newsletter.py              Grok API fetch
├── render.py                  JSON → hosted HTML
├── publish.py                 Copy to docs/ + generate email body
├── send_email.py              Resend API delivery
├── topics.json                Your columns + selection rules
├── routine-prompt.md          Paste target for the Claude Code Routine UI
├── requirements.txt
├── .env.example               Template for local secrets
├── .env                       Local secrets (NEVER commit)
├── .gitignore
├── README.md
├── docs/                      Hosted editions go here (GitHub Pages serves this)
└── templates/
    ├── email.html.j2          Full dark-mode edition
    └── email-summary.html.j2  Gmail-safe minimal email body
```

### `requirements.txt`

```
xai-sdk>=0.1.0
jinja2>=3.1.0
python-dotenv>=1.0.0
resend>=2.0.0
```

### `.gitignore`

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

### `.env.example`

```
XAI_API_KEY=xai-your-key-here
NEWSLETTER_TO=you@example.com
NEWSLETTER_SITE_URL=https://YOUR-USER.github.io/YOUR-REPO
RESEND_API_KEY=re_your-key-here
GRPC_DNS_RESOLVER=native
# NEWSLETTER_FROM=Daily Brief <brief@yourdomain.com>   # uncomment after verifying your domain
```

### `topics.json`

Fill in your own columns. Template:

```json
{
  "columns": [
    {
      "name": "AI",
      "slug": "ai",
      "accent": "#22d3ee",
      "description": "Frontier AI models, research, agents, builder launches, novel techniques.",
      "x_keywords": ["AI", "LLM", "agent", "Claude", "GPT", "Gemini", "open source model", "prompt engineering"],
      "x_semantic_hints": [
        "new AI tool just dropped",
        "built with Claude Code",
        "this prompt is wild",
        "underrated AI use case",
        "I shipped this agent"
      ],
      "news_query": "AI model releases and research breakthroughs in the last 24 hours",
      "exclude_handles": ["OpenAI", "AnthropicAI", "Google", "GoogleDeepMind", "xai", "MetaAI", "TechCrunch", "verge", "WIRED", "arstechnica"]
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
      "sports (unless directly about business/tech)",
      "partisan outrage with no business impact",
      "crypto shilling / meme coins"
    ]
  }
}
```

### `newsletter.py`

The Grok fetch. Critical setup at the top — must happen before importing `xai_sdk`:

```python
"""Fetches trending X posts + web news per column via Grok."""
import json, os, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv

# MUST be before `from xai_sdk import ...`:
# 1. Point grpc at the sandbox's CA bundle if one is set (Claude Code cloud env).
_ca = os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("SSL_CERT_FILE")
if _ca and not os.environ.get("GRPC_DEFAULT_SSL_ROOTS_FILE_PATH"):
    os.environ["GRPC_DEFAULT_SSL_ROOTS_FILE_PATH"] = _ca
# 2. Force grpc to use OS DNS resolver instead of c-ares (which breaks in sandboxes
#    with "DNS cache overflow" errors).
os.environ.setdefault("GRPC_DNS_RESOLVER", "native")

from xai_sdk import Client
from xai_sdk.chat import system, user
from xai_sdk.tools import web_search, x_search

ROOT = Path(__file__).parent
MODEL = "grok-4-1-fast-non-reasoning"  # cheaper; skip thinking tokens
```

Then a `build_system_prompt(col, rules, since_date)` function that returns the prompt template below, and a `fetch_column(client, col, rules, since_date)` function that calls Grok:

```python
def fetch_column(client, col, rules, since_date):
    from_date = datetime.now(timezone.utc) - timedelta(hours=rules["time_window_hours"])
    # xAI caps excluded_x_handles at 10 — truncate.
    excludes = (col.get("exclude_handles") or [])[:10]
    tools = [
        x_search(from_date=from_date, excluded_x_handles=excludes),
        web_search(),
    ]
    chat = client.chat.create(model=MODEL, tools=tools, temperature=0.3)
    chat.append(system(build_system_prompt(col, rules, since_date)))
    chat.append(user(f"Assemble today's '{col['name']}' column. Return JSON only."))
    response = chat.sample()
    # strip optional code fences, parse JSON, return dict
```

And a `pick_hero(columns)` function that picks the single highest-`importance` item across all columns for the hero slot (free — no extra LLM call).

### The system prompt (this is the load-bearing piece)

Inside `build_system_prompt`:

```
You curate the "{name}" column of a daily newsletter. Focus: {description}

TIME WINDOW: posts/articles from since:{since_date} only (last {hours}h).

TOOL BUDGET (STRICT — exceeding wastes money):
  - Max {max_calls} search tool calls TOTAL across x_search and web_search combined.
  - DO NOT call x_thread_fetch — we don't need thread context.
  - DO NOT run "disambiguation" follow-up searches for specific names you encounter.
    Use whatever you got from initial searches; if unsure about a name, quote the post.
  - Maximum ONE web_search call. Use a single broad query.
  - Plan before calling — aim for 3 calls total: one x_keyword_search, one x_semantic_search,
    one web_search.

TWO-BUCKET RETRIEVAL:
  A) Mainstream (40%): x_keyword_search Top mode, min_faves:500. Keywords: {keywords}.
  B) Hidden gems (60%, MORE IMPORTANT): x_semantic_search on phrases like:
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

Keep summaries TIGHT (max 15 words). JSON ONLY.
```

### `render.py`

Loads `newsletter.json`, renders `templates/email.html.j2` via Jinja2. Provides custom filters:
- `fmt_int` — `1234 → "1.2K"`, `1500000 → "1.5M"`
- `time_ago` — ISO timestamp → `"4h ago"`

And a `build_tldr(hero, columns)` helper that picks one highest-importance item per column (excluding whatever became the hero) for the "Today in 30 seconds" strip.

### `templates/email.html.j2` (the hosted edition — goes big)

This is where design lives. Rendered in a real browser, not Gmail, so you can go wild:

- `<body>` with radial-gradient ambient glows (cyan top-left, amber top-right, violet bottom)
- Google Fonts: **Instrument Serif** for display + **Space Grotesk** for body
- Masthead with serif italic accent: `<h1>The <em>morning</em> edition</h1>`
- "Today in 30 seconds" strip with `backdrop-filter: blur(18px)`
- Hero block: `backdrop-filter` + rainbow top border + inner radial color orbs
- Responsive `<table>` 3-column layout that stacks <700px
- Per-column accent color on: column dot, section labels, signal pills, card links
- Cards: rounded `#16161a` bg with `#27272a` border, bold sans headline, muted post body with colored left border, "Why:" callout
- News cards: plain rounded block, bold title, source · time-ago, summary

### `templates/email-summary.html.j2` (the Gmail-safe email body — goes minimal)

Must be email-safe — different file, different rules:
- Inline styles only (no `<style>` blocks)
- Table-based layout
- Light mode (`#f4f4f5` bg) — dark mode breaks in many clients
- NO backdrop-filter, NO Google Fonts (Gmail strips them)
- System font stack with Georgia serif fallback
- Structure: masthead → hero preview with gradient background → TL;DR list → big CTA button → footer
- One primary CTA: **"Read the full brief →"** linking to `{{ url }}`

### `publish.py`

```python
def publish():
    """Copy newsletter.html → docs/{date}.html + docs/index.html; rebuild archive.html"""

def render_email(public_url):
    """Render email-summary.html.j2 → email.html with the URL baked in"""
```

Also generates `docs/archive.html` — a simple list of every dated edition, newest first, so you can scroll back through history.

### `send_email.py`

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

Build a plain-text fallback body with the TL;DR bullets + link. Helps deliverability (some spam filters downrank HTML-only emails) and covers clients that don't render HTML.

### `routine-prompt.md`

This is what you'll paste into the Claude Code Routine UI later:

```
You are the delivery agent for the user's daily newsletter.

Python deps are pre-installed by the environment's setup script —
do NOT run pip install.

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

## Step 4: Local test (critical — don't skip)

Prove the pipeline works on your machine before touching the cloud.

```
cd Newsletter
pip install -r requirements.txt
cp .env.example .env
# edit .env — fill in XAI_API_KEY and NEWSLETTER_TO

python newsletter.py     # ~30–90 seconds — calls Grok 3 times
python render.py         # produces newsletter.html
python publish.py        # produces docs/{date}.html + email.html
```

Open `newsletter.html` in your browser. Iterate on the design until it looks right — this is *much* faster than iterating via the cloud routine. Also open `email.html` to preview what Gmail will receive.

**If `newsletter.py` fails locally**, common fixes:
- `XAI_API_KEY not set` → you forgot to save `.env` or edit it
- `A maximum of 10 handles can be excluded` → a column's `exclude_handles` list has >10 entries. Trim.
- `Live search is deprecated` → `pip install -U xai-sdk`

---

## Step 5: Deploy to GitHub + GitHub Pages

From your Newsletter folder:

```
git init -b main
git remote add origin https://github.com/<you>/<repo>.git
git add .
git commit -m "Initial scaffold"
git push -u origin main
```

Then on GitHub:
1. Your repo → **Settings → Pages**
2. Source: `Deploy from a branch`
3. Branch: `main` / folder: `/docs`
4. **Save**
5. Wait ~60 seconds, refresh. Green banner: `Your site is live at https://<you>.github.io/<repo>/`
6. Visit that URL + `/YYYY-MM-DD.html` (today's date) — your full edition should load in dark mode with liquid glass etc.
7. Update `NEWSLETTER_SITE_URL` in your local `.env` to this real URL
8. Re-run `python publish.py` so `email.html` has the correct link
9. `git add . && git commit -m "Real URL" && git push`

---

## Step 6: Create the Claude Code Routine

### 6a. Configure the cloud environment

The default "Trusted" network policy blocks the APIs we need. Go to https://claude.ai/code → **Environments** → create or edit the environment your routine will use:

**Network access:** change to **Custom**

**Allowed domains** (one per line):
```
api.x.ai
api.resend.com
pypi.org
files.pythonhosted.org
github.com
```

**Setup script:**
```
pip install --no-input --ignore-installed xai-sdk jinja2 python-dotenv resend
```

Why these specific flags:
- `--ignore-installed` — Ubuntu ships `packaging` via distutils and pip refuses to overwrite it without this flag
- Inline packages (not `-r requirements.txt`) — the setup script runs BEFORE the repo clones, so it can't read repo files
- Running in setup script (not the routine prompt) — runs before Claude starts, so the routine starts faster and uses fewer Claude tokens

### 6b. Create the routine

https://claude.ai/code/routines → **New routine**:

| Field | Value |
|---|---|
| Name | Daily Brief |
| Repository | `<you>/<repo>` · branch `main` |
| Environment | the one configured above |
| Trigger | Scheduled · Daily · 07:00 local |
| Connectors | **none** (delivery is via Resend API directly) |
| Prompt | paste contents of `routine-prompt.md` |

**Environment variables** (separate panel from the environment's setup config):

| Name | Value |
|---|---|
| `XAI_API_KEY` | your Grok key |
| `NEWSLETTER_TO` | your delivery email |
| `NEWSLETTER_SITE_URL` | your GitHub Pages URL |
| `RESEND_API_KEY` | your Resend key |
| `GRPC_DNS_RESOLVER` | `native` |

### 6c. Grant repo write access

When you select the repo, you'll be asked for permissions. Grant **write access to contents** — the routine needs it to push the daily edition to `main` so GitHub Pages updates.

### 6d. Run now

Click **Run now**. Expected sequence (~3–4 min):
1. Container spin-up (~20 sec)
2. Setup script: `pip install` (~60 sec)
3. Claude session starts
4. `python newsletter.py` (~90 sec — 3 columns × ~30 sec each)
5. `python render.py`, `publish.py` (each <2 sec)
6. `git push` (~5 sec)
7. `python send_email.py` (~2 sec) — Resend returns a message ID
8. Email arrives

---

## Step 7: Check your Spam folder

The first email almost always lands in **Gmail Spam**. This is normal — emails from `@resend.dev` (Resend's sandbox domain) are brand-new senders and Gmail distrusts them.

### Quick fix (30 seconds, permanent)

- Open the email in Spam
- Click **"Report not spam"**
- Click the sender name → **"Add to contacts"**

All future sends land in Primary inbox.

### Proper fix (10 min, professional)

Verify your own domain with Resend:
1. Resend dashboard → **Domains → Add Domain** → your domain
2. Add the provided SPF/DKIM/DMARC records to your DNS registrar
3. Wait ~5 min for verification
4. Update routine env: `NEWSLETTER_FROM=Daily Brief <brief@yourdomain.com>`
5. Emails now come from your own domain — Primary inbox, no spam risk, professional "From" line

---

## Troubleshooting runbook

Every one of these is a bug hit during the real build. If the first run fails, work through these.

### Setup script fails

| Error | Cause | Fix |
|---|---|---|
| `Cannot uninstall 'packaging'` | Ubuntu distutils conflict | Already included: `--ignore-installed` flag |
| `Could not open requirements.txt` | Setup script runs before repo clones | Inline package names instead of using `-r requirements.txt` |
| pip hangs >2 min on downloads | Custom allowlist missing PyPI hosts | Add `pypi.org` and `files.pythonhosted.org` |

### `newsletter.py` fails

| Error | Cause | Fix |
|---|---|---|
| `CERTIFICATE_VERIFY_FAILED` | Sandbox TLS interception | `newsletter.py` handles this via `REQUESTS_CA_BUNDLE` → grpc. If still failing, confirm `api.x.ai` is in allowlist. |
| `DNS cache overflow` (grpc UNAVAILABLE) | c-ares broken in sandbox | Set `GRPC_DNS_RESOLVER=native` as routine env var |
| `A maximum of 10 handles can be excluded` | Column's `exclude_handles` has >10 | Trim to 10 in `topics.json` |
| `Live search is deprecated` | Outdated xai-sdk | `pip install -U xai-sdk` |
| `XAI_API_KEY not set` | Secret didn't reach runtime | Confirm it's in the **routine's** env vars |

### `send_email.py` reports success but no email arrives

| Check | Fix |
|---|---|
| Does the returned message ID appear in Resend's Emails dashboard? | If no → you're checking a different account. Regenerate the API key under the correct account. |
| Email in Gmail Spam? | Expected for first send. "Not Spam" + Add Contact. |
| Resend dashboard shows bounce/reject? | Sandbox sender only delivers to the Resend account owner's email. `NEWSLETTER_TO` must match the email that registered the Resend account. |

### `git push` fails in routine

| Error | Fix |
|---|---|
| `Permission denied (push)` | Re-select repo in routine settings, grant write access |
| `nothing to commit` | First run was already committed OR `publish.py` failed silently. Check `docs/` contents. |

### Cost higher than expected (~$0.30+/run)

Tool calls dominate, not tokens. Common causes:
- Grok making `x_thread_fetch` calls — **forbid in prompt** (already in template)
- Grok doing disambiguation web searches — **forbid in prompt** (already in template)
- Using reasoning model — use `grok-4-1-fast-non-reasoning` not `-reasoning`
- Too many columns — 3 is optimal
- `max_tool_calls_per_column` too high — set to 3

---

## Iteration in week 2

1. **Tune `topics.json`** — if a column returns weak posts, refine `x_semantic_hints` (what great content sounds like) and `exclude_handles` (which mega-accounts keep leaking through).
2. **Tune the system prompt** in `newsletter.py` if Grok isn't respecting a rule. Be very explicit.
3. **Iterate the design locally** — edit `templates/email.html.j2`, run `python render.py`, refresh browser. Commit when happy. Tomorrow's routine picks it up automatically.
4. **Bookmark your archive** — `docs/archive.html` auto-regenerates each run.
5. **Verify a custom domain** in Resend (big upgrade — no more spam filter).
6. **Add a column** — add an entry to `topics.json → columns` with its own accent color.

---

## The 5 things not to break

1. **Two-bucket retrieval** (40% mainstream + 60% hidden gems) — this is what makes this newsletter different from every generic news scraper
2. **≥2 of 5 posts from <50k-follower accounts** — the floor that prevents mega-account dominance
3. **Excluded-categories list in the system prompt** — keeps Coachella-class noise out
4. **Hosted web edition + minimal email link** — don't fight Gmail's CSS sanitizer
5. **`grok-4-1-fast-non-reasoning` + tool budget** — keeps daily cost under $0.20

---

## You're done when

- You've received an email with a working "Read the full brief →" button
- Clicking it loads the full styled edition at your GitHub Pages URL
- The hosted edition shows today's date with all your columns populated
- The routine is scheduled and enabled (not manual-run only)
- Your email lands in Primary inbox (or you've moved it out of Spam)

The routine now fires every morning automatically. Edit `topics.json` or the template any time, commit + push, and tomorrow's run uses the new version.

Happy reading.
