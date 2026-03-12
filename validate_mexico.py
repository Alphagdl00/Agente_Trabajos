"""
Mexico Company Validator — test multinacionales con presencia en México
Run: python validate_mexico.py
"""
import csv
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

GREENHOUSE_MX = [
    ("Kavak", "Tech", "LATAM", "Mexico", "B", ["kavak"]),
    ("Bitso", "Fintech", "LATAM", "Mexico", "B", ["bitso"]),
    ("Clara", "Fintech", "LATAM", "Mexico", "B", ["clara", "clarafinance"]),
    ("Clip", "Fintech", "LATAM", "Mexico", "B", ["clip", "clipmx"]),
    ("Konfio", "Fintech", "LATAM", "Mexico", "B", ["konfio"]),
    ("Stori", "Fintech", "LATAM", "Mexico", "B", ["stori", "storicard"]),
    ("Habi", "Tech", "LATAM", "Mexico", "C", ["habi"]),
    ("Kueski", "Fintech", "LATAM", "Mexico", "B", ["kueski"]),
    ("Nowports", "Tech", "LATAM", "Mexico", "B", ["nowports"]),
    ("Jüsto", "Tech", "LATAM", "Mexico", "C", ["justo", "justomx"]),
    ("Coppel", "Consumer", "LATAM", "Mexico", "B", ["coppel"]),
    ("BBVA Mexico", "Financial Services", "LATAM", "Mexico", "A", ["bbva", "bbvamexico"]),
    ("Banorte", "Financial Services", "LATAM", "Mexico", "A", ["banorte"]),
    ("Televisa", "Consumer", "LATAM", "Mexico", "B", ["televisa", "televisaunivision"]),
    ("Softtek", "Consulting", "LATAM", "Mexico", "B", ["softtek"]),
    ("KIO Networks", "Tech", "LATAM", "Mexico", "B", ["kionetworks", "kio"]),
    ("Wizeline", "Tech", "LATAM", "Mexico", "B", ["wizeline"]),
    ("Ualá", "Fintech", "LATAM", "Mexico", "B", ["uala"]),
    ("Betterfly", "Tech", "LATAM", "Mexico", "C", ["betterfly"]),
    ("Rappi", "Tech", "LATAM", "Colombia", "B", ["rappi"]),
    ("MercadoLibre", "Fintech", "LATAM", "Argentina", "A", ["mercadolibre"]),
    ("dLocal", "Fintech", "LATAM", "Uruguay", "B", ["dlocal"]),
    ("VTEX", "Tech", "LATAM", "Brazil", "B", ["vtex"]),
    ("Nuvemshop", "Tech", "LATAM", "Brazil", "C", ["nuvemshop"]),
    ("Creditas", "Fintech", "LATAM", "Brazil", "B", ["creditas"]),
    ("iFood", "Tech", "LATAM", "Brazil", "B", ["ifood"]),
    ("QuintoAndar", "Tech", "LATAM", "Brazil", "B", ["quintoandar"]),
    ("Oxxo / FEMSA Digital", "Consumer", "LATAM", "Mexico", "A", ["femsa", "oxxo", "femsadigital"]),
    ("Liverpool", "Consumer", "LATAM", "Mexico", "B", ["liverpool"]),
    ("Grupo Bimbo", "Consumer", "LATAM", "Mexico", "A", ["grupobimbo", "bimbo"]),
    ("Nemak", "Industrial", "LATAM", "Mexico", "B", ["nemak"]),
    ("Ternium", "Industrial", "LATAM", "Mexico", "B", ["ternium"]),
    ("HEINEKEN Mexico", "Consumer", "LATAM", "Mexico", "A", ["heineken", "heinekenmx"]),
    ("AB InBev / Grupo Modelo", "Consumer", "LATAM", "Mexico", "A", ["abinbev", "grupomodelo"]),
]

WORKDAY_MX = [
    ("Flex", "Industrial", "LATAM", "Mexico", "B",
     ["https://flextronics.wd1.myworkdayjobs.com/Careers"]),
    ("General Motors Mexico", "Industrial", "LATAM", "Mexico", "A",
     ["https://generalmotors.wd5.myworkdayjobs.com/Careers_GM"]),
    ("Procter & Gamble Mexico", "Consumer", "LATAM", "Mexico", "A",
     ["https://pg.wd5.myworkdayjobs.com/PGCareers"]),
    ("Nestlé Mexico", "Consumer", "LATAM", "Mexico", "A",
     ["https://nestle.wd3.myworkdayjobs.com/External",
      "https://nestle.wd3.myworkdayjobs.com/NestleCareers"]),
    ("Unilever Mexico", "Consumer", "LATAM", "Mexico", "A",
     ["https://unilever.wd3.myworkdayjobs.com/UnileverExternalCareers"]),
    ("PepsiCo Mexico", "Consumer", "LATAM", "Mexico", "A",
     ["https://pepsico.wd1.myworkdayjobs.com/Pepsico"]),
    ("Coca-Cola FEMSA", "Consumer", "LATAM", "Mexico", "A",
     ["https://coke.wd1.myworkdayjobs.com/coca-cola-careers"]),
    ("Mondelez Mexico", "Consumer", "LATAM", "Mexico", "B",
     ["https://mondelez.wd3.myworkdayjobs.com/MDLZ_Careers"]),
    ("Colgate-Palmolive", "Consumer", "LATAM", "Mexico", "B",
     ["https://colgate.wd5.myworkdayjobs.com/ColgateCareers"]),
    ("Nike Mexico", "Consumer", "LATAM", "Mexico", "B",
     ["https://nike.wd1.myworkdayjobs.com/NikeCareers"]),
    ("AB InBev Mexico", "Consumer", "LATAM", "Mexico", "A",
     ["https://abinbev.wd1.myworkdayjobs.com/ABInBev"]),
    ("Baxter Mexico", "Pharma", "LATAM", "Mexico", "B",
     ["https://baxter.wd1.myworkdayjobs.com/Baxter"]),
    ("Medtronic Mexico", "MedTech", "LATAM", "Mexico", "A",
     ["https://medtronic.wd1.myworkdayjobs.com/MedtronicCareers"]),
    ("Johnson & Johnson Mexico", "Pharma", "LATAM", "Mexico", "A",
     ["https://jj.wd5.myworkdayjobs.com/JJ"]),
    ("AstraZeneca Mexico", "Pharma", "LATAM", "Mexico", "A",
     ["https://astrazeneca.wd3.myworkdayjobs.com/Careers"]),
    ("Pfizer Mexico", "Pharma", "LATAM", "Mexico", "A",
     ["https://pfizer.wd1.myworkdayjobs.com/PfizerCareers"]),
    ("Bosch Mexico", "Industrial", "LATAM", "Mexico", "B",
     ["https://bosch.wd3.myworkdayjobs.com/boschglobalcareers"]),
    ("Continental", "Industrial", "LATAM", "Mexico", "B",
     ["https://continental.wd3.myworkdayjobs.com/External",
      "https://continental.wd3.myworkdayjobs.com/Careers"]),
    ("Schneider Electric Mexico", "Industrial", "LATAM", "Mexico", "B",
     ["https://schneiderelectric.wd3.myworkdayjobs.com/External",
      "https://schneiderelectric.wd3.myworkdayjobs.com/SchneiderElectricCareers"]),
    ("Siemens Mexico", "Industrial", "LATAM", "Mexico", "A",
     ["https://siemens.wd3.myworkdayjobs.com/External",
      "https://siemens.wd3.myworkdayjobs.com/Careers"]),
]


def test_greenhouse(token):
    try:
        r = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs", timeout=8)
        if r.status_code == 200:
            return len(r.json().get("jobs", []))
    except:
        pass
    return None


def test_workday(url):
    from urllib.parse import urlparse
    parsed = urlparse(url.rstrip("/"))
    host = parsed.netloc
    parts = [p for p in parsed.path.split("/") if p and p != "en-US"]
    tenant = host.split(".")[0]
    site = parts[-1] if parts else ""
    if not site:
        return None

    api = f"https://{host}/wday/cxs/{tenant}/{site}/jobs"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": f"https://{host}",
        "Referer": url,
        "User-Agent": "Mozilla/5.0",
    }
    try:
        r = requests.post(api, json={"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": ""}, headers=headers, timeout=8)
        if r.status_code == 200:
            return r.json().get("total", 0)
    except:
        pass
    return None


def main():
    print(f"\n{'='*60}")
    print(f"MEXICO & LATAM COMPANY VALIDATION")
    print(f"{'='*60}\n")

    results = []

    print("--- GREENHOUSE ---")
    for company, ind, reg, country, pri, tokens in GREENHOUSE_MX:
        found = False
        for token in tokens:
            count = test_greenhouse(token)
            if count and count > 0:
                print(f"  ✅ {company}: {count} jobs (token: {token})")
                results.append({
                    "company": company, "industry": ind, "region": reg, "country": country,
                    "priority": pri, "international_hiring": "High", "profile_fit": "Medium",
                    "salary_band": "", "ats": "greenhouse",
                    "career_url": f"https://boards.greenhouse.io/{token}",
                })
                found = True
                break
        if not found:
            print(f"  ❌ {company}")

    print("\n--- WORKDAY ---")
    for company, ind, reg, country, pri, urls in WORKDAY_MX:
        found = False
        for url in urls:
            count = test_workday(url)
            if count and count > 0:
                print(f"  ✅ {company}: {count} jobs → {url}")
                results.append({
                    "company": company, "industry": ind, "region": reg, "country": country,
                    "priority": pri, "international_hiring": "High", "profile_fit": "Medium",
                    "salary_band": "", "ats": "workday", "career_url": url,
                })
                found = True
                break
        if not found:
            print(f"  ❌ {company}")

    print(f"\n{'='*60}")
    print(f"VALIDATED: {len(results)} companies")
    print(f"{'='*60}\n")

    # Save
    out = "config/mexico_validated.csv"
    fieldnames = ["company", "industry", "region", "country", "priority",
                  "international_hiring", "profile_fit", "salary_band", "ats", "career_url"]
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow(r)

    print(f"Saved to {out}")
    print(f"To add these to your main list:")
    print(f"  1. Open config/companies.csv")
    print(f"  2. Copy rows from {out} and paste at the bottom")


if __name__ == "__main__":
    main()
