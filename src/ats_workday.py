import requests
from urllib.parse import urlparse


def extract_workday_parts(career_url: str):

    parsed = urlparse(career_url)
    host = parsed.netloc
    path_parts = [p for p in parsed.path.split("/") if p]

    tenant = host.split(".")[0]
    site = path_parts[-1] if path_parts else ""

    if not host or not tenant or not site:
        return None

    api_url = f"https://{host}/wday/cxs/{tenant}/{site}/jobs"
    referer = career_url.rstrip("/")

    return {
        "host": host,
        "tenant": tenant,
        "site": site,
        "api_url": api_url,
        "referer": referer,
    }


def scrape_workday(company_name: str, career_url: str):

    jobs = []

    parts = extract_workday_parts(career_url)

    if not parts:
        print(f"Workday URL inválida: {career_url}")
        return jobs

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": f"https://{parts['host']}",
        "Referer": parts["referer"],
        "User-Agent": "Mozilla/5.0",
    }

    offset = 0
    limit = 20

    while True:

        payload = {
            "appliedFacets": {},
            "limit": limit,
            "offset": offset,
            "searchText": "",
        }

        try:

            response = requests.post(
                parts["api_url"],
                json=payload,
                headers=headers,
                timeout=15,
            )

            response.raise_for_status()

            data = response.json()

            postings = data.get("jobPostings", [])

            if not postings:
                break

            for job in postings:

                title = job.get("title", "")

                location = job.get("locationsText", "")

                if not location:
                    locations = job.get("locations", [])
                    if isinstance(locations, list):
                        location = "; ".join(
                            [
                                loc.get("displayName", "")
                                for loc in locations
                                if isinstance(loc, dict)
                            ]
                        )

                external_path = job.get("externalPath", "")
                url = ""

                if external_path:
                    if external_path.startswith("http"):
                        url = external_path
                    else:
                        url = career_url.rstrip("/") + "/" + external_path.lstrip("/")

                jobs.append({
                    "company": company_name,
                    "title": title,
                    "location": location,
                    "url": url,
                    "department": "",
                    "workplace_type": str(job.get("remoteType", "")),
                    "description_snippet": "",
                    "ats": "workday"
                })

            if len(postings) < limit:
                break

            offset += limit

        except Exception as e:
            print(f"Workday error {career_url}: {e}")
            break

    print(f"Workday OK {company_name}: {len(jobs)} jobs")

    return jobs