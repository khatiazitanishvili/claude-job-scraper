import time
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode
from .base import Job, REQUEST_HEADERS, make_absolute, is_berlin_or_remote, role_matches, matched_role

BASE_URL = "https://www.it-jobs.de"


def scrape(roles: list[str]) -> list[Job]:
    jobs: list[Job] = []
    seen: set[str] = set()

    for role in roles:
        page = 1
        while page <= 5:
            params = {"was": role, "wo": "Berlin", "pg": page}
            url = f"{BASE_URL}/jobs/suche/?" + urlencode(params)

            try:
                resp = requests.get(url, headers=REQUEST_HEADERS, timeout=15)
                resp.raise_for_status()
            except Exception as e:
                print(f"    it-jobs [{role} p{page}] error: {e}")
                break

            soup = BeautifulSoup(resp.text, "lxml")

            cards = (
                soup.select(".stellenanzeige")
                or soup.select(".job-item")
                or soup.select(".job_item")
                or soup.select("article.job")
                or soup.select(".result-item")
                or soup.select(".stelle")
            )

            if not cards:
                break

            new_on_page = 0
            for card in cards:
                heading = card.find("h2") or card.find("h3") or card.select_one(".job-title, .title")
                if not heading:
                    continue
                title_a = heading.find("a") or card.find("a", href=True)
                if not title_a:
                    continue

                title = heading.get_text(strip=True)
                job_url = make_absolute(title_a.get("href", ""), BASE_URL)

                if not title or not job_url or job_url in seen:
                    continue
                seen.add(job_url)
                new_on_page += 1

                company_el = (
                    card.select_one(".company")
                    or card.select_one(".arbeitgeber")
                    or card.select_one(".employer")
                )
                company = company_el.get_text(strip=True) if company_el else ""

                loc_el = (
                    card.select_one(".location")
                    or card.select_one(".ort")
                    or card.select_one(".standort")
                )
                location_text = loc_el.get_text(strip=True) if loc_el else "Berlin, Germany"

                if location_text and not is_berlin_or_remote(location_text):
                    continue

                date_el = card.select_one("time") or card.select_one(".date, .datum")
                posted = (
                    date_el.get("datetime", date_el.get_text(strip=True))
                    if date_el
                    else ""
                )

                jobs.append(
                    Job(
                        title=title,
                        company=company,
                        location=location_text,
                        url=job_url,
                        source="it-jobs.de",
                        role=matched_role(title, roles),
                        posted_date=posted,
                    )
                )

            if new_on_page == 0:
                break

            next_btn = soup.find("a", rel="next") or soup.find(
                "a", string=lambda t: t and "weiter" in t.lower()
            )
            if not next_btn:
                break

            page += 1
            time.sleep(random.uniform(1.5, 3.0))

    return jobs
