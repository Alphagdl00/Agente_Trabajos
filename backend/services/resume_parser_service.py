from __future__ import annotations

import hashlib
import re
from datetime import datetime
from io import BytesIO

from backend.services.skill_extraction_service import DEFAULT_SKILL_CATALOG

try:  # pragma: no cover - optional parser dependency
    from pypdf import PdfReader
except Exception:  # pragma: no cover
    PdfReader = None


ROLE_HINTS = [
    "analyst",
    "specialist",
    "manager",
    "director",
    "head",
    "vice president",
    "vp",
    "counsel",
    "consultant",
    "engineer",
    "partner",
    "lead",
]


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split()).strip()


def _strip_leading_markers(text: str) -> str:
    return re.sub(r"^[•\-\u25b8\u2023\u2043\u2219]+\s*", "", text).strip()


def _normalize_text_keep_lines(text: str) -> str:
    lines: list[str] = []
    for raw_line in (text or "").replace("\x00", " ").splitlines():
        cleaned = _clean_text(raw_line)
        if cleaned:
            lines.append(cleaned)
    return "\n".join(lines)


def _extract_text_from_bytes(file_name: str, file_bytes: bytes) -> str:
    suffix = file_name.lower().rsplit(".", 1)[-1] if "." in file_name else ""
    if suffix == "pdf" and PdfReader is not None:
        reader = PdfReader(BytesIO(file_bytes))
        pages: list[str] = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                pages.append(page_text)
        return "\n".join(pages).strip()

    for encoding in ("utf-8", "latin-1"):
        try:
            return file_bytes.decode(encoding, errors="ignore").strip()
        except Exception:
            continue
    return ""


def _find_first(pattern: str, text: str, flags: int = 0) -> str:
    match = re.search(pattern, text, flags)
    if not match:
        return ""
    return _clean_text(match.group(0))


def _extract_linkedin(text: str) -> str:
    match = re.search(r"((?:https?://)?(?:www\.)?linkedin\.com/[^\s|]+)", text, re.IGNORECASE)
    if not match:
        return ""
    value = _clean_text(match.group(1))
    if value.lower().startswith(("http://", "https://")):
        return value
    return f"https://{value}"


def _normalize_role_line(line: str) -> str:
    cleaned = _strip_leading_markers(_clean_text(line))
    cleaned = cleaned.replace("→", "->")
    cleaned = re.sub(r"\s+\|\s+[A-Z][a-z]+.*?\b(?:19|20)\d{2}\b.*$", "", cleaned)
    cleaned = re.sub(r"\s+[A-Z][a-z]+,\s*[A-Z][a-z]+.*?\b(?:19|20)\d{2}\b.*$", "", cleaned)
    cleaned = re.sub(r"\s+\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b.*$", "", cleaned)
    cleaned = re.sub(r"\s+\b(?:19|20)\d{2}\b.*$", "", cleaned)
    return _clean_text(cleaned)


def _extract_role_lines(text: str) -> list[str]:
    roles: list[str] = []
    for line in text.splitlines():
        cleaned = _normalize_role_line(line)
        lowered = cleaned.lower()
        if not cleaned:
            continue
        if len(cleaned) > 100:
            continue
        if "|" in cleaned and cleaned.count("|") >= 2:
            continue
        if any(cleaned.lower().startswith(prefix) for prefix in ["partnered with", "managed usd", "delivered ", "led ", "developed ", "implemented "]):
            continue
        if any(marker in lowered for marker in ["sap s/4hana", "oracle", "cognos", "anaplan", "power bi", "tableau"]):
            continue
        if any(token in lowered for token in ROLE_HINTS):
            roles.append(cleaned)
    deduped: list[str] = []
    seen: set[str] = set()
    for role in roles:
        key = role.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(role)
        if len(deduped) >= 8:
            break
    return deduped


def _infer_years_from_summary(text: str) -> tuple[int, list[dict]]:
    match = re.search(r"\b(\d{1,2})\+?\s+years\b", text, re.IGNORECASE)
    if not match:
        return 0, []
    years = int(match.group(1))
    return years, [
        {
            "evidence_type": "years_summary",
            "evidence_value": str(years),
            "evidence_text": _clean_text(match.group(0)),
        }
    ]


def _infer_years_experience(text: str) -> tuple[int, list[dict]]:
    current_year = datetime.now().year
    summary_years, summary_evidence = _infer_years_from_summary(text)
    if summary_years > 0:
        return summary_years, summary_evidence

    spans: list[tuple[int, int, str]] = []
    in_experience_section = False
    for raw_line in text.splitlines():
        line = _clean_text(raw_line)
        lowered = line.lower()
        if not line:
            continue
        if "professional experience" in lowered or lowered == "experience":
            in_experience_section = True
            continue
        if in_experience_section and any(
            marker in lowered
            for marker in [
                "education",
                "languages",
                "technical proficiencies",
                "additional information",
            ]
        ):
            break
        if not in_experience_section:
            continue

        for match in re.finditer(r"\b(19\d{2}|20\d{2})\s*[-–]\s*(present|current|19\d{2}|20\d{2})\b", line, re.IGNORECASE):
            start_year = int(match.group(1))
            raw_end = match.group(2).lower()
            end_year = current_year if raw_end in {"present", "current"} else int(raw_end)
            if end_year >= start_year:
                spans.append((start_year, end_year, _clean_text(match.group(0))))

    if not spans:
        return 0, []

    ordered_spans = sorted(spans, key=lambda item: (item[0], item[1]))
    merged: list[tuple[int, int]] = []
    for start_year, end_year, _ in ordered_spans:
        if not merged:
            merged.append((start_year, end_year))
            continue
        previous_start, previous_end = merged[-1]
        if start_year <= previous_end:
            merged[-1] = (previous_start, max(previous_end, end_year))
        else:
            merged.append((start_year, end_year))

    inferred_years = sum(max(0, end - start) for start, end in merged)
    evidence = [
        {
            "evidence_type": "experience_span",
            "evidence_value": f"{start_year}-{end_year}",
            "evidence_text": span_text,
        }
        for start_year, end_year, span_text in ordered_spans[:5]
    ]
    return inferred_years, evidence


def parse_resume(file_name: str, file_bytes: bytes) -> dict:
    raw_text = _extract_text_from_bytes(file_name, file_bytes)
    text = _normalize_text_keep_lines(raw_text)
    content_hash = hashlib.sha256(file_bytes).hexdigest()

    email = _find_first(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.IGNORECASE)
    linkedin = _extract_linkedin(text)
    phone = _find_first(r"(\+?\d[\d\s().-]{7,}\d)", text)
    role_lines = _extract_role_lines(text)
    inferred_years, years_evidence = _infer_years_experience(text)

    skills: list[dict] = []
    lowered = text.lower()
    for term, category in DEFAULT_SKILL_CATALOG.items():
        if term and term in lowered:
            skills.append(
                {
                    "name": term,
                    "category": category,
                    "years_experience": float(inferred_years),
                    "evidence_text": term,
                    "confidence": 1.0,
                }
            )

    unique_skills: dict[str, dict] = {}
    for item in skills:
        unique_skills[item["name"]] = item

    evidence_items: list[dict] = []
    if email:
        evidence_items.append({"evidence_type": "email", "evidence_value": email, "evidence_text": email})
    if linkedin:
        evidence_items.append({"evidence_type": "linkedin", "evidence_value": linkedin, "evidence_text": linkedin})
    if phone:
        evidence_items.append({"evidence_type": "phone", "evidence_value": phone, "evidence_text": phone})
    for role in role_lines:
        evidence_items.append({"evidence_type": "role_title", "evidence_value": role, "evidence_text": role})
    evidence_items.extend(years_evidence)
    for item in unique_skills.values():
        evidence_items.append(
            {
                "evidence_type": "skill",
                "evidence_value": item["name"],
                "evidence_text": item["evidence_text"],
            }
        )

    return {
        "file_name": file_name,
        "content_hash": content_hash,
        "extracted_text": text,
        "email": email,
        "linkedin": linkedin,
        "phone": phone,
        "roles": role_lines,
        "skills": list(unique_skills.values()),
        "years_experience": inferred_years,
        "evidence_items": evidence_items,
    }
