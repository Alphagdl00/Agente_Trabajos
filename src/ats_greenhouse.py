import requests


def scrape_greenhouse(company_name: str, careers_page_url: str):
    """
    Lee vacantes desde Greenhouse public API
    """
    jobs = []

    try:
        token = careers_page_url.rstrip("/").split("/")[-1]
        api_url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"

        r = requests.get(api_url, timeout=20)
        r.raise_for_status()
        data = r.json()

        for j in data.get("jobs", []):
            jobs.append({
                "company": company_name,
                "title": j.get("title", ""),
                "location": (j.get("location") or {}).get("name", ""),
                "url": j.get("absolute_url", ""),
                "department": (j.get("departments") or [{}])[0].get("name", "") if j.get("departments") else "",
                "workplace_type": "",
                "description_snippet": "",
                "ats": "greenhouse"
            })

    except requests.RequestException as e:
        print(f"Greenhouse error {careers_page_url}: {e}")

    return jobs