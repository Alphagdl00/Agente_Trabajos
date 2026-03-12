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
    STRONG_JOBS_FILE,
    ensure_directories,
    load_run_metadata,
    load_titles_from_file,
)

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Radar Global de Trabajos",
    page_icon="🎯",
    layout="wide",
)

ensure_directories()


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


def dataframe_download_button(df: pd.DataFrame, label: str, file_name: str, key: str):
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
        key=key,
    )


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


def render_jobs_table(
    title: str,
    df: pd.DataFrame,
    csv_name: str,
    table_key: str,
    height: int = 520,
):
    st.subheader(title)

    if df is None or df.empty:
        st.info("No hay resultados en este bloque.")
        return

    display_df = prepare_display_df(df)

    top1, top2 = st.columns([1, 4])
    with top1:
        dataframe_download_button(
            display_df,
            f"Descargar {csv_name}",
            csv_name,
            key=f"download_{table_key}",
        )
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
        key=f"dataframe_{table_key}",
    )


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
            "keywords_used": load_titles_from_file(),
        },
    }


# =========================================================
# LOAD
# =========================================================
result = load_result_from_files()
meta = load_run_metadata()

last_run_ts = meta.get("last_run_timestamp", "")
last_run_date = meta.get("last_run_date", "")
keywords_used = meta.get("keywords_used", result.get("summary", {}).get("keywords_used", []))

# =========================================================
# HEADER
# =========================================================
st.title("Job Radar")
st.caption("Dashboard diario para revisar vacantes ya procesadas, enfocarte en nuevas oportunidades y abrir links directos para aplicar.")

if not last_run_date:
    st.warning("No se encontraron resultados procesados. Primero ejecuta: python run_radar_full.py")
    st.stop()

meta_col1, meta_col2 = st.columns([2, 5])
with meta_col1:
    st.caption(f"Última corrida: {last_run_date}")
with meta_col2:
    st.caption(f"Timestamp: {last_run_ts or 'N/A'}")

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
    if keywords_used:
        st.write(", ".join(keywords_used))
    else:
        st.write("No hay keywords cargadas.")

# =========================================================
# DAILY FOCUS
# =========================================================
new_jobs_df = result.get("new_jobs_today", pd.DataFrame())

st.markdown("## Radar diario")
if new_jobs_df is not None and not new_jobs_df.empty:
    st.success(f"Hoy detecté {len(new_jobs_df)} vacantes nuevas. Empieza aquí.")
    render_jobs_table(
        "Nuevas hoy",
        new_jobs_df,
        "new_jobs_today.csv",
        table_key="daily_new_jobs_top",
        height=420,
    )
else:
    st.warning("Hoy no se detectaron vacantes nuevas.")

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
    render_jobs_table(
        "Vacantes nuevas detectadas hoy",
        result.get("new_jobs_today", pd.DataFrame()),
        "new_jobs_today.csv",
        table_key="tab_new_jobs",
    )

with tab_strong:
    render_jobs_table(
        "Vacantes fuertes (score >= 14)",
        result.get("strong_jobs", pd.DataFrame()),
        "strong_jobs.csv",
        table_key="tab_strong_jobs",
    )

with tab_priority:
    render_jobs_table(
        "Vacantes Priority A",
        result.get("priority_jobs", pd.DataFrame()),
        "priority_jobs.csv",
        table_key="tab_priority_jobs",
    )

with tab_global:
    render_jobs_table(
        "Vacantes con señal global / internacional",
        result.get("global_jobs", pd.DataFrame()),
        "global_jobs.csv",
        table_key="tab_global_jobs",
    )

with tab_filtered:
    render_jobs_table(
        "Vacantes filtradas por keywords",
        result.get("filtered_jobs", pd.DataFrame()),
        "filtered_jobs.csv",
        table_key="tab_filtered_jobs",
    )

with tab_all:
    render_jobs_table(
        "Todas las vacantes",
        result.get("all_jobs", pd.DataFrame()),
        "all_jobs.csv",
        table_key="tab_all_jobs",
    )