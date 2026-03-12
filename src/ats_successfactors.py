# src/ats_successfactors.py

from __future__ import annotations

from src.http_utils import create_session, safe_request


def scrape_successfactors(company_name: str, career_url: str) -> list[dict]:
    """
    Placeholder consistente para SuccessFactors.
    Mantiene la arquitectura estable mientras luego construimos
    un scraper dedicado.
    """
    session = create_session()
    response = safe_request(session, "GET", career_url)

    if response is None:
        print(f"SuccessFactors error {career_url}")
        return []

    print(f"SuccessFactors board detectado para {company_name}")
    return []