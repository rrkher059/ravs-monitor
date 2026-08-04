# ravs-monitor

Scripts for watching public web data for changes and alerting by email when something moves.

## Setup

```
python3 -m pip install requests python-dotenv
cp .env.example .env
```

Fill in `.env` with a real Resend API key and recipient address (see below). `.env` is gitignored
and never committed.

## Scripts

### `github_stars.py`

Fetches the current `stargazers_count` for a list of repos from the GitHub API and saves the
result to `snapshots/YYYY-MM-DD.json`.

- Edit the `REPOS` list at the top of the file to change which repos are tracked.
- Waits 1 second between requests.
- If a repo's fetch fails (e.g. 404), its value is stored as `null` instead of crashing the run.

Run it:

```
python3 github_stars.py
```

### `diff_snapshots.py`

Compares today's snapshot against the most recent previous one and reports four categories:

1. **Star count changed** — a repo's count differs between the two snapshots.
2. **New repos added** — present today, wasn't in the previous snapshot.
3. **Repos no longer in the list** — was in the previous snapshot, missing today.
4. **Error (fetch broke)** — had a real count before, is `null` today. This means the script
   failed to fetch that repo, not that anything about the repo actually changed.

If there's no previous snapshot yet, it prints `baseline saved` and exits.

If any of the four categories has entries, it sends an alert email via the
[Resend](https://resend.com) API using the credentials from `.env`. No email is sent on a clean
diff. The subject line summarizes what happened (e.g. `3 changes`, or `SCRAPER ERROR` if any
fetch broke), and the body is the same diff report printed to the console.

Run it:

```
python3 diff_snapshots.py
```

Pass `--test` to send a sample alert email immediately, regardless of the actual diff, to confirm
your Resend credentials work:

```
python3 diff_snapshots.py --test
```

### `ravs_watch.py`

A separate, earlier watcher for a single Shopify product page — looks for the number in the
"Page Reference Answers to RAVS Reviewer's Questions: N" line in the page HTML. Currently blocked
by the site's Cloudflare bot challenge on direct HTTP requests; not yet wired into the
snapshot/diff/email flow above.

## Environment variables

See `.env.example` for the full list with placeholder values:

| Variable          | Purpose                                          |
|-------------------|---------------------------------------------------|
| `RESEND_API_KEY`  | API key from your Resend account                  |
| `ALERT_TO`        | Recipient address for alert emails                 |

The sender address is fixed to `onboarding@resend.dev` (Resend's shared sandbox sender) in the
script itself — no variable needed for it.

## Typical workflow

```
python3 github_stars.py      # fetch today's counts, save snapshot
python3 diff_snapshots.py    # compare to previous snapshot, email if something changed
```

## GitHub Actions

`.github/workflows/daily-monitor.yml` runs both scripts once a day (`0 12 * * *`, i.e. 8am
Eastern) and can also be triggered manually from the Actions tab (`workflow_dispatch`).

Before it can send alerts, add two repo secrets under Settings → Secrets and variables → Actions:

- `RESEND_API_KEY`
- `ALERT_TO`

After each run, the workflow commits the new `snapshots/YYYY-MM-DD.json` file back to the repo
(only if it's actually new — a same-day re-run won't create an empty commit), so the next run has
a previous snapshot to diff against.
