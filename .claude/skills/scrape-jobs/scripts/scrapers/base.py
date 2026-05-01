from dataclasses import dataclass, field
from datetime import datetime


REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,de;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
}


@dataclass
class Job:
    title: str
    company: str
    location: str
    url: str
    source: str
    role: str
    posted_date: str = ""
    description: str = ""
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_row(self) -> list:
        return [
            self.title,
            self.company,
            self.location,
            self.url,
            self.source,
            self.role,
            self.scraped_at,
            "",  # Applied — filled manually
        ]


def is_berlin_or_remote(text: str) -> bool:
    t = text.lower()
    return "berlin" in t or "remote" in t


def make_absolute(href: str, base: str) -> str:
    if not href:
        return ""
    if href.startswith("http"):
        return href
    if href.startswith("//"):
        return "https:" + href
    return base.rstrip("/") + "/" + href.lstrip("/")


def role_matches(title: str, role: str) -> bool:
    title_l = title.lower()
    role_l = role.lower()
    if role_l in title_l:
        return True
    significant = [w for w in role_l.split() if len(w) > 3]
    return any(w in title_l for w in significant)


def matched_role(title: str, roles: list[str]) -> str:
    for r in roles:
        if role_matches(title, r):
            return r
    return roles[0]
