"""
Workday URL Validator & Auto-Discoverer
Run locally: python verify_workday_urls.py

Tests each Workday URL in companies.csv and attempts to find the correct
site name if the current one fails.
"""
import csv
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

COMMON_SITE_NAMES = [
    # Most common patterns
    "{company}Careers",
    "{company}_Careers",
    "{company}",
    "Careers",
    "External",
    "External_Careers",
    "{company}_External",
    "en-US/Careers",
    "en-US/{company}Careers",
    "en-US/{company}",
    "en-US/External",
    # Less common
    "SearchJobs",
    "Jobs",
    "Global",
    "{company}Jobs",
    "{company}_Jobs",
    "CorporateCareers",
    "ExternalCareers",
]


def test_workday_url(host: str, tenant: str, site: str, timeout: int = 8) -> dict | None:
    """Test if a Workday API endpoint responds with jobs."""
    api_url = f"https://{host}/wday/cxs/{tenant}/{site}/jobs"
    referer = f"https://{host}/{site}"

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": f"https://{host}",
        "Referer": referer,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    payload = {"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": ""}

    try:
        r = requests.post(api_url, json=payload, headers=headers, timeout=timeout)
        if r.status_code == 200:
            data = r.json()
            total = data.get("total", 0)
            return {"site": site, "total": total, "url": f"https://{host}/{site}"}
    except Exception:
        pass
    return None


def discover_correct_site(host: str, tenant: str, company_name: str) -> dict | None:
    """Try common site name patterns to find the working one."""
    # Clean company name for pattern matching
    clean = company_name.replace(" ", "").replace("&", "").replace("-", "")

    candidates = []
    for pattern in COMMON_SITE_NAMES:
        site = pattern.replace("{company}", clean)
        candidates.append(site)

    # Also try the tenant name itself
    candidates.extend([tenant, f"{tenant}Careers", f"{tenant}_Careers", f"en-US/{tenant}"])

    # Deduplicate
    seen = set()
    unique = []
    for c in candidates:
        if c.lower() not in seen:
            seen.add(c.lower())
            unique.append(c)

    for site in unique:
        result = test_workday_url(host, tenant, site, timeout=5)
        if result and result["total"] > 0:
            return result

    return None


def validate_company(row: dict) -> dict:
    """Validate a single company's Workday URL."""
    company = row["company"]
    url = row["career_url"].strip().rstrip("/")

    # Parse the URL
    from urllib.parse import urlparse
    parsed = urlparse(url)
    host = parsed.netloc
    path_parts = [p for p in parsed.path.split("/") if p and p != "en-US"]
    tenant = host.split(".")[0]
    site = path_parts[-1] if path_parts else ""

    # Handle en-US in path
    full_site = "/".join(p for p in parsed.path.split("/") if p) if parsed.path else site

    result = {
        "company": company,
        "original_url": url,
        "tenant": tenant,
        "original_site": full_site,
        "status": "unknown",
        "correct_url": "",
        "total_jobs": 0,
    }

    # First test the original URL
    test = test_workday_url(host, tenant, full_site)
    if test and test["total"] > 0:
        result["status"] = "✅ OK"
        result["correct_url"] = test["url"]
        result["total_jobs"] = test["total"]
        return result

    # Also test without en-US prefix
    if "/" in full_site:
        bare_site = full_site.split("/")[-1]
        test = test_workday_url(host, tenant, bare_site)
        if test and test["total"] > 0:
            result["status"] = "🔧 FIXED (removed en-US)"
            result["correct_url"] = test["url"]
            result["total_jobs"] = test["total"]
            return result

    # Try auto-discovery
    print(f"  🔍 Discovering correct site for {company}...")
    discovered = discover_correct_site(host, tenant, company)
    if discovered:
        result["status"] = f"🔧 FIXED (discovered: {discovered['site']})"
        result["correct_url"] = discovered["url"]
        result["total_jobs"] = discovered["total"]
        return result

    result["status"] = "❌ FAILED"
    return result


def main():
    csv_path = "config/companies.csv"

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = [r for r in reader if r.get("ats", "").strip().lower() == "workday"]

    print(f"\n{'='*60}")
    print(f"Validating {len(rows)} Workday URLs...")
    print(f"{'='*60}\n")

    results = []
    ok_count = 0
    fixed_count = 0
    failed_count = 0

    for i, row in enumerate(rows, 1):
        company = row["company"]
        print(f"[{i}/{len(rows)}] {company}...", end=" ", flush=True)

        result = validate_company(row)
        results.append(result)

        if "OK" in result["status"]:
            ok_count += 1
            print(f"{result['status']} ({result['total_jobs']} jobs)")
        elif "FIXED" in result["status"]:
            fixed_count += 1
            print(f"{result['status']} ({result['total_jobs']} jobs)")
            print(f"         NEW URL: {result['correct_url']}")
        else:
            failed_count += 1
            print(f"{result['status']}")

    print(f"\n{'='*60}")
    print(f"SUMMARY: {ok_count} OK | {fixed_count} Fixed | {failed_count} Failed")
    print(f"{'='*60}\n")

    # Output corrections
    if fixed_count > 0 or failed_count > 0:
        print("CORRECTIONS TO APPLY:")
        for r in results:
            if "FIXED" in r["status"]:
                print(f"  {r['company']}: {r['original_url']} → {r['correct_url']}")

        print(f"\nFAILED (need manual URL lookup):")
        for r in results:
            if "FAILED" in r["status"]:
                print(f"  {r['company']}: {r['original_url']}")

    # Save results
    with open("output/workday_validation.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nFull results saved to output/workday_validation.json")


if __name__ == "__main__":
    main()
