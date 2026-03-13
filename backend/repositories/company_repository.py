from __future__ import annotations

from backend.models.company import Company


def upsert_company(session, payload: dict) -> Company:
    external_key = payload["external_key"]
    company = session.query(Company).filter(Company.external_key == external_key).one_or_none()
    if company is None:
        company = Company(**payload)
        session.add(company)
        session.flush()
        return company

    for key, value in payload.items():
        setattr(company, key, value)
    session.flush()
    return company
