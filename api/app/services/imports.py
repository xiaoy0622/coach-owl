"""Smart-import service (CO-S04).

Two phases, never silently writing:

1. ``parse`` — a deterministic, network-free heuristic parser turns raw CSV or
   pasted text into candidate student records (splitting name / contact /
   guardian, detecting columns even when messy) and stores them on an
   ``import_jobs`` row with ``status=review``. If ``ANTHROPIC_API_KEY`` is set the
   result *may* be enhanced by an LLM, but parsing never blocks on the network and
   always yields candidates for the user to confirm.
2. ``commit`` — the user-confirmed/edited structure is persisted by calling the
   SAME students/guardians services used for manual entry.
"""
from __future__ import annotations

import re
import uuid

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import scoped
from app.core.errors import AppError
from app.models.enums import ImportStatus, StudentStatus
from app.models.import_jobs import ImportJob
from app.schemas.guardians import GuardianCreate
from app.schemas.students import StudentCreate
from app.services import guardians as guardians_service
from app.services import students as students_service

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# A phone is a run with >= 7 digits, allowing +, spaces, (), -, ..
PHONE_RE = re.compile(r"\+?\(?\d[\d\s().-]{5,}\d")
WEEKDAYS = (
    "monday|mon|tuesday|tues|tue|wednesday|wed|thursday|thurs|thur|thu|"
    "friday|fri|saturday|sat|sunday|sun"
)
SCHEDULE_RE = re.compile(
    rf"\b(?:{WEEKDAYS})\b.*?\d{{1,2}}\s*(?::\d{{2}})?\s*(?:am|pm)?"
    r"(?:\s*[-–to]+\s*\d{1,2}\s*(?::\d{2})?\s*(?:am|pm)?)?",
    re.IGNORECASE,
)

_HEADER_KEYWORDS: dict[str, tuple[str, ...]] = {
    "guardianName": ("guardian", "parent", "mother", "father", "carer", "caregiver"),
    "guardianPhone": (
        "guardian phone",
        "parent phone",
        "guardian mobile",
        "parent mobile",
        "guardian contact",
    ),
    "guardianEmail": ("guardian email", "parent email"),
    "guardianRelationship": ("relationship", "relation"),
    "email": ("email", "e-mail", "mail"),
    "phone": ("phone", "mobile", "cell", "tel", "contact", "number"),
    "status": ("status",),
    "tags": ("tag", "tags", "subject", "subjects", "group"),
    "schedule": ("schedule", "lesson", "time", "availability", "recurring"),
    "notes": ("note", "notes", "comment", "comments"),
    "name": ("name", "student", "child", "full name", "fullname"),
}

_DELIMITERS = ("\t", ",", ";", "|")


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #
def parse_text(raw: str) -> dict:
    """Heuristically parse raw CSV / pasted text into candidate records."""
    lines = [ln for ln in (raw or "").splitlines() if ln.strip()]
    if not lines:
        return {"source": "empty", "columns": [], "candidates": []}

    delimiter = _detect_delimiter(lines)
    if delimiter:
        return _parse_delimited(lines, delimiter)
    return _parse_freetext(lines)


def _detect_delimiter(lines: list[str]) -> str | None:
    # A single line is almost always free text (even if it contains commas);
    # real pasted CSV has a header + rows. Require >= 2 lines to treat as tabular.
    if len(lines) < 2:
        return None
    best: tuple[int, int, str] | None = None
    for delim in _DELIMITERS:
        counts = [ln.count(delim) for ln in lines]
        if min(counts) < 1:
            continue
        # Prefer delimiters that give a consistent column count.
        distinct = len(set(counts))
        score = (1, -distinct)
        if best is None or score > best[:2]:
            best = (*score, delim)
    return best[2] if best else None


def _looks_like_header(cells: list[str]) -> bool:
    hits = 0
    for cell in cells:
        low = cell.strip().lower()
        if any(low == kw or kw in low for kws in _HEADER_KEYWORDS.values() for kw in kws):
            hits += 1
    return hits >= max(1, len(cells) // 2)


def _classify_header(label: str) -> str:
    low = label.strip().lower()
    # Most specific roles first (guardian* before generic email/phone/name).
    for role in (
        "guardianPhone",
        "guardianEmail",
        "guardianRelationship",
        "guardianName",
        "status",
        "tags",
        "schedule",
        "notes",
        "email",
        "phone",
        "name",
    ):
        for kw in _HEADER_KEYWORDS[role]:
            if low == kw or kw in low:
                return role
    return "unknown"


def _parse_delimited(lines: list[str], delim: str) -> dict:
    rows = [[c.strip() for c in ln.split(delim)] for ln in lines]
    header: list[str] | None = None
    roles: list[str] | None = None
    data = rows
    if _looks_like_header(rows[0]):
        header = rows[0]
        roles = [_classify_header(h) for h in header]
        data = rows[1:]

    candidates = [
        _candidate_from_row(row, roles) for row in data if any(c for c in row)
    ]
    return {
        "source": "csv",
        "delimiter": {"\t": "tab", ",": "comma", ";": "semicolon", "|": "pipe"}[delim],
        "columns": header or [],
        "candidates": candidates,
    }


def _candidate_from_row(row: list[str], roles: list[str] | None) -> dict:
    cand = _blank_candidate()
    guardian: dict = {}
    warnings = cand["warnings"]

    if roles is not None:
        for value, role in zip(row, roles, strict=False):
            value = value.strip()
            if not value:
                continue
            _assign_role(cand, guardian, role, value, warnings)
    else:
        _assign_unmapped(cand, guardian, row, warnings)

    _finalize(cand, guardian, warnings)
    return cand


def _assign_role(
    cand: dict, guardian: dict, role: str, value: str, warnings: list[str]
) -> None:
    if role == "name":
        cand["name"] = value
    elif role == "email":
        cand["email"] = _first_email(value)
    elif role == "phone":
        cand["phone"] = _first_phone(value) or value
    elif role == "status":
        cand["status"] = _norm_status(value)
    elif role == "tags":
        cand["tags"].extend(_split_tags(value))
    elif role == "schedule":
        cand["scheduleText"] = value
    elif role == "notes":
        cand["notes"] = (cand["notes"] + " " + value).strip() if cand["notes"] else value
    elif role == "guardianName":
        guardian["name"] = value
    elif role == "guardianPhone":
        guardian["phone"] = _first_phone(value) or value
    elif role == "guardianEmail":
        guardian["email"] = _first_email(value)
    elif role == "guardianRelationship":
        guardian["relationship"] = value
    else:  # unknown column — infer from content.
        _infer_unknown(cand, value, warnings)


def _assign_unmapped(
    cand: dict, guardian: dict, row: list[str], warnings: list[str]
) -> None:
    word_cells: list[str] = []
    for value in row:
        value = value.strip()
        if not value:
            continue
        if EMAIL_RE.search(value):
            email = _first_email(value)
            if cand["email"] is None:
                cand["email"] = email
            else:
                guardian.setdefault("email", email)
        elif _first_phone(value):
            phone = _first_phone(value)
            if cand["phone"] is None:
                cand["phone"] = phone
            else:
                guardian.setdefault("phone", phone)
        elif SCHEDULE_RE.search(value):
            cand["scheduleText"] = value
        else:
            word_cells.append(value)
    if word_cells:
        cand["name"] = word_cells[0]
    if len(word_cells) > 1:
        guardian.setdefault("name", word_cells[1])


def _infer_unknown(cand: dict, value: str, warnings: list[str]) -> None:
    if EMAIL_RE.search(value) and cand["email"] is None:
        cand["email"] = _first_email(value)
    elif _first_phone(value) and cand["phone"] is None:
        cand["phone"] = _first_phone(value)
    elif SCHEDULE_RE.search(value) and not cand["scheduleText"]:
        cand["scheduleText"] = value
    elif not cand["name"]:
        cand["name"] = value
    else:
        cand["notes"] = (cand["notes"] + " " + value).strip() if cand["notes"] else value


def _parse_freetext(lines: list[str]) -> dict:
    candidates = [_candidate_from_freeline(ln) for ln in lines]
    return {"source": "text", "columns": [], "candidates": candidates}


def _candidate_from_freeline(line: str) -> dict:
    cand = _blank_candidate()
    guardian: dict = {}
    warnings = cand["warnings"]
    remainder = line

    emails = EMAIL_RE.findall(remainder)
    for e in emails:
        remainder = remainder.replace(e, " ")
    phones = PHONE_RE.findall(remainder)
    for p in phones:
        remainder = remainder.replace(p, " ")
    schedule = SCHEDULE_RE.search(remainder)
    if schedule:
        cand["scheduleText"] = schedule.group(0).strip()
        remainder = remainder.replace(schedule.group(0), " ")

    # Guardian segment: "... parent: Jane ..." / "(guardian Jane)".
    guardian_marker = re.search(
        r"(?:parent|guardian|mother|father|mum|mom|dad|carer)"
        r"\s*[:\-]?\s*([A-Za-z][A-Za-z .'-]+)",
        remainder,
        re.IGNORECASE,
    )
    if guardian_marker:
        guardian["name"] = guardian_marker.group(1).strip(" .,-")
        remainder = (
            remainder[: guardian_marker.start()]
            + remainder[guardian_marker.end():]
        )

    # Name is the first clean chunk (split on common separators / brackets).
    name_chunk = re.split(r"[,/|()\-–]", remainder, maxsplit=1)[0]
    cand["name"] = re.sub(r"\s+", " ", name_chunk).strip(" .,-")

    if emails:
        cand["email"] = emails[0]
    if phones:
        cand["phone"] = _clean_phone(phones[0])
    if len(emails) > 1:
        guardian.setdefault("email", emails[1])
    if len(phones) > 1:
        guardian.setdefault("phone", _clean_phone(phones[1]))

    _finalize(cand, guardian, warnings)
    return cand


# --------------------------------------------------------------------------- #
# Candidate helpers
# --------------------------------------------------------------------------- #
def _blank_candidate() -> dict:
    return {
        "name": "",
        "email": None,
        "phone": None,
        "status": "active",
        "tags": [],
        "notes": None,
        "scheduleText": None,
        "guardians": [],
        "confidence": 1.0,
        "warnings": [],
    }


def _finalize(cand: dict, guardian: dict, warnings: list[str]) -> None:
    cand["name"] = (cand["name"] or "").strip()
    # De-dupe tags preserving order.
    seen: list[str] = []
    for t in cand["tags"]:
        t = t.strip()
        if t and t not in seen:
            seen.append(t)
    cand["tags"] = seen

    if guardian.get("name"):
        guardian.setdefault("relationship", None)
        guardian.setdefault("email", None)
        guardian.setdefault("phone", None)
        guardian["isPrimary"] = True
        cand["guardians"] = [guardian]

    confidence = 1.0
    if not cand["name"]:
        confidence -= 0.5
        warnings.append("No name detected — please fill it in.")
    if cand["email"] is None and cand["phone"] is None and not cand["guardians"]:
        confidence -= 0.2
        warnings.append("No contact details detected.")
    cand["confidence"] = round(max(0.0, confidence), 2)


def _first_email(value: str) -> str | None:
    m = EMAIL_RE.search(value)
    return m.group(0) if m else None


def _first_phone(value: str) -> str | None:
    m = PHONE_RE.search(value)
    return _clean_phone(m.group(0)) if m else None


def _clean_phone(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _split_tags(value: str) -> list[str]:
    return [t.strip() for t in re.split(r"[;,/]", value) if t.strip()]


def _norm_status(value: str) -> str:
    low = value.strip().lower()
    for s in StudentStatus:
        if low == s.value:
            return s.value
    return StudentStatus.active.value


# --------------------------------------------------------------------------- #
# Job persistence + commit
# --------------------------------------------------------------------------- #
def create_parse_job(db: Session, org_id: uuid.UUID, raw_input: str) -> ImportJob:
    # LLM-first when a key is configured; the parser falls back to ``parse_text``
    # (the deterministic heuristic below) on no key or any failure.
    from app.ai.import_parser import parse_import

    parsed = parse_import(raw_input)
    job = ImportJob(
        org_id=org_id,
        raw_input=raw_input,
        parsed=parsed,
        status=ImportStatus.review,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_job(db: Session, org_id: uuid.UUID, job_id: uuid.UUID) -> ImportJob:
    stmt = scoped(select(ImportJob), org_id, ImportJob).where(
        ImportJob.id == job_id
    )
    job = db.scalar(stmt)
    if job is None:
        raise AppError(
            "Import job not found", code="not_found", status_code=404
        )
    return job


def commit_job(
    db: Session, org_id: uuid.UUID, job_id: uuid.UUID, parsed: dict
) -> ImportJob:
    job = get_job(db, org_id, job_id)
    if job.status == ImportStatus.committed:
        raise AppError(
            "Import job already committed",
            code="already_committed",
            status_code=409,
        )

    candidates = parsed.get("candidates") or []
    created_ids: list[str] = []
    for idx, cand in enumerate(candidates):
        if not isinstance(cand, dict) or cand.get("skip"):
            continue
        name = (cand.get("name") or "").strip()
        if not name:
            raise AppError(
                f"Candidate #{idx + 1} is missing a name",
                code="invalid_candidate",
                status_code=422,
            )
        try:
            student_in = StudentCreate(
                name=name,
                email=_safe_email(cand.get("email")),
                phone=cand.get("phone"),
                status=_status_enum(cand.get("status")),
                tags=list(cand.get("tags") or []),
                notes=cand.get("notes"),
            )
        except ValidationError as exc:
            raise AppError(
                f"Candidate #{idx + 1} failed validation",
                code="invalid_candidate",
                status_code=422,
                details=exc.errors(),
            ) from exc

        student = students_service.create_student(db, org_id, student_in)
        created_ids.append(str(student.id))

        for g in cand.get("guardians") or []:
            if not isinstance(g, dict) or not (g.get("name") or "").strip():
                continue
            try:
                guardian_in = GuardianCreate(
                    student_id=student.id,
                    name=g["name"].strip(),
                    relationship=g.get("relationship"),
                    email=_safe_email(g.get("email")),
                    phone=g.get("phone"),
                    is_primary=bool(g.get("isPrimary", True)),
                )
            except ValidationError:
                continue
            guardians_service.create_guardian(db, org_id, guardian_in)

    job.status = ImportStatus.committed
    job.parsed = {**parsed, "createdStudentIds": created_ids}
    db.commit()
    db.refresh(job)
    return job


def discard_job(db: Session, org_id: uuid.UUID, job_id: uuid.UUID) -> ImportJob:
    job = get_job(db, org_id, job_id)
    job.status = ImportStatus.discarded
    db.commit()
    db.refresh(job)
    return job


def _safe_email(value) -> str | None:
    if value and isinstance(value, str) and EMAIL_RE.fullmatch(value.strip()):
        return value.strip()
    return None


def _status_enum(value) -> StudentStatus:
    if isinstance(value, str):
        for s in StudentStatus:
            if value.strip().lower() == s.value:
                return s
    return StudentStatus.active
