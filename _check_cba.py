"""Temporary script to check what data CBA decision pages contain."""

import re

import requests

HEADERS = {"User-Agent": "Mozilla/5.0"}

# Check several different decisions
urls = [
    "https://www.cba.am/en/chairman-decisions/8828/",  # Ameriabank supplement
    "https://www.cba.am/en/chairman-decisions/8810/",  # AMIO Bank new
    "https://www.cba.am/en/chairman-decisions/8733/",  # Fast Bank new
]

for url in urls:
    print(f"\n{'='*60}")
    print(f"Fetching: {url}")
    resp = requests.get(url, headers=HEADERS, timeout=20)

    # Get the full text content
    body = re.sub(r"<[^>]+>", " ", resp.text)
    body = re.sub(r"\s+", " ", body)

    # Find the decision content - look for the actual decision text
    for keyword in ["REPUBLIC OF ARMENIA", "Republic of Armenia"]:
        idx = body.find(keyword, body.find("Chairman") if "Chairman" in body else 0)
        if idx >= 0:
            text = body[idx : idx + 3000]
            print(text)
            print()
            break
