"""Guardian service (CO-S02).

A student may have multiple guardians; one (or more) can be ``is_primary``.

Minor students are flagged by the first-class ``students.is_minor`` column. For a
minor student we enforce that at least one primary guardian remains — you cannot
delete or demote the last primary guardian of a minor.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import scoped
from app.core.errors import AppError
from app.models.student import Guardian, Student
from app.schemas.guardians import GuardianCreate, GuardianUpdate


def _get_student(
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


def is_minor(student: Student) -> bool:
    return bool(student.is_minor)


def _get_guardian(
    db: Session, org_id: uuid.UUID, guardian_id: uuid.UUID
) -> Guardian:
    stmt = scoped(select(Guardian), org_id, Guardian).where(
        Guardian.id == guardian_id
    )
    guardian = db.scalar(stmt)
    if guardian is None:
        raise AppError(
            "Guardian not found", code="not_found", status_code=404
        )
    return guardian


def _primary_count(
    db: Session, org_id: uuid.UUID, student_id: uuid.UUID
) -> int:
    stmt = scoped(select(Guardian), org_id, Guardian).where(
        Guardian.student_id == student_id, Guardian.is_primary.is_(True)
    )
    return len(db.scalars(stmt).all())


def list_guardians(
    db: Session, org_id: uuid.UUID, student_id: uuid.UUID | None = None
) -> list[Guardian]:
    stmt = scoped(select(Guardian), org_id, Guardian)
    if student_id is not None:
        stmt = stmt.where(Guardian.student_id == student_id)
    stmt = stmt.order_by(
        Guardian.is_primary.desc(), Guardian.created_at.asc()
    )
    return list(db.scalars(stmt).all())


def create_guardian(
    db: Session, org_id: uuid.UUID, data: GuardianCreate
) -> Guardian:
    # Student must exist within this org (also blocks cross-tenant attach).
    _get_student(db, org_id, data.student_id)
    guardian = Guardian(
        org_id=org_id,
        student_id=data.student_id,
        name=data.name.strip(),
        relationship=data.relationship,
        email=data.email,
        phone=data.phone,
        is_primary=data.is_primary,
    )
    db.add(guardian)
    db.commit()
    db.refresh(guardian)
    return guardian


def update_guardian(
    db: Session,
    org_id: uuid.UUID,
    guardian_id: uuid.UUID,
    data: GuardianUpdate,
) -> Guardian:
    guardian = _get_guardian(db, org_id, guardian_id)
    fields = data.model_dump(exclude_unset=True)

    demoting_primary = (
        guardian.is_primary and fields.get("is_primary") is False
    )
    if demoting_primary:
        student = _get_student(db, org_id, guardian.student_id)
        if is_minor(student) and _primary_count(
            db, org_id, guardian.student_id
        ) <= 1:
            raise AppError(
                "A minor student must keep at least one primary guardian",
                code="primary_guardian_required",
                status_code=422,
            )

    if "name" in fields and fields["name"] is not None:
        guardian.name = fields["name"].strip()
    if "relationship" in fields:
        guardian.relationship = fields["relationship"]
    if "email" in fields:
        guardian.email = fields["email"]
    if "phone" in fields:
        guardian.phone = fields["phone"]
    if "is_primary" in fields and fields["is_primary"] is not None:
        guardian.is_primary = fields["is_primary"]

    db.commit()
    db.refresh(guardian)
    return guardian


def delete_guardian(
    db: Session, org_id: uuid.UUID, guardian_id: uuid.UUID
) -> None:
    guardian = _get_guardian(db, org_id, guardian_id)
    if guardian.is_primary:
        student = _get_student(db, org_id, guardian.student_id)
        if is_minor(student) and _primary_count(
            db, org_id, guardian.student_id
        ) <= 1:
            raise AppError(
                "A minor student must keep at least one primary guardian",
                code="primary_guardian_required",
                status_code=422,
            )
    db.delete(guardian)
    db.commit()
