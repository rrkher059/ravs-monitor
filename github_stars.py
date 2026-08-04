import json
import time
from datetime import date
from pathlib import Path

import requests

REPOS = [
    "anthropics/claude-code",
    "anthropics/anthropic-sdk-python",
    "openai/openai-python",
    "langchain-ai/langchain",
    "ollama/ollama",
]

HEADERS = {"User-Agent": "rrkher059"}
SNAPSHOT_DIR = Path(__file__).parent / "snapshots"


def fetch_stargazers_count(repo: str) -> int:
    url = f"https://api.github.com/repos/{repo}"
    response = requests.get(url, headers=HEADERS, timeout=10)
    response.raise_for_status()
    return response.json()["stargazers_count"]


def collect_star_counts(repos: list[str]) -> dict:
    results = {}
    for i, repo in enumerate(repos):
        try:
            results[repo] = fetch_stargazers_count(repo)
        except requests.RequestException as exc:
            print(f"failed to fetch {repo}: {exc}")
            results[repo] = None
        if i < len(repos) - 1:
            time.sleep(1)
    return results


def save_snapshot(results: dict) -> Path:
    SNAPSHOT_DIR.mkdir(exist_ok=True)
    path = SNAPSHOT_DIR / f"{date.today().isoformat()}.json"
    path.write_text(json.dumps(results, indent=2))
    return path


if __name__ == "__main__":
    results = collect_star_counts(REPOS)
    path = save_snapshot(results)
    print(f"saved {path}")
    for repo, count in results.items():
        print(f"{repo}: {count}")
