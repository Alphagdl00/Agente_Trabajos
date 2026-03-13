# src/ats_successfactors.py

from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.http_utils import create_session, safe_request


def scrape_successfactors(company_name: str, career_url: str) -> list[dict]:
    session = create_session()
    response = safe_request(session, "GET", career_url)

    if response is None:
        print(f"SuccessFactors error {career_url}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    jobs: list[dict] = []
    seen: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = urljoin(career_url, str(anchor.get("href", "")).strip())
        title = " ".join(anchor.get_text(" ", strip=True).split()).strip()

        if not href or href in seen:
            continue

        href_lower = href.lower()
        title_lower = title.lower()
        if not any(token in href_lower for token in ["job", "career", "requisition"]) and not any(token in title_lower for token in ["job", "career", "vacante", "empleo"]):
            continue

        jobs.append(
            {
                "company": company_name,
                "title": title or "Unknown title",
                "location": "",
                "url": href,
                "department": "",
                "workplace_type": "",
                "description_snippet": "",
                "ats": "successfactors",
            }
        )
        seen.add(href)

    print(f"SuccessFactors OK {company_name}: {len(jobs)} jobs")
    return jobs
