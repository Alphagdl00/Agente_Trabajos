import re
import requests


def _strip_html(html: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    if not html:
        return ""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    return text.strip()[:500]


def scrape_greenhouse(company_name: str, careers_page_url: str):
    """
    Fetch jobs from Greenhouse public API including description snippets.
    """
    jobs = []

    try:
        token = careers_page_url.rstrip("/").split("/")[-1]
        api_url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"

        r = requests.get(api_url, timeout=20)
        r.raise_for_status()
        data = r.json()

        for j in data.get("jobs", []):
            content = j.get("content", "")
            snippet = _strip_html(content)

            location_obj = j.get("location") or {}
            departments = j.get("departments") or []

            jobs.append({
                "company": company_name,
                "title": j.get("title", ""),
                "location": location_obj.get("name", ""),
                "url": j.get("absolute_url", ""),
                "department": departments[0].get("name", "") if departments else "",
                "workplace_type": "",
                "description_snippet": snippet,
                "posted_date": j.get("updated_at", ""),
                "ats": "greenhouse",
            })

    except requests.RequestException as e:
        print(f"[GREENHOUSE] Error {careers_page_url}: {e}")

    return jobs
