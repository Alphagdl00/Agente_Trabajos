from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from db.connection import get_connection, is_database_enabled


DEMO_USER_ID = UUID("00000000-0000-0000-0000-000000000001")
DEMO_PROFILE_ID = UUID("00000000-0000-0000-0000-000000000010")
LOCAL_PROFILE_FILE = Path(__file__).resolve().parent.parent / "history" / "active_profile.json"


def _default_profile() -> dict:
    return {
        "display_name": "Default",
        "practices": [],
        "seniority_levels": [],
        "preferred_regions": [],
        "preferred_countries": [],
        "preferred_work_modes": [],
        "preferred_companies": [],
        "keywords": [],
    }


def load_active_profile() -> dict:
    if is_database_enabled():
        with get_connection() as conn:
            if conn is None:
                return _load_local_profile()

            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into users (id, email, full_name)
                    values (%s, %s, %s)
                    on conflict (email) do nothing
                    """,
                    (DEMO_USER_ID, "demo@jobradar.local", "Demo User"),
                )
                cur.execute(
                    """
                    select display_name, practices, seniority_levels, preferred_regions,
                           preferred_countries, preferred_work_modes, preferred_companies, keywords
                    from user_profiles
                    where user_id = %s and is_default = true
                    limit 1
                    """,
                    (DEMO_USER_ID,),
                )
                row = cur.fetchone()
                if row:
                    return {
                        "display_name": row[0] or "Default",
                        "practices": row[1] or [],
                        "seniority_levels": row[2] or [],
                        "preferred_regions": row[3] or [],
                        "preferred_countries": row[4] or [],
                        "preferred_work_modes": row[5] or [],
                        "preferred_companies": row[6] or [],
                        "keywords": row[7] or [],
                    }
    return _load_local_profile()


def save_active_profile(profile: dict) -> bool:
    payload = {
        "display_name": profile.get("display_name", "Default") or "Default",
        "practices": profile.get("practices", []) or [],
        "seniority_levels": profile.get("seniority_levels", []) or [],
        "preferred_regions": profile.get("preferred_regions", []) or [],
        "preferred_countries": profile.get("preferred_countries", []) or [],
        "preferred_work_modes": profile.get("preferred_work_modes", []) or [],
        "preferred_companies": profile.get("preferred_companies", []) or [],
        "keywords": profile.get("keywords", []) or [],
    }

    if is_database_enabled():
        with get_connection() as conn:
            if conn is None:
                return _save_local_profile(payload)

            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into users (id, email, full_name)
                    values (%s, %s, %s)
                    on conflict (email) do update set full_name = excluded.full_name
                    """,
                    (DEMO_USER_ID, "demo@jobradar.local", "Demo User"),
                )
                cur.execute(
                    """
                    insert into user_profiles (
                        id, user_id, display_name, practices, seniority_levels,
                        preferred_regions, preferred_countries, preferred_work_modes,
                        preferred_companies, keywords, is_default
                    )
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, true)
                    on conflict (id)
                    do update set
                        display_name = excluded.display_name,
                        practices = excluded.practices,
                        seniority_levels = excluded.seniority_levels,
                        preferred_regions = excluded.preferred_regions,
                        preferred_countries = excluded.preferred_countries,
                        preferred_work_modes = excluded.preferred_work_modes,
                        preferred_companies = excluded.preferred_companies,
                        keywords = excluded.keywords,
                        updated_at = now()
                    """,
                    (
                        DEMO_PROFILE_ID,
                        DEMO_USER_ID,
                        payload["display_name"],
                        payload["practices"],
                        payload["seniority_levels"],
                        payload["preferred_regions"],
                        payload["preferred_countries"],
                        payload["preferred_work_modes"],
                        payload["preferred_companies"],
                        payload["keywords"],
                    ),
                )
                return True

    return _save_local_profile(payload)


def _load_local_profile() -> dict:
    if not LOCAL_PROFILE_FILE.exists():
        return _default_profile()

    try:
        data = json.loads(LOCAL_PROFILE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return _default_profile()

    profile = _default_profile()
    profile.update({k: v for k, v in data.items() if k in profile})
    return profile


def _save_local_profile(profile: dict) -> bool:
    LOCAL_PROFILE_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOCAL_PROFILE_FILE.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    return True
