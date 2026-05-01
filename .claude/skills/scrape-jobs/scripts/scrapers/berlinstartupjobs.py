"""
berlinstartupjobs.com scraper — requires Playwright (WordPress + JS navigation).

Confirmed selectors (tested 2026-04-30):
  Card:     li.bjs-jlid
  Title:    h4.bjs-jlid__h > a  (text + href)
  Company:  a.bjs-jlid__b
  Location: always Berlin, Germany (site is Berlin-only)
"""
import time
import random
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from bs4 import BeautifulSoup
from .base import Job, role_matches, matched_role

BASE_URL = "https://berlinstartupjobs.com"
CATEGORY_URLS = [
    f"{BASE_URL}/engineering/",
    f"{BASE_URL}/design-ux/",
    f"{BASE_URL}/product/",
    f"{BASE_URL}/operations/",
]
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def _parse_cards(soup, roles: list[str]) -> list[Job]:
    jobs: list[Job] = []
    for card in soup.find_all("li", class_="bjs-jlid"):
        title_a = card.select_one("h4.bjs-jlid__h a")
        if not title_a:
            continue
        title = title_a.get_text(strip=True)
        job_url = title_a.get("href", "")

        if not title or not job_url:
            continue
        if not any(role_matches(title, r) for r in roles):
            continue

        company_a = card.select_one("a.bjs-jlid__b")
        company = company_a.get_text(strip=True) if company_a else ""

        jobs.append(Job(
            title=title,
            company=company,
            location="Berlin, Germany",
            url=job_url,
            source="berlinstartupjobs.com",
            role=matched_role(title, roles),
        ))
    return jobs


def scrape(roles: list[str]) -> list[Job]:
    jobs: list[Job] = []
    seen: set[str] = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=UA)
        page = ctx.new_page()

        for cat_url in CATEGORY_URLS:
            try:
                page.goto(cat_url, wait_until="domcontentloaded", timeout=25000)
                page.wait_for_timeout(3000)
            except PWTimeout:
                print(f"    berlinstartupjobs [{cat_url}] timeout")
                continue

            soup = BeautifulSoup(page.content(), "lxml")
            for job in _parse_cards(soup, roles):
                if job.url and job.url not in seen:
                    seen.add(job.url)
                    jobs.append(job)

            time.sleep(random.uniform(1.0, 2.0))

        browser.close()

    return jobs
