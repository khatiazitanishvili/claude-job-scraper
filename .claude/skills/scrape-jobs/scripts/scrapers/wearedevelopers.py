"""
wearedevelopers.com scraper — server-side rendered, requests + BS4 works.

Confirmed selectors (tested 2026-04-30):
  Card:     article.wad4-job-card
  Title:    h3.wad4-job-card__title
  URL:      a.wad4-job-card__link  (href)
  Location: div.wad4-job-card__info--light
"""
import time
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode
from .base import Job, REQUEST_HEADERS, make_absolute, role_matches, matched_role

BASE_URL = "https://www.wearedevelopers.com"


def scrape(roles: list[str]) -> list[Job]:
    jobs: list[Job] = []
    seen: set[str] = set()

    for role in roles:
        for location in ("Berlin", "Remote"):
            page = 1
            while page <= 5:
                params: dict = {"q": role, "location": location}
                if page > 1:
                    params["page"] = page
                url = f"{BASE_URL}/jobs?" + urlencode(params)

                try:
                    resp = requests.get(url, headers=REQUEST_HEADERS, timeout=15)
                    resp.raise_for_status()
                except Exception as e:
                    print(f"    wearedevelopers [{role}/{location} p{page}] error: {e}")
                    break

                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.select("article.wad4-job-card")

                if not cards:
                    break

                new_on_page = 0
                for card in cards:
                    link = card.select_one("a.wad4-job-card__link")
                    if not link:
                        continue
                    job_url = make_absolute(link.get("href", ""), BASE_URL)
                    if not job_url or job_url in seen:
                        continue

                    title_el = card.select_one("h3.wad4-job-card__title")
                    title = title_el.get_text(strip=True) if title_el else ""
                    if not title:
                        continue

                    if not any(role_matches(title, r) for r in roles):
                        continue

                    seen.add(job_url)
                    new_on_page += 1

                    loc_el = card.select_one("div.wad4-job-card__info--light")
                    location_text = loc_el.get_text(strip=True) if loc_el else location

                    time_tag = card.find("time")
                    posted = (
                        time_tag.get("datetime", time_tag.get_text(strip=True))
                        if time_tag else ""
                    )

                    jobs.append(Job(
                        title=title,
                        company="",
                        location=location_text,
                        url=job_url,
                        source="wearedevelopers.com",
                        role=matched_role(title, roles),
                        posted_date=posted,
                    ))

                if new_on_page == 0:
                    break

                next_btn = soup.find("a", rel="next")
                if not next_btn:
                    break

                page += 1
                time.sleep(random.uniform(1.0, 2.0))

    return jobs
