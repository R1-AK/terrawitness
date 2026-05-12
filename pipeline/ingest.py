"""
TerraWitness Ingestion Pipeline
================================
Monitors Indonesian environmental news, extracts incident data using Claude API,
and geocodes locations to produce structured incident records.

Usage:
  python ingest.py --demo          # Process 3 known real articles (no API key needed for fetch)
  python ingest.py --rss           # Monitor live RSS feeds + extract (needs GROQ_API_KEY)
  python ingest.py --url <URL>     # Process a single article URL
"""

import argparse
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from article_parser import fetch_article
from extractor import extract_incident
from geocoder import geocode

# Real, verified articles already confirmed to parse correctly
DEMO_URLS = [
    "https://mongabay.co.id/2021/05/04/tambang-antam-cemari-pesisir-halmahera-timur/",
    "https://www.betahita.id/news/detail/8869/kala-pertambangan-nikel-beroperasi-di-wawonii.html",
    "https://mongabay.co.id/2025/02/12/nasib-warga-kala-tambang-nikel-kuasai-pulau-kabaena/",
]


def generate_id() -> str:
    return f"TW-{datetime.now().strftime('%Y')}-{str(uuid.uuid4())[:6].upper()}"


def process_url(url: str) -> dict | None:
    print(f"\n{'─'*60}")
    print(f"  URL: {url}")

    print("  [1/3] Fetching article ...")
    article = fetch_article(url)
    if not article:
        print("  [FAIL] Failed to fetch article.")
        return None
    print(f"        Title : {article['title'][:80]}")
    print(f"        Date  : {article['date']}")
    print(f"        Words : {article['word_count']}")

    print("  [2/3] Extracting incident data (Claude API) ...")
    incident = extract_incident(article)
    if not incident:
        print("  [FAIL] Extraction failed.")
        return None
    print(f"        Violation : {incident.get('violation_type')}")
    print(f"        Severity  : {incident.get('severity')}")
    print(f"        Location  : {incident.get('location', {})}")
    print(f"        Company   : {incident.get('concession_holder')}")

    print("  [3/3] Geocoding location ...")
    location = geocode(incident.get("location", {}))
    incident["location"] = location
    confidence = location.get("geo_confidence", "unknown")
    print(f"        Coords    : {location.get('lat'):.4f}, {location.get('lng'):.4f}  [{confidence}]")

    incident["id"] = generate_id()
    return incident


def run_demo():
    print("\n[TerraWitness] Demo Ingestion Pipeline")
    print("   Processing 3 verified real articles\n")

    results = []
    for url in DEMO_URLS:
        incident = process_url(url)
        if incident:
            results.append(incident)

    return results


def run_rss():
    from rss_monitor import get_all_articles

    print("\n[TerraWitness] Live RSS Ingestion Pipeline")

    rss_articles = get_all_articles(max_per_feed=5)
    if not rss_articles:
        print("No matching articles found in feeds.")
        return []

    print(f"\nFound {len(rss_articles)} matching articles across all feeds.")

    results = []
    for article_meta in rss_articles:
        incident = process_url(article_meta["url"])
        if incident:
            results.append(incident)

    return results


def save_results(incidents: list[dict], output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(incidents, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] Saved {len(incidents)} incidents -> {output_path}")


def print_summary(incidents: list[dict]):
    print(f"\n{'═'*60}")
    print(f"  PIPELINE SUMMARY — {len(incidents)} incidents extracted")
    print(f"{'═'*60}")
    for inc in incidents:
        loc = inc.get("location", {})
        print(f"\n  {inc['id']}")
        print(f"  Type     : {inc.get('violation_type')}")
        print(f"  Severity : {inc.get('severity')}")
        print(f"  Location : {loc.get('kabupaten')}, {loc.get('provinsi')}")
        print(f"  Coords   : {loc.get('lat'):.4f}, {loc.get('lng'):.4f}  [{loc.get('geo_confidence')}]")
        print(f"  Company  : {inc.get('concession_holder')}")
        print(f"  Violation: {inc.get('violation_flag')}")
        print(f"  Change   : {inc.get('change_score')}")
        print(f"  Quote    : {inc.get('post_text', '')[:100]}...")


def main():
    parser = argparse.ArgumentParser(description="TerraWitness ingestion pipeline")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--demo", action="store_true", help="Process 3 known demo articles")
    group.add_argument("--rss",  action="store_true", help="Monitor live RSS feeds")
    group.add_argument("--url",  type=str,            help="Process a single article URL")
    parser.add_argument("--output", type=str, default="output/incidents.json",
                        help="Output JSON file path (default: output/incidents.json)")
    args = parser.parse_args()

    if not os.environ.get("GROQ_API_KEY"):
        print("Error: GROQ_API_KEY not set.")
        print("Get a free key at https://console.groq.com (no credit card needed)")
        print("Then add to pipeline/.env:  GROQ_API_KEY=gsk_...")
        sys.exit(1)

    if args.demo:
        incidents = run_demo()
    elif args.rss:
        incidents = run_rss()
    else:
        incident = process_url(args.url)
        incidents = [incident] if incident else []

    if incidents:
        print_summary(incidents)
        output_path = Path(args.output)
        save_results(incidents, output_path)
    else:
        print("\nNo incidents extracted.")


if __name__ == "__main__":
    main()
