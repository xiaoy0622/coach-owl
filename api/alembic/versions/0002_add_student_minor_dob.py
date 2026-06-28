"""add student is_minor + date_of_birth

Replaces the interim "minor = `minor` tag" hack with first-class columns:
``students.is_minor`` (bool, NOT NULL default false) drives the primary-guardian
rule, and ``students.date_of_birth`` (date, nullable) records DOB.

Idempotent (ADD/DROP COLUMN IF [NOT] EXISTS) so it is safe to re-run.

Revision ID: 0002_add_student_minor_dob
Revises: 0001_initial
Create Date: 2026-06-28
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0002_add_student_minor_dob'
down_revision: Union[str, None] = '0001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE students "
        "ADD COLUMN IF NOT EXISTS is_minor BOOLEAN NOT NULL DEFAULT false"
    )
    op.execute(
        "ALTER TABLE students ADD COLUMN IF NOT EXISTS date_of_birth DATE"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE students DROP COLUMN IF EXISTS date_of_birth")
    op.execute("ALTER TABLE students DROP COLUMN IF EXISTS is_minor")
