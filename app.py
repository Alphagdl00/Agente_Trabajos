from __future__ import annotations

import json
from urllib.error import URLError
from urllib.request import Request, urlopen
from io import BytesIO
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from main import (
    ALL_JOBS_FILE,
    DEFAULT_PROFILE_PRESETS,
    FILTERED_JOBS_FILE,
    GLOBAL_JOBS_FILE,
    NEW_JOBS_TODAY_FILE,
    PRIORITY_JOBS_FILE,
    SENIORITY_LABEL_MAP,
    STRONG_JOBS_FILE,
    ensure_directories,
    load_companies,
    load_run_metadata,
    run_radar,
)
from repositories.jobs_repository import load_latest_run_bundle
from repositories.profile_repository import load_active_profile, save_active_profile

try:
    from backend.core.db import get_session as get_phase1_session
    from backend.repositories.phase1_query_repository import latest_phase1_run, list_phase1_matches
    from backend.repositories.resume_repository import save_resume_parse
    from backend.services.application_intelligence_service import build_interview_talking_points, build_positioning_summary
    from backend.services.resume_parser_service import parse_resume
except Exception:  # pragma: no cover - optional while SQLAlchemy is not installed locally
    get_phase1_session = None
    latest_phase1_run = None
    list_phase1_matches = None
    save_resume_parse = None
    build_interview_talking_points = None
    build_positioning_summary = None
    parse_resume = None

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="North Hound",
    page_icon="🎯",
    layout="wide",
)

ensure_directories()
FEEDBACK_FILE = Path(__file__).resolve().parent / "history" / "job_feedback.csv"
PIPELINE_STATUS_OPTIONS = [
    "new",
    "saved",
    "apply_today",
    "applied",
    "interview",
    "offer",
    "rejected",
    "not_fit",
]

if "ui_language" not in st.session_state:
    st.session_state.ui_language = "es"

PHASE1_API_BASE_URL = "http://127.0.0.1:8000"


def t(key: str, **kwargs) -> str:
    template = TRANSLATIONS.get(st.session_state.ui_language, TRANSLATIONS["es"]).get(key, key)
    return template.format(**kwargs)


def practice_label(practice_key: str) -> str:
    return PRACTICE_LABELS.get(st.session_state.ui_language, PRACTICE_LABELS["es"]).get(practice_key, practice_key)


def practice_from_label(label: str) -> str:
    labels = PRACTICE_LABELS.get(st.session_state.ui_language, PRACTICE_LABELS["es"])
    for key, value in labels.items():
        if value == label:
            return key
    return label


def localized_level_labels() -> list[str]:
    return LEVEL_LABELS.get(st.session_state.ui_language, LEVEL_LABELS["es"])


def internal_to_display_level(level: str) -> str:
    mapping = {
        "Fuerte": t("level_strong"),
        "Medio": t("level_medium"),
        "Bajo": t("level_low"),
    }
    return mapping.get(level, level)


def display_to_internal_level(level: str) -> str:
    reverse = {
        t("level_strong"): "Fuerte",
        t("level_medium"): "Medio",
        t("level_low"): "Bajo",
    }
    return reverse.get(level, level)

TRANSLATIONS = {
    "es": {
        "app_title": "North Hound",
        "app_subtitle": "Selecciona tu práctica y nivel para recalcular el radar según lo que realmente quieres ver.",
        "placeholder_select": "Selecciona opciones",
        "placeholder_choose_practice": "Selecciona una o más prácticas",
        "placeholder_choose_level": "Selecciona uno o más niveles",
        "status_today": "Estado del radar: actualizado hoy",
        "status_last": "Estado del radar: última actualización {date}",
        "status_missing": "No se encontraron resultados procesados. Usa el panel lateral para correr tu primer radar.",
        "phase1_status_title": "Estado de la corrida v2",
        "phase1_status_idle": "Sin corrida activa.",
        "phase1_status_running": "North Hound está procesando la corrida v2.",
        "phase1_status_completed": "La última corrida v2 terminó correctamente.",
        "phase1_status_failed": "La última corrida v2 terminó con error.",
        "phase1_status_unknown": "Estado de la corrida v2 no disponible.",
        "phase1_stage_queued": "En cola",
        "phase1_stage_scrape_and_persist": "Extrayendo y guardando vacantes",
        "phase1_stage_scraped": "Vacantes extraídas",
        "phase1_stage_persisting_companies": "Guardando empresas",
        "phase1_stage_persisting_jobs_and_matches": "Guardando vacantes y recalculando matches",
        "phase1_stage_finalizing_run": "Cerrando corrida",
        "phase1_stage_completed": "Completada",
        "phase1_stage_failed": "Fallida",
        "phase1_stage_unknown": "Sin etapa disponible",
        "phase1_status_detail": "Estado: {status} | Etapa: {stage}",
        "phase1_status_limit": "Alcance: {companies} empresas | {jobs} vacantes máximas",
        "phase1_status_progress": "Progreso: {done}/{total} vacantes procesadas",
        "phase1_status_error": "Error reportado: {error}",
        "phase1_section_title": "North Hound Phase 1",
        "phase1_run_summary": "Run #{run_id} | matches recalculados: {matches} | jobs persistidos: {jobs}",
        "phase1_matches_title": "Matches v2",
        "phase1_matches_empty": "Todavía no hay matches v2 disponibles.",
        "gap_section_title": "Brechas detectadas",
        "gap_none": "No hay brechas de skills visibles todavía.",
        "gap_missing": "Skills por reforzar",
        "gap_matched": "Skills ya evidenciadas",
        "gap_coverage": "Cobertura de skills",
        "positioning_title": "Como posicionarte mejor",
        "positioning_strengths": "Fortalezas a resaltar",
        "positioning_gaps": "Brechas a contextualizar",
        "positioning_checklist": "Checklist de aplicacion",
        "positioning_empty": "Analiza tu CV y genera matches v2 para ver este bloque.",
        "interview_title": "Talking points para entrevista",
        "interview_points": "Mensajes clave",
        "interview_examples": "Historias que conviene preparar",
        "interview_prep": "Preparacion sugerida",
        "interview_empty": "Genera matches v2 para ver talking points por vacante.",
        "tracker_title": "Seguimiento de hoy",
        "tracker_empty": "Todavia no hay aplicaciones o follow-ups guardados.",
        "tracker_due": "Follow-up pendiente",
        "tracker_status": "Estado",
        "tracker_save": "Guardar en seguimiento",
        "tracker_saved": "Vacante guardada en seguimiento.",
        "sidebar_radar": "Filtros del radar",
        "sidebar_explore": "Filtros de exploración",
        "language": "Idioma",
        "language_es": "Español",
        "language_en": "English",
        "practice": "Práctica",
        "target_level": "Nivel objetivo",
        "fast_mode": "Modo rápido",
        "fast_mode_help": "Escanea menos empresas para terminar más rápido.",
        "update_radar": "Actualizar radar",
        "update_spinner": "Actualizando radar según tu práctica y nivel...",
        "update_started": "La corrida v2 se lanzó en segundo plano.",
        "update_busy": "Ya hay una corrida v2 en progreso.",
        "update_error": "No fue posible iniciar la corrida v2 desde la UI.",
        "warning_select_practice": "Selecciona al menos una práctica para correr el radar.",
        "metrics_all_jobs": "Todas",
        "metrics_filtered": "Filtradas",
        "metrics_strong": "Fuertes",
        "metrics_priority": "Prioridad A",
        "metrics_global": "Globales",
        "metrics_new": "Nuevas hoy",
        "practice_terms": "Palabras de la práctica",
        "hero_kicker": "Plan del día",
        "hero_title": "Empieza por vacantes nuevas, luego revisa las más fuertes.",
        "hero_copy": "Estás viendo la práctica <strong>{profiles}</strong> y el nivel <strong>{levels}</strong>.<br>Hoy tienes {new_today} vacantes nuevas y {strong} vacantes fuertes.",
        "onboarding_title": "Empecemos con tu radar",
        "onboarding_copy": "Cuéntame qué quieres ver y te preparo una primera búsqueda más útil desde el inicio.",
        "onboarding_region": "Región preferida",
        "onboarding_country": "País preferido",
        "onboarding_mode": "Modalidad preferida",
        "onboarding_cta": "Guardar y actualizar radar",
        "onboarding_saved": "Tu configuración inicial quedó guardada.",
        "onboarding_edit": "Ajustar onboarding",
        "resume_section": "Perfil profesional",
        "resume_title": "Carga tu CV",
        "resume_copy": "Extraigo solo señales evidenciadas en tu CV para mejorar el perfil. No invento skills ni experiencia.",
        "resume_upload": "Sube tu CV (PDF o TXT)",
        "resume_parse": "Analizar CV",
        "resume_saved": "CV analizado y perfil actualizado.",
        "resume_manage": "Actualizar CV y ver detalle",
        "resume_skills": "Skills detectadas",
        "resume_roles": "Roles detectados",
        "resume_years": "Años de experiencia inferidos",
        "resume_none": "Todavía no hay CV analizado.",
        "resume_parser_unavailable": "El parser de CV no está disponible en este entorno todavía.",
        "resume_file": "Archivo",
        "resume_summary_title": "Resumen de perfil",
        "top10_section": "Top 10 para hoy",
        "top10_title": "Las mejores oportunidades para revisar primero",
        "top10_empty": "Todavía no hay suficientes resultados para construir tu Top 10.",
        "daily_section": "Radar diario",
        "daily_success": "Hoy detecté {count} vacantes nuevas. Empieza aquí.",
        "daily_title": "Shortlist de hoy",
        "daily_empty": "Hoy no hay shortlist nueva.",
        "strong_title": "Apuestas fuertes",
        "strong_empty": "No hay vacantes fuertes para mostrar.",
        "explore_section": "Explorar datos",
        "preset": "Vista",
        "list_level": "Nivel en lista",
        "work_mode": "Modalidad",
        "companies": "Empresas",
        "region": "Región",
        "country": "País",
        "search": "Buscar",
        "explore_hint": "Usa el panel lateral para ajustar filtros y presiona Buscar.",
        "showing_results": "Mostrando {count} vacantes según tus filtros.",
        "filtered_jobs": "Vacantes filtradas",
        "download_list": "Descargar lista",
        "no_download": "Sin datos para descargar.",
        "results_count": "Resultados: {count}",
        "open_job": "Abrir vacante",
        "worth_viewing": "Por qué vale la pena verla",
        "no_extra_signals": "Sin señales adicionales todavía.",
        "no_results_block": "No hay resultados en este bloque.",
        "hyperlink": "Hipervínculo",
        "apply": "Aplicar",
        "all": "Todo",
        "only_new": "Solo nuevas",
        "only_strong": "Solo fuertes",
        "only_remote": "Solo remotas",
        "only_global": "Solo globales",
        "only_priority_a": "Solo prioridad A",
        "level_strong": "Fuerte",
        "level_medium": "Medio",
        "level_low": "Bajo",
        "col_level": "Nivel",
        "col_company": "Empresa",
        "col_title": "Vacante",
        "col_location": "Ubicación",
        "col_mode": "Modalidad",
        "col_priority": "Prioridad",
        "col_why": "Por qué",
        "all_practices": "todas las prácticas",
        "all_levels": "todos los niveles",
        "no_keywords": "No hay palabras clave activas todavía.",
        "no_new_today": "Hoy no se detectaron vacantes nuevas.",
        "link_help": "Abre la vacante directamente",
        "priority_chip": "prioridad {priority}",
        "global_chip": "global",
        "untitled_job": "Sin título",
        "unknown_company": "Empresa",
        "unknown_location": "Ubicación no especificada",
        "seniority_beginner": "Principiante",
        "seniority_intermediate": "Intermedio",
        "seniority_senior": "Senior",
        "seniority_executive": "Ejecutivo",
        "remote": "Remoto",
        "hybrid": "Híbrido",
        "onsite": "Presencial",
        "unknown_mode": "Sin definir",
        "preset_all": "Todo",
        "preset_new": "Solo nuevas",
        "preset_strong": "Solo fuertes",
        "preset_remote": "Solo remotas",
        "preset_global": "Solo globales",
        "preset_priority": "Solo prioridad A",
        "region_latam": "LATAM",
        "region_north_america": "Norteamérica",
        "region_europe": "Europa",
        "region_asia_pacific": "Asia-Pacífico",
    },
    "en": {
        "app_title": "North Hound",
        "app_subtitle": "Choose your practice and level to refresh the radar based on what you actually want to see.",
        "placeholder_select": "Choose options",
        "placeholder_choose_practice": "Choose one or more practices",
        "placeholder_choose_level": "Choose one or more levels",
        "status_today": "Radar status: updated today",
        "status_last": "Radar status: last updated {date}",
        "status_missing": "No processed results were found. Use the left panel to run your first radar.",
        "phase1_status_title": "v2 run status",
        "phase1_status_idle": "No active v2 run.",
        "phase1_status_running": "North Hound is processing the v2 run.",
        "phase1_status_completed": "The latest v2 run finished successfully.",
        "phase1_status_failed": "The latest v2 run finished with an error.",
        "phase1_status_unknown": "v2 run status unavailable.",
        "phase1_stage_queued": "Queued",
        "phase1_stage_scrape_and_persist": "Scraping and persisting jobs",
        "phase1_stage_scraped": "Jobs scraped",
        "phase1_stage_persisting_companies": "Persisting companies",
        "phase1_stage_persisting_jobs_and_matches": "Persisting jobs and recalculating matches",
        "phase1_stage_finalizing_run": "Finalizing run",
        "phase1_stage_completed": "Completed",
        "phase1_stage_failed": "Failed",
        "phase1_stage_unknown": "No stage available",
        "phase1_status_detail": "Status: {status} | Stage: {stage}",
        "phase1_status_limit": "Scope: {companies} companies | {jobs} max jobs",
        "phase1_status_progress": "Progress: {done}/{total} processed jobs",
        "phase1_status_error": "Reported error: {error}",
        "phase1_section_title": "North Hound Phase 1",
        "phase1_run_summary": "Run #{run_id} | recalculated matches: {matches} | persisted jobs: {jobs}",
        "phase1_matches_title": "v2 matches",
        "phase1_matches_empty": "No v2 matches are available yet.",
        "gap_section_title": "Detected gaps",
        "gap_none": "There are no visible skill gaps yet.",
        "gap_missing": "Skills to strengthen",
        "gap_matched": "Skills already evidenced",
        "gap_coverage": "Skill coverage",
        "positioning_title": "How to position yourself better",
        "positioning_strengths": "Strengths to highlight",
        "positioning_gaps": "Gaps to contextualize",
        "positioning_checklist": "Application checklist",
        "positioning_empty": "Analyze your resume and generate v2 matches to see this section.",
        "interview_title": "Interview talking points",
        "interview_points": "Key messages",
        "interview_examples": "Stories worth preparing",
        "interview_prep": "Suggested prep",
        "interview_empty": "Generate v2 matches to see job-specific talking points.",
        "tracker_title": "Today follow-up",
        "tracker_empty": "There are no saved applications or follow-ups yet.",
        "tracker_due": "Follow-up due",
        "tracker_status": "Status",
        "tracker_save": "Save to tracker",
        "tracker_saved": "Role saved to tracker.",
        "sidebar_radar": "Radar Filters",
        "sidebar_explore": "Explore Filters",
        "language": "Language",
        "language_es": "Spanish",
        "language_en": "English",
        "practice": "Practice",
        "target_level": "Target level",
        "fast_mode": "Fast mode",
        "fast_mode_help": "Scan fewer companies to finish faster.",
        "update_radar": "Refresh radar",
        "update_spinner": "Refreshing radar based on your practice and level...",
        "update_started": "The v2 run started in the background.",
        "update_busy": "There is already a v2 run in progress.",
        "update_error": "The UI could not start the v2 run.",
        "warning_select_practice": "Select at least one practice to run the radar.",
        "metrics_all_jobs": "All jobs",
        "metrics_filtered": "Filtered",
        "metrics_strong": "Strong",
        "metrics_priority": "Priority A",
        "metrics_global": "Global",
        "metrics_new": "New today",
        "practice_terms": "Practice keywords",
        "hero_kicker": "Today plan",
        "hero_title": "Start with new roles, then review the strongest ones.",
        "hero_copy": "You are viewing <strong>{profiles}</strong> and level <strong>{levels}</strong>.<br>Today you have {new_today} new openings and {strong} strong openings.",
        "onboarding_title": "Let's set up your radar",
        "onboarding_copy": "Tell me what you want to see and I will prepare a more useful first search from the start.",
        "onboarding_region": "Preferred region",
        "onboarding_country": "Preferred country",
        "onboarding_mode": "Preferred work mode",
        "onboarding_cta": "Save and refresh radar",
        "onboarding_saved": "Your initial setup was saved.",
        "onboarding_edit": "Adjust onboarding",
        "resume_section": "Professional profile",
        "resume_title": "Upload your resume",
        "resume_copy": "I only extract evidence-based signals from your resume to improve the profile. I do not invent skills or experience.",
        "resume_upload": "Upload your resume (PDF or TXT)",
        "resume_parse": "Analyze resume",
        "resume_saved": "Resume analyzed and profile updated.",
        "resume_manage": "Update resume and view details",
        "resume_skills": "Detected skills",
        "resume_roles": "Detected roles",
        "resume_years": "Inferred years of experience",
        "resume_none": "No analyzed resume yet.",
        "resume_parser_unavailable": "The resume parser is not available in this environment yet.",
        "resume_file": "File",
        "resume_summary_title": "Profile summary",
        "top10_section": "Top 10 for today",
        "top10_title": "Best opportunities to review first",
        "top10_empty": "There are not enough results yet to build your Top 10.",
        "daily_section": "Daily radar",
        "daily_success": "Today I found {count} new openings. Start here.",
        "daily_title": "Today shortlist",
        "daily_empty": "There is no new shortlist today.",
        "strong_title": "Strong bets",
        "strong_empty": "There are no strong openings to show.",
        "explore_section": "Explore data",
        "preset": "View",
        "list_level": "List level",
        "work_mode": "Work mode",
        "companies": "Companies",
        "region": "Region",
        "country": "Country",
        "search": "Search",
        "explore_hint": "Use the left panel to adjust filters and press Search.",
        "showing_results": "Showing {count} openings based on your filters.",
        "filtered_jobs": "Filtered openings",
        "download_list": "Download list",
        "no_download": "No data available to download.",
        "results_count": "Results: {count}",
        "open_job": "Open job",
        "worth_viewing": "Why it is worth reviewing",
        "no_extra_signals": "No extra signals yet.",
        "no_results_block": "No results in this section.",
        "hyperlink": "Hyperlink",
        "apply": "Apply",
        "all": "All",
        "only_new": "Only new",
        "only_strong": "Only strong",
        "only_remote": "Only remote",
        "only_global": "Only global",
        "only_priority_a": "Only priority A",
        "level_strong": "Strong",
        "level_medium": "Medium",
        "level_low": "Low",
        "col_level": "Level",
        "col_company": "Company",
        "col_title": "Role",
        "col_location": "Location",
        "col_mode": "Work mode",
        "col_priority": "Priority",
        "col_why": "Why",
        "all_practices": "all practices",
        "all_levels": "all levels",
        "no_keywords": "There are no active keywords yet.",
        "no_new_today": "No new openings were detected today.",
        "link_help": "Open the job directly",
        "priority_chip": "priority {priority}",
        "global_chip": "global",
        "untitled_job": "Untitled role",
        "unknown_company": "Company",
        "unknown_location": "Location not specified",
        "seniority_beginner": "Beginner",
        "seniority_intermediate": "Intermediate",
        "seniority_senior": "Senior",
        "seniority_executive": "Executive",
        "remote": "Remote",
        "hybrid": "Hybrid",
        "onsite": "Onsite",
        "unknown_mode": "Unknown",
        "preset_all": "All",
        "preset_new": "Only new",
        "preset_strong": "Only strong",
        "preset_remote": "Only remote",
        "preset_global": "Only global",
        "preset_priority": "Only priority A",
        "region_latam": "LATAM",
        "region_north_america": "North America",
        "region_europe": "Europe",
        "region_asia_pacific": "Asia-Pacific",
    },
}

PRACTICE_LABELS = {
    "es": {
        "Finance": "Finanzas",
        "Legal": "Legal",
        "Strategy": "Estrategia",
        "Operations": "Operaciones",
        "IT/Data": "IT/Datos",
        "HR": "Recursos Humanos",
    },
    "en": {
        "Finance": "Finance",
        "Legal": "Legal",
        "Strategy": "Strategy",
        "Operations": "Operations",
        "IT/Data": "IT/Data",
        "HR": "HR",
    },
}

LEVEL_LABELS = {
    "es": ["Fuerte", "Medio", "Bajo"],
    "en": ["Strong", "Medium", "Low"],
}

SENIORITY_TRANSLATIONS = {
    "Principiante": "seniority_beginner",
    "Intermedio": "seniority_intermediate",
    "Senior": "seniority_senior",
    "Ejecutivo": "seniority_executive",
}

WORK_MODE_TRANSLATIONS = {
    "remote": "remote",
    "hybrid": "hybrid",
    "onsite": "onsite",
    "unknown": "unknown_mode",
}

PRESET_TRANSLATIONS = {
    "all": "preset_all",
    "new": "preset_new",
    "strong": "preset_strong",
    "remote": "preset_remote",
    "global": "preset_global",
    "priority_a": "preset_priority",
}

REGION_TRANSLATIONS = {
    "LATAM": "region_latam",
    "North America": "region_north_america",
    "Europe": "region_europe",
    "Asia-Pacific": "region_asia_pacific",
}

COUNTRY_TRANSLATIONS = {
    "Mexico": {"es": "México", "en": "Mexico"},
    "US": {"es": "Estados Unidos", "en": "United States"},
    "Canada": {"es": "Canadá", "en": "Canada"},
    "Brazil": {"es": "Brasil", "en": "Brazil"},
    "Argentina": {"es": "Argentina", "en": "Argentina"},
    "Colombia": {"es": "Colombia", "en": "Colombia"},
    "Chile": {"es": "Chile", "en": "Chile"},
    "Portugal": {"es": "Portugal", "en": "Portugal"},
    "Singapore": {"es": "Singapur", "en": "Singapore"},
    "India": {"es": "India", "en": "India"},
    "Turkey": {"es": "Turquía", "en": "Turkey"},
    "Costa Rica": {"es": "Costa Rica", "en": "Costa Rica"},
    "Japan": {"es": "Japón", "en": "Japan"},
    "Egypt": {"es": "Egipto", "en": "Egypt"},
    "South Africa": {"es": "Sudáfrica", "en": "South Africa"},
    "Peru": {"es": "Perú", "en": "Peru"},
    "Spain": {"es": "España", "en": "Spain"},
    "Germany": {"es": "Alemania", "en": "Germany"},
    "Netherlands": {"es": "Países Bajos", "en": "Netherlands"},
    "Switzerland": {"es": "Suiza", "en": "Switzerland"},
    "France": {"es": "Francia", "en": "France"},
    "UK": {"es": "Reino Unido", "en": "United Kingdom"},
    "Ireland": {"es": "Irlanda", "en": "Ireland"},
    "Denmark": {"es": "Dinamarca", "en": "Denmark"},
    "Italy": {"es": "Italia", "en": "Italy"},
    "China": {"es": "China", "en": "China"},
    "Australia": {"es": "Australia", "en": "Australia"},
}


def seniority_to_display(level: str) -> str:
    return t(SENIORITY_TRANSLATIONS.get(level, "")) if level in SENIORITY_TRANSLATIONS else level


def seniority_from_display(level: str) -> str:
    for internal_level, translation_key in SENIORITY_TRANSLATIONS.items():
        if t(translation_key) == level:
            return internal_level
    return level


def work_mode_to_display(work_mode: str) -> str:
    normalized = clean_text(work_mode).lower()
    translation_key = WORK_MODE_TRANSLATIONS.get(normalized)
    return t(translation_key) if translation_key else clean_text(work_mode)


def preset_to_display(preset_key: str) -> str:
    return t(PRESET_TRANSLATIONS.get(preset_key, "preset_all"))


def region_to_display(region: str) -> str:
    return t(REGION_TRANSLATIONS.get(region, "")) if region in REGION_TRANSLATIONS else region


def country_to_display(country: str) -> str:
    normalized = clean_text(country)
    if not normalized:
        return ""
    translations = COUNTRY_TRANSLATIONS.get(normalized)
    if translations:
        return translations.get(st.session_state.ui_language, normalized)
    return normalized


def phase1_status_to_display(status: str) -> str:
    mapping = {
        "idle": t("phase1_status_idle"),
        "running": t("phase1_status_running"),
        "completed": t("phase1_status_completed"),
        "failed": t("phase1_status_failed"),
    }
    return mapping.get(clean_text(status).lower(), t("phase1_status_unknown"))


def phase1_stage_to_display(stage: str) -> str:
    mapping = {
        "queued": t("phase1_stage_queued"),
        "scrape_and_persist": t("phase1_stage_scrape_and_persist"),
        "scraped": t("phase1_stage_scraped"),
        "persisting_companies": t("phase1_stage_persisting_companies"),
        "persisting_jobs_and_matches": t("phase1_stage_persisting_jobs_and_matches"),
        "finalizing_run": t("phase1_stage_finalizing_run"),
        "completed": t("phase1_stage_completed"),
        "failed": t("phase1_stage_failed"),
    }
    return mapping.get(clean_text(stage).lower(), t("phase1_stage_unknown"))

st.markdown(
    """
    <style>
    .hero-note {
        padding: 1rem 1.1rem;
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 18px;
        background: linear-gradient(135deg, rgba(9,20,41,0.92), rgba(18,58,41,0.70));
        margin-bottom: 1rem;
    }
    .hero-kicker {
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #9ec5ff;
        margin-bottom: 0.35rem;
    }
    .hero-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #f8f6ef;
        margin-bottom: 0.35rem;
    }
    .hero-copy {
        color: #c6d1e1;
        font-size: 0.96rem;
    }
    .job-card {
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 18px;
        padding: 1rem;
        background: linear-gradient(180deg, rgba(15,18,26,0.95), rgba(9,12,18,0.98));
        min-height: 260px;
        margin-bottom: 0.9rem;
    }
    .job-card-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #f7f1e6;
        margin-bottom: 0.35rem;
        line-height: 1.35;
    }
    .job-card-company {
        color: #7dd3a8;
        font-weight: 600;
        margin-bottom: 0.6rem;
    }
    .job-card-meta {
        color: #c8d0dc;
        font-size: 0.92rem;
        margin-bottom: 0.75rem;
    }
    .chip-row {
        margin: 0.45rem 0 0.8rem 0;
    }
    .chip {
        display: inline-block;
        padding: 0.2rem 0.55rem;
        border-radius: 999px;
        margin: 0 0.35rem 0.35rem 0;
        font-size: 0.78rem;
        background: rgba(102, 189, 255, 0.14);
        color: #dbeafe;
        border: 1px solid rgba(102, 189, 255, 0.18);
    }
    .reason-list {
        color: #d7dee9;
        font-size: 0.88rem;
        line-height: 1.45;
        margin-bottom: 0.9rem;
    }
    .apply-link a {
        color: #7dd3a8 !important;
        font-weight: 700;
        text-decoration: none;
    }
    .section-label {
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #90a7c3;
        margin-bottom: 0.45rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# HELPERS
# =========================================================
def read_excel_if_exists(path: Path) -> pd.DataFrame:
    if path.exists():
        try:
            return pd.read_excel(path)
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()


def clean_text(value) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split()).strip()


def build_job_key(row: pd.Series) -> str:
    existing = clean_text(row.get("dedupe_key", ""))
    if existing:
        return existing
    parts = [
        clean_text(row.get("url", "")),
        clean_text(row.get("company", "")),
        clean_text(row.get("title", "")),
    ]
    return " | ".join(part.lower() for part in parts if part)


def read_feedback() -> pd.DataFrame:
    if not FEEDBACK_FILE.exists():
        return pd.DataFrame(
            columns=[
                "job_key",
                "status",
                "notes",
                "company",
                "title",
                "location",
                "work_mode",
                "updated_at",
            ]
        )

    try:
        df = pd.read_csv(FEEDBACK_FILE)
    except Exception:
        return pd.DataFrame(
            columns=[
                "job_key",
                "status",
                "notes",
                "company",
                "title",
                "location",
                "work_mode",
                "updated_at",
            ]
        )

    for col in ["job_key", "status", "notes", "company", "title", "location", "work_mode", "updated_at"]:
        if col not in df.columns:
            df[col] = ""

    df = df.fillna("")
    df["job_key"] = df["job_key"].astype(str).map(clean_text)
    df = df[df["job_key"] != ""].copy()
    return df.drop_duplicates(subset=["job_key"], keep="last").reset_index(drop=True)


def merge_feedback(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
    out["job_key"] = out.apply(build_job_key, axis=1)

    feedback_df = read_feedback()
    if feedback_df.empty:
        out["application_status"] = "new"
        out["application_notes"] = ""
        out["status_updated_at"] = ""
        return out

    merged = out.merge(feedback_df, how="left", on="job_key")
    merged["application_status"] = merged["status"].map(clean_text)
    merged["application_status"] = merged["application_status"].replace("", "new")
    merged["application_notes"] = merged["notes"].map(clean_text)
    merged["status_updated_at"] = merged["updated_at"].map(clean_text)
    return merged.drop(columns=["status", "notes", "updated_at"], errors="ignore")


def save_feedback_updates(edited_df: pd.DataFrame) -> None:
    feedback_df = read_feedback()
    current_map = {
        clean_text(row.get("job_key", "")): {
            "job_key": clean_text(row.get("job_key", "")),
            "status": clean_text(row.get("status", "")) or "new",
            "notes": clean_text(row.get("notes", "")),
            "company": clean_text(row.get("company", "")),
            "title": clean_text(row.get("title", "")),
            "location": clean_text(row.get("location", "")),
            "work_mode": clean_text(row.get("work_mode", "")),
            "updated_at": clean_text(row.get("updated_at", "")),
        }
        for _, row in feedback_df.iterrows()
        if clean_text(row.get("job_key", ""))
    }

    timestamp = datetime.now().isoformat(timespec="seconds")
    for _, row in edited_df.iterrows():
        job_key = clean_text(row.get("job_key", ""))
        if not job_key:
            continue

        current_map[job_key] = {
            "job_key": job_key,
            "status": clean_text(row.get("application_status", "")) or "new",
            "notes": clean_text(row.get("application_notes", "")),
            "company": clean_text(row.get("company", "")),
            "title": clean_text(row.get("title", "")),
            "location": clean_text(row.get("location", "")),
            "work_mode": clean_text(row.get("work_mode", "")),
            "updated_at": timestamp,
        }

    pd.DataFrame(current_map.values()).sort_values(by=["status", "updated_at", "job_key"]).to_csv(
        FEEDBACK_FILE,
        index=False,
        encoding="utf-8-sig",
    )


def dataframe_download_button(df: pd.DataFrame, label: str, file_name: str, key: str):
    if df is None or df.empty:
        st.caption(t("no_download"))
        return

    export_df = prepare_export_df(df)
    buffer = BytesIO()

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        export_df.to_excel(writer, index=False, sheet_name="Jobs")
        worksheet = writer.sheets["Jobs"]

        hyperlink_col = None
        for idx, column_name in enumerate(export_df.columns, start=1):
            if column_name == t("hyperlink"):
                hyperlink_col = idx
                break

        if hyperlink_col is not None:
            for row_idx in range(2, len(export_df) + 2):
                cell = worksheet.cell(row=row_idx, column=hyperlink_col)
                url = clean_text(cell.value)
                if url:
                    cell.hyperlink = url
                    cell.style = "Hyperlink"

    buffer.seek(0)
    st.download_button(
        label=label,
        data=buffer.getvalue(),
        file_name=file_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        key=key,
    )


def prepare_display_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = enrich_job_geography(df)
    out["nivel"] = out["score"].map(score_to_display_band) if "score" in out.columns else t("level_low")
    out["por_que"] = out["score_reasons"].map(reason_preview) if "score_reasons" in out.columns else ""
    selected_cols = {
        "nivel": t("col_level"),
        "company": t("col_company"),
        "title": t("col_title"),
        "location": t("col_location"),
        "work_mode": t("col_mode"),
        "priority": t("col_priority"),
        "por_que": t("col_why"),
        "url": t("hyperlink"),
    }

    existing_cols = [col for col in selected_cols if col in out.columns]
    out = out[existing_cols].rename(columns=selected_cols)
    if t("col_mode") in out.columns:
        out[t("col_mode")] = out[t("col_mode")].map(work_mode_to_display)
    return out


def prepare_export_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    # If the dataframe is already formatted for the user-facing table, keep it as-is.
    formatted_cols = {t("col_level"), t("col_company"), t("col_title"), t("col_location"), t("col_mode"), t("col_priority"), t("col_why"), t("hyperlink")}
    if any(col in df.columns for col in formatted_cols):
        export_cols = [col for col in [t("col_level"), t("col_company"), t("col_title"), t("col_location"), t("col_mode"), t("col_priority"), t("col_why"), t("hyperlink")] if col in df.columns]
        return df[export_cols].copy()

    display_df = prepare_display_df(df)
    if display_df.empty:
        return display_df
    return display_df.copy()


def score_to_band(score: object) -> str:
    try:
        value = int(score)
    except Exception:
        return "Bajo"

    if value >= 9:
        return "Fuerte"
    if value >= 6:
        return "Medio"
    return "Bajo"


def score_to_display_band(score: object) -> str:
    return internal_to_display_level(score_to_band(score))


def infer_country_from_location(location: object) -> str:
    normalized = clean_text(location).lower()
    if not normalized:
        return ""

    rules = {
        "mexico": ["mexico", "ciudad de mexico", "mexico city", "monterrey", "guadalajara", "querétaro", "queretaro", "ramos arizpe", "tijuana", "chihuahua"],
        "canada": ["canada", "markham", "toronto", "ontario", "vancouver", "montreal"],
        "brazil": ["brazil", "brasil", "sao paulo"],
        "argentina": ["argentina", "buenos aires"],
        "colombia": ["colombia", "bogota", "medellin"],
        "chile": ["chile", "santiago"],
        "portugal": ["portugal", "lisbon", "porto"],
        "singapore": ["singapore"],
        "india": ["india", "mumbai", "bangalore", "bengaluru", "hyderabad", "chennai", "pune"],
        "turkey": ["turkey", "istanbul"],
        "costa rica": ["costa rica", "san jose costa rica"],
        "japan": ["japan", "tokyo", "osaka"],
        "egypt": ["egypt", "cairo", "egy"],
        "south africa": ["south africa", "johannesburg", "saf"],
        "us": ["united states", "usa", "new york", "california", "texas"],
    }

    for country_name, terms in rules.items():
        if any(term in normalized for term in terms):
            return country_name.title() if country_name != "us" else "US"

    return ""


def infer_region_from_country(country: object) -> str:
    normalized = clean_text(country).lower()
    if not normalized:
        return ""

    if normalized in {"mexico", "brazil", "argentina", "colombia", "chile", "costa rica", "peru"}:
        return "LATAM"
    if normalized in {"us", "canada"}:
        return "North America"
    if normalized in {"portugal", "spain", "germany", "netherlands", "switzerland", "france", "uk", "ireland", "denmark", "italy"}:
        return "Europe"
    if normalized in {"japan", "singapore", "india", "china", "australia", "turkey"}:
        return "Asia-Pacific"
    return ""


def enrich_job_geography(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for required_col in ["region", "country", "location"]:
        if required_col not in out.columns:
            out[required_col] = ""

    out["country"] = out["country"].map(clean_text)
    out["region"] = out["region"].map(clean_text)
    out["location"] = out["location"].map(clean_text)

    inferred_country = out["location"].map(infer_country_from_location)
    out["geo_country"] = inferred_country
    out["geo_region"] = out["geo_country"].map(infer_region_from_country)

    # For display/export, keep best available country/region.
    country_mask = out["geo_country"].ne("")
    out.loc[country_mask, "country"] = out["geo_country"][country_mask]

    region_mask = out["geo_region"].ne("")
    out.loc[region_mask, "region"] = out["geo_region"][region_mask]

    return out


def compact_reasons(raw_value: str) -> list[str]:
    return [clean_text(part) for part in str(raw_value).split("|") if clean_text(part)]


def reason_preview(raw_value: str) -> str:
    reasons = compact_reasons(raw_value)[:2]
    return " • ".join(reasons)


def build_signal_chips(row: pd.Series) -> list[str]:
    chips: list[str] = []
    work_mode = clean_text(row.get("work_mode", ""))
    priority = clean_text(row.get("priority", ""))
    level = score_to_display_band(row.get("score", 0))
    chips.append(level)
    if work_mode and work_mode != "unknown":
        chips.append(work_mode_to_display(work_mode))
    if priority:
        chips.append(t("priority_chip", priority=priority))
    if bool(row.get("global_signal", False)):
        chips.append(t("global_chip"))
    return chips


def filter_explore_view(
    df: pd.DataFrame,
    preset: str,
    levels: list[str],
    work_modes: list[str],
    companies: list[str],
    regions: list[str],
    countries: list[str],
) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = merge_feedback(df)
    for required_col in ["region", "country", "work_mode", "company", "score", "title"]:
        if required_col not in out.columns:
            out[required_col] = ""
    out = enrich_job_geography(out)
    out["nivel"] = out["score"].map(score_to_display_band)

    if preset == "new":
        out = out[out["is_new_today"] == True]
    elif preset == "strong":
        out = out[out["nivel"] == t("level_strong")]
    elif preset == "remote":
        out = out[out["work_mode"].str.lower() == "remote"]
    elif preset == "global":
        out = out[out["global_signal"] == True]
    elif preset == "priority_a":
        out = out[out["priority"].str.upper() == "A"]
    if levels:
        out = out[out["nivel"].isin(levels)]
    if work_modes:
        allowed_work_modes = {item.lower() for item in work_modes}
        out = out[out["work_mode"].str.lower().isin(allowed_work_modes)]
    if companies:
        allowed_companies = {item.lower() for item in companies}
        out = out[out["company"].str.lower().isin(allowed_companies)]
    if regions:
        allowed_regions = {item.lower() for item in regions}
        out = out[out["geo_region"].str.lower().isin(allowed_regions)]
    if countries:
        allowed_countries = {item.lower() for item in countries}
        out = out[out["geo_country"].str.lower().isin(allowed_countries)]

    return out.sort_values(by=["score", "company", "title"], ascending=[False, True, True]).reset_index(drop=True)


def render_focus_cards(
    title: str,
    df: pd.DataFrame,
    empty_message: str,
    *,
    limit: int = 6,
):
    st.subheader(title)

    if df is None or df.empty:
        st.info(empty_message)
        return

    shortlist = df.head(limit).copy()
    columns = st.columns(2)

    for idx, (_, row) in enumerate(shortlist.iterrows()):
        with columns[idx % 2]:
            title_text = clean_text(row.get("title", t("untitled_job")))
            company = clean_text(row.get("company", t("unknown_company")))
            location = clean_text(row.get("location", t("unknown_location")))
            chips = "".join(f"<span class='chip'>{chip}</span>" for chip in build_signal_chips(row))
            reasons = compact_reasons(row.get("score_reasons", ""))[:3]
            reason_items = "".join(f"<li>{reason}</li>" for reason in reasons) or f"<li>{t('no_extra_signals')}</li>"
            url = clean_text(row.get("url", ""))
            apply_link = f"<div class='apply-link'><a href='{url}' target='_blank'>{t('open_job')}</a></div>" if url else ""

            st.markdown(
                f"""
                <div class="job-card">
                    <div class="job-card-title">{title_text}</div>
                    <div class="job-card-company">{company}</div>
                    <div class="job-card-meta">{location}</div>
                    <div class="chip-row">{chips}</div>
                    <div class="section-label">{t("worth_viewing")}</div>
                    <ul class="reason-list">{reason_items}</ul>
                    {apply_link}
                </div>
                """,
                unsafe_allow_html=True,
            )


def build_top_10_for_today(result_payload: dict) -> pd.DataFrame:
    new_jobs = result_payload.get("new_jobs_today", pd.DataFrame())
    strong_jobs = result_payload.get("strong_jobs", pd.DataFrame())
    all_jobs = result_payload.get("all_jobs", pd.DataFrame())

    frames = []
    if new_jobs is not None and not new_jobs.empty:
        new_copy = new_jobs.copy()
        new_copy["_top_source"] = 2
        frames.append(new_copy)
    if strong_jobs is not None and not strong_jobs.empty:
        strong_copy = strong_jobs.copy()
        strong_copy["_top_source"] = 1
        frames.append(strong_copy)
    if all_jobs is not None and not all_jobs.empty:
        all_copy = all_jobs.copy()
        all_copy["_top_source"] = 0
        frames.append(all_copy)

    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    combined["job_key"] = combined.apply(build_job_key, axis=1)
    combined = (
        combined.sort_values(by=["_top_source", "score", "company", "title"], ascending=[False, False, True, True])
        .drop_duplicates(subset=["job_key"], keep="first")
        .head(10)
        .reset_index(drop=True)
    )
    return combined.drop(columns=["_top_source"], errors="ignore")


def load_phase1_matches(limit: int | None = 6) -> tuple[pd.DataFrame, dict]:
    if get_phase1_session is None or list_phase1_matches is None or latest_phase1_run is None:
        return pd.DataFrame(), {}

    try:
        with get_phase1_session() as session:
            if session is None:
                return pd.DataFrame(), {}
            items = list_phase1_matches(session, limit=limit)
            run_info = latest_phase1_run(session) or {}
    except Exception:
        return pd.DataFrame(), {}

    if not items:
        return pd.DataFrame(), run_info

    df = pd.DataFrame(items)
    if "total_score" in df.columns:
        df["score"] = pd.to_numeric(df["total_score"], errors="coerce").fillna(0)
    if "explanation" in df.columns:
        df["score_reasons"] = df["explanation"]
    if "location" not in df.columns:
        df["location"] = ""
    if "global_signal" not in df.columns:
        df["global_signal"] = False
    if "is_new_today" not in df.columns:
        df["is_new_today"] = False
    if "has_keyword_match" not in df.columns:
        df["has_keyword_match"] = df.get("score", pd.Series(dtype=float)).fillna(0).gt(0)
    if "posted_date" not in df.columns:
        df["posted_date"] = ""
    return df, run_info


def load_phase1_ingest_status() -> dict:
    try:
        with urlopen(f"{PHASE1_API_BASE_URL}/phase1/ingest/status", timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
            item = payload.get("item")
            return item if isinstance(item, dict) else {}
    except (URLError, TimeoutError, ValueError, OSError):
        return {}


def start_phase1_ingest_from_ui(profile_payload: dict, *, fast_mode: bool) -> dict:
    query = "fast=true" if fast_mode else "fast=false&company_limit=12&max_jobs=400"
    request = Request(
        url=f"{PHASE1_API_BASE_URL}/phase1/ingest/start?{query}",
        data=json.dumps(profile_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def save_application_from_ui(job_id: int, *, status: str, notes: str = "", reminder_days: int | None = None) -> dict:
    request = Request(
        url=f"{PHASE1_API_BASE_URL}/phase1/applications",
        data=json.dumps(
            {
                "job_id": job_id,
                "status": status,
                "notes": notes,
                "reminder_days": reminder_days,
            }
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def load_phase1_applications(*, due_only: bool = False, limit: int = 20) -> pd.DataFrame:
    try:
        with urlopen(f"{PHASE1_API_BASE_URL}/phase1/applications?due_only={'true' if due_only else 'false'}&limit={limit}", timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))
            items = payload.get("items", [])
            return pd.DataFrame(items)
    except (URLError, TimeoutError, ValueError, OSError):
        return pd.DataFrame()


def apply_resume_parse(uploaded_file, current_profile: dict) -> dict | None:
    if parse_resume is None or uploaded_file is None:
        return None

    file_bytes = uploaded_file.getvalue()
    parsed = parse_resume(uploaded_file.name, file_bytes)

    updated_profile = dict(current_profile or {})
    updated_profile["skills"] = parsed.get("skills", [])
    updated_profile["years_experience"] = parsed.get("years_experience", 0)
    updated_profile["resume_summary"] = {
        "file_name": parsed.get("file_name", ""),
        "email": parsed.get("email", ""),
        "linkedin": parsed.get("linkedin", ""),
        "phone": parsed.get("phone", ""),
        "roles": parsed.get("roles", []),
        "skills": [item.get("name", "") for item in parsed.get("skills", [])],
        "years_experience": parsed.get("years_experience", 0),
    }
    updated_profile["keywords"] = list(
        dict.fromkeys(
            [
                *[item.get("name", "") for item in parsed.get("skills", []) if item.get("name", "")],
                *(updated_profile.get("keywords", []) or []),
            ]
        )
    )
    save_active_profile(updated_profile)

    if get_phase1_session is not None and save_resume_parse is not None:
        try:
            with get_phase1_session() as session:
                if session is not None:
                    save_resume_parse(
                        session,
                        email=updated_profile.get("email", "demo@northhound.local"),
                        full_name=updated_profile.get("full_name", "North Hound Demo User"),
                        parsed_resume=parsed,
                    )
        except Exception:
            pass

    st.session_state.active_profile_preferences = load_active_profile()
    return parsed


def render_jobs_table(
    title: str,
    df: pd.DataFrame,
    csv_name: str,
    table_key: str,
    height: int = 520,
):
    st.subheader(title)

    if df is None or df.empty:
        st.info(t("no_results_block"))
        return

    if "application_status" in df.columns:
        display_df = prepare_display_df(df)
    else:
        display_df = prepare_display_df(merge_feedback(df))

    st.caption(t("results_count", count=len(display_df)))

    column_config = {}
    hyperlink_col = t("hyperlink")
    if hyperlink_col in display_df.columns:
        column_config[hyperlink_col] = st.column_config.LinkColumn(
            hyperlink_col,
            help=t("link_help"),
            display_text=t("apply"),
        )

    st.dataframe(
        display_df,
        use_container_width=True,
        height=height,
        column_config=column_config,
        key=f"dataframe_{table_key}",
    )

    dataframe_download_button(
        display_df,
        t("download_list"),
        csv_name,
        key=f"download_{table_key}",
    )


def render_skill_gap_cards(df: pd.DataFrame, limit: int = 3) -> None:
    st.markdown(f"## {t('gap_section_title')}")
    if df is None or df.empty or "missing_skills" not in df.columns:
        st.info(t("gap_none"))
        return

    candidates = df.copy()
    candidates["missing_count"] = candidates["missing_skills"].map(lambda values: len(values) if isinstance(values, list) else 0)
    candidates = candidates[candidates["missing_count"] > 0].sort_values(
        by=["missing_count", "score"],
        ascending=[False, False],
    ).head(limit)

    if candidates.empty:
        st.info(t("gap_none"))
        return

    cols = st.columns(min(limit, len(candidates)))
    for idx, (_, row) in enumerate(candidates.iterrows()):
        with cols[idx]:
            st.markdown(f"**{clean_text(row.get('title', '')) or t('untitled_job')}**")
            st.caption(clean_text(row.get("company", "")) or t("unknown_company"))
            st.write(f"**{t('gap_coverage')}:** {int(float(row.get('skill_coverage_ratio', 0) or 0) * 100)}%")
            st.write(f"**{t('gap_missing')}:** {', '.join((row.get('missing_skills') or [])[:6])}")
            matched = row.get("matched_skills") or []
            if matched:
                st.write(f"**{t('gap_matched')}:** {', '.join(matched[:6])}")


def render_positioning_summary(resume_summary: dict, active_practices: list[str], matches_df: pd.DataFrame) -> None:
    st.markdown(f"## {t('positioning_title')}")
    if build_positioning_summary is None or not resume_summary or matches_df is None or matches_df.empty:
        st.info(t("positioning_empty"))
        return

    summary = build_positioning_summary(
        resume_summary=resume_summary,
        active_practices=active_practices,
        matches=matches_df.head(5).to_dict(orient="records"),
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.caption(t("positioning_strengths"))
        for item in summary.get("strengths", []):
            st.write(f"- {item}")
    with c2:
        st.caption(t("positioning_gaps"))
        for item in summary.get("gaps", []):
            st.write(f"- {item}")
    with c3:
        st.caption(t("positioning_checklist"))
        for item in summary.get("checklist", []):
            st.write(f"- {item}")


def render_interview_talking_points(resume_summary: dict, matches_df: pd.DataFrame) -> None:
    st.markdown(f"## {t('interview_title')}")
    if build_interview_talking_points is None or not resume_summary or matches_df is None or matches_df.empty:
        st.info(t("interview_empty"))
        return

    top_match = matches_df.head(1).to_dict(orient="records")[0]
    summary = build_interview_talking_points(
        resume_summary=resume_summary,
        match=top_match,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.caption(t("interview_points"))
        for item in summary.get("points", []):
            st.write(f"- {item}")
    with c2:
        st.caption(t("interview_examples"))
        for item in summary.get("examples", []):
            st.write(f"- {item}")
    with c3:
        st.caption(t("interview_prep"))
        for item in summary.get("prep", []):
            st.write(f"- {item}")


def render_tracker_section(matches_df: pd.DataFrame) -> None:
    st.markdown(f"## {t('tracker_title')}")
    due_df = load_phase1_applications(due_only=True, limit=10)
    if due_df is not None and not due_df.empty:
        for _, row in due_df.head(5).iterrows():
            st.write(
                f"- **{clean_text(row.get('title', ''))}** · {clean_text(row.get('company', ''))} "
                f"· {t('tracker_due')}: {clean_text(row.get('reminder_due_at', ''))}"
            )
    else:
        st.info(t("tracker_empty"))

    if matches_df is None or matches_df.empty:
        return

    top_match = matches_df.head(1).to_dict(orient="records")[0]
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        st.caption(clean_text(top_match.get("title", "")) or t("untitled_job"))
        st.write(clean_text(top_match.get("company", "")) or t("unknown_company"))
    with c2:
        selected_status = st.selectbox(
            t("tracker_status"),
            options=["saved", "apply_today", "applied", "interview", "rejected"],
            key="tracker_status_select",
        )
    with c3:
        if st.button(t("tracker_save"), key="tracker_save_button", use_container_width=True):
            response = save_application_from_ui(
                int(top_match.get("job_id", 0) or 0),
                status=selected_status,
                reminder_days=5 if selected_status in {"applied", "interview"} else None,
            )
            if response.get("status") == "ok":
                st.success(t("tracker_saved"))
                st.rerun()


def render_pipeline_editor(df: pd.DataFrame, table_key: str):
    st.subheader("Pipeline de aplicación")

    if df is None or df.empty:
        st.info("No hay vacantes disponibles para gestionar.")
        return

    pipeline_df = merge_feedback(df)
    editor_cols = [
        "job_key",
        "application_status",
        "application_notes",
        "score",
        "company",
        "title",
        "location",
        "work_mode",
        "score_reasons",
        "url",
    ]
    available_cols = [col for col in editor_cols if col in pipeline_df.columns]
    editable_df = pipeline_df[available_cols].copy()

    edited_df = st.data_editor(
        editable_df,
        use_container_width=True,
        hide_index=True,
        height=520,
        key=f"pipeline_editor_{table_key}",
        column_config={
            "job_key": st.column_config.TextColumn("job_key", disabled=True),
            "application_status": st.column_config.SelectboxColumn(
                "status",
                options=PIPELINE_STATUS_OPTIONS,
                required=True,
            ),
            "application_notes": st.column_config.TextColumn("notes"),
            "url": st.column_config.LinkColumn(
                "Apply link",
                display_text="Aplicar",
            ),
        },
        disabled=["job_key", "score", "company", "title", "location", "work_mode", "score_reasons", "url"],
    )

    if st.button("Guardar cambios del pipeline", key=f"save_pipeline_{table_key}", use_container_width=True):
        save_feedback_updates(edited_df)
        st.success("Pipeline actualizado.")


def load_result_from_files() -> dict:
    all_jobs = read_excel_if_exists(ALL_JOBS_FILE)
    filtered_jobs = read_excel_if_exists(FILTERED_JOBS_FILE)
    strong_jobs = read_excel_if_exists(STRONG_JOBS_FILE)
    priority_jobs = read_excel_if_exists(PRIORITY_JOBS_FILE)
    global_jobs = read_excel_if_exists(GLOBAL_JOBS_FILE)
    new_jobs_today = read_excel_if_exists(NEW_JOBS_TODAY_FILE)

    return {
        "all_jobs": all_jobs,
        "filtered_jobs": filtered_jobs,
        "strong_jobs": strong_jobs,
        "priority_jobs": priority_jobs,
        "global_jobs": global_jobs,
        "new_jobs_today": new_jobs_today,
        "summary": {
            "all_jobs": len(all_jobs),
            "filtered": len(filtered_jobs),
            "strong": len(strong_jobs),
            "priority": len(priority_jobs),
            "global": len(global_jobs),
            "new_today": len(new_jobs_today),
            "keywords_used": [],
        },
    }


def load_result_from_storage() -> tuple[dict, dict]:
    db_bundle = load_latest_run_bundle()
    if db_bundle:
        return db_bundle["result"], db_bundle["meta"]
    return load_result_from_files(), load_run_metadata()


def apply_radar_preferences(
    profiles: list[str],
    seniority_levels: list[str],
    fast_mode: bool,
    preferred_regions: list[str],
    preferred_countries: list[str],
    preferred_work_modes: list[str],
    preferred_companies: list[str],
) -> tuple[dict, dict, dict, dict]:
    save_active_profile(
        {
            "display_name": "Default",
            "practices": profiles,
            "seniority_levels": seniority_levels,
            "preferred_regions": preferred_regions,
            "preferred_countries": preferred_countries,
            "preferred_work_modes": preferred_work_modes,
            "preferred_companies": preferred_companies,
            "keywords": [],
        }
    )
    live_profile = load_active_profile()
    api_response: dict = {}
    try:
        api_response = start_phase1_ingest_from_ui(live_profile, fast_mode=fast_mode)
    except Exception:
        api_response = {"status": "error", "started": False}

    live_result, live_meta = load_result_from_storage()
    live_meta["profile_name"] = profiles
    live_meta["selected_seniority"] = seniority_levels
    live_meta["fast_mode"] = fast_mode
    st.session_state.active_profile_preferences = live_profile
    st.session_state.active_result = live_result
    st.session_state.active_meta = live_meta
    return live_result, live_meta, live_profile, api_response


# =========================================================
# LOAD
# =========================================================
stored_result, stored_meta = load_result_from_storage()

if "active_result" not in st.session_state:
    st.session_state.active_result = stored_result
if "active_meta" not in st.session_state:
    st.session_state.active_meta = stored_meta
if "active_profile_preferences" not in st.session_state:
    st.session_state.active_profile_preferences = load_active_profile()

result = st.session_state.active_result
meta = st.session_state.active_meta
profile_preferences = st.session_state.active_profile_preferences
companies_catalog = load_companies()

last_run_ts = meta.get("last_run_timestamp", "")
last_run_date = meta.get("last_run_date", "")
active_profiles = profile_preferences.get("practices", [])
if isinstance(active_profiles, str):
    active_profiles = [active_profiles]
active_profiles = [item for item in active_profiles if item in DEFAULT_PROFILE_PRESETS]
selected_seniority_labels = [item for item in profile_preferences.get("seniority_levels", []) if item in SENIORITY_LABEL_MAP.values()]
active_fast_mode = bool(meta.get("fast_mode", False))
language_options = ["es", "en"]

# =========================================================
# HEADER
# =========================================================
st.title(t("app_title"))
st.caption(t("app_subtitle"))

seniority_options = list(SENIORITY_LABEL_MAP.values())
seniority_display_options = [seniority_to_display(item) for item in seniority_options]
region_options = sorted([item for item in companies_catalog["region"].dropna().astype(str).unique().tolist() if clean_text(item)])
country_options = sorted([item for item in companies_catalog["country"].dropna().astype(str).unique().tolist() if clean_text(item)])

if last_run_date == datetime.now().strftime("%Y-%m-%d"):
    st.caption(t("status_today"))
elif last_run_date:
    st.caption(t("status_last", date=last_run_date))
else:
    st.warning(t("status_missing"))

phase1_ingest_status = load_phase1_ingest_status()
if phase1_ingest_status:
    status_value = clean_text(phase1_ingest_status.get("status", "")).lower()
    stage_value = clean_text(phase1_ingest_status.get("stage", ""))
    status_message = phase1_status_to_display(status_value)
    if status_value == "running":
        st.info(status_message)
    elif status_value == "completed":
        st.success(status_message)
    elif status_value == "failed":
        st.error(status_message)
    else:
        st.caption(status_message)

    st.caption(
        t(
            "phase1_status_detail",
            status=status_value or "unknown",
            stage=phase1_stage_to_display(stage_value),
        )
    )

    company_limit_value = phase1_ingest_status.get("company_limit")
    max_jobs_value = phase1_ingest_status.get("max_jobs")
    if company_limit_value or max_jobs_value:
        st.caption(
            t(
                "phase1_status_limit",
                companies=company_limit_value or "-",
                jobs=max_jobs_value or "-",
            )
        )

    deduped_jobs_value = int(phase1_ingest_status.get("deduped_jobs", 0) or 0)
    processed_jobs_value = int(phase1_ingest_status.get("processed_jobs", 0) or 0)
    if deduped_jobs_value > 0:
        st.caption(
            t(
                "phase1_status_progress",
                done=processed_jobs_value,
                total=deduped_jobs_value,
            )
        )

    if phase1_ingest_status.get("error"):
        st.caption(t("phase1_status_error", error=phase1_ingest_status["error"]))

with st.sidebar:
    selected_language = st.selectbox(
        t("language"),
        options=language_options,
        index=language_options.index(st.session_state.ui_language),
        format_func=lambda code: t(f"language_{code}"),
    )
    if selected_language != st.session_state.ui_language:
        st.session_state.ui_language = selected_language
        st.rerun()

    st.header(t("sidebar_radar"))
    with st.form("sidebar_radar_controls"):
        practice_labels = [practice_label(item) for item in DEFAULT_PROFILE_PRESETS.keys()]
        chosen_profiles = st.multiselect(
            t("practice"),
            practice_labels,
            default=[],
            placeholder=t("placeholder_choose_practice"),
        )
        chosen_seniority_display = st.multiselect(
            t("target_level"),
            seniority_display_options,
            default=[],
            placeholder=t("placeholder_choose_level"),
        )
        chosen_fast_mode = st.checkbox(t("fast_mode"), value=False, help=t("fast_mode_help"))
        recalc_submitted = st.form_submit_button(t("update_radar"), use_container_width=True)

if recalc_submitted:
    internal_profiles = [practice_from_label(item) for item in chosen_profiles]
    chosen_seniority = [seniority_from_display(item) for item in chosen_seniority_display]
    if not internal_profiles:
        st.warning(t("warning_select_practice"))
    else:
        with st.spinner(t("update_spinner")):
            live_result, live_meta, live_profile, api_response = apply_radar_preferences(
                profiles=internal_profiles,
                seniority_levels=chosen_seniority,
                fast_mode=chosen_fast_mode,
                preferred_regions=profile_preferences.get("preferred_regions", []),
                preferred_countries=profile_preferences.get("preferred_countries", []),
                preferred_work_modes=profile_preferences.get("preferred_work_modes", []),
                preferred_companies=profile_preferences.get("preferred_companies", []),
            )
            result = live_result
            meta = live_meta
            profile_preferences = live_profile
            last_run_ts = meta.get("last_run_timestamp", "")
            last_run_date = meta.get("last_run_date", "")
            active_profiles = internal_profiles
            selected_seniority_labels = chosen_seniority
            active_fast_mode = chosen_fast_mode
            if api_response.get("status") == "accepted":
                st.success(t("update_started"))
            elif api_response.get("status") == "busy":
                st.info(t("update_busy"))
            else:
                st.warning(t("update_error"))

# =========================================================
# METRICS
# =========================================================
summary = result.get("summary", {})

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric(t("metrics_all_jobs"), summary.get("all_jobs", 0))
m2.metric(t("metrics_filtered"), summary.get("filtered", 0))
m3.metric(t("metrics_strong"), summary.get("strong", 0))
m4.metric(t("metrics_priority"), summary.get("priority", 0))
m5.metric(t("metrics_global"), summary.get("global", 0))
m6.metric(t("metrics_new"), summary.get("new_today", 0))

with st.expander(t("practice_terms"), expanded=False):
    combined_terms: list[str] = []
    for profile_name in active_profiles:
        combined_terms.extend(DEFAULT_PROFILE_PRESETS.get(profile_name, []))
    deduped_terms = ", ".join(list(dict.fromkeys(combined_terms)))
    st.write(deduped_terms or t("no_keywords"))

show_onboarding = not active_profiles and not selected_seniority_labels
with st.expander(t("onboarding_edit"), expanded=show_onboarding):
    st.markdown(f"### {t('onboarding_title')}")
    st.caption(t("onboarding_copy"))
    onboarding_work_mode_options = ["remote", "hybrid", "onsite"]
    onboarding_practice_labels = [practice_label(item) for item in DEFAULT_PROFILE_PRESETS.keys()]
    onboarding_default_practices = [practice_label(item) for item in active_profiles]
    onboarding_default_seniority = [seniority_to_display(item) for item in selected_seniority_labels]
    onboarding_default_regions = [item for item in profile_preferences.get("preferred_regions", []) if item in region_options]
    onboarding_default_countries = [item for item in profile_preferences.get("preferred_countries", []) if item in country_options]
    onboarding_default_modes = [item for item in profile_preferences.get("preferred_work_modes", []) if item in onboarding_work_mode_options]

    with st.form("onboarding_form"):
        c1, c2 = st.columns(2)
        with c1:
            onboarding_profiles = st.multiselect(
                t("practice"),
                onboarding_practice_labels,
                default=onboarding_default_practices,
                placeholder=t("placeholder_choose_practice"),
            )
            onboarding_seniority_display = st.multiselect(
                t("target_level"),
                seniority_display_options,
                default=onboarding_default_seniority,
                placeholder=t("placeholder_choose_level"),
            )
        with c2:
            onboarding_regions = st.multiselect(
                t("onboarding_region"),
                region_options,
                default=onboarding_default_regions,
                placeholder=t("placeholder_select"),
                format_func=region_to_display,
            )
            onboarding_countries = st.multiselect(
                t("onboarding_country"),
                country_options,
                default=onboarding_default_countries,
                placeholder=t("placeholder_select"),
                format_func=country_to_display,
            )
        onboarding_work_modes_display = st.multiselect(
            t("onboarding_mode"),
            [work_mode_to_display(item) for item in onboarding_work_mode_options],
            default=[work_mode_to_display(item) for item in onboarding_default_modes],
            placeholder=t("placeholder_select"),
        )
        onboarding_fast_mode = st.checkbox(t("fast_mode"), value=active_fast_mode, help=t("fast_mode_help"))
        onboarding_submitted = st.form_submit_button(t("onboarding_cta"), use_container_width=True)

    if onboarding_submitted:
        internal_profiles = [practice_from_label(item) for item in onboarding_profiles]
        internal_seniority = [seniority_from_display(item) for item in onboarding_seniority_display]
        internal_work_modes = [
            work_mode.lower()
            for work_mode in onboarding_work_mode_options
            if work_mode_to_display(work_mode) in onboarding_work_modes_display
        ]
        if not internal_profiles:
            st.warning(t("warning_select_practice"))
        else:
            with st.spinner(t("update_spinner")):
                live_result, live_meta, live_profile, api_response = apply_radar_preferences(
                    profiles=internal_profiles,
                    seniority_levels=internal_seniority,
                    fast_mode=onboarding_fast_mode,
                    preferred_regions=onboarding_regions,
                    preferred_countries=onboarding_countries,
                    preferred_work_modes=internal_work_modes,
                    preferred_companies=profile_preferences.get("preferred_companies", []),
                )
                st.success(t("onboarding_saved"))
                result = live_result
                meta = live_meta
                profile_preferences = live_profile
                last_run_ts = meta.get("last_run_timestamp", "")
                last_run_date = meta.get("last_run_date", "")
                active_profiles = internal_profiles
                selected_seniority_labels = internal_seniority
                active_fast_mode = onboarding_fast_mode
                if api_response.get("status") == "accepted":
                    st.success(t("update_started"))
                elif api_response.get("status") == "busy":
                    st.info(t("update_busy"))
                else:
                    st.warning(t("update_error"))

st.markdown(f"## {t('resume_section')}")
resume_summary = profile_preferences.get("resume_summary", {}) or {}
if resume_summary:
    st.caption(t("resume_summary_title"))
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(t("resume_years"), resume_summary.get("years_experience", 0))
    c2.write(f"**Email:** {resume_summary.get('email', '-') or '-'}")
    c3.write(f"**LinkedIn:** {resume_summary.get('linkedin', '-') or '-'}")
    c4.write(f"**{t('resume_file')}:** {resume_summary.get('file_name', '-') or '-'}")
    st.write(f"**{t('resume_roles')}:** {', '.join(resume_summary.get('roles', [])[:3]) or '-'}")
    st.write(f"**{t('resume_skills')}:** {', '.join(resume_summary.get('skills', [])[:8]) or '-'}")
else:
    st.info(t("resume_none"))

with st.expander(t("resume_manage"), expanded=not bool(resume_summary)):
    st.caption(t("resume_copy"))
    uploaded_resume = st.file_uploader(
        t("resume_upload"),
        type=["pdf", "txt"],
        key="resume_uploader",
    )
    if uploaded_resume is not None:
        if parse_resume is None:
            st.warning(t("resume_parser_unavailable"))
        elif st.button(t("resume_parse"), key="resume_parse_button", use_container_width=False):
            parsed_resume = apply_resume_parse(uploaded_resume, profile_preferences)
            if parsed_resume is not None:
                profile_preferences = st.session_state.active_profile_preferences
                resume_summary = profile_preferences.get("resume_summary", {}) or {}
                st.success(t("resume_saved"))
                st.rerun()

display_profiles = ", ".join(practice_label(item) for item in active_profiles) if active_profiles else t("all_practices")
display_levels = ", ".join(seniority_to_display(item) for item in selected_seniority_labels) if selected_seniority_labels else t("all_levels")
hero_copy = t(
    "hero_copy",
    profiles=display_profiles,
    levels=display_levels,
    new_today=summary.get("new_today", 0),
    strong=summary.get("strong", 0),
)

st.markdown(
    f"""
    <div class="hero-note">
        <div class="hero-kicker">{t("hero_kicker")}</div>
        <div class="hero-title">{t("hero_title")}</div>
        <div class="hero-copy">
            {hero_copy}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

phase1_matches_df, phase1_run_info = load_phase1_matches(limit=None)
phase1_available = phase1_matches_df is not None and not phase1_matches_df.empty

top_10_df = phase1_matches_df.head(10).copy() if phase1_available else build_top_10_for_today(result)
st.markdown(f"## {t('top10_section')}")
render_focus_cards(
    t("top10_title"),
    top_10_df,
    t("top10_empty"),
    limit=10,
)

if phase1_available:
    st.markdown(f"## {t('phase1_section_title')}")
    if phase1_run_info:
        st.caption(
            t(
                "phase1_run_summary",
                run_id=phase1_run_info.get("run_id", ""),
                matches=phase1_run_info.get("recalculated_matches", 0),
                jobs=phase1_run_info.get("persisted_jobs", 0),
            )
        )
    render_focus_cards(
        t("phase1_matches_title"),
        phase1_matches_df.head(6),
        t("phase1_matches_empty"),
        limit=6,
    )
    render_positioning_summary(resume_summary, active_profiles, phase1_matches_df)
    render_interview_talking_points(resume_summary, phase1_matches_df)
    render_tracker_section(phase1_matches_df)
    render_skill_gap_cards(phase1_matches_df, limit=3)

# =========================================================
# DAILY FOCUS
# =========================================================
new_jobs_df = result.get("new_jobs_today", pd.DataFrame())

st.markdown(f"## {t('daily_section')}")
if new_jobs_df is not None and not new_jobs_df.empty:
    st.success(t("daily_success", count=len(new_jobs_df)))
    render_focus_cards(
        t("daily_title"),
        new_jobs_df,
        t("daily_empty"),
        limit=6,
    )
else:
    st.warning(t("no_new_today"))

strong_jobs_df = phase1_matches_df[phase1_matches_df["score"] >= 75].copy() if phase1_available else result.get("strong_jobs", pd.DataFrame())
render_focus_cards(
    t("strong_title"),
    strong_jobs_df,
    t("strong_empty"),
    limit=4,
)

st.markdown(f"## {t('explore_section')}")
explore_base_df = phase1_matches_df.copy() if phase1_available else result.get("all_jobs", pd.DataFrame())
explore_with_feedback = merge_feedback(explore_base_df)

preset_options = ["all", "new", "strong", "remote", "global", "priority_a"]
work_mode_options = sorted([item for item in explore_with_feedback.get("work_mode", pd.Series(dtype=str)).fillna("").astype(str).unique().tolist() if item and item != "unknown"])
top_companies = (
    explore_with_feedback.get("company", pd.Series(dtype=str))
    .fillna("")
    .astype(str)
    .value_counts()
    .head(20)
    .index
    .tolist()
)

with st.sidebar:
    st.divider()
    st.subheader(t("sidebar_explore"))
    with st.form("sidebar_explore_filters"):
        selected_preset = st.selectbox(
            t("preset"),
            preset_options,
            index=0,
            format_func=preset_to_display,
        )
        selected_level_display = st.multiselect(
            t("list_level"),
            localized_level_labels(),
            default=[],
            placeholder=t("placeholder_select"),
        )
        selected_work_mode_display = st.multiselect(
            t("work_mode"),
            [work_mode_to_display(item) for item in work_mode_options],
            default=[],
            placeholder=t("placeholder_select"),
        )
        selected_companies = st.multiselect(
            t("companies"),
            top_companies,
            default=[],
            placeholder=t("placeholder_select"),
        )
        selected_regions = st.multiselect(
            t("region"),
            region_options,
            default=[],
            placeholder=t("placeholder_select"),
            format_func=region_to_display,
        )
        selected_countries = st.multiselect(
            t("country"),
            country_options,
            default=[],
            placeholder=t("placeholder_select"),
            format_func=country_to_display,
        )
        search_submitted = st.form_submit_button(t("search"), use_container_width=True)

selected_levels = [display_to_internal_level(item) for item in selected_level_display]
selected_work_modes = [work_mode.lower() for work_mode in work_mode_options if work_mode_to_display(work_mode) in selected_work_mode_display]

if search_submitted:
    save_active_profile(
        {
            "display_name": "Default",
            "practices": active_profiles,
            "seniority_levels": selected_seniority_labels,
            "preferred_regions": selected_regions,
            "preferred_countries": selected_countries,
            "preferred_work_modes": selected_work_modes,
            "preferred_companies": selected_companies,
            "keywords": [],
        }
    )
    st.session_state.active_profile_preferences = load_active_profile()
    profile_preferences = st.session_state.active_profile_preferences

filtered_explore_df = filter_explore_view(
    explore_base_df,
    selected_preset,
    selected_levels,
    selected_work_modes,
    selected_companies,
    selected_regions,
    selected_countries,
)

if not search_submitted:
    st.caption(t("explore_hint"))

st.caption(t("showing_results", count=len(filtered_explore_df)))
render_jobs_table(
    t("filtered_jobs"),
    filtered_explore_df,
    "lista_filtrada.xlsx",
    table_key="tab_explore_jobs",
)
