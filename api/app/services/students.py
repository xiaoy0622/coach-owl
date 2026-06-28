"""Student CRM service (CO-S01).

All access is org-scoped: every query passes through ``scoped(...)`` so a caller
can never read or mutate another tenant's rows. Listing uses keyset (cursor)
pagination ordered by ``(created_at, id)`` so it is stable under inserts.
"""
from __future__ import annotations

import base64
import binascii
import uuid
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.deps import scoped
from app.core.errors import AppError
from app.models.enums import StudentStatus
from app.models.student import Student
from app.schemas.students import StudentCreate, StudentUpdate

_DEFAULT_LIMIT = 50
_MAX_LIMIT = 200


def _encode_cursor(item: Student) -> str:
    raw = f"{item.created_at.isoformat()}|{item.id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        created_raw, id_raw = raw.split("|", 1)
        return datetime.fromisoformat(created_raw), uuid.UUID(id_raw)
    except (ValueError, binascii.Error) as exc:
        raise AppError(
            "Invalid pagination cursor",
            code="invalid_cursor",
            status_code=400,
        ) from exc


def create_student(
    db: Session, org_id: uuid.UUID, data: StudentCreate
) -> Student:
    student = Student(
        org_id=org_id,
        name=data.name.strip(),
        email=data.email,
        phone=data.phone,
        status=data.status,
        tags=_clean_tags(data.tags),
        notes=data.notes,
        is_minor=data.is_minor,
        date_of_birth=data.date_of_birth,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


def get_student(
    db: Session, org_id: uuid.UUID, student_id: uuid.UUID
) -> Student:
    stmt = scoped(select(Student), org_id, Student).where(
        Student.id == student_id
    )
    student = db.scalar(stmt)
    if student is None:
        raise AppError(
            "Student not found", code="not_found", status_code=404
        )
    return student


def list_students(
    db: Session,
    org_id: uuid.UUID,
    *,
    limit: int = _DEFAULT_LIMIT,
    cursor: str | None = None,
    search: str | None = None,
    status: StudentStatus | None = None,
    tag: str | None = None,
) -> tuple[list[Student], str | None]:
    limit = max(1, min(limit, _MAX_LIMIT))

    stmt = scoped(select(Student), org_id, Student)

    if search:
        term = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Student.name.ilike(term),
                Student.email.ilike(term),
                Student.phone.ilike(term),
            )
        )
    if status is not None:
        stmt = stmt.where(Student.status == status)
    if tag:
        # Postgres array containment: the student carries this tag.
        stmt = stmt.where(Student.tags.contains([tag]))

    stmt = stmt.order_by(Student.created_at.asc(), Student.id.asc())

    if cursor:
        c_created, c_id = _decode_cursor(cursor)
        # Keyset: strictly after the (created_at, id) of the last seen row.
        stmt = stmt.where(
            (Student.created_at, Student.id) > (c_created, c_id)
        )

    rows = db.scalars(stmt.limit(limit + 1)).all()
    has_more = len(rows) > limit
    items = list(rows[:limit])
    next_cursor = _encode_cursor(items[-1]) if has_more and items else None
    return items, next_cursor


def update_student(
    db: Session,
    org_id: uuid.UUID,
    student_id: uuid.UUID,
    data: StudentUpdate,
) -> Student:
    student = get_student(db, org_id, student_id)
    fields = data.model_dump(exclude_unset=True)

    if "name" in fields and fields["name"] is not None:
        student.name = fields["name"].strip()
    if "email" in fields:
        student.email = fields["email"]
    if "phone" in fields:
        student.phone = fields["phone"]
    if "status" in fields and fields["status"] is not None:
        student.status = fields["status"]
    if "tags" in fields and fields["tags"] is not None:
        student.tags = _clean_tags(fields["tags"])
    if "notes" in fields:
        student.notes = fields["notes"]
    if "is_minor" in fields and fields["is_minor"] is not None:
        student.is_minor = fields["is_minor"]
    if "date_of_birth" in fields:
        student.date_of_birth = fields["date_of_birth"]

    db.commit()
    db.refresh(student)
    return student


def delete_student(
    db: Session, org_id: uuid.UUID, student_id: uuid.UUID
) -> None:
    student = get_student(db, org_id, student_id)
    db.delete(student)
    db.commit()


def _clean_tags(tags: list[str] | None) -> list[str]:
    if not tags:
        return []
    seen: list[str] = []
    for t in tags:
        t = t.strip()
        if t and t not in seen:
            seen.append(t)
    return seen
