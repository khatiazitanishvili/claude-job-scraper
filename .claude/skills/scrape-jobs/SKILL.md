---
name: scrape-jobs
description: Scrape and filter job listings for user-specified roles from German tech job boards, and save to a Google Sheet.
---

# Goal

Scrapes job listings for user-specified roles from German tech job boards, filters for Berlin or Remote (Germany), and appends new results to a Google Sheet.

## Inputs

Invoke this skill when the user says anything like:
- "Scrape jobs for [role]"
- "Find new [role] jobs"
- "Run the job scraper"
- "Search for [role] positions"



## Scripts
All scripts are located in `.claude/skills/scrape-jobs/scripts/`.:
- `scrape_jobs.py`: Main entry point; parses arguments, orchestrates scraping and Google Sheets updates.
- `scrapers/`: Contains individual scraper modules for each job board (e.g. `germantechjobs.py`, `berlinstartupjobs.py`, etc.). Each module has a `scrape_jobs(roles)` function that returns a list of job dicts.
- `google_sheets.py`: Contains functions for authenticating and appending data to Google Sheets using the Sheets API.
- `utils.py`: Helper functions for date parsing, deduplication, and logging.
- `.env`: Optional file to store environment variables like `LI_AT_COOKIE` for LinkedIn scraping.

## Process

**Run Full Pipeline**
```bash
python3 scrape_jobs.py --roles "Software Engineer" "Backend Developer" --credentials /path/to/credentials.json --sheet-id YOUR_SHEET_ID
```
This will run all scrapers, filter results for the specified roles, and append new jobs to the Google Sheet.

| Argument | Description | Example |
|---|---|---|
| `--roles` | One or more job roles | `"Software Engineer" "Backend Developer"` |
| `--credentials` | Path to service account JSON | `~/credentials.json` |
| `--sheet-id` | Google Spreadsheet ID | `1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms` |
| `--linkedin` | Enable LinkedIn (optional flag) | _(no value needed)_ |
| `--sources` | Only run specific sources (optional) | `germantechjobs.de wearedevelopers.com` |

## How to Run

Ask the user for:
1. Role(s) to search
2. Path to their Google service account credentials JSON
3. Google Sheet ID

Then run:
```bash
cd .claude/skills/scrape-jobs/scripts
python scrape_jobs.py \
  --roles "Software Engineer" "Backend Developer" \
  --credentials /path/to/credentials.json \
  --sheet-id YOUR_SHEET_ID
```

To also scrape LinkedIn (requires `LI_AT_COOKIE` in a `.env` file):
```bash
python scrape_jobs.py --roles "Software Engineer" --credentials creds.json --sheet-id ID --linkedin
```

## Output Sheet

**The ONLY deliverable is the Google Sheet URL.** Local JSON files in `.tmp/` are temporary intermediates.

Sheet name: **Jobs**

Columns: `Title | Company | Location | URL | Posted Date | Description | Source | Role | Scraped At`

New jobs are appended only. Existing rows (matched by URL) are never duplicated.

## Edge Cases
- **No results for a role**: Ask the user if they want to try a different role or check the spelling.
- **API Error**: Check the credentials in the `.env` file.
- **LinkedIn blocked**: If LinkedIn scraping returns 0 results, suggest adding a valid `LI_AT_COOKIE` to the `.env` file for authenticated access. 
- **Google Sheets API errors**: Log the error details and suggest checking API quotas

## Environment Variables
Requuires in `.env`:
```
LI_AT_COOKIE=your_linkedin_cookie_value

```

## Sources Scraped

| Source | Method | Notes |
|---|---|---|
| germantechjobs.de | requests + BS4 | Fetches Berlin + Remote pages, filters by role keyword in title |
| berlinstartupjobs.com | requests + BS4 | WordPress keyword search |
| it-jobs.de | requests + BS4 | Keyword + Berlin location filter |
| it-entwickler-jobs.de | requests + BS4 | Keyword + Berlin location filter |
| instaffo.com | Playwright | JS-rendered React app; uses headless Chromium |
| wearedevelopers.com | requests + BS4 | Keyword + location search |
| linkedin.com | Playwright | Disabled by default; `--linkedin` flag to enable |

## Troubleshooting

**0 results from a source**
The site's HTML may have changed. Open the relevant file in `scripts/scrapers/`, inspect the live site with chrome-devtools-mcp, and update the CSS selectors.

**Google Sheets auth error**
Ensure the service account email (found in the credentials JSON as `client_email`) has **Editor** access to the spreadsheet.

**Playwright timeout on instaffo**
Run `playwright install chromium` to ensure the browser binary is present. If it still times out, open `scripts/scrapers/instaffo.py` and set `headless=False` to debug visually.

**LinkedIn blocked / 0 results**
LinkedIn throttles unauthenticated access. Add `LI_AT_COOKIE=<your_cookie_value>` to a `.env` file in `scripts/` for a logged-in session.
