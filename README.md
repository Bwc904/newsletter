# Daily Brief Newsletter

Dark-mode, liquid-glass daily edition with trending X posts + web news across:
**AI · Ecommerce & Amazon · Business & World**.

Hosted as a webpage (so styling survives), with a minimal email in your inbox that links to it.

Built on **Claude Code Routines** (scheduled cloud execution) + **xAI Grok API** (X search + web news) + **GitHub Pages** (hosting).

## Pipeline

```
Routine (cloud, daily 7am)
  ├─ python newsletter.py          # Grok API → newsletter.json (~71k tokens, ~$0.10–0.15)
  ├─ python render.py               # → newsletter.html (full dark-mode design)
  ├─ python publish.py              # → docs/YYYY-MM-DD.html + docs/index.html + email.html
  ├─ git commit + push              # GitHub Pages picks up the new edition
  └─ python send_email.py           # sends via Resend API → Gmail inbox
```

Quality: Grok's two-bucket algorithm enforces ≥2 of 5 posts per column from accounts with <50k followers. Excludes mega-account news handles + entertainment/celebrity/sports/crypto-shill categories.

## Local test

```
pip install -r requirements.txt
cp .env.example .env
# edit .env — set XAI_API_KEY

python newsletter.py     # fetches, ~30–60s
python render.py         # renders newsletter.html
python publish.py        # copies to docs/, generates email.html
```

Open `newsletter.html` in a browser for the full version, or `email.html` to preview the Gmail body.

## Deploy

### 1. GitHub repo + Pages

1. Create a **public** GitHub repo (private requires GitHub Pro for Pages) — e.g. `daily-brief`.
2. Push this folder to it.
3. In the repo: **Settings → Pages** → Source: `Deploy from a branch` → Branch: `main` / folder: `/docs` → Save.
4. Note your public URL (shown on the Pages settings page) — looks like `https://<user>.github.io/daily-brief/`.

### 2. Sign up for Resend

1. https://resend.com → Sign up **with the same address you'll deliver to** (important — the sandbox sender can only deliver to the Resend account owner's email).
2. https://resend.com/api-keys → Create API key (name it "Daily Brief").
3. Free tier: 100 emails/day, 3,000/month — plenty.

### 3. Create the routine

https://claude.ai/code/routines → **New routine**:

- **Repository:** this repo, `main` branch
- **Environment secrets:**
  - `XAI_API_KEY` = your Grok key from https://console.x.ai
  - `NEWSLETTER_TO` = your delivery email
  - `NEWSLETTER_SITE_URL` = `https://bwc904.github.io/newsletter`
  - `RESEND_API_KEY` = your Resend key from step 2
- **Connectors:** none required
- **Trigger:** Scheduled · Daily · 07:00 local
- **Prompt:** paste contents of `routine-prompt.md`

### 4. Verify

Hit **Run now**. Within ~60 seconds you should:
- Receive the email with the "Read the full brief" button
- Click it → full liquid-glass edition loads at the hosted URL
- Browse `archive.html` to see past editions

## Files

| File | Purpose |
|---|---|
| `newsletter.py` | Fetch trending X posts + web news via Grok (3 columns) |
| `render.py` | Render `newsletter.json` → `newsletter.html` |
| `publish.py` | Copy HTML into `docs/`, generate email body |
| `templates/email.html.j2` | Full dark-mode edition (hosted) |
| `templates/email-summary.html.j2` | Minimal Gmail inbox body with CTA |
| `topics.json` | 3 columns + keywords + exclude lists + selection rules |
| `docs/` | Published editions (served by GitHub Pages) |
| `routine-prompt.md` | Paste into the Routines UI |
| `grokapidoc.md` | Grok API reference |

## Tuning

- **Bad post picks?** Edit `x_keywords` / `x_semantic_hints` / `exclude_handles` in `topics.json`.
- **Design iteration:** edit `templates/email.html.j2` — it's the hosted version, so full modern CSS works (dark mode, backdrop-filter, Google Fonts, etc.).
- **Email body iteration:** edit `templates/email-summary.html.j2` — must stay Gmail-safe (inline styles, tables, light-mode friendly).
- **Costs too high?** Lower `max_tool_calls_per_column` in `topics.json` from 3 → 2, or `final_posts_per_column` from 5 → 4.

## Expected cost

~$0.10–0.15 per run × 30 days = **~$3–5/month** for daily delivery.
