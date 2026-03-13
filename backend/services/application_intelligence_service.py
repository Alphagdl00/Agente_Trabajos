from __future__ import annotations


def _normalize(values: list[str] | None) -> list[str]:
    cleaned = []
    for value in values or []:
        item = " ".join(str(value).split()).strip().lower()
        if item:
            cleaned.append(item)
    return cleaned


def build_skill_gap_summary(user_skills: list[str] | None, job_skills: list[str] | None) -> dict:
    normalized_user = set(_normalize(user_skills))
    normalized_job = set(_normalize(job_skills))

    if not normalized_job:
        return {
            "matched_skills": [],
            "missing_skills": [],
            "coverage_ratio": 0.0,
        }

    matched = sorted(normalized_user.intersection(normalized_job))
    missing = sorted(normalized_job.difference(normalized_user))
    coverage = round(len(matched) / len(normalized_job), 2) if normalized_job else 0.0

    return {
        "matched_skills": matched,
        "missing_skills": missing,
        "coverage_ratio": coverage,
    }


def build_positioning_summary(
    *,
    resume_summary: dict | None,
    active_practices: list[str] | None,
    matches: list[dict] | None,
) -> dict:
    resume_summary = resume_summary or {}
    active_practices = active_practices or []
    matches = matches or []

    strengths: list[str] = []
    gaps: list[str] = []
    checklist: list[str] = []

    years = int(resume_summary.get("years_experience", 0) or 0)
    roles = resume_summary.get("roles", []) or []
    skills = resume_summary.get("skills", []) or []

    if years >= 15:
        strengths.append(f"{years} anos de experiencia ya evidenciados en el CV")
    elif years > 0:
        strengths.append(f"{years} anos de experiencia evidenciados en el CV")

    if roles:
        strengths.append(f"Trayectoria visible en roles como {roles[0]}")

    if active_practices:
        strengths.append(f"Tu perfil ya esta alineado con {', '.join(active_practices[:2])}")

    if skills:
        strengths.append(f"Skills demostradas: {', '.join(skills[:5])}")

    top_match = matches[0] if matches else {}
    missing_skills = top_match.get("missing_skills", []) or []
    matched_skills = top_match.get("matched_skills", []) or []

    for item in missing_skills[:3]:
        gaps.append(f"Si la vacante pide {item}, conviene contextualizarlo con evidencia cercana")

    if not gaps and top_match and not matched_skills:
        gaps.append("La vacante no tiene skills estructuradas suficientes todavia para comparar")

    checklist.append("Resalta el impacto financiero y operativo con metricas reales")
    checklist.append("Usa los titulos exactos de tu experiencia mas cercana en el resumen profesional")
    if missing_skills:
        checklist.append("Explica brevemente como tus skills transferibles cubren las brechas visibles")
    else:
        checklist.append("Prioriza vacantes donde tu evidencia ya cubre la mayoria de skills detectadas")

    return {
        "strengths": strengths[:4],
        "gaps": gaps[:3],
        "checklist": checklist[:4],
    }


def build_interview_talking_points(
    *,
    resume_summary: dict | None,
    match: dict | None,
) -> dict:
    resume_summary = resume_summary or {}
    match = match or {}

    roles = resume_summary.get("roles", []) or []
    skills = resume_summary.get("skills", []) or []
    company = str(match.get("company", "")).strip()
    title = str(match.get("title", "")).strip()
    matched_skills = match.get("matched_skills", []) or []
    missing_skills = match.get("missing_skills", []) or []

    points: list[str] = []
    examples: list[str] = []
    prep: list[str] = []

    if roles:
        points.append(f"Abre conectando tu experiencia mas cercana: {roles[0]}")
    if company and title:
        points.append(f"Explica por que tu trayectoria encaja con {title} en {company}")
    if matched_skills:
        points.append(f"Refuerza skills ya evidenciadas como {', '.join(matched_skills[:3])}")

    if roles:
        examples.append(f"Prepara una historia STAR basada en {roles[0]}")
    if skills:
        examples.append(f"Lleva un ejemplo con impacto medible usando {', '.join(skills[:3])}")
    if company:
        examples.append(f"Relaciona tu experiencia multinacional con el contexto del negocio de {company}")

    prep.append("Cuantifica alcance, presupuesto, equipo o ahorro cuando sea posible")
    prep.append("Usa titulos y responsabilidades exactas del CV, sin inflar seniority")
    if missing_skills:
        prep.append(f"Ten lista una respuesta honesta para cubrir brechas como {', '.join(missing_skills[:2])}")
    else:
        prep.append("Prioriza ejemplos donde ya cubres la mayor parte de las skills detectadas")

    return {
        "points": points[:3],
        "examples": examples[:3],
        "prep": prep[:4],
    }
