from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from main import (
    ALL_JOBS_FILE,
    FILTERED_JOBS_FILE,
    GLOBAL_JOBS_FILE,
    NEW_JOBS_TODAY_FILE,
    PRIORITY_JOBS_FILE,
    RUN_META_FILE,
    STRONG_JOBS_FILE,
    DEFAULT_PROFILE_PRESETS,
    ensure_directories,
    has_run_today,
    load_companies,
    load_run_metadata,
    load_titles_from_file,
    parse_keywords_from_text,
    run_radar,
    save_titles_to_file,
)

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Radar Global de Trabajos",
    page_icon="🌍",
    layout="wide",
)

ensure_directories()


# =========================================================
# HELPERS
# =========================================================
def dataframe_download_button(df: pd.DataFrame, label: str, file_name: str):
    if df is None or df.empty:
        st.caption("Sin datos para descargar.")
        return

    csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label=label,
        data=csv_bytes,
        file_name=file_name,
        mime="text/csv",
        use_container_width=True,
    )


def read_excel_if_exists(path: Path) -> pd.DataFrame:
    if path.exists():
        try:
            return pd.read_excel(path)
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()


def build_keywords_ui(profile_name: str, use_custom: bool, custom_text: str) -> list[str]:
    if use_custom:
        keywords = parse_keywords_from_text(custom_text)
        return [x.lower().strip() for x in keywords if x.strip()]

    preset_keywords = DEFAULT_PROFILE_PRESETS.get(profile_name, [])
    return [x.lower().strip() for x in preset_keywords if x.strip()]


def prepare_display_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    preferred_cols = [
        "score",
        "company",
        "title",
        "location",
        "work_mode",
        "priority",
        "global_signal",
        "ats",
        "url",
    ]

    cols = [c for c in preferred_cols if c in out.columns] + [c for c in out.columns if c not in preferred_cols]
    out = out[cols]

    return out


def render_jobs_table(title: str, df: pd.DataFrame, csv_name: str, height: int = 520):
    st.subheader(title)

    if df is None or df.empty:
        st.info("No hay resultados en este bloque.")
        return

    display_df = prepare_display_df(df)

    top1, top2 = st.columns([1, 4])
    with top1:
        dataframe_download_button(display_df, f"Descargar {csv_name}", csv_name)
    with top2:
        st.caption(f"Resultados: {len(display_df)}")

    column_config = {}
    if "url" in display_df.columns:
        column_config["url"] = st.column_config.LinkColumn(
            "Apply link",
            help="Abre la vacante directamente",
            display_text="Aplicar",
        )

    st.dataframe(
        display_df,
        use_container_width=True,
        height=height,
        column_config=column_config,
    )


def load_result_from_files() -> dict:
    return {
        "all_jobs": read_excel_if_exists(ALL_JOBS_FILE),
        "filtered_jobs": read_excel_if_exists(FILTERED_JOBS_FILE),
        "strong_jobs": read_excel_if_exists(STRONG_JOBS_FILE),
        "priority_jobs": read_excel_if_exists(PRIORITY_JOBS_FILE),
        "global_jobs": read_excel_if_exists(GLOBAL_JOBS_FILE),
        "new_jobs_today": read_excel_if_exists(NEW_JOBS_TODAY_FILE),
        "summary": {
            "all_jobs": len(read_excel_if_exists(ALL_JOBS_FILE)),
            "filtered": len(read_excel_if_exists(FILTERED_JOBS_FILE)),
            "strong": len(read_excel_if_exists(STRONG_JOBS_FILE)),
            "priority": len(read_excel_if_exists(PRIORITY_JOBS_FILE)),
            "global": len(read_excel_if_exists(GLOBAL_JOBS_FILE)),
            "new_today": len(read_excel_if_exists(NEW_JOBS_TODAY_FILE)),
            "keywords_used": load_titles_from_file(),
        },
    }


# =========================================================
# STATE
# =========================================================
if "radar_result" not in st.session_state:
    st.session_state["radar_result"] = None

if "auto_run_done" not in st.session_state:
    st.session_state["auto_run_done"] = False


# =========================================================
# HEADER
# =========================================================
st.title("Radar Global de Trabajos")
st.caption("Dashboard diario para monitorear vacantes globales, abrir links directos y enfocarte primero en nuevas oportunidades.")


# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    st.header("Configuración")

    companies_df = load_companies()

    all_companies = sorted([x for x in companies_df["company"].dropna().astype(str).unique().tolist() if x.strip()])
    all_priorities = sorted([x for x in companies_df["priority"].dropna().astype(str).unique().tolist() if x.strip()])
    all_ats = sorted([x for x in companies_df["ats"].dropna().astype(str).unique().tolist() if x.strip()])

    profile_options = list(DEFAULT_PROFILE_PRESETS.keys()) + ["Custom"]

    profile_name = st.selectbox(
        "Perfil de búsqueda",
        options=profile_options,
        index=0,
    )

    use_custom_keywords = profile_name == "Custom"

    default_titles_text = "\n".join(load_titles_from_file())

    if use_custom_keywords:
        custom_keywords_text = st.text_area(
            "Keywords personalizadas",
            value=default_titles_text if default_titles_text else "",
            height=220,
            help="Una por línea o separadas por comas.",
        )
    else:
        preset_text = "\n".join(DEFAULT_PROFILE_PRESETS.get(profile_name, []))
        custom_keywords_text = st.text_area(
            "Preview de keywords del preset",
            value=preset_text,
            height=220,
            disabled=True,
        )

    st.markdown("---")

    selected_work_modes = st.multiselect(
        "Modo de trabajo",
        options=["remote", "hybrid", "onsite", "unknown"],
        default=[],
    )

    selected_companies = st.multiselect(
        "Empresas",
        options=all_companies,
        default=[],
    )

    selected_ats = st.multiselect(
        "ATS",
        options=all_ats,
        default=[],
    )

    selected_priorities = st.multiselect(
        "Prioridad",
        options=all_priorities,
        default=[],
    )

    min_score = st.slider(
        "Score mínimo",
        min_value=0,
        max_value=25,
        value=0,
        step=1,
    )

    save_keywords_now = st.checkbox("Guardar keywords en config/titles.txt", value=True)

    st.markdown("---")
    run_button = st.button("Ejecutar radar ahora", type="primary", use_container_width=True)


# =========================================================
# AUTO RUN DAILY
# =========================================================
keywords_for_run = build_keywords_ui(profile_name, use_custom_keywords, custom_keywords_text)

should_auto_run = (not has_run_today()) and (not st.session_state["auto_run_done"])

if should_auto_run:
    if save_keywords_now and keywords_for_run:
        save_titles_to_file(keywords_for_run)

    with st.spinner("Ejecutando radar diario automáticamente..."):
        result = run_radar(
            keywords=keywords_for_run,
            work_modes=selected_work_modes,
            selected_companies=selected_companies,
            selected_ats=selected_ats,
            selected_priorities=selected_priorities,
            min_score=min_score,
            save_outputs=True,
        )
    st.session_state["radar_result"] = result
    st.session_state["auto_run_done"] = True
    st.success("Radar diario ejecutado automáticamente.")

# =========================================================
# MANUAL RUN
# =========================================================
if run_button:
    if not keywords_for_run:
        st.error("Necesitas al menos una keyword válida.")
        st.stop()

    if save_keywords_now:
        save_titles_to_file(keywords_for_run)

    with st.spinner("Ejecutando radar global..."):
        result = run_radar(
            keywords=keywords_for_run,
            work_modes=selected_work_modes,
            selected_companies=selected_companies,
            selected_ats=selected_ats,
            selected_priorities=selected_priorities,
            min_score=min_score,
            save_outputs=True,
        )

    st.session_state["radar_result"] = result
    st.session_state["auto_run_done"] = True
    st.success("Radar ejecutado correctamente.")


# =========================================================
# RESULT SOURCE
# =========================================================
result = st.session_state.get("radar_result")

if result is None:
    result = load_result_from_files()
    if has_run_today():
        st.info("Mostrando resultados de la corrida automática de hoy.")
    else:
        st.info("Aún no hay corrida de hoy. Mostrando últimos archivos disponibles si existen.")


# =========================================================
# DAILY META
# =========================================================
meta = load_run_metadata()
last_run_ts = meta.get("last_run_timestamp", "")
last_run_date = meta.get("last_run_date", "")

meta_col1, meta_col2 = st.columns([2, 5])
with meta_col1:
    st.caption(f"Última corrida: {last_run_date or 'N/A'}")
with meta_col2:
    if last_run_ts:
        st.caption(f"Timestamp: {last_run_ts}")


# =========================================================
# METRICS
# =========================================================
summary = result.get("summary", {})

m1, m2, m3, m4, m5, m6 = st.columns(6)

m1.metric("All jobs", summary.get("all_jobs", 0))
m2.metric("Filtered", summary.get("filtered", 0))
m3.metric("Strong", summary.get("strong", 0))
m4.metric("Priority A", summary.get("priority", 0))
m5.metric("Global", summary.get("global", 0))
m6.metric("Nuevas hoy", summary.get("new_today", 0))

with st.expander("Keywords activas", expanded=False):
    active_keywords = summary.get("keywords_used", [])
    if active_keywords:
        st.write(", ".join(active_keywords))
    else:
        st.write("No hay keywords cargadas.")


# =========================================================
# DAILY FOCUS: NEW JOBS FIRST
# =========================================================
new_jobs_df = result.get("new_jobs_today", pd.DataFrame())

st.markdown("## Radar diario")
if new_jobs_df is not None and not new_jobs_df.empty:
    st.success(f"Hoy detecté {len(new_jobs_df)} vacantes nuevas. Aquí es donde deberías empezar.")
    render_jobs_table("Nuevas hoy", new_jobs_df, "new_jobs_today.csv", height=420)
else:
    st.warning("Hoy no se detectaron vacantes nuevas con los filtros actuales.")


# =========================================================
# TOP INSIGHTS
# =========================================================
all_jobs_df = result.get("all_jobs", pd.DataFrame())

if not all_jobs_df.empty:
    left, right = st.columns(2)

    with left:
        st.subheader("Top empresas por volumen")
        company_counts = (
            all_jobs_df["company"]
            .fillna("")
            .astype(str)
            .value_counts()
            .reset_index()
        )
        company_counts.columns = ["company", "jobs"]
        st.dataframe(company_counts.head(15), use_container_width=True, height=360)

    with right:
        st.subheader("Top ATS")
        ats_counts = (
            all_jobs_df["ats"]
            .fillna("")
            .astype(str)
            .value_counts()
            .reset_index()
        )
        ats_counts.columns = ["ats", "jobs"]
        st.dataframe(ats_counts.head(10), use_container_width=True, height=360)


# =========================================================
# TABS
# =========================================================
tab_new, tab_strong, tab_priority, tab_global, tab_filtered, tab_all = st.tabs(
    [
        "Nuevas hoy",
        "Strong",
        "Priority A",
        "Global",
        "Filtered",
        "All jobs",
    ]
)

with tab_new:
    render_jobs_table("Vacantes nuevas detectadas hoy", result.get("new_jobs_today", pd.DataFrame()), "new_jobs_today.csv")

with tab_strong:
    render_jobs_table("Vacantes fuertes (score >= 14)", result.get("strong_jobs", pd.DataFrame()), "strong_jobs.csv")

with tab_priority:
    render_jobs_table("Vacantes Priority A", result.get("priority_jobs", pd.DataFrame()), "priority_jobs.csv")

with tab_global:
    render_jobs_table("Vacantes con señal global / internacional", result.get("global_jobs", pd.DataFrame()), "global_jobs.csv")

with tab_filtered:
    render_jobs_table("Vacantes filtradas por keywords", result.get("filtered_jobs", pd.DataFrame()), "filtered_jobs.csv")

with tab_all:
    render_jobs_table("Todas las vacantes", result.get("all_jobs", pd.DataFrame()), "all_jobs.csv")