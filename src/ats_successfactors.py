import requests


def scrape_successfactors(company_name: str, career_url: str):
    """
    Scraper básico para SuccessFactors job boards.
    Muchos boards usan JSON endpoint interno.
    """

    jobs = []

    try:

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        }

        r = requests.get(career_url, headers=headers, timeout=12)
        r.raise_for_status()

        # SuccessFactors muchas veces no expone API limpia
        # este scraper es placeholder y puede ampliarse después

        print(f"SuccessFactors board detectado para {company_name}")

    except requests.RequestException as e:
        print(f"SuccessFactors error {career_url}: {e}")

    return jobs