"""Read-only share links service (CO-W06).

A share link is a no-login, org-scoped pointer to a single student's *read-only*
schedule + credit balance. The management side (create / list / revoke) is fully
org-scoped — a caller can only ever touch links for students in their own org.

The public side resolves a bare ``token`` (no auth, no org context) into exactly
one student's name, upcoming lessons and current credit balance — and nothing
else. Expired or revoked (deleted) tokens are rejected so a stale link leaks no
data. Lesson + balance data is read through the Scheduling and Credits services
so this stream never re-implements those rules.
"""
from __future__ import annotations

import secrets
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.enums import LessonStatus
from app.models.share_links import ShareLink
from app.models.student import Student
from app.schemas.share_links import (
    PublicLessonOut,
    PublicShareOut,
    ShareLinkCreate,
)
from app.services import credits as credits_service
from app.services import scheduling as scheduling_service

# How many upcoming lessons the public page shows.
PUBLIC_UPCOMING_LIMIT = 20
# Token length in URL-safe bytes (~43 chars, well within String(64)).
_TOKEN_BYTES = 32


def _require_student(
    db: Session, org_id: uuid.UUID, student_id: uuid.UUID
) -> Student:
    """Org-scoped student lookup (404 if missing or another tenant's)."""
    student = db.scalar(
        select(Student).where(
            Student.id == student_id, Student.org_id == org_id
        )
    )
    if student is None:
        raise AppError("Student not found", code="not_found", status_code=404)
    return student


def _generate_token(db: Session) -> str:
    """A cryptographically-random, unique share token."""
    for _ in range(5):
        token = secrets.token_urlsafe(_TOKEN_BYTES)
        exists = db.scalar(
            select(ShareLink.id).where(ShareLink.token == token)
        )
        if exists is None:
            return token
    raise AppError(  # pragma: no cover — astronomically unlikely
        "Could not generate a unique share token",
        code="token_generation_failed",
        status_code=500,
    )


def create_share_link(
    db: Session, org_id: uuid.UUID, body: ShareLinkCreate
) -> ShareLink:
    """Create a read-only share link for one of the org's students."""
    _require_student(db, org_id, body.student_id)

    link = ShareLink(
        org_id=org_id,
        student_id=body.student_id,
        token=_generate_token(db),
        expires_at=body.expires_at,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def list_share_links(
    db: Session, org_id: uuid.UUID, student_id: uuid.UUID | None = None
) -> Sequence[ShareLink]:
    """List the org's share links, newest first (optionally per student)."""
    stmt = select(ShareLink).where(ShareLink.org_id == org_id)
    if student_id is not None:
        stmt = stmt.where(ShareLink.student_id == student_id)
    stmt = stmt.order_by(ShareLink.created_at.desc())
    return list(db.scalars(stmt))


def revoke_share_link(
    db: Session, org_id: uuid.UUID, link_id: uuid.UUID
) -> None:
    """Delete (revoke) a share link. 404 if it's missing or another org's."""
    link = db.scalar(
        select(ShareLink).where(
            ShareLink.id == link_id, ShareLink.org_id == org_id
        )
    )
    if link is None:
        raise AppError(
            "Share link not found", code="not_found", status_code=404
        )
    db.delete(link)
    db.commit()


def resolve_public_share(db: Session, token: str) -> PublicShareOut:
    """Resolve a public token → one student's schedule + balance.

    No auth and no org context: the org is taken from the link itself. Revoked
    (deleted) tokens → 404; expired tokens → 410. Nothing beyond that single
    student's name, upcoming lessons and credit balance is exposed.
    """
    link = db.scalar(select(ShareLink).where(ShareLink.token == token))
    if link is None:
        raise AppError(
            "This share link is invalid", code="not_found", status_code=404
        )
    if link.expires_at is not None and link.expires_at <= datetime.now(UTC):
        raise AppError(
            "This share link has expired", code="expired", status_code=410
        )

    student = _require_student(db, link.org_id, link.student_id)
    tz_name = scheduling_service.org_timezone(db, link.org_id)
    balance = credits_service.get_balance(db, link.org_id, student.id)

    # Reuse the scheduling service to fetch upcoming lessons, then narrow to
    # this one student's still-scheduled sessions (next N).
    now = datetime.now(UTC)
    lessons = scheduling_service.list_lessons(db, link.org_id, now, None)
    upcoming = [
        PublicLessonOut(
            starts_at=lesson.starts_at,
            duration_min=lesson.duration_min,
            location=lesson.location,
            meeting_url=lesson.meeting_url,
        )
        for lesson in lessons
        if lesson.student_id == student.id
        and lesson.status == LessonStatus.scheduled
    ][:PUBLIC_UPCOMING_LIMIT]

    return PublicShareOut(
        student_name=student.name,
        timezone=tz_name,
        credit_balance=balance,
        upcoming_lessons=upcoming,
    )
