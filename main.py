from __future__ import annotations

import json
import re
import traceback
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd

from repositories.jobs_repository import persist_radar_run
from src.parallel_scraper import collect_jobs_parallel
from src.ats_router import scrape_company_jobs
from src.scoring import score_job


# =========================================================
# PATHS
# =========================================================
BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "config"
OUTPUT_DIR = BASE_DIR / "output"
HISTORY_DIR = BASE_DIR / "history"

COMPANIES_FILE = CONFIG_DIR / "companies.csv"
TITLES_FILE = CONFIG_DIR / "titles.txt"
HISTORY_FILE = HISTORY_DIR / "jobs_history.csv"
FEEDBACK_FILE = HISTORY_DIR / "job_feedback.csv"
RUN_META_FILE = OUTPUT_DIR / "last_run_meta.json"

ALL_JOBS_FILE = OUTPUT_DIR / "all_jobs.xlsx"
FILTERED_JOBS_FILE = OUTPUT_DIR / "filtered_jobs.xlsx"
STRONG_JOBS_FILE = OUTPUT_DIR / "strong_jobs.xlsx"
PRIORITY_JOBS_FILE = OUTPUT_DIR / "priority_jobs.xlsx"
GLOBAL_JOBS_FILE = OUTPUT_DIR / "global_jobs.xlsx"
NEW_JOBS_TODAY_FILE = OUTPUT_DIR / "new_jobs_today.xlsx"


# =========================================================
# DEFAULTS
# =========================================================
DEFAULT_PROFILE_PRESETS = {
    "Finance": [
        "finance",
        "fp&a",
        "financial planning",
        "business partner",
        "finance transformation",
        "strategic finance",
        "commercial finance",
        "corporate finance",
        "it finance",
        "finance manager",
        "finance director",
        "director finance",
        "senior finance manager",
        "head of finance",
    ],
    "Legal": [
        "legal",
        "counsel",
        "senior counsel",
        "corporate counsel",
        "compliance",
        "contracts",
        "employment law",
        "commercial law",
        "regulatory",
        "legal director",
    ],
    "Strategy": [
        "strategy",
        "strategic planning",
        "corporate strategy",
        "business strategy",
        "transformation",
        "chief of staff",
        "strategic initiatives",
        "pmo",
        "program director",
    ],
    "Operations": [
        "operations",
        "operational excellence",
        "business operations",
        "process improvement",
        "continuous improvement",
        "supply chain",
        "manufacturing",
        "plant finance",
        "procurement",
    ],
    "IT/Data": [
        "data",
        "analytics",
        "business intelligence",
        "it",
        "digital transformation",
        "data science",
        "data analytics",
        "product analytics",
        "systems",
        "erp",
        "sap",
        "jde",
    ],
    "HR": [
        "human resources",
        "hr",
        "people partner",
        "people operations",
        "talent acquisition",
        "recruiting",
        "recruiter",
        "hr business partner",
        "learning and development",
        "organizational development",
        "compensation",
        "benefits",
    ],
}

SENIORITY_LABEL_MAP = {
    "individual": "Principiante",
    "senior_individual": "Intermedio",
    "manager": "Senior",
    "executive": "Ejecutivo",
}


# =========================================================
# UTILS
# =========================================================
def ensure_directories() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def clean_text(value) -> str:
    if value is None:
        return ""
    value = str(value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def safe_lower(value) -> str:
    return clean_text(value).lower()


def make_slug_key(*parts: str) -> str:
    joined = " | ".join(clean_text(p) for p in parts if clean_text(p))
    if not joined:
        return ""
    return safe_lower(joined)


def parse_keywords_from_text(raw_text: str) -> list[str]:
    if not raw_text:
        return []

    lines = []
    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue
        lines.append(line)

    if len(lines) == 1 and "," in lines[0]:
        return [clean_text(x).lower() for x in lines[0].split(",") if clean_text(x)]

    return [clean_text(x).lower() for x in lines if clean_text(x)]


def load_titles_from_file(path: Path = TITLES_FILE) -> list[str]:
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8", errors="ignore")
    return parse_keywords_from_text(content)


def save_titles_to_file(keywords: Iterable[str], path: Path = TITLES_FILE) -> None:
    values = [clean_text(x) for x in keywords if clean_text(x)]
    path.write_text("\n".join(values), encoding="utf-8")


def get_profile_keywords(
    profile_names: str | list[str] | None,
    fallback_keywords: list[str] | None = None,
) -> list[str]:
    if isinstance(profile_names, str):
        candidates = [clean_text(profile_names)]
    elif isinstance(profile_names, list):
        candidates = [clean_text(item) for item in profile_names if clean_text(item)]
    else:
        candidates = []

    combined: list[str] = []
    for profile in candidates:
        if profile in DEFAULT_PROFILE_PRESETS:
            combined.extend(DEFAULT_PROFILE_PRESETS[profile])

    if combined:
        deduped = list(dict.fromkeys(clean_text(x).lower() for x in combined if clean_text(x)))
        return deduped

    if fallback_keywords:
        return [clean_text(x).lower() for x in fallback_keywords if clean_text(x)]

    return load_titles_from_file()


def load_companies(path: Path = COMPANIES_FILE) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo de empresas: {path}")

    file_candidates = [path]
    for extra_name in ["companies_validated.csv", "mexico_validated.csv"]:
        extra_path = path.parent / extra_name
        if extra_path.exists() and extra_path != path:
            file_candidates.append(extra_path)

    frames = [pd.read_csv(file_path) for file_path in file_candidates]
    df = pd.concat(frames, ignore_index=True)

    expected_cols = [
        "company",
        "industry",
        "region",
        "priority",
        "international_hiring",
        "profile_fit",
        "salary_band",
        "ats",
        "career_url",
    ]

    for col in expected_cols:
        if col not in df.columns:
            df[col] = ""

    df = df.fillna("")
    df["company"] = df["company"].astype(str).str.strip()
    df["career_url"] = df["career_url"].astype(str).str.strip()
    df["ats"] = df["ats"].astype(str).str.strip()
    df["priority"] = df["priority"].astype(str).str.strip()
    df["industry"] = df["industry"].astype(str).str.strip()
    if "country" not in df.columns:
        df["country"] = ""
    df["country"] = df["country"].astype(str).str.strip()
    df["international_hiring"] = df["international_hiring"].astype(str).str.strip()
    df["profile_fit"] = df["profile_fit"].astype(str).str.strip()

    df = df[df["company"] != ""].copy()
    df = df.drop_duplicates(subset=["company", "career_url"], keep="first").reset_index(drop=True)
    return df


def rank_companies_for_scan(companies_df: pd.DataFrame) -> pd.DataFrame:
    def priority_points(value: str) -> int:
        v = clean_text(value).upper()
        if v == "A":
            return 30
        if v == "B":
            return 20
        if v == "C":
            return 10
        return 0

    def fit_points(value: str) -> int:
        v = clean_text(value).lower()
        if v == "high":
            return 20
        if v == "medium":
            return 10
        if v == "low":
            return 5
        return 0

    def intl_points(value: str) -> int:
        v = clean_text(value).lower()
        if v == "high":
            return 15
        if v == "medium":
            return 8
        if v == "low":
            return 3
        return 0

    def ats_points(value: str) -> int:
        v = clean_text(value).lower()
        if v == "workday":
            return 8
        if v == "greenhouse":
            return 7
        if v == "lever":
            return 6
        if v == "successfactors":
            return 4
        if v == "auto":
            return 3
        return 1

    df = companies_df.copy()
    df["scan_rank"] = (
        df["priority"].map(priority_points)
        + df["profile_fit"].map(fit_points)
        + df["international_hiring"].map(intl_points)
        + df["ats"].map(ats_points)
    )

    df = df.sort_values(
        by=["scan_rank", "priority", "profile_fit", "company"],
        ascending=[False, True, True, True],
    ).reset_index(drop=True)

    return df


def normalize_jobs_df(jobs: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(jobs)

    required_cols = [
        "company",
        "title",
        "location",
        "url",
        "ats",
        "source_url",
        "description_snippet",
        "industry",
        "region",
        "country",
        "priority",
        "international_hiring",
        "profile_fit",
        "salary_band",
        "department",
        "workplace_type",
    ]

    for col in required_cols:
        if col not in df.columns:
            df[col] = ""

    if "posted_date" not in df.columns:
        df["posted_date"] = ""
    if "work_mode" not in df.columns:
        df["work_mode"] = ""
    if "seniority_level" not in df.columns:
        df["seniority_level"] = ""
    if "score" not in df.columns:
        df["score"] = 0
    if "keyword_matches" not in df.columns:
        df["keyword_matches"] = ""
    if "score_reasons" not in df.columns:
        df["score_reasons"] = ""
    if "global_signal" not in df.columns:
        df["global_signal"] = False
    if "is_new_today" not in df.columns:
        df["is_new_today"] = False

    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].fillna("").map(clean_text)

    return df


def classify_work_mode(title: str, location: str, description: str, workplace_type: str) -> str:
    blob = f"{title} {location} {description} {workplace_type}".lower()

    remote_terms = [
        "remote",
        "work from home",
        "home based",
        "virtual",
        "telecommute",
        "anywhere",
        "distributed",
    ]
    hybrid_terms = [
        "hybrid",
        "flexible working",
        "flexible work",
        "mix of remote",
        "part remote",
    ]
    onsite_terms = [
        "on-site",
        "onsite",
        "site based",
        "office based",
        "in office",
        "presential",
    ]

    if any(term in blob for term in hybrid_terms):
        return "hybrid"
    if any(term in blob for term in remote_terms):
        return "remote"
    if any(term in blob for term in onsite_terms):
        return "onsite"

    return "unknown"


def detect_global_signal(title: str, location: str, description: str, international_hiring: str) -> bool:
    blob = f"{title} {location} {description} {international_hiring}".lower()

    terms = [
        "global",
        "international",
        "visa",
        "sponsorship",
        "relocation",
        "relocate",
        "worldwide",
        "europe",
        "switzerland",
        "ireland",
        "spain",
        "united kingdom",
        "uk",
        "germany",
        "netherlands",
        "singapore",
        "dubai",
        "remote",
        "work from anywhere",
    ]

    return any(term in blob for term in terms)


def compute_score(
    row: pd.Series,
    keywords: list[str],
    feedback_profile: dict | None = None,
) -> dict:
    return score_job(row.to_dict(), keywords, feedback_profile=feedback_profile)


def detect_seniority_band(title: str) -> str:
    normalized = clean_text(title).lower()
    if any(token in normalized for token in ["vp", "vice president", "head of", "director", "senior director", "sr director"]):
        return "executive"
    if any(token in normalized for token in ["manager", "lead", "principal", "senior manager"]):
        return "manager"
    if any(token in normalized for token in ["senior", "sr ", "specialist", "staff"]):
        return "senior_individual"
    if normalized:
        return "individual"
    return ""


def extract_geo_preferences(location: str) -> set[str]:
    normalized = clean_text(location).lower()
    if not normalized:
        return set()

    tokens: set[str] = set()
    if any(term in normalized for term in ["mexico", "cdmx", "guadalajara", "monterrey"]):
        tokens.add("mexico")
    if any(term in normalized for term in ["latam", "latin america", "mexico", "brazil", "colombia", "argentina", "chile"]):
        tokens.add("latam")
    if any(term in normalized for term in ["united states", "usa", "us ", "new york", "california", "texas"]):
        tokens.add("us")
    if any(term in normalized for term in ["europe", "spain", "germany", "netherlands", "switzerland", "france", "ireland", "uk", "united kingdom"]):
        tokens.add("europe")
    if "remote" in normalized or "anywhere" in normalized:
        tokens.add("remote_geo")
    return tokens


def load_history(path: Path = HISTORY_FILE) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["job_key", "url", "company", "title", "first_seen_date", "last_seen_date"])

    df = pd.read_csv(path)

    for col in ["job_key", "url", "company", "title", "first_seen_date", "last_seen_date"]:
        if col not in df.columns:
            df[col] = ""

    df = df.fillna("")

    if not df.empty:
        df["job_key"] = df["job_key"].astype(str).map(clean_text)
        df = df[df["job_key"] != ""].copy()
        df = (
            df.sort_values(by=["job_key", "last_seen_date", "first_seen_date"], ascending=[True, False, True])
            .drop_duplicates(subset=["job_key"], keep="first")
            .reset_index(drop=True)
        )

    return df


def load_feedback_profile(path: Path = FEEDBACK_FILE) -> dict:
    if not path.exists():
        return {}

    try:
        df = pd.read_csv(path)
    except Exception:
        return {}

    if df.empty:
        return {}

    for col in ["job_key", "status", "company", "title", "location", "work_mode"]:
        if col not in df.columns:
            df[col] = ""

    df = df.fillna("")
    df["job_key"] = df["job_key"].astype(str).map(clean_text)
    df["status"] = df["status"].astype(str).map(lambda x: clean_text(x).lower())
    df["company"] = df["company"].astype(str).map(lambda x: clean_text(x).lower())
    df["title"] = df["title"].astype(str).map(lambda x: clean_text(x).lower())
    df["location"] = df["location"].astype(str).map(lambda x: clean_text(x).lower())
    df["work_mode"] = df["work_mode"].astype(str).map(lambda x: clean_text(x).lower())
    df = df[df["job_key"] != ""].copy()

    if df.empty:
        return {}

    positive_statuses = {"saved", "apply_today", "applied", "interview", "offer"}
    negative_statuses = {"not_fit", "rejected"}

    profile = {
        "positive_titles": set(),
        "negative_titles": set(),
        "positive_companies": set(),
        "negative_companies": set(),
        "positive_work_modes": set(),
        "negative_work_modes": set(),
        "positive_geos": set(),
        "negative_geos": set(),
        "positive_seniority": set(),
        "negative_seniority": set(),
    }

    for _, row in df.iterrows():
        job_key = clean_text(row.get("job_key", "")).lower()
        status = clean_text(row.get("status", "")).lower()
        parts = [clean_text(part).lower() for part in job_key.split("|")]

        company = clean_text(row.get("company", "")).lower() or (parts[1] if len(parts) >= 2 else "")
        title = clean_text(row.get("title", "")).lower() or (parts[2] if len(parts) >= 3 else "")
        location = clean_text(row.get("location", "")).lower()
        work_mode = clean_text(row.get("work_mode", "")).lower()

        title_tokens = [
            token for token in re.split(r"[^a-z0-9&+/.-]+", title)
            if len(token) >= 4
        ][:6]

        seniority = detect_seniority_band(title)
        geo_tokens = extract_geo_preferences(location)

        if status in positive_statuses:
            profile["positive_titles"].update(title_tokens)
            if company:
                profile["positive_companies"].add(company)
            if work_mode:
                profile["positive_work_modes"].add(work_mode)
            if seniority:
                profile["positive_seniority"].add(seniority)
            profile["positive_geos"].update(geo_tokens)
        elif status in negative_statuses:
            profile["negative_titles"].update(title_tokens)
            if company:
                profile["negative_companies"].add(company)
            if work_mode:
                profile["negative_work_modes"].add(work_mode)
            if seniority:
                profile["negative_seniority"].add(seniority)
            profile["negative_geos"].update(geo_tokens)

    return profile


def update_history_and_get_new_jobs(df_all: pd.DataFrame, history_path: Path = HISTORY_FILE) -> pd.DataFrame:
    history_df = load_history(history_path)
    known_keys = set(history_df["job_key"].astype(str).tolist())

    today_str = datetime.now().strftime("%Y-%m-%d")

    df_all = df_all.copy()
    df_all["job_key"] = df_all.apply(
        lambda r: make_slug_key(r.get("url", ""), r.get("company", ""), r.get("title", "")),
        axis=1,
    )

    df_all = df_all[df_all["job_key"].map(lambda x: clean_text(x) != "")].copy()

    df_all = (
        df_all.sort_values(by=["score", "company", "title"], ascending=[False, True, True])
        .drop_duplicates(subset=["job_key"], keep="first")
        .reset_index(drop=True)
    )

    df_all["is_new_today"] = ~df_all["job_key"].isin(known_keys)
    new_jobs_df = df_all[df_all["is_new_today"]].copy()

    current_seen = df_all[["job_key", "url", "company", "title"]].drop_duplicates().copy()
    current_seen["first_seen_date"] = today_str
    current_seen["last_seen_date"] = today_str

    hist_base = {}
    for _, row in history_df.iterrows():
        key = clean_text(row.get("job_key", ""))
        if not key:
            continue
        hist_base[key] = {
            "url": clean_text(row.get("url", "")),
            "company": clean_text(row.get("company", "")),
            "title": clean_text(row.get("title", "")),
            "first_seen_date": clean_text(row.get("first_seen_date", "")),
            "last_seen_date": clean_text(row.get("last_seen_date", "")),
        }

    cur_base = {}
    for _, row in current_seen.iterrows():
        key = clean_text(row.get("job_key", ""))
        if not key:
            continue
        cur_base[key] = {
            "url": clean_text(row.get("url", "")),
            "company": clean_text(row.get("company", "")),
            "title": clean_text(row.get("title", "")),
            "first_seen_date": clean_text(row.get("first_seen_date", today_str)),
            "last_seen_date": clean_text(row.get("last_seen_date", today_str)),
        }

    all_keys = set(hist_base.keys()) | set(cur_base.keys())
    rebuilt = []

    for key in all_keys:
        h = hist_base.get(key, {})
        c = cur_base.get(key, {})

        rebuilt.append(
            {
                "job_key": key,
                "url": c.get("url") or h.get("url") or "",
                "company": c.get("company") or h.get("company") or "",
                "title": c.get("title") or h.get("title") or "",
                "first_seen_date": h.get("first_seen_date") or c.get("first_seen_date") or today_str,
                "last_seen_date": c.get("last_seen_date") or h.get("last_seen_date") or today_str,
            }
        )

    updated_history = pd.DataFrame(rebuilt)

    if not updated_history.empty:
        updated_history = (
            updated_history.sort_values(by=["job_key", "last_seen_date", "first_seen_date"], ascending=[True, False, True])
            .drop_duplicates(subset=["job_key"], keep="first")
            .reset_index(drop=True)
        )

    updated_history.to_csv(history_path, index=False, encoding="utf-8-sig")

    return new_jobs_df


def save_excel(df: pd.DataFrame, path: Path) -> None:
    df_to_save = df.copy()

    preferred_order = [
        "company",
        "title",
        "location",
        "work_mode",
        "score",
        "priority",
        "global_signal",
        "is_new_today",
        "ats",
        "industry",
        "region",
        "international_hiring",
        "profile_fit",
        "salary_band",
        "department",
        "workplace_type",
        "seniority_level",
        "posted_date",
        "keyword_matches",
        "score_reasons",
        "url",
        "source_url",
        "description_snippet",
    ]

    final_cols = [c for c in preferred_order if c in df_to_save.columns] + [
        c for c in df_to_save.columns if c not in preferred_order
    ]

    df_to_save = df_to_save[final_cols]
    df_to_save.to_excel(path, index=False)


def apply_filters(
    df: pd.DataFrame,
    work_modes: list[str] | None = None,
    selected_companies: list[str] | None = None,
    selected_ats: list[str] | None = None,
    selected_priorities: list[str] | None = None,
    selected_seniority: list[str] | None = None,
    selected_regions: list[str] | None = None,
    selected_countries: list[str] | None = None,
    min_score: int = 0,
) -> pd.DataFrame:
    result = df.copy()

    if work_modes:
        wm = {x.lower().strip() for x in work_modes if clean_text(x)}
        result = result[result["work_mode"].str.lower().isin(wm)]

    if selected_companies:
        sc = {x.lower().strip() for x in selected_companies if clean_text(x)}
        result = result[result["company"].str.lower().isin(sc)]

    if selected_ats:
        sa = {x.lower().strip() for x in selected_ats if clean_text(x)}
        result = result[result["ats"].str.lower().isin(sa)]

    if selected_priorities:
        sp = {x.lower().strip() for x in selected_priorities if clean_text(x)}
        result = result[result["priority"].str.lower().isin(sp)]

    if selected_seniority:
        ss = {x.lower().strip() for x in selected_seniority if clean_text(x)}
        result = result[result["seniority_level"].str.lower().isin(ss)]

    if selected_regions:
        sr = {x.lower().strip() for x in selected_regions if clean_text(x)}
        result = result[result["region"].str.lower().isin(sr)]

    if selected_countries:
        scountry = {x.lower().strip() for x in selected_countries if clean_text(x)}
        result = result[result["country"].str.lower().isin(scountry)]

    if min_score > 0 and "score" in result.columns:
        result = result[result["score"] >= min_score]

    return result


def save_run_metadata(summary: dict, keywords: list[str]) -> None:
    payload = {
        "last_run_timestamp": datetime.now().isoformat(),
        "last_run_date": datetime.now().strftime("%Y-%m-%d"),
        "keywords_used": keywords,
        "summary": summary,
    }
    RUN_META_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def load_run_metadata() -> dict:
    if not RUN_META_FILE.exists():
        return {}
    try:
        return json.loads(RUN_META_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def has_run_today() -> bool:
    meta = load_run_metadata()
    return meta.get("last_run_date", "") == datetime.now().strftime("%Y-%m-%d")


# =========================================================
# CORE RADAR
# =========================================================
def collect_jobs_from_companies(
    companies_df: pd.DataFrame,
    company_limit: int | None = None,
    use_parallel: bool = False,
) -> list[dict]:
    ranked_df = rank_companies_for_scan(companies_df)

    if company_limit is not None and company_limit > 0:
        ranked_df = ranked_df.head(company_limit).copy()

    if use_parallel:
        return collect_jobs_parallel(ranked_df)

    all_jobs = []
    total = len(ranked_df)

    for idx, (_, row) in enumerate(ranked_df.iterrows(), start=1):
        company_row = row.to_dict()
        company_name = clean_text(company_row.get("company", "Unknown"))

        try:
            print(f"[RADAR] Scraping ({idx}/{total}): {company_name}")
            jobs = scrape_company_jobs(company_row)

            if not isinstance(jobs, list):
                jobs = []

            for job in jobs:
                job = dict(job)

                job.setdefault("company", company_name)
                job.setdefault("industry", company_row.get("industry", ""))
                job.setdefault("region", company_row.get("region", ""))
                job.setdefault("country", company_row.get("country", ""))
                job.setdefault("priority", company_row.get("priority", ""))
                job.setdefault("international_hiring", company_row.get("international_hiring", ""))
                job.setdefault("profile_fit", company_row.get("profile_fit", ""))
                job.setdefault("salary_band", company_row.get("salary_band", ""))
                job.setdefault("source_url", company_row.get("career_url", ""))
                job.setdefault("ats", company_row.get("ats", ""))

                all_jobs.append(job)

            print(f"[RADAR] {company_name}: {len(jobs)} jobs")
        except Exception as exc:
            print(f"[RADAR] ERROR in {company_name}: {exc}")
            traceback.print_exc()

    return all_jobs


def prepare_scored_jobs_df(
    all_jobs: list[dict],
    keywords: list[str],
    feedback_profile: dict | None = None,
) -> pd.DataFrame:
    df = normalize_jobs_df(all_jobs)

    if df.empty:
        return df

    df["company"] = df["company"].map(clean_text)
    df["title"] = df["title"].map(clean_text)
    df["location"] = df["location"].map(clean_text)
    df["url"] = df["url"].map(clean_text)
    df["description_snippet"] = df["description_snippet"].map(clean_text)
    df["ats"] = df["ats"].map(clean_text)
    df["priority"] = df["priority"].map(clean_text)
    df["department"] = df["department"].map(clean_text)
    df["workplace_type"] = df["workplace_type"].map(clean_text)

    empty_ats_mask = df["ats"].eq("")
    if empty_ats_mask.any():
        df.loc[empty_ats_mask, "ats"] = "unknown"

    df["work_mode"] = df.apply(
        lambda r: classify_work_mode(
            r.get("title", ""),
            r.get("location", ""),
            r.get("description_snippet", ""),
            r.get("workplace_type", ""),
        ),
        axis=1,
    )
    df["seniority_level"] = df["title"].map(lambda value: SENIORITY_LABEL_MAP.get(detect_seniority_band(value), "Principiante"))

    df["global_signal"] = df.apply(
        lambda r: detect_global_signal(
            r.get("title", ""),
            r.get("location", ""),
            r.get("description_snippet", ""),
            r.get("international_hiring", ""),
        ),
        axis=1,
    )

    score_results = df.apply(lambda r: compute_score(r, keywords, feedback_profile), axis=1)
    df["score"] = score_results.map(lambda x: x["score"])
    df["keyword_matches"] = score_results.map(lambda x: ", ".join(x["keyword_matches"]))
    df["score_reasons"] = score_results.map(lambda x: " | ".join(x["score_reasons"]))

    if keywords:
        df["has_keyword_match"] = df["keyword_matches"].map(lambda x: clean_text(x) != "")
    else:
        df["has_keyword_match"] = True

    df["dedupe_key"] = df.apply(
        lambda r: make_slug_key(r.get("url", ""), r.get("company", ""), r.get("title", "")),
        axis=1,
    )

    df = (
        df.sort_values(by=["score", "company", "title"], ascending=[False, True, True])
        .drop_duplicates(subset=["dedupe_key"])
        .reset_index(drop=True)
    )

    return df


def run_radar(
    profile_name: str | list[str] | None = None,
    keywords: list[str] | None = None,
    work_modes: list[str] | None = None,
    selected_companies: list[str] | None = None,
    selected_ats: list[str] | None = None,
    selected_priorities: list[str] | None = None,
    selected_seniority: list[str] | None = None,
    selected_regions: list[str] | None = None,
    selected_countries: list[str] | None = None,
    min_score: int = 0,
    save_outputs: bool = True,
    company_limit: int | None = None,
    use_parallel: bool = False,
) -> dict:
    ensure_directories()

    companies_df = load_companies()

    keywords = get_profile_keywords(profile_name, keywords)

    if selected_companies:
        selected_set = {x.lower().strip() for x in selected_companies}
        companies_df = companies_df[companies_df["company"].str.lower().isin(selected_set)].copy()

    if selected_regions:
        region_set = {x.lower().strip() for x in selected_regions if clean_text(x)}
        companies_df = companies_df[companies_df["region"].str.lower().isin(region_set)].copy()

    if selected_countries:
        country_set = {x.lower().strip() for x in selected_countries if clean_text(x)}
        companies_df = companies_df[companies_df["country"].str.lower().isin(country_set)].copy()

    raw_jobs = collect_jobs_from_companies(
        companies_df,
        company_limit=company_limit,
        use_parallel=use_parallel,
    )
    feedback_profile = load_feedback_profile()
    df_all = prepare_scored_jobs_df(raw_jobs, keywords, feedback_profile=feedback_profile)

    if df_all.empty:
        summary = {
            "all_jobs": 0,
            "filtered": 0,
            "strong": 0,
            "priority": 0,
            "global": 0,
            "new_today": 0,
            "keywords_used": keywords,
            "profile_name": profile_name or [],
            "selected_regions": selected_regions or [],
            "selected_countries": selected_countries or [],
            "company_limit": company_limit,
            "use_parallel": use_parallel,
        }
        if save_outputs:
            save_run_metadata(summary, keywords)

        return {
            "all_jobs": df_all,
            "filtered_jobs": df_all.copy(),
            "strong_jobs": df_all.copy(),
            "priority_jobs": df_all.copy(),
            "global_jobs": df_all.copy(),
            "new_jobs_today": df_all.copy(),
            "summary": summary,
        }

    df_new_today = update_history_and_get_new_jobs(df_all, HISTORY_FILE)

    df_filtered = df_all[df_all["has_keyword_match"]].copy()
    df_strong = df_filtered[df_filtered["score"] >= 9].copy()
    df_priority = df_filtered[df_filtered["priority"].str.upper() == "A"].copy()
    df_global = df_filtered[df_filtered["global_signal"] == True].copy()

    df_all_view = apply_filters(df_all, work_modes, selected_companies, selected_ats, selected_priorities, selected_seniority, selected_regions, selected_countries, min_score)
    df_filtered_view = apply_filters(df_filtered, work_modes, selected_companies, selected_ats, selected_priorities, selected_seniority, selected_regions, selected_countries, min_score)
    df_strong_view = apply_filters(df_strong, work_modes, selected_companies, selected_ats, selected_priorities, selected_seniority, selected_regions, selected_countries, min_score)
    df_priority_view = apply_filters(df_priority, work_modes, selected_companies, selected_ats, selected_priorities, selected_seniority, selected_regions, selected_countries, min_score)
    df_global_view = apply_filters(df_global, work_modes, selected_companies, selected_ats, selected_priorities, selected_seniority, selected_regions, selected_countries, min_score)
    df_new_today_view = apply_filters(df_new_today, work_modes, selected_companies, selected_ats, selected_priorities, selected_seniority, selected_regions, selected_countries, min_score)

    if save_outputs:
        save_excel(df_all_view, ALL_JOBS_FILE)
        save_excel(df_filtered_view, FILTERED_JOBS_FILE)
        save_excel(df_strong_view, STRONG_JOBS_FILE)
        save_excel(df_priority_view, PRIORITY_JOBS_FILE)
        save_excel(df_global_view, GLOBAL_JOBS_FILE)
        save_excel(df_new_today_view, NEW_JOBS_TODAY_FILE)

    summary = {
        "all_jobs": int(len(df_all_view)),
        "filtered": int(len(df_filtered_view)),
        "strong": int(len(df_strong_view)),
        "priority": int(len(df_priority_view)),
        "global": int(len(df_global_view)),
        "new_today": int(len(df_new_today_view)),
        "keywords_used": keywords,
        "profile_name": profile_name or [],
        "selected_regions": selected_regions or [],
        "selected_countries": selected_countries or [],
        "company_limit": company_limit,
        "use_parallel": use_parallel,
    }

    if save_outputs:
        save_run_metadata(summary, keywords)

    persist_radar_run(
        companies_df,
        df_all_view,
        summary,
        profile_scope=profile_name if isinstance(profile_name, list) else ([profile_name] if clean_text(profile_name) else []),
        region_scope=selected_regions or [],
        country_scope=selected_countries or [],
    )

    return {
        "all_jobs": df_all_view,
        "filtered_jobs": df_filtered_view,
        "strong_jobs": df_strong_view,
        "priority_jobs": df_priority_view,
        "global_jobs": df_global_view,
        "new_jobs_today": df_new_today_view,
        "summary": summary,
    }


def main() -> None:
    ensure_directories()

    if not TITLES_FILE.exists():
        default_keywords = DEFAULT_PROFILE_PRESETS["Finance"]
        save_titles_to_file(default_keywords, TITLES_FILE)

    result = run_radar()

    print("\n===== RADAR SUMMARY =====")
    print(f"All jobs:       {result['summary']['all_jobs']}")
    print(f"Filtered:       {result['summary']['filtered']}")
    print(f"Strong:         {result['summary']['strong']}")
    print(f"Priority A:     {result['summary']['priority']}")
    print(f"Global/Remote:  {result['summary']['global']}")
    print(f"New today:      {result['summary']['new_today']}")
    print("=========================\n")


if __name__ == "__main__":
    main()
