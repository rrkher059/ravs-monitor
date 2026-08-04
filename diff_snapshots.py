import json
import re
import sys
from datetime import date
from pathlib import Path

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


def print_report(diff: dict) -> None:
    print("Star count changed:")
    for repo, prev_count, cur_count in diff["changed"]:
        print(f"  {repo}: {prev_count} -> {cur_count}")
    if not diff["changed"]:
        print("  (none)")

    print("New repos added to the list:")
    for repo in diff["added"]:
        print(f"  {repo}")
    if not diff["added"]:
        print("  (none)")

    print("Repos no longer in the list:")
    for repo in diff["removed"]:
        print(f"  {repo}")
    if not diff["removed"]:
        print("  (none)")

    print("ERROR - fetch broke (was tracked, now null):")
    for repo in diff["broken"]:
        print(f"  {repo}")
    if not diff["broken"]:
        print("  (none)")


if __name__ == "__main__":
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
    print_report(diff_snapshots(previous, current))
