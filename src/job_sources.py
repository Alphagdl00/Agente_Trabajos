import requests


def fetch_greenhouse_jobs(board_token: str):
    """
    Obtiene vacantes públicas desde un job board de Greenhouse.
    """
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"

    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        data = response.json()
        return data.get("jobs", [])
    except requests.RequestException as e:
        print(f"Error consultando Greenhouse para {board_token}: {e}")
        return []


def simplify_greenhouse_jobs(jobs, company_name: str):
    """
    Convierte la respuesta de Greenhouse en una lista simple.
    """
    simplified = []

    for job in jobs:
        simplified.append({
            "company": company_name,
            "title": job.get("title", ""),
            "location": job.get("location", {}).get("name", ""),
            "absolute_url": job.get("absolute_url", ""),
            "updated_at": job.get("updated_at", ""),
            "job_id": job.get("id", "")
        })

    return simplified


def try_multiple_greenhouse_boards(test_boards):
    """
    Prueba varios boards y devuelve el primero que funcione.
    test_boards = [{"company": "...", "token": "..."}]
    """
    for board in test_boards:
        company = board["company"]
        token = board["token"]

        print(f"Probando board Greenhouse: {company} ({token})")
        jobs = fetch_greenhouse_jobs(token)

        if jobs:
            print(f"OK: {company} devolvió {len(jobs)} vacantes.")
            return company, token, jobs

    print("Ningún board Greenhouse de prueba respondió correctamente.")
    return None, None, []