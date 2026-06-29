"""LLM-backed smart-import parser (CO-A01).

``parse_import(raw)`` turns messy pasted text / CSV into the SAME candidate
structure the deterministic heuristic in :mod:`app.services.imports` produces, so
the existing review -> commit state machine and ``schemas/imports`` contract keep
working unchanged.

Flow (per §1.4 — only ever a CANDIDATE, never a write):

1. If an API key is configured, ask the LLM to extract structured students
   (name / email / phone split, guardian split, free-text recurring lessons like
   "Tue/Thu 4-5pm" -> a recurrence-rule draft).
2. Validate the reply against a strict schema.
3. On ANY problem — no key, network error, malformed/empty output, validation
   failure — fall back to the deterministic heuristic ``imports.parse_text``.

The heuristic is imported lazily to avoid an import cycle (``imports`` imports
this module at top level).
"""
from __future__ import annotations

import logging

from pydantic import BaseModel, ConfigDict, ValidationError
from pydantic.alias_generators import to_camel

from app.ai import llm
from app.models.enums import StudentStatus

logger = logging.getLogger("coachowl.ai.import_parser")

_SYSTEM = (
    "You convert a tutor's messy roster paste (CSV-ish or free text, possibly "
    "in mixed English/Chinese) into structured student records. Extract only "
    "what is present — never invent contact details. Split the student's own "
    "name/email/phone from a guardian's. Turn free-text recurring lesson times "
    'like "Tue/Thu 4-5pm" or "周二周四4-5pm" into a recurrence draft.'
)

_PROMPT = (
    "Return ONLY minified JSON: an array of student objects. Each object keys:\n"
    '  name (string), email (string|null), phone (string|null),\n'
    '  status ("active"|"paused"|"archived"|null), tags (array of strings),\n'
    "  notes (string|null), scheduleText (string|null),\n"
    "  recurrence (object|null) with keys daysOfWeek (array of two-letter codes "
    "MO TU WE TH FR SA SU), startTime ('HH:MM' 24h|null), endTime ('HH:MM'|null),\n"
    "  guardians (array of {name, relationship|null, email|null, phone|null}).\n"
    "Do not wrap in markdown. Roster:\n\n"
)


# --------------------------------------------------------------------------- #
# Strict validation models for the LLM reply
# --------------------------------------------------------------------------- #
# camelCase JSON aliases (what the model emits) <-> snake_case fields, matching
# the project's CamelModel convention. ``populate_by_name`` also tolerates a
# model that replies in snake_case.
_AI_MODEL_CONFIG = ConfigDict(
    extra="ignore", alias_generator=to_camel, populate_by_name=True
)


class _LLMRecurrence(BaseModel):
    model_config = _AI_MODEL_CONFIG

    days_of_week: list[str] = []
    start_time: str | None = None
    end_time: str | None = None


class _LLMGuardian(BaseModel):
    model_config = _AI_MODEL_CONFIG

    name: str
    relationship: str | None = None
    email: str | None = None
    phone: str | None = None


class _LLMStudent(BaseModel):
    model_config = _AI_MODEL_CONFIG

    name: str = ""
    email: str | None = None
    phone: str | None = None
    status: str | None = None
    tags: list[str] = []
    notes: str | None = None
    schedule_text: str | None = None
    recurrence: _LLMRecurrence | None = None
    guardians: list[_LLMGuardian] = []


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #
def parse_import(raw: str) -> dict:
    """Return a candidate structure ``{source, columns, candidates}``.

    LLM-first when configured, otherwise (or on any failure) the deterministic
    heuristic. Never raises; never persists.
    """
    from app.services import imports as heuristic  # lazy: avoid import cycle

    text = (raw or "").strip()
    if not text or not llm.is_available():
        return heuristic.parse_text(raw)

    try:
        parsed = _parse_with_llm(text, heuristic)
    except (LLMParseError, llm.LLMUnavailableError, ValidationError) as exc:
        logger.info("import_parser falling back to heuristic: %s", exc)
        return heuristic.parse_text(raw)

    return parsed


class LLMParseError(RuntimeError):
    """LLM reply was syntactically fine but unusable (e.g. zero students)."""


def _parse_with_llm(text: str, heuristic) -> dict:
    obj = llm.structured_complete(_PROMPT + text, system=_SYSTEM)
    rows = obj if isinstance(obj, list) else obj.get("candidates") or obj.get("students")
    if not isinstance(rows, list) or not rows:
        raise LLMParseError("model returned no student array")

    students = [_LLMStudent.model_validate(r) for r in rows]
    candidates = [_to_candidate(s, heuristic) for s in students]
    candidates = [c for c in candidates if c is not None]
    if not candidates:
        raise LLMParseError("no usable candidates after validation")

    logger.info("import_parser produced %d candidate(s) via LLM", len(candidates))
    return {"source": "llm", "columns": [], "candidates": candidates}


# --------------------------------------------------------------------------- #
# Normalisation -> the heuristic's candidate shape (commit-path compatible)
# --------------------------------------------------------------------------- #
def _to_candidate(s: _LLMStudent, heuristic) -> dict | None:
    name = (s.name or "").strip()
    email = _clean_email(s.email, heuristic)
    phone = _clean_phone(s.phone, heuristic)

    guardians: list[dict] = []
    for idx, g in enumerate(s.guardians):
        gname = (g.name or "").strip()
        if not gname:
            continue
        guardians.append(
            {
                "name": gname,
                "relationship": (g.relationship or None),
                "email": _clean_email(g.email, heuristic),
                "phone": _clean_phone(g.phone, heuristic),
                "isPrimary": idx == 0,
            }
        )

    tags = _dedupe([t.strip() for t in s.tags if t and t.strip()])

    cand: dict = {
        "name": name,
        "email": email,
        "phone": phone,
        "status": _norm_status(s.status),
        "tags": tags,
        "notes": (s.notes or None),
        "scheduleText": (s.schedule_text or None),
        "guardians": guardians,
        "confidence": 1.0,
        "warnings": [],
    }
    if s.recurrence is not None:
        rec = s.recurrence.model_dump(by_alias=True)
        if any(rec.values()):
            cand["recurrence"] = rec

    _apply_confidence(cand)
    # Drop rows the model emitted with neither a name nor any contact at all.
    if not name and not email and not phone and not guardians:
        return None
    return cand


def _apply_confidence(cand: dict) -> None:
    confidence = 1.0
    if not cand["name"]:
        confidence -= 0.5
        cand["warnings"].append("No name detected — please fill it in.")
    if cand["email"] is None and cand["phone"] is None and not cand["guardians"]:
        confidence -= 0.2
        cand["warnings"].append("No contact details detected.")
    cand["confidence"] = round(max(0.0, confidence), 2)


def _clean_email(value: str | None, heuristic) -> str | None:
    if not value:
        return None
    return heuristic._first_email(value)


def _clean_phone(value: str | None, heuristic) -> str | None:
    if not value:
        return None
    return heuristic._first_phone(value) or value.strip() or None


def _norm_status(value: str | None) -> str:
    if isinstance(value, str):
        low = value.strip().lower()
        for s in StudentStatus:
            if low == s.value:
                return s.value
    return StudentStatus.active.value


def _dedupe(items: list[str]) -> list[str]:
    seen: list[str] = []
    for it in items:
        if it and it not in seen:
            seen.append(it)
    return seen
