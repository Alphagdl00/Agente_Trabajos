# src/ats_lever.py

from __future__ import annotations

from src.http_utils import create_session, safe_request


def scrape_lever(company_name: str, careers_page_url: str) -> list[dict]:
    """
    Lee vacantes desde Lever API.
    """
    jobs: list[dict] = []
    session = create_session(api_mode=True)

    try:
        token = careers_page_url.rstrip("/").split("/")[-1]
        api_url = f"https://api.lever.co/v0/postings/{token}?mode=json"

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

        for job in data:
            categories = job.get("categories") or {}

            jobs.append(
                {
                    "company": company_name,
                    "title": job.get("text", ""),
                    "location": categories.get("location", ""),
                    "department": categories.get("team", ""),
                    "workplace_type": categories.get("workplaceType", ""),
                    "url": job.get("hostedUrl", ""),
                    "description_snippet": "",
                    "ats": "lever",
                }
            )

    except Exception as exc:
        print(f"Lever error {careers_page_url}: {exc}")

    return jobs