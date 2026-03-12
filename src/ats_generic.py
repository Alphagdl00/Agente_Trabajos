# src/ats_generic.py

from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.http_utils import create_session, safe_request


JOB_KEYWORDS = [
    "job",
    "career",
    "opening",
    "vacancy",
    "position",
    "opportunity",
    "empleo",
    "vacante",
    "careers",
    "join-us",
]


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def looks_like_job_link(text: str, href: str) -> bool:
    blob = f"{text} {href}".lower()
    return any(keyword in blob for keyword in JOB_KEYWORDS)


def scrape_generic(company_name: str, career_url: str) -> list[dict]:
    jobs: list[dict] = []

    if not career_url:
        return jobs

    session = create_session()
    response = safe_request(session, "GET", career_url)
    if response is None:
        print(f"[GENERIC] Error fetching {company_name} - {career_url}")
        return jobs

    soup = BeautifulSoup(response.text, "html.parser")
    anchors = soup.find_all("a", href=True)

    seen = set()

    for anchor in anchors:
        title = clean_text(anchor.get_text(" ", strip=True))
        href = clean_text(anchor.get("href"))
        absolute_url = urljoin(career_url, href)

        if not absolute_url or absolute_url in seen:
            continue

        if not looks_like_job_link(title, absolute_url):
            continue

        seen.add(absolute_url)

        jobs.append(
            {
                "company": company_name,
                "title": title or "Unknown title",
                "location": "",
                "url": absolute_url,
                "ats": "generic",
                "source_url": career_url,
                "description_snippet": "",
                "department": "",
                "workplace_type": "",
            }
        )

    return jobs