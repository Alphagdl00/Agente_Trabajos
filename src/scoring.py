def score_job(job: dict) -> int:
    title = (job.get("title") or "").lower()
    location = (job.get("location") or "").lower()
    department = (job.get("department") or "").lower()
    workplace_type = (job.get("workplace_type") or "").lower()
    industry = (job.get("industry") or "").lower()
    priority = (job.get("priority") or "").upper()
    profile_fit = (job.get("profile_fit") or "").lower()
    international_hiring = (job.get("international_hiring") or "").lower()

    score = 0

    # Core finance relevance
    if "finance" in title:
        score += 3
    if "fp&a" in title:
        score += 5
    if "financial planning" in title:
        score += 4
    if "financial analysis" in title:
        score += 3
    if "strategic finance" in title:
        score += 5
    if "corporate finance" in title:
        score += 4
    if "commercial finance" in title:
        score += 4
    if "operations finance" in title:
        score += 3
    if "business finance" in title:
        score += 3
    if "business partner" in title:
        score += 4
    if "finance business partner" in title:
        score += 5
    if "finance systems" in title:
        score += 4
    if "enterprise finance" in title:
        score += 4
    if "finance transformation" in title:
        score += 5
    if "transformation" in title:
        score += 3
    if "it finance" in title:
        score += 5
    if "technology finance" in title:
        score += 5
    if "digital finance" in title:
        score += 4
    if "global finance" in title:
        score += 4
    if "planning analysis" in title:
        score += 3

    # Leadership / seniority
    if "manager" in title:
        score += 2
    if "senior manager" in title:
        score += 3
    if "lead" in title:
        score += 2
    if "principal" in title:
        score += 2

    if "director" in title:
        score += 6
    if "senior director" in title:
        score += 7
    if "head of" in title:
        score += 6
    if "vp" in title or "vice president" in title:
        score += 8

    # Department bonus
    if "finance" in department:
        score += 2
    if "fp&a" in department:
        score += 3
    if "business operations" in department:
        score += 1
    if "corporate functions" in department:
        score += 1

    # Remote / international hints
    remote_terms = [
        "remote",
        "distributed",
        "anywhere",
        "global",
        "international",
        "hybrid",
    ]

    if any(term in location for term in remote_terms):
        score += 3

    if any(term in workplace_type for term in remote_terms):
        score += 3

    # Company metadata bonus
    if priority == "A":
        score += 3
    elif priority == "B":
        score += 2
    elif priority == "C":
        score += 1

    if profile_fit == "high":
        score += 3
    elif profile_fit == "medium":
        score += 2
    elif profile_fit == "low":
        score += 1

    if international_hiring == "high":
        score += 3
    elif international_hiring == "medium":
        score += 2
    elif international_hiring == "low":
        score += 1

    # Industry alignment bonus
    if "pharma" in industry:
        score += 3
    if "medtech" in industry:
        score += 2
    if "life sciences" in industry:
        score += 3
    if "industrial" in industry:
        score += 2
    if "tech" in industry:
        score += 1
    if "fintech" in industry:
        score += 1

    return score