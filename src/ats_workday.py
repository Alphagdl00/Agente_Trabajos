# src/ats_workday.py

from __future__ import annotations

from urllib.parse import urlparse

from src.http_utils import create_session, safe_request


def extract_workday_parts(career_url: str):
    parsed = urlparse(career_url)
    host = parsed.netloc
    path_parts = [p for p in parsed.path.split("/") if p]

    if not host:
        return None

    tenant = host.split(".")[0]
    site = path_parts[-1] if path_parts else ""

    if not tenant or not site:
        return None

    return {
        "host": host,
        "tenant": tenant,
        "site": site,
        "path_parts": path_parts,
        "referer": career_url.rstrip("/"),
    }


def build_candidate_api_urls(career_url: str) -> list[str]:
    parts = extract_workday_parts(career_url)
    if not parts:
        return []

    host = parts["host"]
    tenant = parts["tenant"]
    site = parts["site"]
    path_parts = parts["path_parts"]

    candidates: list[str] = []

    candidates.append(f"https://{host}/wday/cxs/{tenant}/{site}/jobs")

    if len(path_parts) >= 2:
        locale = path_parts[0]
        maybe_site = path_parts[-1]
        candidates.append(f"https://{host}/wday/cxs/{tenant}/{maybe_site}/jobs")
        candidates.append(f"https://{host}/wday/cxs/{tenant}/{locale}/{maybe_site}/jobs")

    candidates.append(f"https://{host}/wday/cxs/{tenant}/recruiting/{site}/jobs")

    seen = set()
    deduped: list[str] = []
    for url in candidates:
        if url not in seen:
            seen.add(url)
            deduped.append(url)

    return deduped


def normalize_workday_url(career_url: str, external_path: str) -> str:
    if not external_path:
        return ""

    if external_path.startswith("http"):
        return external_path

    return f"{career_url.rstrip('/')}/{external_path.lstrip('/')}"


def parse_workday_locations(job: dict) -> str:
    location = job.get("locationsText", "")
    if location:
        return str(location)

    locations = job.get("locations", [])
    if isinstance(locations, list):
        values = []
        for loc in locations:
            if isinstance(loc, dict):
                name = loc.get("displayName", "")
                if name:
                    values.append(str(name))
        if values:
            return "; ".join(values)

    return ""


def build_headers(host: str, referer: str) -> dict:
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": f"https://{host}",
        "Referer": referer,
    }


def try_fetch_from_api(
    session,
    api_url: str,
    headers: dict,
    company_name: str,
    career_url: str,
) -> list[dict]:
    jobs: list[dict] = []
    offset = 0
    limit = 20

    while True:
        payload = {
            "appliedFacets": {},
            "limit": limit,
            "offset": offset,
            "searchText": "",
        }

        response = safe_request(
            session,
            "POST",
            api_url,
            json=payload,
            headers=headers,
        )
        if response is None:
            return []

        data = response.json()
        postings = data.get("jobPostings", [])

        if not postings:
            break

        for job in postings:
            jobs.append(
                {
                    "company": company_name,
                    "title": job.get("title", ""),
                    "location": parse_workday_locations(job),
                    "url": normalize_workday_url(career_url, job.get("externalPath", "")),
                    "department": "",
                    "workplace_type": str(job.get("remoteType", "")),
                    "description_snippet": "",
                    "ats": "workday",
                }
            )

        if len(postings) < limit:
            break

        offset += limit

    return jobs


def scrape_workday(company_name: str, career_url: str) -> list[dict]:
    jobs: list[dict] = []

    parts = extract_workday_parts(career_url)
    if not parts:
        print(f"Workday URL inválida: {career_url}")
        return jobs

    api_urls = build_candidate_api_urls(career_url)
    headers = build_headers(parts["host"], parts["referer"])
    session = create_session()

    last_error = None

    for api_url in api_urls:
        try:
            jobs = try_fetch_from_api(session, api_url, headers, company_name, career_url)
            if jobs:
                print(f"Workday OK {company_name}: {len(jobs)} jobs via {api_url}")
                return jobs
        except Exception as exc:
            last_error = exc
            print(f"Workday error {career_url} using {api_url}: {exc}")

    print(f"Workday OK {company_name}: 0 jobs")
    if last_error:
        print(f"Workday final failure {company_name}: {last_error}")

    return []