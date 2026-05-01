"""
LinkedIn job scraper (Playwright).

Disabled by default — pass --linkedin flag to scrape_jobs.py to enable.

For authenticated access (more results, less blocking), set LI_AT_COOKIE in
a .env file inside scripts/. Without it, LinkedIn limits public results to ~25.
"""
import os
import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from .base import Job, is_berlin_or_remote, role_matches, matched_role

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

SEARCH_URL = "https://www.linkedin.com/jobs/search/"


def scrape(roles: list[str]) -> list[Job]:
    li_at = os.getenv("LI_AT_COOKIE", "")
    jobs: list[Job] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )

        if li_at:
            context.add_cookies(
                [
                    {
                        "name": "li_at",
                        "value": li_at,
                        "domain": ".linkedin.com",
                        "path": "/",
                    }
                ]
            )

        page = context.new_page()
        seen: set[str] = set()

        for role in roles:
            # f_WT=2,3 filters for Remote + Hybrid; f_TPR=r86400 = last 24h
            params = (
                f"?keywords={role.replace(' ', '+')}"
                "&location=Berlin%2C+Germany"
                "&f_WT=2%2C3"
            )
            url = SEARCH_URL + params

            try:
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
            except PlaywrightTimeout:
                print(f"    linkedin: timeout for role '{role}'")
                continue

            # Scroll to load lazy job cards
            for _ in range(4):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(1500)

            cards = page.query_selector_all(
                ".job-search-card, .jobs-search__results-list li, "
                "[class*='job-card-container'], [data-entity-urn]"
            )

            for card in cards:
                try:
                    title_el = card.query_selector(
                        "h3, .job-card-list__title, .base-search-card__title"
                    )
                    title = title_el.inner_text().strip() if title_el else ""

                    link_el = card.query_selector("a[href*='/jobs/view/']")
                    job_url = (
                        link_el.get_attribute("href", timeout=1000).split("?")[0]
                        if link_el
                        else ""
                    )

                    if not title or not job_url or job_url in seen:
                        continue
                    seen.add(job_url)

                    if not any(role_matches(title, r) for r in roles):
                        continue

                    company_el = card.query_selector(
                        ".job-card-container__company-name, h4, .base-search-card__subtitle"
                    )
                    company = company_el.inner_text().strip() if company_el else ""

                    loc_el = card.query_selector(
                        ".job-card-container__metadata-item, .job-search-card__location"
                    )
                    location_text = loc_el.inner_text().strip() if loc_el else ""

                    if location_text and not is_berlin_or_remote(location_text):
                        continue

                    time_el = card.query_selector("time")
                    posted = (
                        time_el.get_attribute("datetime") or time_el.inner_text().strip()
                        if time_el
                        else ""
                    )

                    jobs.append(
                        Job(
                            title=title,
                            company=company,
                            location=location_text or "Berlin, Germany",
                            url=job_url,
                            source="linkedin.com",
                            role=matched_role(title, roles),
                            posted_date=posted,
                        )
                    )
                except Exception:
                    continue

            time.sleep(2)

        browser.close()

    return jobs
