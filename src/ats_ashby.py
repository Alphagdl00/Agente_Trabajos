from __future__ import annotations

from urllib.parse import urlparse

from src.http_utils import create_session, safe_request


def extract_job_board_name(career_url: str) -> str:
    parsed = urlparse(career_url.strip())
    path_parts = [part for part in parsed.path.split("/") if part]

    if path_parts:
        return path_parts[-1]

    host = parsed.netloc.lower()
    if host.endswith(".ashbyhq.com"):
        return host.split(".")[0]

    return ""


def scrape_ashby(company_name: str, career_url: str) -> list[dict]:
    board_name = extract_job_board_name(career_url)
    if not board_name:
        print(f"Ashby board inválido: {career_url}")
        return []

    api_url = f"https://api.ashbyhq.com/posting-api/job-board/{board_name}?includeCompensation=true"
    session = create_session(api_mode=True)
    response = safe_request(session, "GET", api_url, api_mode=True, apply_delay=False)
    if response is None:
        print(f"Ashby error {career_url}")
        return []

    data = response.json()
    jobs: list[dict] = []

    for job in data.get("jobs", []):
        secondary_locations = job.get("secondaryLocations") or []
        location_parts = []

        primary_location = str(job.get("location", "") or "").strip()
        if primary_location:
            location_parts.append(primary_location)

        for secondary in secondary_locations:
            location = str((secondary or {}).get("location", "") or "").strip()
            if location:
                location_parts.append(location)

        jobs.append(
            {
                "company": company_name,
                "title": job.get("title", ""),
                "location": " | ".join(dict.fromkeys(location_parts)),
                "url": job.get("jobUrl", "") or f"{career_url.rstrip('/')}/{job.get('id', '')}",
                "department": job.get("department", ""),
                "workplace_type": "remote" if job.get("isRemote") else "",
                "description_snippet": job.get("descriptionPlain", "") or "",
                "posted_date": job.get("publishedDate", "") or "",
                "ats": "ashby",
            }
        )

    return jobs
