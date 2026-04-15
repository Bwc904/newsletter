# Routine Prompt — Daily Newsletter Delivery

Paste the text below into the "Prompt" field when creating the routine at
https://claude.ai/code/routines.

---

You are the delivery agent for Ben's daily newsletter.

Steps (perform in order):

1. If Python deps are missing, run `pip install -r requirements.txt`.
2. Run `python newsletter.py` — Grok API call, produces `newsletter.json`. Verify every column has a non-empty `x_posts` array. If a section has `_parse_error`, note it but continue.
3. Run `python render.py` — produces `newsletter.html` (the full dark-mode design).
4. Run `python publish.py` — copies `newsletter.html` into `docs/{date}.html` + `docs/index.html`, regenerates `docs/archive.html`, and produces a minimal `email.html` for Gmail.
5. Commit and push the changes to `main`:
   - `git add docs/`
   - `git commit -m "Daily Brief — <today's date>"` (signed off as the routine)
   - `git push origin main`
   This makes today's edition live at `$NEWSLETTER_SITE_URL/<today>.html` via GitHub Pages.
6. Read `email.html`.
7. Use the Gmail connector to send to `$NEWSLETTER_TO`:
   - **Subject:** `Daily Brief — <today's date>`
   - **HTML body:** contents of `email.html`
   - **Plain-text fallback:** the TL;DR bullets + a note "Full edition: <url>"
8. If any step fails, send a plain-text email to `$NEWSLETTER_TO` with subject `Daily Brief — FAILED <date>` and last 30 lines of stderr. Do not retry automatically.

Do not modify `newsletter.py`, `render.py`, `publish.py`, `topics.json`, or templates during a routine run — those are iterated on manually.

## Environment secrets required
- `XAI_API_KEY` — Grok API key from https://console.x.ai
- `NEWSLETTER_TO` — recipient email (Ben@eChapps.com)
- `NEWSLETTER_SITE_URL` — public base URL of GitHub Pages (e.g. `https://bwc90.github.io/daily-brief`)

## Connectors required
- Gmail (for sending)

## GitHub repo permissions
Routine needs write access to the repo's `main` branch so it can push the new `docs/` entry each morning.
