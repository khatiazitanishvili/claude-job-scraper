import gspread
from google.oauth2.service_account import Credentials
from scrapers.base import Job

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_HEADERS = [
    "Title",
    "Company",
    "Location",
    "URL",
    "Source",
    "Role",
    "Scraped At",
    "Applied",
]


def save_jobs(jobs: list[Job], credentials_path: str, sheet_id: str) -> int:
    creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(sheet_id)

    try:
        ws = spreadsheet.worksheet("Jobs")
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet("Jobs", rows=5000, cols=len(SHEET_HEADERS))

    # Ensure header row is present
    if ws.row_values(1) != SHEET_HEADERS:
        ws.insert_row(SHEET_HEADERS, 1)

    # Deduplicate against existing rows by URL (column 4)
    existing_urls = set(ws.col_values(4)[1:])
    new_jobs = [j for j in jobs if j.url and j.url not in existing_urls]

    if new_jobs:
        rows = [j.to_row() for j in new_jobs]
        ws.append_rows(rows, value_input_option="USER_ENTERED")

    return len(new_jobs)
