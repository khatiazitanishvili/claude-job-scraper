"""
germantechjobs.de scraper — requires Playwright (JS-rendered site).

Confirmed selectors (tested 2026-04-30):
  Card:     div[data-test="card"]
  Title:    div.jobteaser-name-header
  URL:      a containing div.jobteaser-name-header  (href starts with /jobs/)
  Company:  span.mr-3 (first one inside the card body)
  Location: second div.d-inline-flex.align-items-center
"""
import time
import random
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from bs4 import BeautifulSoup
from .base import Job, make_absolute, role_matches, matched_role

BASE_URL = "https://germantechjobs.de"
LOCATION_SLUGS = ("Berlin", "remote")
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def _parse_cards(soup, location_slug: str, roles: list[str]) -> list[Job]:
    jobs: list[Job] = []
    cards = soup.find_all("div", attrs={"data-test": "card"})
    for card in cards:
        title_div = card.find("div", class_="jobteaser-name-header")
        if not title_div:
            continue
        title = title_div.get_text(strip=True)

        if not any(role_matches(title, r) for r in roles):
            continue

        title_a = title_div.find_parent("a")
        if not title_a:
            title_a = card.find("a", href=lambda h: h and h.startswith("/jobs/") and "/jobs/all" not in h)
        if not title_a:
            continue
        job_url = make_absolute(title_a.get("href", ""), BASE_URL)

        company_span = card.find("span", class_="mr-3")
        company = company_span.get_text(strip=True) if company_span else ""

        loc_divs = card.find_all("div", class_=lambda c: c and "d-inline-flex" in c and "align-items-center" in c)
        location_text = loc_divs[1].get_text(strip=True) if len(loc_divs) > 1 else (
            "Remote, Germany" if location_slug == "remote" else "Berlin, Germany"
        )

        time_tag = card.find("time")
        posted = time_tag.get("datetime", time_tag.get_text(strip=True)) if time_tag else ""

        jobs.append(Job(
            title=title,
            company=company,
            location=location_text,
            url=job_url,
            source="germantechjobs.de",
            role=matched_role(title, roles),
            posted_date=posted,
        ))
    return jobs


def scrape(roles: list[str]) -> list[Job]:
    jobs: list[Job] = []
    seen: set[str] = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=UA)
        page = ctx.new_page()

        for loc_slug in LOCATION_SLUGS:
            pg = 1
            while pg <= 10:
                url = f"{BASE_URL}/jobs/all/{loc_slug}"
                if pg > 1:
                    url += f"?page={pg}"

                try:
                    page.goto(url, wait_until="networkidle", timeout=30000)
                    page.wait_for_timeout(1500)
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(1500)
                except PWTimeout:
                    print(f"    germantechjobs [{loc_slug} p{pg}] timeout")
                    break

                soup = BeautifulSoup(page.content(), "lxml")
                page_jobs = _parse_cards(soup, loc_slug, roles)

                new_this_page = 0
                for job in page_jobs:
                    if job.url and job.url not in seen:
                        seen.add(job.url)
                        jobs.append(job)
                        new_this_page += 1

                if new_this_page == 0:
                    break

                next_link = soup.find("a", href=lambda h: h and f"page={pg + 1}" in h)
                if not next_link:
                    break

                pg += 1
                time.sleep(random.uniform(1.5, 2.5))

        browser.close()

    return jobs
