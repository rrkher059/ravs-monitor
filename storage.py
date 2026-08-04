import json
import re
from datetime import date
from pathlib import Path

SNAPSHOT_DIR = Path(__file__).parent / "snapshots"
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}\.json$")


def today_snapshot_path() -> Path:
    return SNAPSHOT_DIR / f"{date.today().isoformat()}.json"


def save_snapshot(results: dict) -> Path:
    SNAPSHOT_DIR.mkdir(exist_ok=True)
    path = today_snapshot_path()
    path.write_text(json.dumps(results, indent=2))
    return path


def load_snapshot(path: Path) -> dict:
    text = path.read_text()
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in snapshot file {path}: {exc}") from exc


def find_previous_snapshot(today_path: Path) -> Path | None:
    candidates = [
        p for p in SNAPSHOT_DIR.glob("*.json")
        if DATE_PATTERN.match(p.name) and p != today_path
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stem)
