# src/ats_greenhouse.py

from __future__ import annotations

from src.http_utils import create_session, safe_request


def scrape_greenhouse(company_name: str, careers_page_url: str) -> list[dict]:
    """
    Lee vacantes desde Greenhouse public API.
    """
    jobs: list[dict] = []
    session = create_session(api_mode=True)

    try:
        token = careers_page_url.rstrip("/").split("/")[-1]
        api_url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"

        response = safe_request(
            session,
            "GET",
            api_url,
            api_mode=True,
            apply_delay=False,
        )
        if response is None:
            return jobs

        data = response.json()

        for job in data.get("jobs", []):
            departments = job.get("departments") or []
            department_name = ""
            if departments and isinstance(departments[0], dict):
                department_name = departments[0].get("name", "")

            jobs.append(
                {
                    "company": company_name,
                    "title": job.get("title", ""),
                    "location": (job.get("location") or {}).get("name", ""),
                    "url": job.get("absolute_url", ""),
                    "department": department_name,
                    "workplace_type": "",
                    "description_snippet": "",
                    "ats": "greenhouse",
                }
            )

    except Exception as exc:
        print(f"Greenhouse error {careers_page_url}: {exc}")

    return jobs