from __future__ import annotations

import json
import re
import traceback
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd

from src.ats_router import scrape_company_jobs


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


def load_companies(path: Path = COMPANIES_FILE) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo de empresas: {path}")

    df = pd.read_csv(path)

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

    df = df[df["company"] != ""].copy()
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
    if "score" not in df.columns:
        df["score"] = 0
    if "keyword_matches" not in df.columns:
        df["keyword_matches"] = ""
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


def keyword_match_details(title: str, description: str, keywords: list[str]) -> tuple[bool, list[str]]:
    if not keywords:
        return True, []

    blob = f"{title} {description}".lower()
    matches = []

    for kw in keywords:
        kw = kw.lower().strip()
        if not kw:
            continue
        if kw in blob:
            matches.append(kw)

    return len(matches) > 0, matches


def compute_score(row: pd.Series, keywords: list[str]) -> tuple[int, list[str]]:
    """
    Consolidated scoring engine. Combines keyword matching with granular
    role relevance, seniority, company metadata, and recency signals.
    Max theoretical score ~50+ for a perfect-fit role.
    """
    title = safe_lower(row.get("title", ""))
    description = safe_lower(row.get("description_snippet", ""))
    department = safe_lower(row.get("department", ""))
    location = safe_lower(row.get("location", ""))
    workplace_type = safe_lower(row.get("workplace_type", ""))
    priority = clean_text(row.get("priority", "")).upper()
    profile_fit = safe_lower(row.get("profile_fit", ""))
    international_hiring = safe_lower(row.get("international_hiring", ""))
    industry = safe_lower(row.get("industry", ""))
    posted_date = safe_lower(row.get("posted_date", ""))

    _, matches = keyword_match_details(title, description, keywords)

    score = 0

    # --- Keyword matches (0-5) ---
    if matches:
        score += min(5, len(matches) * 2)

    # --- Role relevance from title (0-10) ---
    role_signals = {
        5: ["fp&a", "it finance", "technology finance", "finance transformation",
            "strategic finance", "finance business partner"],
        4: ["financial planning", "corporate finance", "commercial finance",
            "finance systems", "enterprise finance", "digital finance",
            "global finance", "business partner"],
        3: ["finance", "financial analysis", "operations finance",
            "business finance", "transformation", "planning analysis"],
    }
    role_pts = 0
    for pts, terms in role_signals.items():
        if any(term in title for term in terms):
            role_pts = max(role_pts, pts)
    score += role_pts

    # --- Seniority (0-8) ---
    if any(x in title for x in ["vp", "vice president"]):
        score += 8
    elif any(x in title for x in ["senior director", "sr director"]):
        score += 7
    elif any(x in title for x in ["director", "head of"]):
        score += 6
    elif any(x in title for x in ["senior manager"]):
        score += 4
    elif any(x in title for x in ["manager", "lead", "principal"]):
        score += 2

    # --- Department bonus (0-3) ---
    if "fp&a" in department:
        score += 3
    elif "finance" in department:
        score += 2
    elif any(x in department for x in ["business operations", "corporate functions"]):
        score += 1

    # --- Remote / international from location+workplace (0-3) ---
    remote_terms = ["remote", "distributed", "anywhere", "global",
                    "international", "hybrid"]
    if any(term in location for term in remote_terms):
        score += 2
    if any(term in workplace_type for term in remote_terms):
        score += 1

    # --- Company priority (0-3) ---
    if priority == "A":
        score += 3
    elif priority == "B":
        score += 2
    elif priority == "C":
        score += 1

    # --- Profile fit (0-3) ---
    if profile_fit == "high":
        score += 3
    elif profile_fit == "medium":
        score += 2
    elif profile_fit == "low":
        score += 1

    # --- International hiring (0-3) ---
    if international_hiring == "high":
        score += 3
    elif international_hiring == "medium":
        score += 2
    elif international_hiring == "low":
        score += 1

    # --- Industry alignment (0-3) ---
    if any(x in industry for x in ["pharma", "life sciences"]):
        score += 3
    elif any(x in industry for x in ["industrial", "medtech"]):
        score += 2
    elif any(x in industry for x in ["tech", "fintech"]):
        score += 1

    # --- Recency (0-4) ---
    date_blob = f"{posted_date} {title} {description}"
    if any(x in date_blob for x in ["today", "just posted", "posted today"]):
        score += 4
    elif any(x in date_blob for x in ["yesterday", "1 day ago", "2 days ago", "3 days ago"]):
        score += 3

    return score, matches


def load_history(path: Path = HISTORY_FILE) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["job_key", "url", "company", "title", "first_seen_date", "last_seen_date"])

    df = pd.read_csv(path)
    for col in ["job_key", "url", "company", "title", "first_seen_date", "last_seen_date"]:
        if col not in df.columns:
            df[col] = ""
    return df.fillna("")


def update_history_and_get_new_jobs(df_all: pd.DataFrame, history_path: Path = HISTORY_FILE) -> pd.DataFrame:
    history_df = load_history(history_path)
    known_keys = set(history_df["job_key"].astype(str).tolist())

    today_str = datetime.now().strftime("%Y-%m-%d")

    df_all = df_all.copy()
    df_all["job_key"] = df_all.apply(
        lambda r: make_slug_key(r.get("url", ""), r.get("company", ""), r.get("title", "")),
        axis=1,
    )

    df_all["is_new_today"] = ~df_all["job_key"].isin(known_keys)
    new_jobs_df = df_all[df_all["is_new_today"]].copy()

    current_seen = df_all[["job_key", "url", "company", "title"]].drop_duplicates().copy()
    current_seen["first_seen_date"] = today_str
    current_seen["last_seen_date"] = today_str

    if not history_df.empty:
        hist_base = history_df.set_index("job_key").to_dict("index")
        cur_base = current_seen.set_index("job_key").to_dict("index")

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
    else:
        updated_history = current_seen.copy()

    updated_history = updated_history.drop_duplicates(subset=["job_key"]).copy()
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
        "posted_date",
        "keyword_matches",
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
# SCRAPE CACHE (scrape once, serve many users)
# =========================================================
_SCRAPE_CACHE: dict[str, tuple[str, list[dict]]] = {}  # key: cache_key -> (date_str, jobs)


def get_cached_or_scrape(companies_df: pd.DataFrame) -> list[dict]:
    """
    Returns cached scrape results if available for today,
    otherwise scrapes and caches. Cache key is based on the
    sorted set of career URLs to allow different company lists.
    """
    today = datetime.now().strftime("%Y-%m-%d")

    urls = sorted(companies_df["career_url"].dropna().astype(str).unique().tolist())
    cache_key = hash(tuple(urls))

    cached = _SCRAPE_CACHE.get(cache_key)
    if cached and cached[0] == today:
        print(f"[CACHE] Returning {len(cached[1])} cached jobs for today")
        return cached[1]

    raw_jobs = collect_jobs_from_companies(companies_df)
    _SCRAPE_CACHE[cache_key] = (today, raw_jobs)
    return raw_jobs


# =========================================================
# CORE RADAR
# =========================================================
def collect_jobs_from_companies(companies_df: pd.DataFrame) -> list[dict]:
    all_jobs = []

    for _, row in companies_df.iterrows():
        company_row = row.to_dict()
        company_name = clean_text(company_row.get("company", "Unknown"))

        try:
            print(f"[RADAR] Scraping: {company_name}")
            jobs = scrape_company_jobs(company_row)

            if not isinstance(jobs, list):
                jobs = []

            for job in jobs:
                job = dict(job)

                job.setdefault("company", company_name)
                job.setdefault("industry", company_row.get("industry", ""))
                job.setdefault("region", company_row.get("region", ""))
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


def prepare_scored_jobs_df(all_jobs: list[dict], keywords: list[str]) -> pd.DataFrame:
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

    df["global_signal"] = df.apply(
        lambda r: detect_global_signal(
            r.get("title", ""),
            r.get("location", ""),
            r.get("description_snippet", ""),
            r.get("international_hiring", ""),
        ),
        axis=1,
    )

    score_results = df.apply(lambda r: compute_score(r, keywords), axis=1)
    df["score"] = score_results.map(lambda x: x[0])
    df["keyword_matches"] = score_results.map(lambda x: ", ".join(x[1]))

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
    keywords: list[str] | None = None,
    work_modes: list[str] | None = None,
    selected_companies: list[str] | None = None,
    selected_ats: list[str] | None = None,
    selected_priorities: list[str] | None = None,
    min_score: int = 0,
    save_outputs: bool = True,
    companies_df: pd.DataFrame | None = None,
) -> dict:
    ensure_directories()

    if companies_df is None:
        companies_df = load_companies()

    if keywords is None:
        keywords = load_titles_from_file()

    keywords = [clean_text(x).lower() for x in keywords if clean_text(x)]

    if selected_companies:
        selected_set = {x.lower().strip() for x in selected_companies}
        companies_df = companies_df[companies_df["company"].str.lower().isin(selected_set)].copy()

    raw_jobs = get_cached_or_scrape(companies_df)
    df_all = prepare_scored_jobs_df(raw_jobs, keywords)

    if df_all.empty:
        summary = {
            "all_jobs": 0,
            "filtered": 0,
            "strong": 0,
            "priority": 0,
            "global": 0,
            "new_today": 0,
            "keywords_used": keywords,
        }
        if save_outputs:
            save_run_metadata(summary, keywords)

        result = {
            "all_jobs": df_all,
            "filtered_jobs": df_all.copy(),
            "strong_jobs": df_all.copy(),
            "priority_jobs": df_all.copy(),
            "global_jobs": df_all.copy(),
            "new_jobs_today": df_all.copy(),
            "summary": summary,
        }
        return result

    df_new_today = update_history_and_get_new_jobs(df_all, HISTORY_FILE)

    df_filtered = df_all[df_all["has_keyword_match"]].copy()
    df_strong = df_filtered[df_filtered["score"] >= 20].copy()
    df_priority = df_filtered[df_filtered["priority"].str.upper() == "A"].copy()
    df_global = df_filtered[df_filtered["global_signal"] == True].copy()

    df_all_view = apply_filters(df_all, work_modes, selected_companies, selected_ats, selected_priorities, min_score)
    df_filtered_view = apply_filters(df_filtered, work_modes, selected_companies, selected_ats, selected_priorities, min_score)
    df_strong_view = apply_filters(df_strong, work_modes, selected_companies, selected_ats, selected_priorities, min_score)
    df_priority_view = apply_filters(df_priority, work_modes, selected_companies, selected_ats, selected_priorities, min_score)
    df_global_view = apply_filters(df_global, work_modes, selected_companies, selected_ats, selected_priorities, min_score)
    df_new_today_view = apply_filters(df_new_today, work_modes, selected_companies, selected_ats, selected_priorities, min_score)

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
    }

    if save_outputs:
        save_run_metadata(summary, keywords)

    result = {
        "all_jobs": df_all_view,
        "filtered_jobs": df_filtered_view,
        "strong_jobs": df_strong_view,
        "priority_jobs": df_priority_view,
        "global_jobs": df_global_view,
        "new_jobs_today": df_new_today_view,
        "summary": summary,
    }

    return result


# =========================================================
# CLI ENTRYPOINT
# =========================================================
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