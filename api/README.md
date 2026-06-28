# CoachOwl API

FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL 16 backend for CoachOwl — a
lightweight tutor/coach management SaaS for the Australian market.

## Stack

- **Python 3.12** · FastAPI · Pydantic v2 (+ pydantic-settings)
- **SQLAlchemy 2.0** (typed `Mapped`/`mapped_column`) · **Alembic** migrations
- **PostgreSQL 16** (uuid PKs, tz-aware timestamps, numeric money)
- **argon2** password hashing · **JWT** (Bearer) auth
- **pytest** + Starlette `TestClient` · **ruff** lint

## Layout

```
app/
  core/      config, db (Base + mixins), security, deps (tenancy), errors
  models/    ORM by domain (+ enums, _types); __init__ registers all tables
  schemas/   Pydantic request/response by domain (camelCase JSON)
  api/v1/    routers by domain (auth + org implemented; rest are 501 stubs)
  utils/     localization (AUD / GST / DD-MM-YYYY / timezone)
alembic/     migration env + versions/0001_initial_schema.py
scripts/     export_openapi.py
tests/       auth, tenant isolation, localization
```

## Run locally

Bring up Postgres + Redis (from the repo root):

```bash
docker compose up -d postgres redis     # postgres on host :5434, redis on :6380
```

Create a virtualenv and install deps:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Point at the DB and run migrations, then the app:

```bash
export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5434/coachowl
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload --port 8000
```

- Health: `GET http://localhost:8000/api/health` → `{"status":"ok"}`
- Interactive docs: `http://localhost:8000/docs`

## Migrations

```bash
.venv/bin/alembic upgrade head      # apply
.venv/bin/alembic downgrade base    # roll back to empty
.venv/bin/alembic revision --autogenerate -m "message"   # new migration
```

The single initial migration creates all §4 tables with `org_id` indexes,
FKs, enum CHECK constraints, and unique constraints (`notifications.dedupe_key`,
`users.email`, `invoices (org_id, number)`, `share_links.token`). An optional
Postgres RLS policy is included (commented) as defence-in-depth.

## Tests & lint

```bash
.venv/bin/pytest        # spins up a throwaway coachowl_test DB on :5434
.venv/bin/ruff check .
```

## OpenAPI export

```bash
.venv/bin/python scripts/export_openapi.py   # writes ../docs/openapi.json
```

## Auth contract

| Method | Path | Body | Result |
|--------|------|------|--------|
| POST | `/api/v1/auth/register` | `{email,password,name,orgName?}` | 201 `{token, user:{id,email,name,role,orgId}}` |
| POST | `/api/v1/auth/login` | `{email,password}` | 200 `{token, user:{…}}` / 401 |
| GET | `/api/v1/auth/me` | — (Bearer) | `{user:{…}, org:{id,name,timezone,currency,gstEnabled,gstRate}}` |
| PATCH | `/api/v1/org` | `{name?,timezone?,currency?,gstEnabled?,gstRate?}` (Bearer, owner) | updated org |

Auth: `Authorization: Bearer <jwt>`. JSON responses use **camelCase** keys;
money is serialised as a decimal string; datetimes are ISO-8601 UTC.

Registration creates an Organization (timezone `Australia/Sydney`, currency
`AUD`, `gstEnabled=false`, `gstRate=0.10`) and an owner User.
