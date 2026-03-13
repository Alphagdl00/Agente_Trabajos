from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.http_utils import create_session, safe_request


TALEO_JOB_PATTERNS = [
    re.compile(r"/careersection/.+/jobdetail\.ftl", re.IGNORECASE),
    re.compile(r"/careersection/.+/jobsearch\.ftl", re.IGNORECASE),
    re.compile(r"jobdetail\.ftl", re.IGNORECASE),
]


def clean_text(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split()).strip()


def looks_like_taleo_job_link(url: str) -> bool:
    normalized = clean_text(url)
    return any(pattern.search(normalized) for pattern in TALEO_JOB_PATTERNS)


def extract_location(anchor) -> str:
    container = anchor.find_parent(["tr", "li", "div", "article"])
    if container is None:
        return ""
    text = clean_text(container.get_text(" ", strip=True))
    return text[:180]


def scrape_taleo(company_name: str, career_url: str) -> list[dict]:
    session = create_session()
    response = safe_request(session, "GET", career_url)
    if response is None:
        print(f"Taleo error {career_url}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    jobs: list[dict] = []
    seen: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = urljoin(career_url, clean_text(anchor.get("href")))
        if href in seen or not looks_like_taleo_job_link(href):
            continue

        title = clean_text(anchor.get_text(" ", strip=True)) or clean_text(anchor.get("title", "")) or "Unknown title"
        jobs.append(
            {
                "company": company_name,
                "title": title,
                "location": extract_location(anchor),
                "url": href,
                "department": "",
                "workplace_type": "",
                "description_snippet": "",
                "ats": "taleo",
            }
        )
        seen.add(href)

    return jobs
