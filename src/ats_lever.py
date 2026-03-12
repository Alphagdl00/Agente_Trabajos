import requests


def scrape_lever(company_name: str, careers_page_url: str):
    """
    Lee vacantes desde Lever API
    """
    jobs = []

    try:
        token = careers_page_url.rstrip("/").split("/")[-1]
        api_url = f"https://api.lever.co/v0/postings/{token}?mode=json"

        r = requests.get(api_url, timeout=20)
        r.raise_for_status()
        data = r.json()

        for j in data:
            cats = j.get("categories") or {}

            jobs.append({
                "company": company_name,
                "title": j.get("text", ""),
                "location": cats.get("location", ""),
                "department": cats.get("team", ""),
                "workplace_type": cats.get("workplaceType", ""),
                "url": j.get("hostedUrl", ""),
                "description_snippet": "",
                "ats": "lever"
            })

    except requests.RequestException as e:
        print(f"Lever error {careers_page_url}: {e}")

    return jobs