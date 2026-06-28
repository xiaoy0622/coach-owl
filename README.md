# CoachOwl

A lightweight tutor/coach management SaaS for the Australian market — scheduling,
credit packs/balances, payments + GST invoices, and channel-agnostic reminders,
with AI smart-import and lesson notes as the differentiating wedge.

See `CoachOwl-PRD-v0.md` (product) and `CoachOwl-Execution-Plan-v0.md` (plan,
the source of truth for the data model and API conventions).

## Repo layout

```
api/        FastAPI backend (this wave) — see api/README.md
web/        React + Vite frontend (separate workstream)
landing/    marketing site
docs/       openapi.json (generated)
docker-compose.yml
.env.example
```

## Quick start

```bash
cp .env.example .env            # adjust JWT_SECRET etc.
docker compose up -d postgres redis

# Backend (host venv):
python3 -m venv api/.venv
api/.venv/bin/pip install -r api/requirements.txt
export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5434/coachowl
(cd api && ../api/.venv/bin/alembic upgrade head)
(cd api && ../api/.venv/bin/uvicorn app.main:app --reload --port 8000)
# -> http://localhost:8000/api/health  and  /docs
```

Or run the whole stack in containers:

```bash
docker compose up --build      # api on http://localhost:8001 (see note below)
```

## Services & ports

| Service  | Container | Host port | Notes |
|----------|-----------|-----------|-------|
| api      | 8000      | **8001**  | host 8000 was occupied in this env; published on 8001 |
| postgres | 5432      | **5434**  | host 5433 was occupied; db `coachowl`, volume `coachowl_pgdata` |
| redis    | 6379      | **6380**  | for background jobs (later waves) |

## Environment

Copy `.env.example` → `.env`. Key vars: `DATABASE_URL`, `JWT_SECRET`,
`REDIS_URL`, plus AU org defaults (`DEFAULT_TIMEZONE=Australia/Sydney`,
`DEFAULT_CURRENCY=AUD`, `DEFAULT_GST_RATE=0.10`).

## Status

Wave 0–1 (backend foundation) is in place: app factory + health, full §4 data
model + one Alembic migration (up/down verified), JWT auth + org onboarding,
Pydantic contracts and routers for every domain (auth + org implemented; the
rest return `501` until their wave), localization utilities, and tests
(auth, cross-tenant isolation, GST). See `api/README.md` for details.
