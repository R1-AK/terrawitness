"""
Fetch and normalize one public X post by URL or ID.

This is meant for known, past posts. It uses X API v2 Post Lookup, not recent
search, so the post can be older than 7 days as long as it is still available
to your API access level.

Usage:
  set X_BEARER_TOKEN=...
  python x_post_lookup.py --url https://x.com/example/status/1234567890
"""

import argparse
import json
import os
import re
from datetime import datetime

import requests


def extract_post_id(value: str) -> str:
    match = re.search(r"/status/(\d+)", value)
    if match:
        return match.group(1)
    if re.fullmatch(r"\d{1,19}", value):
        return value
    raise ValueError("Expected an X post URL containing /status/<id> or a numeric post ID.")


def fetch_post(post_id: str) -> dict:
    token = os.environ.get("X_BEARER_TOKEN")
    if not token:
        raise EnvironmentError("X_BEARER_TOKEN is not set.")

    response = requests.get(
        f"https://api.x.com/2/tweets/{post_id}",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "tweet.fields": "created_at,lang,entities,geo",
            "expansions": "geo.place_id",
            "place.fields": "full_name,country,country_code,geo,name,place_type",
        },
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def normalize_post(raw: dict, source_url: str) -> dict:
    post = raw["data"]
    created_at = post.get("created_at") or datetime.utcnow().isoformat()

    return {
        "source_type": "public_social_post",
        "platform": "x",
        "source_url": source_url,
        "source_date": created_at[:10],
        "post_date": created_at,
        "text": post.get("text", ""),
        "author_stored": False,
        "geo": post.get("geo"),
        "places": raw.get("includes", {}).get("places", []),
    }


def main():
    parser = argparse.ArgumentParser(description="Fetch one public X post for TerraWitness.")
    parser.add_argument("--url", "--post-url", dest="post_url", required=True)
    args = parser.parse_args()

    post_id = extract_post_id(args.post_url)
    raw = fetch_post(post_id)
    normalized = normalize_post(raw, args.post_url)
    print(json.dumps(normalized, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
