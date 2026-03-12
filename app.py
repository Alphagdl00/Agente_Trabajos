"""
Radar Global de Trabajos — Public Edition
Scan 40+ company career pages, score by your profile, find your next role.
"""
from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import streamlit as st

from main import (
    DEFAULT_PROFILE_PRESETS,
    ensure_directories,
    load_companies,
    normalize_jobs_df,
    parse_keywords_from_text,
    run_radar,
)


# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Job Radar — Encuentra tu próximo rol",
    page_icon="🎯",
    layout="wide",
)

ensure_directories()


# =========================================================
# CUSTOM CSS
# =========================================================
st.markdown(
    """
    <style>
    /* Tighter metrics */
    [data-testid="stMetric"] {
        background: #0e1117;
        border: 1px solid #1e2530;
        border-radius: 8px;
        padding: 12px 16px;
    }
    [data-testid="stMetric"] label { font-size: 0.8rem; }
    [data-testid="stMetric"] [data-testid="stMetricValue"] { font-size: 1.6rem; }

    /* Supported ATS badges */
    .ats-badge {
        display: inline-block;
        padding: 2px 8px;
        margin: 2px;
        border-radius: 12px;
        font-size: 0.75rem;
        background: #1a3a2a;
        color: #4ade80;
        border: 1px solid #2d5a3d;
    }
    .ats-badge.partial {
        background: #3a2a1a;
        color: #fbbf24;
        border-color: #5a4a2d;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# HEADER
# =========================================================
st.title("🎯 Job Radar")
st.caption(
    "Escanea career pages de 40+ empresas globales, filtra por tu perfil, "
    "y encuentra vacantes relevantes en segundos. Open source y gratuito."
)


# =========================================================
# HELPERS
# =========================================================
def csv_download_button(df: pd.DataFrame, label: str, file_name: str):
    if df is None or df.empty:
        return
    csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(label=label, data=csv_bytes, file_name=file_name, mime="text/csv", use_container_width=True)


def prepare_display_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
    preferred = ["score", "company", "title", "location", "work_mode", "department", "ats", "url"]
    cols = [c for c in preferred if c in out.columns] + [c for c in out.columns if c not in preferred]

    # Drop internal columns that confuse public users
    drop_cols = [
        "dedupe_key", "job_key", "has_keyword_match", "source_url",
        "priority", "international_hiring", "profile_fit", "salary_band",
    ]
    cols = [c for c in cols if c not in drop_cols]
    return out[cols]


def render_jobs_table(title: str, df: pd.DataFrame, csv_name: str, height: int = 500):
    st.subheader(title)

    if df is None or df.empty:
        st.info("Sin resultados en esta categoría con los filtros actuales.")
        return

    display_df = prepare_display_df(df)

    col1, col2 = st.columns([1, 4])
    with col1:
        csv_download_button(display_df, f"⬇ Descargar CSV", csv_name)
    with col2:
        st.caption(f"{len(display_df)} resultados")

    column_config = {}
    if "url" in display_df.columns:
        column_config["url"] = st.column_config.LinkColumn(
            "Aplicar",
            help="Abre la vacante directamente",
            display_text="🔗 Abrir",
        )

    st.dataframe(display_df, use_container_width=True, height=height, column_config=column_config)


def parse_user_companies_csv(uploaded_file) -> pd.DataFrame | None:
    """Parse a user-uploaded companies CSV with flexible column handling."""
    try:
        df = pd.read_csv(uploaded_file)
    except Exception:
        return None

    # Minimum requirement: company + career_url
    if "company" not in df.columns or "career_url" not in df.columns:
        return None

    # Fill optional columns
    for col in ["industry", "region", "priority", "international_hiring",
                 "profile_fit", "salary_band", "ats"]:
        if col not in df.columns:
            df[col] = ""

    df = df.fillna("")
    df["company"] = df["company"].astype(str).str.strip()
    df["career_url"] = df["career_url"].astype(str).str.strip()
    df = df[df["company"] != ""].copy()
    return df


# =========================================================
# SIDEBAR — USER CONFIGURATION
# =========================================================
with st.sidebar:
    st.header("⚙️ Tu perfil")

    st.markdown(
        "Configura tus keywords y empresas. "
        "Tus datos viven solo en tu sesión — no guardamos nada."
    )

    # --- Profile presets ---
    profile_options = list(DEFAULT_PROFILE_PRESETS.keys()) + ["Custom"]
    profile_name = st.selectbox("Perfil de búsqueda", options=profile_options, index=0)

    use_custom = profile_name == "Custom"

    if use_custom:
        keywords_text = st.text_area(
            "Tus keywords (una por línea)",
            value="",
            height=180,
            help="Ejemplo: marketing, growth, brand manager, head of marketing",
            placeholder="marketing\ngrowth\nbrand manager\nhead of marketing",
        )
    else:
        preset_kws = DEFAULT_PROFILE_PRESETS.get(profile_name, [])
        keywords_text = st.text_area(
            "Keywords del preset (edita si quieres)",
            value="\n".join(preset_kws),
            height=180,
        )

    st.markdown("---")

    # --- Company source ---
    st.subheader("📋 Empresas a escanear")
    company_source = st.radio(
        "Fuente de empresas",
        options=["Usar lista predeterminada (45 empresas)", "Subir mi propio CSV"],
        index=0,
        label_visibility="collapsed",
    )

    user_companies_df = None
    if company_source == "Subir mi propio CSV":
        st.caption("Tu CSV debe tener columnas `company` y `career_url`. Opcional: `ats`, `industry`, `priority`.")

        sample_csv = "company,career_url,ats\nStripe,https://boards.greenhouse.io/stripe,greenhouse\nMi Empresa,https://careers.miempresa.com,\n"
        st.download_button("📥 Descargar plantilla CSV", data=sample_csv, file_name="empresas_template.csv", mime="text/csv")

        uploaded = st.file_uploader("Sube tu CSV de empresas", type=["csv"], label_visibility="collapsed")
        if uploaded:
            user_companies_df = parse_user_companies_csv(uploaded)
            if user_companies_df is not None:
                st.success(f"✅ {len(user_companies_df)} empresas cargadas")
            else:
                st.error("CSV inválido. Necesita columnas `company` y `career_url`.")

    st.markdown("---")

    # --- Filters ---
    st.subheader("🔍 Filtros")

    selected_work_modes = st.multiselect(
        "Modo de trabajo",
        options=["remote", "hybrid", "onsite", "unknown"],
        default=[],
    )

    min_score = st.slider("Score mínimo", min_value=0, max_value=46, value=0, step=1)

    st.markdown("---")

    # --- ATS info ---
    with st.expander("ℹ️ ATS soportados", expanded=False):
        st.markdown(
            '<span class="ats-badge">Greenhouse</span>'
            '<span class="ats-badge">Lever</span>'
            '<span class="ats-badge">Workday</span>'
            '<span class="ats-badge partial">SuccessFactors (parcial)</span>'
            '<span class="ats-badge partial">Genérico (parcial)</span>',
            unsafe_allow_html=True,
        )
        st.caption(
            "Greenhouse, Lever y Workday extraen datos completos via API. "
            "Otros ATS (iCIMS, SmartRecruiters, Taleo, portales custom) "
            "usan un scraper genérico que puede devolver resultados incompletos."
        )

    st.markdown("---")
    run_button = st.button("🚀 Escanear ahora", type="primary", use_container_width=True)


# =========================================================
# BUILD KEYWORDS
# =========================================================
keywords = parse_keywords_from_text(keywords_text)
keywords = [x.lower().strip() for x in keywords if x.strip()]


# =========================================================
# RUN RADAR
# =========================================================
if "radar_result" not in st.session_state:
    st.session_state["radar_result"] = None

if run_button:
    if not keywords:
        st.error("Necesitas al menos una keyword. Escríbelas en la barra lateral.")
        st.stop()

    # Determine which company list to use
    companies_to_use = user_companies_df  # None means use default

    with st.spinner("Escaneando career pages... esto puede tomar 1-2 minutos."):
        result = run_radar(
            keywords=keywords,
            work_modes=selected_work_modes,
            min_score=min_score,
            save_outputs=False,  # Don't write files in multi-user mode
            companies_df=companies_to_use,
        )

    st.session_state["radar_result"] = result
    st.toast("✅ Escaneo completado", icon="🎯")


# =========================================================
# RESULTS
# =========================================================
result = st.session_state.get("radar_result")

if result is None:
    # Landing state — show instructions
    st.markdown("---")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown("### 1️⃣ Configura tu perfil")
        st.markdown("Elige un preset o escribe tus propias keywords en la barra lateral.")
    with col_b:
        st.markdown("### 2️⃣ Escanea")
        st.markdown("Click en **Escanear ahora**. El radar revisa career pages de 40+ empresas globales.")
    with col_c:
        st.markdown("### 3️⃣ Aplica")
        st.markdown("Filtra por score, modo de trabajo, y haz click en **Abrir** para aplicar directo.")

    st.markdown("---")
    with st.expander("🏢 Empresas incluidas en la lista predeterminada", expanded=False):
        try:
            default_companies = load_companies()
            display_companies = default_companies[["company", "industry", "region", "ats"]].copy()
            display_companies = display_companies.sort_values("company").reset_index(drop=True)
            st.dataframe(display_companies, use_container_width=True, height=400)
        except Exception:
            st.info("No se pudo cargar la lista de empresas.")

    st.stop()


# =========================================================
# METRICS
# =========================================================
summary = result.get("summary", {})

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Total", summary.get("all_jobs", 0))
m2.metric("Match keywords", summary.get("filtered", 0))
m3.metric("Strong (≥20)", summary.get("strong", 0))
m4.metric("Global/Remote", summary.get("global", 0))
m5.metric("Nuevas hoy", summary.get("new_today", 0))

with st.expander("Keywords usadas en este escaneo", expanded=False):
    active_kws = summary.get("keywords_used", [])
    if active_kws:
        st.write(", ".join(active_kws))


# =========================================================
# INSIGHTS
# =========================================================
all_jobs_df = result.get("all_jobs", pd.DataFrame())

if not all_jobs_df.empty:
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("🏢 Top empresas por volumen")
        company_counts = (
            all_jobs_df["company"].fillna("").astype(str)
            .value_counts().reset_index()
        )
        company_counts.columns = ["Empresa", "Vacantes"]
        st.dataframe(company_counts.head(15), use_container_width=True, height=340)

    with col_right:
        st.subheader("📊 Distribución por ATS")
        ats_counts = (
            all_jobs_df["ats"].fillna("").astype(str)
            .value_counts().reset_index()
        )
        ats_counts.columns = ["ATS", "Vacantes"]
        st.dataframe(ats_counts.head(10), use_container_width=True, height=340)


# =========================================================
# TABS
# =========================================================
tab_strong, tab_global, tab_filtered, tab_all = st.tabs(
    ["💪 Strong matches", "🌍 Global/Remote", "🔑 Keyword matches", "📋 Todas"]
)

with tab_strong:
    render_jobs_table(
        "Vacantes fuertes (score ≥ 20)",
        result.get("strong_jobs", pd.DataFrame()),
        "strong_jobs.csv",
    )

with tab_global:
    render_jobs_table(
        "Vacantes con señal global / remoto / internacional",
        result.get("global_jobs", pd.DataFrame()),
        "global_jobs.csv",
    )

with tab_filtered:
    render_jobs_table(
        "Todas las vacantes que matchean tus keywords",
        result.get("filtered_jobs", pd.DataFrame()),
        "filtered_jobs.csv",
    )

with tab_all:
    render_jobs_table(
        "Todas las vacantes escaneadas",
        result.get("all_jobs", pd.DataFrame()),
        "all_jobs.csv",
    )


# =========================================================
# FOOTER
# =========================================================
st.markdown("---")
st.caption(
    "Hecho con 🐍 Python + Streamlit. "
    "Los datos se obtienen directamente de las career pages de cada empresa. "
    "Este es un proyecto open source — "
    "[GitHub](https://github.com/Alphagdl00/Agente_Trabajos)"
)
