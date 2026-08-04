import json
import os
import re
import smtplib
import sys
from datetime import date
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv

SNAPSHOT_DIR = Path(__file__).parent / "snapshots"
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}\.json$")


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
    host = os.environ["SMTP_HOST"]
    port = int(os.environ["SMTP_PORT"])
    username = os.environ["SMTP_USERNAME"]
    password = os.environ["SMTP_PASSWORD"]
    sender = os.environ["EMAIL_FROM"]
    recipient = os.environ["EMAIL_TO"]

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = recipient
    message.set_content(body)

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(username, password)
        server.send_message(message)


if __name__ == "__main__":
    load_dotenv()

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
        counts = {category: len(entries) for category, entries in diff.items()}
        subject = (
            f"ravs-monitor alert: {counts['changed']} changed, "
            f"{counts['added']} added, {counts['removed']} removed, "
            f"{counts['broken']} broken"
        )
        send_alert_email(subject, report)
        print("alert email sent")
