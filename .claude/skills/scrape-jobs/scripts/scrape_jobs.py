#!/usr/bin/env python3
"""
Scrape German tech job boards for specified roles and save results to Google Sheets.

Usage:
    python scrape_jobs.py \
        --roles "Software Engineer" "Backend Developer" \
        --credentials credentials.json \
        --sheet-id SPREADSHEET_ID \
        [--linkedin] \
        [--sources germantechjobs.de wearedevelopers.com]
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

from scrapers import (
    germantechjobs,
    berlinstartupjobs,
    itjobs,
    itentwicklerjobs,
    instaffo,
    wearedevelopers,
    linkedin as linkedin_scraper,
)
from scrapers.base import Job
from sheets import save_jobs

ALL_SCRAPERS: dict = {
    "germantechjobs.de":     germantechjobs.scrape,
    "berlinstartupjobs.com": berlinstartupjobs.scrape,
    "it-jobs.de":            itjobs.scrape,
    "it-entwickler-jobs.de": itentwicklerjobs.scrape,
    "instaffo.com":          instaffo.scrape,
    "wearedevelopers.com":   wearedevelopers.scrape,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape German tech job boards")
    parser.add_argument(
        "--roles", nargs="+", required=True, metavar="ROLE",
        help='Job roles to search, e.g. "Software Engineer"',
    )
    parser.add_argument(
        "--credentials", metavar="PATH",
        default=os.getenv("GOOGLE_CREDENTIALS_PATH"),
        help="Path to Google service account JSON (or set GOOGLE_CREDENTIALS_PATH in .env)",
    )
    parser.add_argument(
        "--sheet-id", metavar="ID",
        default=os.getenv("GOOGLE_SHEET_ID"),
        help="Google Spreadsheet ID (or set GOOGLE_SHEET_ID in .env)",
    )
    parser.add_argument(
        "--linkedin", action="store_true",
        help="Enable LinkedIn scraping (requires LI_AT_COOKIE in .env for best results)",
    )
    parser.add_argument(
        "--sources", nargs="*", metavar="SOURCE",
        help="Only run these sources (default: all). E.g.: germantechjobs.de wearedevelopers.com",
    )
    args = parser.parse_args()

    env_file = Path(__file__).parent / ".env"
    missing = []
    if not args.credentials:
        missing.append("GOOGLE_CREDENTIALS_PATH=/path/to/credentials.json")
    if not args.sheet_id:
        missing.append("GOOGLE_SHEET_ID=your_spreadsheet_id")

    if missing:
        print("Setup required — add the following to scripts/.env:\n", file=sys.stderr)
        for line in missing:
            print(f"  {line}", file=sys.stderr)
        print(f"\nFile location: {env_file}", file=sys.stderr)
        print("\nHow to get these values:", file=sys.stderr)
        print("  GOOGLE_CREDENTIALS_PATH → download a service account JSON from Google Cloud Console", file=sys.stderr)
        print("  GOOGLE_SHEET_ID         → the long ID in your Google Sheet URL", file=sys.stderr)
        print("                            https://docs.google.com/spreadsheets/d/<THIS_PART>/edit", file=sys.stderr)
        sys.exit(1)

    if not Path(args.credentials).exists():
        print(f"Error: credentials file not found: {args.credentials}", file=sys.stderr)
        print("Check GOOGLE_CREDENTIALS_PATH in your .env file.", file=sys.stderr)
        sys.exit(1)

    scrapers = dict(ALL_SCRAPERS)
    if args.linkedin:
        scrapers["linkedin.com"] = linkedin_scraper.scrape
    if args.sources:
        unknown = set(args.sources) - set(scrapers)
        if unknown:
            print(f"Warning: unknown sources ignored: {', '.join(unknown)}", file=sys.stderr)
        scrapers = {k: v for k, v in scrapers.items() if k in args.sources}

    print(f"Roles:   {', '.join(args.roles)}")
    print(f"Sources: {', '.join(scrapers)}\n")

    all_jobs: list[Job] = []
    for source, scrape_fn in scrapers.items():
        print(f"[{source}] scraping...")
        try:
            found = scrape_fn(args.roles)
            print(f"  → {len(found)} jobs found")
            all_jobs.extend(found)
        except Exception as exc:
            print(f"  → error: {exc}")

    # Deduplicate by URL across all sources
    seen_urls: set[str] = set()
    unique: list[Job] = []
    for job in all_jobs:
        if job.url and job.url not in seen_urls:
            seen_urls.add(job.url)
            unique.append(job)

    print(f"\nTotal unique jobs collected: {len(unique)}")

    if not unique:
        print("Nothing to save.")
        return

    print("Saving to Google Sheet...")
    added = save_jobs(unique, args.credentials, args.sheet_id)
    print(f"Done. {added} new job(s) added to sheet (duplicates skipped).")


if __name__ == "__main__":
    main()
