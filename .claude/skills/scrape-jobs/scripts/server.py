#!/usr/bin/env python3
"""
Flask server for the job scraper UI.

Start:  python3 server.py
Open:   http://localhost:5100
"""
import os
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

# Pre-register the scrapers package so Python skips __init__.py entirely.
# This prevents Playwright-based scrapers (which can't run on Vercel) from
# being imported just because __init__.py lists them.
if "scrapers" not in sys.modules:
    _pkg = types.ModuleType("scrapers")
    _pkg.__path__ = [str(Path(__file__).parent / "scrapers")]
    _pkg.__package__ = "scrapers"
    sys.modules["scrapers"] = _pkg

from flask import Flask, jsonify, request

from scrapers import wearedevelopers
from scrapers.base import Job

app = Flask(__name__, static_folder=str(Path(__file__).parent / "static"), static_url_path="")

ALL_SCRAPERS = {
    "wearedevelopers.com": wearedevelopers.scrape,
}


@app.route("/")
def index():
    return app.send_static_file("index.html")


@app.route("/scrape", methods=["POST"])
def scrape():
    data = request.get_json(force=True)
    roles = [r.strip() for r in data.get("roles", []) if r.strip()]
    sources = data.get("sources", list(ALL_SCRAPERS.keys()))

    if not roles:
        return jsonify({"error": "No roles provided"}), 400

    scrapers = {k: v for k, v in ALL_SCRAPERS.items() if k in sources}

    all_jobs: list[Job] = []
    messages = []
    for source, scrape_fn in scrapers.items():
        messages.append(f"[{source}] scraping...")
        try:
            found = scrape_fn(roles)
            messages.append(f"  → {len(found)} jobs found")
            all_jobs.extend(found)
        except Exception as exc:
            messages.append(f"  → error: {exc}")

    seen: set[str] = set()
    unique: list[Job] = []
    for job in all_jobs:
        if job.url and job.url not in seen:
            seen.add(job.url)
            unique.append(job)

    messages.append(f"Done — {len(unique)} unique jobs collected.")

    return jsonify({
        "count": len(unique),
        "messages": messages,
        "jobs": [
            {
                "title": j.title,
                "company": j.company,
                "location": j.location,
                "url": j.url,
                "source": j.source,
                "role": j.role,
                "scraped_at": j.scraped_at,
            }
            for j in unique
        ],
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5100))
    print(f"\n  Job Scraper UI → http://localhost:{port}\n")
    app.run(port=port, debug=False)
