# src/ats_generic.py

from __future__ import annotations

import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}


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


def scrape_generic(company_name: str, career_url: str, timeout: int = 20) -> list[dict]:
    jobs = []

    if not career_url:
        return jobs

    try:
        response = requests.get(career_url, headers=HEADERS, timeout=timeout)
        response.raise_for_status()
    except Exception as exc:
        print(f"[GENERIC] Error fetching {company_name} - {career_url}: {exc}")
        return jobs

    soup = BeautifulSoup(response.text, "html.parser")
    anchors = soup.find_all("a", href=True)

    seen = set()

    for a in anchors:
        title = clean_text(a.get_text(" ", strip=True))
        href = clean_text(a.get("href"))
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
            }
        )

    return jobs