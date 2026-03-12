"""
Bulk URL Validator — test hundreds of candidate companies at once.
Run: python validate_all_candidates.py
Output: config/companies_validated.csv (only working URLs)
"""
import csv
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

# ============================================================
# CANDIDATE COMPANIES TO TEST
# Each entry: (company, industry, region, country, priority, ats_type, candidate_tokens_or_urls)
# For greenhouse: list of possible tokens to try
# For workday: list of possible full URLs to try
# ============================================================

GREENHOUSE_CANDIDATES = [
    # Tech - FAANG adjacent & enterprise
    ("Stripe", "Fintech", "Global", "US", "A", ["stripe"]),
    ("Coinbase", "Fintech", "Global", "US", "A", ["coinbase"]),
    ("Airbnb", "Tech", "Global", "US", "A", ["airbnb"]),
    ("Datadog", "Tech", "Global", "US", "A", ["datadog"]),
    ("MongoDB", "Tech", "Global", "US", "A", ["mongodb"]),
    ("Figma", "Tech", "Global", "US", "A", ["figma"]),
    ("Duolingo", "Tech", "Global", "US", "B", ["duolingo"]),
    ("Databricks", "Tech", "Global", "US", "A", ["databricks"]),
    ("Cloudflare", "Tech", "Global", "US", "A", ["cloudflare"]),
    ("Okta", "Tech", "Global", "US", "A", ["okta"]),
    ("Twilio", "Tech", "Global", "US", "B", ["twilio"]),
    ("Elastic", "Tech", "Global", "Netherlands", "B", ["elastic"]),
    ("GitLab", "Tech", "Global", "US", "A", ["gitlab"]),
    ("SpaceX", "Tech", "Global", "US", "A", ["spacex"]),
    ("Celonis", "Tech", "Europe", "Germany", "A", ["celonis"]),
    ("Adyen", "Fintech", "Europe", "Netherlands", "A", ["adyen"]),
    ("Nubank", "Fintech", "LATAM", "Brazil", "A", ["nubank"]),
    ("Robinhood", "Fintech", "Global", "US", "B", ["robinhood"]),
    ("Brex", "Fintech", "Global", "US", "B", ["brex"]),
    ("Ripple", "Fintech", "Global", "US", "A", ["ripple"]),
    ("Affirm", "Fintech", "Global", "US", "B", ["affirm"]),
    ("N26", "Fintech", "Europe", "Germany", "B", ["n26"]),
    ("HubSpot", "Tech", "Global", "US", "A", ["hubspot"]),
    ("Wise", "Fintech", "Europe", "UK", "A", ["transferwise", "wise"]),

    # More tech companies to test
    ("Spotify", "Tech", "Europe", "Sweden", "A", ["spotify", "lifeatspotify"]),
    ("Netflix", "Tech", "Global", "US", "A", ["netflix", "netflixjobs"]),
    ("Uber", "Tech", "Global", "US", "A", ["uber", "uberjobs"]),
    ("Tesla", "Tech", "Global", "US", "A", ["tesla", "teslamotors"]),
    ("Palantir", "Tech", "Global", "US", "A", ["palantir", "palantirtechnologies"]),
    ("Snowflake", "Tech", "Global", "US", "A", ["snowflake", "snowflakecomputing"]),
    ("Shopify", "Tech", "Global", "Canada", "A", ["shopify"]),
    ("Atlassian", "Tech", "Asia-Pacific", "Australia", "A", ["atlassian"]),
    ("Notion", "Tech", "Global", "US", "B", ["notion", "notionhq", "makenotion"]),
    ("Canva", "Tech", "Asia-Pacific", "Australia", "B", ["canva"]),
    ("Booking.com", "Tech", "Europe", "Netherlands", "A", ["booking", "bookingcom"]),
    ("Monday.com", "Tech", "Global", "Israel", "B", ["mondaydotcom", "monday"]),
    ("Wiz", "Tech", "Global", "Israel", "A", ["wiz", "wizsecurity"]),
    ("DocuSign", "Tech", "Global", "US", "B", ["docusign"]),
    ("ServiceNow", "Tech", "Global", "US", "A", ["servicenow", "servicenowcareers"]),
    ("Confluent", "Tech", "Global", "US", "B", ["confluent", "confluentinc"]),
    ("Ramp", "Fintech", "Global", "US", "B", ["ramp", "rampfinance"]),
    ("Trade Republic", "Fintech", "Europe", "Germany", "B", ["traderepublic"]),
    ("Klarna", "Fintech", "Europe", "Sweden", "A", ["klarna"]),
    ("Revolut", "Fintech", "Europe", "UK", "A", ["revolut"]),
    ("Checkout.com", "Fintech", "Europe", "UK", "B", ["checkoutcom", "checkout"]),
    ("Grab", "Tech", "Asia-Pacific", "Singapore", "B", ["grab"]),
    ("Delivery Hero", "Tech", "Europe", "Germany", "B", ["deliveryhero"]),
    ("Rappi", "Tech", "LATAM", "Colombia", "B", ["rappi"]),
    ("Globant", "Tech", "LATAM", "Argentina", "B", ["globant"]),
    ("Block (Square)", "Fintech", "Global", "US", "A", ["block", "squareup", "embed/job_board?for=squareup"]),
    ("Plaid", "Fintech", "Global", "US", "A", ["plaid"]),
    ("SoFi", "Fintech", "Global", "US", "B", ["sofi"]),

    # Additional high-value companies
    ("Zoom", "Tech", "Global", "US", "B", ["zoom", "zoomvideocommunications"]),
    ("Asana", "Tech", "Global", "US", "B", ["asana"]),
    ("Toast", "Tech", "Global", "US", "B", ["toast"]),
    ("Snyk", "Tech", "Global", "UK", "B", ["snyk"]),
    ("UiPath", "Tech", "Global", "US", "B", ["uipath"]),
    ("Personio", "Tech", "Europe", "Germany", "B", ["personio"]),
    ("Bolt", "Fintech", "Europe", "Estonia", "B", ["bolt", "bolteu"]),
    ("Circle", "Fintech", "Global", "US", "B", ["circle"]),
    ("Chainalysis", "Fintech", "Global", "US", "B", ["chainalysis"]),
    ("Kraken", "Fintech", "Global", "US", "B", ["kraken", "krakendigitalassetexchange"]),
    ("Gemini", "Fintech", "Global", "US", "B", ["gemini", "geminitrust"]),
    ("Lemonade", "Fintech", "Global", "US", "C", ["lemonade"]),
    ("Marqeta", "Fintech", "Global", "US", "B", ["marqeta"]),
    ("Zilch", "Fintech", "Europe", "UK", "C", ["zilch"]),
    ("Gusto", "Tech", "Global", "US", "B", ["gusto"]),
    ("Lattice", "Tech", "Global", "US", "B", ["lattice"]),
    ("Airtable", "Tech", "Global", "US", "B", ["airtable"]),
    ("Zapier", "Tech", "Global", "US", "B", ["zapier"]),
    ("Vercel", "Tech", "Global", "US", "B", ["vercel"]),
    ("Supabase", "Tech", "Global", "US", "B", ["supabase"]),
    ("Linear", "Tech", "Global", "US", "B", ["linear"]),
    ("Dbt Labs", "Tech", "Global", "US", "B", ["dbtlabs", "dbtlabsinc"]),
    ("Cockroach Labs", "Tech", "Global", "US", "B", ["cockroachlabs"]),
    ("Grafana Labs", "Tech", "Global", "US", "B", ["grafanalabs"]),
    ("HashiCorp", "Tech", "Global", "US", "B", ["hashicorp"]),
    ("LaunchDarkly", "Tech", "Global", "US", "C", ["launchdarkly"]),
    ("Instacart", "Tech", "Global", "US", "B", ["instacart"]),
    ("DoorDash", "Tech", "Global", "US", "B", ["doordash"]),
    ("Lyft", "Tech", "Global", "US", "B", ["lyft"]),
    ("Pinterest", "Tech", "Global", "US", "B", ["pinterest"]),
    ("Reddit", "Tech", "Global", "US", "B", ["reddit"]),
    ("Discord", "Tech", "Global", "US", "B", ["discord"]),
    ("Figma", "Tech", "Global", "US", "A", ["figma"]),
    ("Anthropic", "Tech", "Global", "US", "A", ["anthropic"]),
    ("OpenAI", "Tech", "Global", "US", "A", ["openai"]),
    ("Scale AI", "Tech", "Global", "US", "A", ["scaleai"]),
    ("Cohere", "Tech", "Global", "Canada", "B", ["cohere"]),
    ("Anduril", "Tech", "Global", "US", "A", ["anduril"]),
    ("Relativity Space", "Tech", "Global", "US", "B", ["relativityspace"]),
    ("Flexport", "Tech", "Global", "US", "B", ["flexport"]),
    ("Navan", "Tech", "Global", "US", "B", ["navan", "tripactions"]),
    ("Deel", "Tech", "Global", "US", "A", ["deel"]),
    ("Remote", "Tech", "Global", "US", "B", ["remote", "remotecom"]),
    ("Oyster HR", "Tech", "Global", "US", "B", ["oysterhr"]),
    ("Miro", "Tech", "Global", "US", "B", ["miro", "realtimeboard"]),
    ("Pleo", "Fintech", "Europe", "Denmark", "B", ["pleo"]),
    ("Mollie", "Fintech", "Europe", "Netherlands", "B", ["mollie"]),
    ("SumUp", "Fintech", "Europe", "Germany", "B", ["sumup"]),
    ("GoCardless", "Fintech", "Europe", "UK", "B", ["gocardless"]),
    ("Thought Machine", "Fintech", "Europe", "UK", "B", ["thoughtmachine"]),
    ("MoonPay", "Fintech", "Global", "US", "B", ["moonpay"]),
    ("Fireblocks", "Fintech", "Global", "US", "B", ["fireblocks"]),
]

WORKDAY_CANDIDATES = [
    # Pharma / Life Sciences - test multiple site name variants
    ("Johnson & Johnson", "Pharma", "Global", "US", "A",
     ["https://jnj.wd5.myworkdayjobs.com/JnJCareers",
      "https://jj.wd5.myworkdayjobs.com/JJ",
      "https://jj.wd5.myworkdayjobs.com/en-US/JJ"]),
    ("Roche", "Pharma", "Europe", "Switzerland", "A",
     ["https://roche.wd3.myworkdayjobs.com/RocheCareers",
      "https://roche.wd3.myworkdayjobs.com/roche-ext",
      "https://roche.wd3.myworkdayjobs.com/en-US/roche-ext"]),
    ("Bayer", "Pharma", "Europe", "Germany", "A",
     ["https://bayer.wd3.myworkdayjobs.com/BayerCareers",
      "https://bayer.wd3.myworkdayjobs.com/External",
      "https://bayer.wd3.myworkdayjobs.com/Careers"]),
    ("Takeda", "Pharma", "Asia-Pacific", "Japan", "A",
     ["https://takeda.wd3.myworkdayjobs.com/TakedaCareers",
      "https://takeda.wd3.myworkdayjobs.com/External",
      "https://takeda.wd3.myworkdayjobs.com/Careers"]),
    ("Merck", "Pharma", "Global", "US", "A",
     ["https://msd.wd5.myworkdayjobs.com/SearchJobs",
      "https://msd.wd5.myworkdayjobs.com/External"]),
    ("AbbVie", "Pharma", "Global", "US", "A",
     ["https://abbvie.wd5.myworkdayjobs.com/AbbVie",
      "https://abbvie.wd5.myworkdayjobs.com/abbvie",
      "https://abbvie.wd5.myworkdayjobs.com/External"]),
    ("Bristol-Myers Squibb", "Pharma", "Global", "US", "A",
     ["https://bristolmyerssquibb.wd5.myworkdayjobs.com/BMS",
      "https://bms.wd1.myworkdayjobs.com/BMS"]),
    ("Eli Lilly", "Pharma", "Global", "US", "A",
     ["https://lilly.wd5.myworkdayjobs.com/Lilly_Careers",
      "https://lilly.wd5.myworkdayjobs.com/External"]),
    ("Amgen", "Pharma", "Global", "US", "A",
     ["https://amgen.wd1.myworkdayjobs.com/Careers",
      "https://amgen.wd1.myworkdayjobs.com/External"]),
    ("Gilead Sciences", "Pharma", "Global", "US", "A",
     ["https://gilead.wd1.myworkdayjobs.com/Gilead",
      "https://gilead.wd1.myworkdayjobs.com/External"]),
    ("Novo Nordisk", "Pharma", "Europe", "Denmark", "A",
     ["https://novonordisk.wd1.myworkdayjobs.com/NovoNordisk",
      "https://novonordisk.wd1.myworkdayjobs.com/External"]),
    ("Boehringer Ingelheim", "Pharma", "Europe", "Germany", "B",
     ["https://boehringeringelheim.wd3.myworkdayjobs.com/BI",
      "https://boehringeringelheim.wd3.myworkdayjobs.com/External"]),
    ("Regeneron", "Pharma", "Global", "US", "A",
     ["https://regeneron.wd1.myworkdayjobs.com/RegeneronCareers",
      "https://regeneron.wd1.myworkdayjobs.com/External"]),
    ("Biogen", "Pharma", "Global", "US", "B",
     ["https://biogen.wd1.myworkdayjobs.com/Careers",
      "https://biogen.wd1.myworkdayjobs.com/External"]),
    ("IQVIA", "Life Sciences", "Global", "US", "B",
     ["https://iqvia.wd5.myworkdayjobs.com/IQVIA",
      "https://iqvia.wd1.myworkdayjobs.com/IQVIA_Careers"]),

    # MedTech
    ("Medtronic", "MedTech", "Global", "US", "A",
     ["https://medtronic.wd1.myworkdayjobs.com/MedtronicCareers",
      "https://medtronic.wd1.myworkdayjobs.com/External"]),
    ("Abbott", "MedTech", "Global", "US", "A",
     ["https://abbott.wd5.myworkdayjobs.com/AbbottCareers",
      "https://abbott.wd5.myworkdayjobs.com/External"]),
    ("Stryker", "MedTech", "Global", "US", "A",
     ["https://stryker.wd1.myworkdayjobs.com/StrykerCareers",
      "https://stryker.wd1.myworkdayjobs.com/External"]),
    ("Boston Scientific", "MedTech", "Global", "US", "A",
     ["https://bostonscientific.wd1.myworkdayjobs.com/bscCareers",
      "https://bostonscientific.wd1.myworkdayjobs.com/External"]),
    ("Philips", "MedTech", "Europe", "Netherlands", "A",
     ["https://philips.wd3.myworkdayjobs.com/PhilipsCareers",
      "https://philips.wd3.myworkdayjobs.com/External"]),
    ("Siemens Healthineers", "MedTech", "Europe", "Germany", "A",
     ["https://siemenshealthineers.wd3.myworkdayjobs.com/SHCareers",
      "https://siemenshealthineers.wd3.myworkdayjobs.com/External"]),

    # Industrial
    ("ABB", "Industrial", "Europe", "Switzerland", "A",
     ["https://abb.wd3.myworkdayjobs.com/External",
      "https://abb.wd3.myworkdayjobs.com/ABB_Careers",
      "https://abb.wd3.myworkdayjobs.com/Careers"]),
    ("GE Aerospace", "Industrial", "Global", "US", "A",
     ["https://gehc.wd1.myworkdayjobs.com/GEHC_External",
      "https://geaerospace.wd5.myworkdayjobs.com/External"]),
    ("Emerson", "Industrial", "Global", "US", "B",
     ["https://emerson.wd5.myworkdayjobs.com/Emerson_Careers",
      "https://emerson.wd5.myworkdayjobs.com/External"]),
    ("Bosch", "Industrial", "Europe", "Germany", "B",
     ["https://bosch.wd3.myworkdayjobs.com/boschglobalcareers",
      "https://bosch.wd3.myworkdayjobs.com/External"]),
    ("Volvo Group", "Industrial", "Europe", "Sweden", "B",
     ["https://volvogroup.wd3.myworkdayjobs.com/External_Career_Site",
      "https://volvogroup.wd3.myworkdayjobs.com/External"]),
    ("Caterpillar", "Industrial", "Global", "US", "B",
     ["https://caterpillar.wd5.myworkdayjobs.com/CaterpillarCareers",
      "https://cat.wd5.myworkdayjobs.com/CaterpillarCareers"]),
    ("3M", "Industrial", "Global", "US", "B",
     ["https://3m.wd1.myworkdayjobs.com/Search",
      "https://3m.wd1.myworkdayjobs.com/External"]),

    # Tech - Workday users
    ("Adobe", "Tech", "Global", "US", "A",
     ["https://adobe.wd5.myworkdayjobs.com/external_experienced",
      "https://adobe.wd5.myworkdayjobs.com/External"]),
    ("Cisco", "Tech", "Global", "US", "A",
     ["https://cisco.wd5.myworkdayjobs.com/External"]),
    ("IBM", "Tech", "Global", "US", "A",
     ["https://ibm.wd5.myworkdayjobs.com/IBMCareers",
      "https://ibm.wd1.myworkdayjobs.com/External"]),
    ("Intel", "Tech", "Global", "US", "B",
     ["https://intel.wd1.myworkdayjobs.com/External"]),
    ("Palo Alto Networks", "Tech", "Global", "US", "A",
     ["https://paloaltonetworks.wd5.myworkdayjobs.com/Careers",
      "https://paloaltonetworks.wd5.myworkdayjobs.com/External"]),
    ("CrowdStrike", "Tech", "Global", "US", "A",
     ["https://crowdstrike.wd5.myworkdayjobs.com/crowdstrikecareers"]),
    ("Workday", "Tech", "Global", "US", "A",
     ["https://workday.wd5.myworkdayjobs.com/Workday"]),
    ("Intuit", "Tech", "Global", "US", "A",
     ["https://intuit.wd1.myworkdayjobs.com/External"]),

    # Financial Services
    ("Citi", "Financial Services", "Global", "US", "A",
     ["https://citi.wd5.myworkdayjobs.com/2"]),
    ("BlackRock", "Financial Services", "Global", "US", "A",
     ["https://blackrock.wd1.myworkdayjobs.com/BlackRock"]),
    ("Fidelity", "Financial Services", "Global", "US", "A",
     ["https://fidelity.wd5.myworkdayjobs.com/FidelityCareers"]),
    ("Visa", "Financial Services", "Global", "US", "A",
     ["https://visa.wd5.myworkdayjobs.com/Visa_Careers"]),
    ("Mastercard", "Financial Services", "Global", "US", "A",
     ["https://mastercard.wd1.myworkdayjobs.com/CorporateCareers"]),
    ("PayPal", "Fintech", "Global", "US", "A",
     ["https://paypal.wd1.myworkdayjobs.com/PayPalJobs",
      "https://paypal.wd1.myworkdayjobs.com/External"]),
    ("American Express", "Financial Services", "Global", "US", "A",
     ["https://americanexpress.wd5.myworkdayjobs.com/AmericanExpress"]),

    # Consumer
    ("Unilever", "Consumer", "Europe", "UK", "A",
     ["https://unilever.wd3.myworkdayjobs.com/UnileverExternalCareers"]),
    ("PepsiCo", "Consumer", "Global", "US", "A",
     ["https://pepsico.wd1.myworkdayjobs.com/Pepsico"]),
    ("Nike", "Consumer", "Global", "US", "A",
     ["https://nike.wd1.myworkdayjobs.com/NikeCareers"]),

    # Consulting
    ("Gartner", "Consulting", "Global", "US", "B",
     ["https://gartner.wd5.myworkdayjobs.com/Gartner_Careers"]),
    ("Capgemini", "Consulting", "Europe", "France", "B",
     ["https://capgemini.wd3.myworkdayjobs.com/CapgeminiCareers"]),

    # Mercado Libre
    ("Mercado Libre", "Fintech", "LATAM", "Argentina", "A",
     ["https://mercadolibre.wd3.myworkdayjobs.com/MELI",
      "https://mercadolibre.wd1.myworkdayjobs.com/MELI"]),
]


def test_greenhouse_token(token: str) -> int | None:
    """Test if a Greenhouse board token exists. Returns job count or None."""
    url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
    try:
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            data = r.json()
            return len(data.get("jobs", []))
    except Exception:
        pass
    return None


def test_workday_url(career_url: str) -> int | None:
    """Test if a Workday career URL works. Returns job count or None."""
    from urllib.parse import urlparse

    parsed = urlparse(career_url.rstrip("/"))
    host = parsed.netloc
    path_parts = [p for p in parsed.path.split("/") if p and p != "en-US"]
    tenant = host.split(".")[0]
    site = path_parts[-1] if path_parts else ""

    if not site:
        return None

    api_url = f"https://{host}/wday/cxs/{tenant}/{site}/jobs"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": f"https://{host}",
        "Referer": career_url,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    payload = {"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": ""}

    try:
        r = requests.post(api_url, json=payload, headers=headers, timeout=8)
        if r.status_code == 200:
            data = r.json()
            return data.get("total", 0)
    except Exception:
        pass
    return None


def validate_greenhouse(entry) -> dict | None:
    company, industry, region, country, priority, tokens = entry
    for token in tokens:
        count = test_greenhouse_token(token)
        if count is not None and count > 0:
            return {
                "company": company,
                "industry": industry,
                "region": region,
                "country": country,
                "priority": priority,
                "international_hiring": "High",
                "profile_fit": "Medium",
                "salary_band": "",
                "ats": "greenhouse",
                "career_url": f"https://boards.greenhouse.io/{token}",
                "jobs_found": count,
            }
    return None


def validate_workday(entry) -> dict | None:
    company, industry, region, country, priority, urls = entry
    for url in urls:
        count = test_workday_url(url)
        if count is not None and count > 0:
            return {
                "company": company,
                "industry": industry,
                "region": region,
                "country": country,
                "priority": priority,
                "international_hiring": "High",
                "profile_fit": "Medium",
                "salary_band": "",
                "ats": "workday",
                "career_url": url,
                "jobs_found": count,
            }
    return None


def main():
    print(f"\n{'='*60}")
    print(f"BULK VALIDATION")
    print(f"Testing {len(GREENHOUSE_CANDIDATES)} Greenhouse + {len(WORKDAY_CANDIDATES)} Workday candidates")
    print(f"{'='*60}\n")

    validated = []
    failed = []

    # Test Greenhouse (fast, parallel)
    print("--- GREENHOUSE ---")
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = {executor.submit(validate_greenhouse, c): c[0] for c in GREENHOUSE_CANDIDATES}
        for future in as_completed(futures):
            company = futures[future]
            try:
                result = future.result(timeout=15)
                if result:
                    print(f"  ✅ {company}: {result['jobs_found']} jobs → {result['career_url']}")
                    validated.append(result)
                else:
                    print(f"  ❌ {company}: no working token found")
                    failed.append(company)
            except Exception:
                print(f"  ❌ {company}: error")
                failed.append(company)

    print(f"\n--- WORKDAY ---")
    # Test Workday (slower, moderate parallelism)
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(validate_workday, c): c[0] for c in WORKDAY_CANDIDATES}
        for future in as_completed(futures):
            company = futures[future]
            try:
                result = future.result(timeout=30)
                if result:
                    print(f"  ✅ {company}: {result['jobs_found']} jobs → {result['career_url']}")
                    validated.append(result)
                else:
                    print(f"  ❌ {company}: no working URL found")
                    failed.append(company)
            except Exception:
                print(f"  ❌ {company}: error/timeout")
                failed.append(company)

    # Deduplicate by company name (keep first/best)
    seen = set()
    unique = []
    for v in validated:
        if v["company"] not in seen:
            seen.add(v["company"])
            unique.append(v)

    # Sort by jobs found
    unique.sort(key=lambda x: x["jobs_found"], reverse=True)

    print(f"\n{'='*60}")
    print(f"RESULTS: {len(unique)} validated | {len(failed)} failed")
    print(f"{'='*60}\n")

    # Write validated CSV
    output_path = "config/companies_validated.csv"
    fieldnames = ["company", "industry", "region", "country", "priority",
                  "international_hiring", "profile_fit", "salary_band", "ats", "career_url"]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for v in unique:
            row = {k: v[k] for k in fieldnames}
            writer.writerow(row)

    print(f"✅ Validated companies saved to: {output_path}")
    print(f"   Copy this file to config/companies.csv to use it")
    print(f"\n❌ Failed companies ({len(failed)}):")
    for f_name in sorted(set(failed)):
        print(f"   {f_name}")

    # Also save the already-verified ones from current config
    print(f"\n💡 TIP: After validation, also add back the 6 verified Workday URLs")
    print(f"   (AstraZeneca, GSK, Sanofi, Novartis, Danaher, Pfizer)")


if __name__ == "__main__":
    main()
