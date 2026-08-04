import re
import requests

URL = "https://sunshinesafetyservices.com/products/behavior-based-safety-program-isnetworld-ravs-section-us"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ravs-monitor/1.0)"}

PATTERN = re.compile(r"Page Reference Answers to RAVS.*?:\s*(\d+)")


def fetch_ravs_number(url: str) -> int:
    response = requests.get(url, headers=HEADERS, timeout=10)
    response.raise_for_status()
    match = PATTERN.search(response.text)
    if not match:
        raise ValueError("RAVS reference number not found on page")
    return int(match.group(1))


if __name__ == "__main__":
    print(fetch_ravs_number(URL))
