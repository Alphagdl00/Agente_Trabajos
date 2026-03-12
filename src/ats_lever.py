import re
import requests


def _strip_html(html: str) -> str:
    if not html:
        return ""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    return text.strip()[:500]


def scrape_lever(company_name: str, careers_page_url: str):
    """
    Fetch jobs from Lever public API including description snippets.
    """
    jobs = []

    try:
        token = careers_page_url.rstrip("/").split("/")[-1]
        api_url = f"https://api.lever.co/v0/postings/{token}?mode=json"

        r = requests.get(api_url, timeout=12)
        r.raise_for_status()
        data = r.json()

        for j in data:
            cats = j.get("categories") or {}

            # Lever provides descriptionPlain or description (HTML)
            snippet = (j.get("descriptionPlain") or "").strip()[:500]
            if not snippet:
                snippet = _strip_html(j.get("description", ""))

            # Also grab content from additional lists
            additional = j.get("additional") or j.get("additionalPlain") or ""
            if additional and len(snippet) < 300:
                extra = additional if isinstance(additional, str) else _strip_html(str(additional))
                snippet = f"{snippet} {extra}".strip()[:500]

            jobs.append({
                "company": company_name,
                "title": j.get("text", ""),
                "location": cats.get("location", ""),
                "department": cats.get("team", ""),
                "workplace_type": cats.get("workplaceType", ""),
                "url": j.get("hostedUrl", ""),
                "description_snippet": snippet,
                "posted_date": "",
                "ats": "lever",
            })

    except requests.RequestException as e:
        print(f"[LEVER] Error {careers_page_url}: {e}")

    return jobs
