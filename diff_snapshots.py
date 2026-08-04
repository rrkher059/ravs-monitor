import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

import requests
from dotenv import load_dotenv

RESEND_URL = "https://api.resend.com/emails"
ALERT_FROM = "onboarding@resend.dev"

SNAPSHOT_DIR = Path(__file__).parent / "snapshots"
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}\.json$")

SAMPLE_DIFF = {
    "changed": [("example/repo", 100, 105)],
    "added": ["example/new-repo"],
    "removed": ["example/removed-repo"],
    "broken": ["example/broken-repo"],
}


def load_snapshot(path: Path) -> dict:
    return json.loads(path.read_text())


def find_previous_snapshot(today_path: Path) -> Path | None:
    candidates = [
        p for p in SNAPSHOT_DIR.glob("*.json")
        if DATE_PATTERN.match(p.name) and p != today_path
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stem)


def diff_snapshots(previous: dict, current: dict) -> dict:
    changed, removed, broken = [], [], []

    for repo, prev_count in previous.items():
        if repo not in current:
            removed.append(repo)
            continue
        cur_count = current[repo]
        if prev_count is not None and cur_count is None:
            broken.append(repo)
        elif cur_count is not None and prev_count != cur_count:
            changed.append((repo, prev_count, cur_count))

    added = [repo for repo in current if repo not in previous]

    return {"changed": changed, "added": added, "removed": removed, "broken": broken}


def has_findings(diff: dict) -> bool:
    return any(diff.values())


def build_subject(diff: dict) -> str:
    total_changes = len(diff["changed"]) + len(diff["added"]) + len(diff["removed"])
    if diff["broken"]:
        return "SCRAPER ERROR" if total_changes == 0 else f"{total_changes} changes, SCRAPER ERROR"
    return f"{total_changes} changes"


def format_report(diff: dict) -> str:
    lines = []

    lines.append("Star count changed:")
    for repo, prev_count, cur_count in diff["changed"]:
        lines.append(f"  {repo}: {prev_count} -> {cur_count}")
    if not diff["changed"]:
        lines.append("  (none)")

    lines.append("New repos added to the list:")
    for repo in diff["added"]:
        lines.append(f"  {repo}")
    if not diff["added"]:
        lines.append("  (none)")

    lines.append("Repos no longer in the list:")
    for repo in diff["removed"]:
        lines.append(f"  {repo}")
    if not diff["removed"]:
        lines.append("  (none)")

    lines.append("ERROR - fetch broke (was tracked, now null):")
    for repo in diff["broken"]:
        lines.append(f"  {repo}")
    if not diff["broken"]:
        lines.append("  (none)")

    return "\n".join(lines)


def print_report(diff: dict) -> None:
    print(format_report(diff))


def send_alert_email(subject: str, body: str) -> None:
    api_key = os.environ["RESEND_API_KEY"]
    recipient = os.environ["ALERT_TO"]

    response = requests.post(
        RESEND_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "from": ALERT_FROM,
            "to": [recipient],
            "subject": subject,
            "text": body,
        },
        timeout=10,
    )
    response.raise_for_status()


if __name__ == "__main__":
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--test", action="store_true", help="send a sample alert email and exit, ignoring snapshots"
    )
    args = parser.parse_args()

    if args.test:
        report = format_report(SAMPLE_DIFF)
        subject = f"[TEST] {build_subject(SAMPLE_DIFF)}"
        send_alert_email(subject, report)
        print("test email sent")
        sys.exit(0)

    today_path = SNAPSHOT_DIR / f"{date.today().isoformat()}.json"
    if not today_path.exists():
        sys.exit(f"no snapshot found for today at {today_path}")

    previous_path = find_previous_snapshot(today_path)
    if previous_path is None:
        print("baseline saved")
        sys.exit(0)

    previous = load_snapshot(previous_path)
    current = load_snapshot(today_path)
    print(f"comparing {previous_path.name} -> {today_path.name}")

    diff = diff_snapshots(previous, current)
    report = format_report(diff)
    print(report)

    if has_findings(diff):
        subject = build_subject(diff)
        send_alert_email(subject, report)
        print("alert email sent")
