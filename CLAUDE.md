## Preferences
- Be direct. Run commands without asking for permission on safe operations.
- Don't create files unless necessary.
- Skills are installed at `~/.claude/skills/` (pdf, docx, pptx, xlsx, canvas-design, and more).

# Fluitsignaal

Ticket alert service that notifies users when tickets go on sale for major sporting events.

## What this project does
- Monitors ticket sale dates for 22+ sporting events across tennis, football, golf, rugby and hockey
- Sends personalised email alerts to users the day before and day of each sale
- Sends a weekly digest every Monday at 8am
- Has a local admin interface to manage events and dates

## Project structure
- `events_db.json` — master database of all events (edit via admin, not directly)
- `config.py` — shared config: loads all secrets from environment variables, no hardcoded credentials in any script
- Subscribers live in a Google Sheet (`SPREADSHEET_ID` in config.py, worksheet "Users"); `send_alerts.py`/`weekly_digest.py`/`welcome_email.py` all read from there. `users.csv` was removed 2026-09-04 — it was dead, unused by any script.
- `send_alerts.py` — daily alert script, runs at 9am via cron
- `weekly_digest.py` — weekly HTML email digest, runs Monday 8am via cron
- `welcome_email.py` — sends the welcome email to new signups
- `sync_events.py` — pushes events_db.json to the "Events" worksheet in the same Google Sheet; called automatically by admin.py's /save endpoint
- `admin.py` — local web server for the event admin interface (its /save endpoint writes events_db.json and triggers sync_events.py — use this instead of hand-editing the JSON)
- `admin.html` — admin UI, runs at http://localhost:8765
- `apps_script.gs` — Google Apps Script backend (deployed separately on Google's side, not run from this repo) for the signup form and Stripe checkout; reads `STRIPE_SECRET` from Apps Script's own Script Properties, not from this file

## Secrets / config
All secrets are loaded from environment variables via `config.py` — nothing is hardcoded in the scripts anymore (fixed 2026-09-03, see Important notes).
- `SMTP_PASSWORD` — Gmail app password for Jouwfluitsignaal@gmail.com (needed by anything that sends email; not required to import config.py itself — e.g. sync_events.py only needs Google creds)
- `TWILIO_SID` / `TWILIO_TOKEN` — optional, only needed if SMS reminders are used
- `GOOGLE_CREDENTIALS_JSON` — full service-account JSON as a string (used in GitHub Actions); falls back to a local `credentials.json` file (path overridable via `GOOGLE_CREDENTIALS_FILE`) for local runs — that file is gitignored, never commit it
- For local manual runs, secret values are in `.env.local` (gitignored) — `set -a; source .env.local; set +a` before running a script

## How to run
Start the admin: `nohup python3 admin.py &`
Send alerts manually: `set -a; source .env.local; set +a; python3 send_alerts.py`
Send digest manually: `set -a; source .env.local; set +a; python3 weekly_digest.py`

## Email config
Sending from: Jouwfluitsignaal@gmail.com
Alerts go to each subscriber's email in the Google Sheet (see Project structure)
Digest currently goes to: coenvanrappard@gmail.com

## Weekly digest editorial / design rules
- The digest is sports-tickets only — one top-level section, `Tickets`. The old `Amsterdam this weekend` section (and its `weekend_picks.json` / `amsterdam_agenda.json` data) was removed 2026-09-03.
- Orange is the main editorial accent and should be used primarily for major section headings, not small badges or utility links.
- `On sale now` and `Action required` cards should use the same card system:
  - same image size
  - same CTA sizing
  - same title/date/body/button rhythm
- `Action required` cards should feel like a positive prep step, not an error state.
- The spotlight card should use the editorial layout:
  - title and meta across the full card
  - circular inset image embedded in the text block
  - green primary `More info` CTA
- The top `In this issue` block should stay simple and editorial:
  - plain linked contents list
  - no dashboard-style tiles

## Event statuses
- `on_sale` — tickets available now, show buy button
- `coming_soon` — sale date known, show countdown
- `action_required` — user must do something (register, create account), always requires notes field
- `date_unknown` — monitoring, no date yet

## Adding a new user
Add a row to the "Users" worksheet in the Google Sheet (`SPREADSHEET_ID` in config.py), or via the signup form on the live site (posts to the Apps Script backend, which appends the row).

## Website / repo
Live at: https://fluitsignaal.com (custom domain, CNAME in repo) — GitHub Pages serving https://github.com/coenvanrappard-lgtm/Fluitsignaal, public repo, default branch `main`.
This local folder and that GitHub repo were reconciled 2026-09-04 — before that, the live site's actual history (developed via a separate Claude session over several months, 90+ commits) had diverged from what existed locally. They're merged now; push/pull normally with git, no more manual uploading.

## Important notes
- Project lives locally at `~/Fluitsignaal` (moved off iCloud Drive on 2026-09-03 — cron/launchd couldn't read files under `~/Library/Mobile Documents/...` without Full Disk Access, which kept silently breaking). It's a git repo now; the old iCloud copy is archived at `Claude agent/Fluitsignaal (archief - verplaatst naar ~-Fluitsignaal)`.
- Admin must be running for http://localhost:8765 to work
- events_db.json is the source of truth — send_alerts.py reads from it
- Do not edit events_db.json directly, use the admin interface
- 2026-09-03: found hardcoded SMTP + Twilio credentials (and a stray leaked password for an unrelated Gmail account) committed in plaintext across several scripts, before this repo had ever been pushed anywhere. Moved everything to `config.py` reading from environment variables, deleted the legacy script that held the unrelated credential, gitignored the local credentials file, and rewrote git history from a clean commit so the old secrets aren't sitting in history either. Nothing was ever exposed publicly — caught before any push. Goal going forward: run send_alerts.py/weekly_digest.py on a schedule via GitHub Actions instead of local cron, using GitHub Actions secrets for SMTP_PASSWORD/TWILIO_*/GOOGLE_CREDENTIALS_JSON.

## GitHub Actions (scheduled sends)
- `.github/workflows/daily-alerts.yml` — runs `send_alerts.py` daily at 07:00 UTC
- `.github/workflows/weekly-digest.yml` — runs `weekly_digest.py` Mondays at 06:00 UTC
- Repo secrets are set (Settings → Secrets and variables → Actions): `SMTP_PASSWORD`, `TWILIO_SID`, `TWILIO_TOKEN`, `GOOGLE_CREDENTIALS_JSON`. Both workflows were manually triggered and verified working end-to-end on 2026-09-03 (digest actually sent from a GitHub-hosted runner).
- Local admin edits to events_db.json only take effect in the cloud runs once committed and pushed — the workflow checks out the repo fresh each run
- Local cron/launchd was never re-set-up after the 2026-09-03 move and doesn't need to be — these GitHub Actions workflows are now the only scheduled sender, running regardless of whether this laptop is on

## Known outstanding items (2026-09-04)
- The Apps Script backend (`apps_script.gs`) is deployed separately on Google's infrastructure. Its *deployed* copy likely still has the Stripe secret key hardcoded (from before the 2026-09-03 cleanup) — the source in this repo no longer does. Needs manually adding `STRIPE_SECRET` under the Apps Script project's Script Properties, then redeploying with the current script.
- `apps_script.gs` was never previously tracked in the live site's git history — only existed locally until the 2026-09-04 merge. Worth confirming the currently-deployed Apps Script version actually matches what's in this repo now.
- No subscriber signup flow issue — one already exists (site form → apps_script.gs `doPost` → Google Sheet). Low subscriber count (1) is a distribution/marketing question, not a missing feature.
