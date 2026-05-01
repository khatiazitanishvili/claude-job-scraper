# claude-job-scraper

A Claude Code skill that scrapes German tech job boards for user-specified roles, filters for Berlin or Remote (Germany) positions, and appends new results to a Google Sheet — all triggered via a `/scrape-jobs` slash command.

## What it does

Say something like `"Scrape jobs for Data Engineer"` in Claude Code and it will:

1. Search across 7 job boards simultaneously
2. Filter listings to Berlin or Remote (Germany)
3. Deduplicate against rows already in your sheet
4. Append new jobs to a Google Sheet with title, company, location, URL, posted date, and source

## Job boards

| Source | Method |
|---|---|
| germantechjobs.de | requests + BeautifulSoup |
| berlinstartupjobs.com | requests + BeautifulSoup |
| it-jobs.de | requests + BeautifulSoup |
| it-entwickler-jobs.de | requests + BeautifulSoup |
| instaffo.com | Playwright (headless Chromium) |
| wearedevelopers.com | requests + BeautifulSoup |
| linkedin.com | Playwright — opt-in via `--linkedin` flag |

## Setup

### 1. Install dependencies

```bash
cd .claude/skills/scrape-jobs/scripts
pip install -r requirements.txt
playwright install chromium
```

### 2. Google Sheets credentials

1. Create a [Google Cloud service account](https://console.cloud.google.com/iam-admin/serviceaccounts) and download the JSON key
2. Share your target spreadsheet with the service account's `client_email` (Editor access)
3. Copy the spreadsheet ID from its URL

### 3. Configure environment variables

Create `.claude/skills/scrape-jobs/scripts/.env`:

```
GOOGLE_CREDENTIALS_PATH=/path/to/your/credentials.json
GOOGLE_SHEET_ID=your_spreadsheet_id

# Optional — only needed for LinkedIn scraping
# To get it: log into LinkedIn in Chrome → DevTools → Application → Cookies → copy li_at value
LI_AT_COOKIE=
```

## Usage

### Via Claude Code (recommended)

Just ask Claude:

> "Scrape jobs for Software Engineer"
> "Find new Data Engineer positions"
> "Run the job scraper for Backend Developer and ML Engineer"

### Via CLI

```bash
cd .claude/skills/scrape-jobs/scripts

python scrape_jobs.py \
  --roles "Software Engineer" "Backend Developer" \
  --credentials /path/to/credentials.json \
  --sheet-id YOUR_SHEET_ID
```

With LinkedIn enabled:

```bash
python scrape_jobs.py --roles "Data Engineer" --credentials creds.json --sheet-id ID --linkedin
```

Run only specific sources:

```bash
python scrape_jobs.py --roles "ML Engineer" --credentials creds.json --sheet-id ID \
  --sources germantechjobs.de wearedevelopers.com
```

## Output

Results are appended to a sheet named **Jobs** with these columns:

`Title | Company | Location | URL | Posted Date | Description | Source | Role | Scraped At`

Existing rows (matched by URL) are never duplicated.

## Troubleshooting

**0 results from a source** — the site's HTML may have changed. Open the relevant file in `scripts/scrapers/` and update the CSS selectors.

**Google Sheets auth error** — ensure the service account email has Editor access to the spreadsheet.

**Playwright timeout on instaffo** — run `playwright install chromium`. If it still times out, set `headless=False` in `scripts/scrapers/instaffo.py` to debug visually.

**LinkedIn returns 0 results** — add a valid `LI_AT_COOKIE` to your `.env` file for authenticated access.
