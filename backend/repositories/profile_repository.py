from __future__ import annotations

import json

from backend.models.user import User, UserProfile


def _json_text(values: list[str]) -> str:
    cleaned = [" ".join(str(value).split()).strip() for value in values if " ".join(str(value).split()).strip()]
    return json.dumps(cleaned, ensure_ascii=False)


def ensure_user_profile(session, profile: dict) -> UserProfile:
    email = str(profile.get("email", "demo@northhound.local")).strip().lower() or "demo@northhound.local"
    user = session.query(User).filter(User.email == email).one_or_none()
    if user is None:
        user = User(
            email=email,
            full_name=str(profile.get("full_name", "North Hound Demo User")).strip() or "North Hound Demo User",
        )
        session.add(user)
        session.flush()

    display_name = str(profile.get("display_name", "Default")).strip() or "Default"
    user_profile = (
        session.query(UserProfile)
        .filter(UserProfile.user_id == user.id, UserProfile.display_name == display_name)
        .one_or_none()
    )

    payload = {
        "target_role": str(profile.get("target_role", "")).strip(),
        "practice_area": str(profile.get("practice_area", "")).strip(),
        "seniority_target": str(profile.get("seniority_target", "")).strip(),
        "preferred_regions": _json_text(profile.get("preferred_regions", []) or []),
        "preferred_countries": _json_text(profile.get("preferred_countries", []) or []),
        "preferred_work_modes": _json_text(profile.get("preferred_work_modes", []) or []),
        "preferred_companies": _json_text(profile.get("preferred_companies", []) or []),
        "keywords": _json_text(profile.get("keywords", []) or []),
        "years_experience": int(profile.get("years_experience", 0) or 0),
        "is_default": True,
    }

    if user_profile is None:
        user_profile = UserProfile(user_id=user.id, display_name=display_name, **payload)
        session.add(user_profile)
        session.flush()
        return user_profile

    for key, value in payload.items():
        setattr(user_profile, key, value)
    session.flush()
    return user_profile
