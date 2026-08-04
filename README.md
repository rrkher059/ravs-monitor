# ravs-monitor

Watches a list of GitHub repos' star counts once a day, saves each day's numbers, and emails an
alert when something changes. Runs on GitHub Actions; no server to keep up.

## How it works

1. **Fetch** (`github_stars.py`) — pulls `stargazers_count` for each repo in `REPOS` from the
   GitHub API and saves the result as `snapshots/YYYY-MM-DD.json`.
2. **Diff** (`diff_snapshots.py`) — compares today's snapshot to the most recent earlier one and
   sorts what it finds into four categories.
3. **Alert** — if the diff found anything at all, it emails the report via Resend. A clean diff
   sends nothing.

This runs automatically once a day via GitHub Actions (`.github/workflows/daily-monitor.yml`),
which also commits each day's snapshot back to the repo so the next run has something to compare
against.

## The four diff categories

| Category | Meaning |
|---|---|
| **Star count changed** | A repo's number is different from yesterday's — a real change. |
| **New repos added** | A repo showed up in today's snapshot that wasn't in the previous one. |
| **Repos no longer in the list** | A repo was in the previous snapshot but is missing today. |
| **Error (fetch broke)** | A repo had a real number before and is `null` today. |

That last category looks like the other three but isn't the same kind of thing: it doesn't mean
the repo changed, it means **the fetch step failed for that repo** (network blip, API error,
rename, etc.) and the script degraded gracefully instead of crashing. The alert email's subject
line reflects this — a run with only real changes is titled like `3 changes`; a run where
something is `null` is titled `SCRAPER ERROR` (or `2 changes, SCRAPER ERROR` if both happened at
once). Treat that subject as "something's broken, go look," not "the data changed."

## Swapping in a different data source

Fetching is deliberately split from diffing/alerting so a new source doesn't touch either.
`storage.py` defines the one thing every fetcher has to agree on: write a JSON object shaped like
`{"name": number_or_null, ...}` to `snapshots/YYYY-MM-DD.json` via `save_snapshot()`. That's the
whole contract — `diff_snapshots.py` only ever reads that shape, it has no idea the data came from
GitHub.

To add a new source: write a script that builds a `dict` of `{identifier: value_or_None}` (catch
your own per-item failures and store `None` for them, the way `github_stars.py` does for a repo
whose fetch fails) and call `storage.save_snapshot(results)` at the end. Nothing else needs to
change.

`ravs_watch.py` in this repo is an example of a *different* fetcher (a single Shopify product
page, watching a number in the page text) that predates this contract and isn't wired into it —
it's currently blocked by the site's bot protection anyway, so it's left as-is rather than forced
into a pipeline it can't run in.

## Local setup

```
python3 -m pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env` with a real Resend API key and recipient address. `.env` is gitignored and never
committed — `.env.example` shows the shape with fake values.

| Variable | Purpose |
|---|---|
| `RESEND_API_KEY` | API key from your Resend account |
| `ALERT_TO` | Recipient address for alert emails |

The sender address is fixed to `onboarding@resend.dev` (Resend's shared sandbox sender) in code —
no variable needed for it.

Run the pipeline manually:

```
python3 github_stars.py      # fetch today's counts, save snapshot
python3 diff_snapshots.py    # compare to previous snapshot, email if something changed
```

Two flags on `diff_snapshots.py` for checking your setup without waiting for a real change:

```
python3 diff_snapshots.py --test         # sends a sample alert email immediately
python3 diff_snapshots.py --fail-alert "message"   # sends a SCRAPER ERROR alert with this body
```

## GitHub Actions

`.github/workflows/daily-monitor.yml` runs the fetch + diff once a day (`0 12 * * *`, 8am Eastern)
and can also be triggered manually from the Actions tab (`workflow_dispatch`).

Before it can send alerts, add two repo secrets under Settings → Secrets and variables → Actions:

- `RESEND_API_KEY`
- `ALERT_TO`

After a successful run, it commits the new `snapshots/YYYY-MM-DD.json` back to the repo (skipped
if nothing changed, so a same-day re-run doesn't create an empty commit) — that's how tomorrow's
run gets something to diff against.

If any step in the job fails outright — not a single repo's fetch failing, but the whole process
dying — a final step (`if: failure()`) still runs and sends a `SCRAPER ERROR` alert with a link to
the failed run, using the same Resend path as everything else. That's independent of GitHub's own
notification settings, so a total crash is loud even if you've never touched your GitHub
notification preferences.

## Files

| File | What it does |
|---|---|
| `github_stars.py` | Fetches star counts for `REPOS` from the GitHub API, saves a snapshot. |
| `diff_snapshots.py` | Compares today's snapshot to the previous one, emails an alert if anything's found. |
| `storage.py` | Shared snapshot read/write helpers — the contract fetchers and the diff script agree on. |
| `ravs_watch.py` | Standalone, unintegrated example fetcher for a Shopify page; currently blocked by Cloudflare. |
| `requirements.txt` | Pinned Python dependencies (`requests`, `python-dotenv`). |
| `.env.example` | Documents the required environment variables with fake values. |
| `.github/workflows/daily-monitor.yml` | Runs the daily pipeline on a schedule or on demand. |
| `snapshots/` | One JSON file per day, `{repo: stars_or_null}` — the data history the diff reads from. |
