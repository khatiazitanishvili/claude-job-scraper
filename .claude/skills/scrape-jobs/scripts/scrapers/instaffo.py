from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from .base import Job, is_berlin_or_remote, role_matches, matched_role

BASE_URL = "https://instaffo.com"
JOBS_URL = "https://instaffo.com/jobs"


def scrape(roles: list[str]) -> list[Job]:
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
        page = context.new_page()
        seen: set[str] = set()

        for role in roles:
            try:
                page.goto(JOBS_URL, timeout=30000, wait_until="networkidle")
            except PlaywrightTimeout:
                print(f"    instaffo: timeout loading {JOBS_URL}")
                continue

            # Try to find and use a search box
            try:
                search = page.locator(
                    "input[type='search'], input[placeholder*='search' i], "
                    "input[placeholder*='suche' i], input[placeholder*='role' i], "
                    "input[placeholder*='job' i]"
                ).first
                search.fill(role)
                search.press("Enter")
                page.wait_for_timeout(2000)
            except Exception:
                pass

            # Scroll to trigger lazy-loaded content
            for _ in range(6):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(1200)

            cards = page.query_selector_all(
                "article, [class*='job-card'], [class*='JobCard'], "
                "[class*='position'], [class*='listing']"
            )

            for card in cards:
                try:
                    title_el = card.query_selector("h2, h3, h4, [class*='title']")
                    title = title_el.inner_text().strip() if title_el else ""

                    link_el = card.query_selector("a[href]")
                    href = link_el.get_attribute("href") if link_el else ""
                    job_url = (
                        BASE_URL + href
                        if href and not href.startswith("http")
                        else href
                    )

                    if not title or not job_url or job_url in seen:
                        continue
                    seen.add(job_url)

                    if not any(role_matches(title, r) for r in roles):
                        continue

                    company_el = card.query_selector(
                        "[class*='company'], [class*='employer'], [class*='Company']"
                    )
                    company = company_el.inner_text().strip() if company_el else ""

                    loc_el = card.query_selector(
                        "[class*='location'], [class*='city'], [class*='Location']"
                    )
                    location_text = loc_el.inner_text().strip() if loc_el else ""

                    if location_text and not is_berlin_or_remote(location_text):
                        continue

                    jobs.append(
                        Job(
                            title=title,
                            company=company,
                            location=location_text or "Berlin / Remote",
                            url=job_url,
                            source="instaffo.com",
                            role=matched_role(title, roles),
                        )
                    )
                except Exception:
                    continue

        browser.close()

    return jobs
