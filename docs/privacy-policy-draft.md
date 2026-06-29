# Privacy Policy — DRAFT

> **DRAFT — NOT LEGAL ADVICE.** This document is an internal working draft to
> guide CoachOwl's compliance with the Australian Privacy Act 1988 (Cth) and the
> Australian Privacy Principles (APPs). It must be reviewed by qualified legal
> counsel before publication. Do not present this to end users as-is.

## 1. Who we are

CoachOwl ("we", "us") provides scheduling, billing, and student-management
software to independent coaches and tutoring studios. Each studio is an
"organization" (tenant). Studios are the data controllers for the personal
information of their students and guardians; CoachOwl processes that information
on their behalf.

## 2. The information we collect

- **Account / coach data:** name, email, hashed password, role (owner/coach).
- **Student data:** name, contact details, status, tags, free-text notes, date
  of birth, and a minor flag.
- **Guardian data:** name, relationship, contact details for the guardians of
  (typically minor) students.
- **Operational data:** lessons, recurrence schedules, credit packs and ledger
  entries, payments, invoices, lesson notes, notifications, share links, and
  import jobs.

We collect only what is reasonably necessary to deliver the service (APP 3).

## 3. Minors and guardian data (APP 3, APP 6)

Many students are under 18. Where a student is flagged as a minor, we expect a
primary guardian to be recorded, and guardian contact details are treated as
sensitive. Personal information about minors is used solely to administer their
coaching (scheduling, billing, progress notes) and is never sold or used for
unrelated marketing. Guardians may exercise the access and deletion rights below
on behalf of a minor.

## 4. How we use information (APP 6)

Personal information is used only to operate the studio's account: scheduling
lessons, tracking credits and payments, issuing invoices, sending operational
notifications, and producing read-only schedule share links. We do not disclose
personal information to third parties except sub-processors strictly required to
run the service (e.g. hosting, email delivery).

## 5. Security (APP 11)

All tenant data is segregated by `org_id` and every query is org-scoped, so one
studio can never access another's data. Passwords are hashed (argon2). Access is
authenticated via short-lived tokens.

## 6. Access and correction (APP 12, APP 13)

A studio owner or coach may export **all** of their organization's data at any
time via the in-app data export (`GET /api/v1/compliance/export`), which returns
a complete JSON document of every record the organization holds. Corrections can
be made directly through the application.

## 7. Deletion and erasure

A studio owner may permanently delete their organization and **all** associated
data via `DELETE /api/v1/compliance/account`. This action:

- requires the owner role and an explicit confirmation matching the
  organization's name;
- removes every record (students, guardians, lessons, billing, notes, etc.) in a
  single transaction;
- is **irreversible** — there is no undo and no recovery once completed.

Individuals who want their personal information removed should contact their
studio, who can delete the relevant student/guardian records or the whole
account.

## 8. Retention

Personal information is retained for as long as the studio's account is active.
On account deletion, data is erased as described in §7. Backups follow our
standard retention schedule and are purged on a rolling basis.

## 9. Contact

Questions or complaints about privacy should be directed to the studio in the
first instance, or to CoachOwl support. Unresolved complaints may be referred to
the Office of the Australian Information Commissioner (OAIC).

---
*DRAFT v0 — pending legal review.*
