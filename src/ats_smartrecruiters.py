from __future__ import annotations

from urllib.parse import urlparse

from src.http_utils import create_session, safe_request


def extract_company_identifier(career_url: str) -> str:
    parsed = urlparse(career_url.strip())
    path_parts = [part for part in parsed.path.split("/") if part]

    if path_parts:
        return path_parts[-1]

    return ""


def scrape_smartrecruiters(company_name: str, career_url: str) -> list[dict]:
    company_identifier = extract_company_identifier(career_url)
    if not company_identifier:
        print(f"SmartRecruiters company inválida: {career_url}")
        return []

    session = create_session(api_mode=True)
    api_url = f"https://api.smartrecruiters.com/v1/companies/{company_identifier}/postings"
    response = safe_request(session, "GET", api_url, api_mode=True, apply_delay=False)
    if response is None:
        print(f"SmartRecruiters error {career_url}")
        return []

    data = response.json()
    jobs: list[dict] = []

    for job in data.get("content", []):
        location_data = job.get("location") or {}
        location_bits = [
            str(location_data.get("city", "") or "").strip(),
            str(location_data.get("region", "") or "").strip(),
            str(location_data.get("country", "") or "").strip(),
        ]
        location = ", ".join([bit for bit in location_bits if bit])

        jobs.append(
            {
                "company": company_name,
                "title": job.get("name", ""),
                "location": location,
                "url": job.get("applyUrl", "") or job.get("postingUrl", ""),
                "department": ((job.get("department") or {}).get("label", "")),
                "workplace_type": "remote" if location_data.get("remote") else "",
                "description_snippet": ((job.get("jobAd") or {}).get("jobDescription", "")),
                "posted_date": job.get("releasedDate", "") or "",
                "ats": "smartrecruiters",
            }
        )

    return jobs
