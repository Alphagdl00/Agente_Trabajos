from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.http_utils import create_session, safe_request


JOB_PATH_PATTERN = re.compile(r"/jobs/\d+/.+/(job|apply)", re.IGNORECASE)


def clean_text(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split()).strip()


def looks_like_icims_job_url(url: str) -> bool:
    normalized = clean_text(url)
    return bool(normalized and JOB_PATH_PATTERN.search(normalized))


def extract_location(anchor) -> str:
    container = anchor.find_parent(["div", "li", "article", "tr"])
    if container is None:
        return ""

    text = clean_text(container.get_text(" ", strip=True))
    location_markers = [
        "location",
        "locations",
        "ubicacion",
        "remote",
        "hybrid",
        "onsite",
    ]

    lowered = text.lower()
    if any(marker in lowered for marker in location_markers):
        return text[:180]

    return ""


def collect_from_page(company_name: str, page_url: str) -> list[dict]:
    session = create_session()
    response = safe_request(session, "GET", page_url)
    if response is None:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    jobs: list[dict] = []
    seen: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = urljoin(page_url, clean_text(anchor.get("href")))
        if href in seen or not looks_like_icims_job_url(href):
            continue

        title = clean_text(anchor.get_text(" ", strip=True))
        if not title:
            title = clean_text(anchor.get("title", "")) or "Unknown title"

        jobs.append(
            {
                "company": company_name,
                "title": title,
                "location": extract_location(anchor),
                "url": href,
                "department": "",
                "workplace_type": "",
                "description_snippet": "",
                "ats": "icims",
            }
        )
        seen.add(href)

    return jobs


def build_candidate_pages(career_url: str) -> list[str]:
    normalized = career_url.rstrip("/")
    candidates = [
        normalized,
        f"{normalized}/jobs/search?ss=1",
        f"{normalized}/jobs/search",
    ]

    deduped: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate not in seen:
            deduped.append(candidate)
            seen.add(candidate)
    return deduped


def scrape_icims(company_name: str, career_url: str) -> list[dict]:
    all_jobs: list[dict] = []
    seen_urls: set[str] = set()

    for page_url in build_candidate_pages(career_url):
        page_jobs = collect_from_page(company_name, page_url)
        for job in page_jobs:
            job_url = clean_text(job.get("url", ""))
            if job_url and job_url not in seen_urls:
                all_jobs.append(job)
                seen_urls.add(job_url)

        if all_jobs:
            break

    if not all_jobs:
        print(f"iCIMS OK {company_name}: 0 jobs")

    return all_jobs
