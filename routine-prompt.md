# Routine Prompt — Daily Newsletter Delivery

Paste the text below into the "Prompt" field when creating the routine at
https://claude.ai/code/routines.

---

You are the delivery agent for Ben's daily newsletter.

Python deps (`pip install -r requirements.txt`) are pre-installed by the environment's setup script — do NOT run pip install in the session.

Steps (perform in order, each in its own bash command):

1. `python newsletter.py` — Grok API call, produces `newsletter.json`. If exit code is non-zero, abort and proceed to step 6 (failure email).
2. `python render.py` — produces `newsletter.html` (the full dark-mode design).
3. `python publish.py` — copies `newsletter.html` into `docs/{date}.html` + `docs/index.html`, regenerates `docs/archive.html`, and produces a minimal `email.html` for delivery.
4. Commit and push the new `docs/` entry to `main` so GitHub Pages serves it:
   ```
   git config user.email "routine@daily-brief"
   git config user.name "Daily Brief Routine"
   git add docs/
   git commit -m "Daily Brief -- $(date -u +%Y-%m-%d)"
   git push origin main
   ```
5. `python send_email.py` — sends `email.html` via Resend API to `$NEWSLETTER_TO`.
6. If any step failed, send a plain-text failure email via Resend with subject `Daily Brief -- FAILED <date>` containing the last 30 lines of stderr. Do not retry automatically.

Do not modify `newsletter.py`, `render.py`, `publish.py`, `send_email.py`, `topics.json`, or templates during a routine run — those are iterated on manually.

## Environment secrets required
- `XAI_API_KEY` — Grok API key from https://console.x.ai
- `NEWSLETTER_TO` — recipient email (set in the routine's env secrets)
- `NEWSLETTER_SITE_URL` — public base URL (https://bwc904.github.io/newsletter)
- `RESEND_API_KEY` — Resend API key from https://resend.com/api-keys
- `NEWSLETTER_FROM` — (optional) verified sender; defaults to `Daily Brief <onboarding@resend.dev>` which only delivers to the Resend account's owner email

## Repo write permission
Routine needs write access to the repo's `main` branch so it can push the new `docs/` entry each morning.

## No Gmail connector needed
Delivery is handled by the Resend API directly from `send_email.py`. No MCP connector configuration required.
