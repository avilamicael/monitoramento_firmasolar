# Technology Stack

**Analysis Date:** 2026-04-07

## Languages

**Primary:**
- Python 3.11 - All backend logic (API clients, data ingestion, tasks, models)

**Secondary:**
- JSON - Dashboard definitions in Grafana (`frontend/grafana/dashboards/`)
- YAML - Grafana provisioning configs (`frontend/grafana/provisioning/`)
- Shell - Container entrypoint (`backend_monitoramento/entrypoint.sh`)

## Runtime

**Environment:**
- Python 3.11-slim (Docker image)
- Timezone: `America/Sao_Paulo` (configured in Django settings and Celery)

**Package Manager:**
- pip (no Poetry or pipenv)
- Lockfile: Not present — requirements pinned with `==X.Y.*` glob constraints

## Frameworks

**Core:**
- Django 5.1.* - Web framework, ORM, admin interface, email, static files
  - Settings split: `config/settings/base.py`, `config/settings/dev.py`, `config/settings/prod.py`
  - WSGI: `config/wsgi.py` (no ASGI — no async views used)

**Task Queue:**
- Celery 5.4.* - Async task execution and periodic scheduling
  - Beat schedules: every 10min (data collection), every 6h (token refresh), daily at 3h (cleanup)
  - Concurrency: 2 workers per container
  - Config: `config/celery.py`

**Testing:**
- pytest 8.* - Test runner
- pytest-django 4.* - Django integration for pytest
- factory-boy 3.* - Test data factories
- Config: `backend_monitoramento/pytest.ini`

**Build/Dev:**
- gunicorn 23.* - WSGI server (2 workers, port 8000)
- whitenoise 6.* - Static file serving in production
- django-debug-toolbar 4.* - Development only

## Key Dependencies

**Critical:**
- `django==5.1.*` - Core framework: ORM, admin, email, middleware
- `celery==5.4.*` - Distributed task queue; powers all data collection scheduling
- `psycopg2-binary==2.9.*` - PostgreSQL driver (Django ORM)
- `redis==5.2.*` - Redis client; used for Celery broker/backend and rate limiter
- `cryptography==43.*` - Fernet symmetric encryption for provider credentials at rest
- `requests==2.32.*` - HTTP client for all external solar provider API calls

**Infrastructure:**
- `python-dotenv==1.0.*` - `.env` loading in dev environment (dev.py only)
- `gunicorn==23.*` - Production WSGI server
- `whitenoise==6.*` - Production static file serving
- `sentry-sdk==2.*` - Error tracking (prod only, in `requirements/prod.txt`)

## Configuration

**Environment:**
- All configuration via environment variables, no hardcoded values
- Template: `backend_monitoramento/.env.example`
- Dev: loaded from `.env` file via `python-dotenv`
- Prod: injected by Docker Compose via `env_file: .env`

**Required environment variables:**
- `DJANGO_SECRET_KEY` - Django secret
- `DEBUG` - `true`/`false`
- `ALLOWED_HOSTS` - Comma-separated hostnames
- `DB_NOME`, `DB_USUARIO`, `DB_SENHA`, `DB_HOST`, `DB_PORTA` - PostgreSQL
- `REDIS_URL` - Redis connection string (e.g. `redis://redis:6379/0`)
- `CHAVE_CRIPTOGRAFIA` - Fernet key for credential encryption
- `EMAIL_HOST`, `EMAIL_PORTA`, `EMAIL_USUARIO`, `EMAIL_SENHA`, `NOTIFICACAO_EMAIL_DE` - SMTP
- `WHATSAPP_PROVEDOR` - `meta` or `evolution`
- `WHATSAPP_API_TOKEN`, `WHATSAPP_PHONE_ID` - Meta Cloud API (if `WHATSAPP_PROVEDOR=meta`)
- `WHATSAPP_EVOLUTION_URL`, `WHATSAPP_EVOLUTION_TOKEN`, `WHATSAPP_EVOLUTION_INSTANCIA` - Evolution API (if `WHATSAPP_PROVEDOR=evolution`)

**Build:**
- `backend_monitoramento/Dockerfile` - Python 3.11-slim, installs `requirements/base.txt`
- `backend_monitoramento/docker-compose.yml` - Orchestrates: db, redis, web, celery, beat, evolution-api
- `frontend/docker-compose.yml` - Orchestrates: grafana

## Infrastructure Services

**Containers (backend_monitoramento/docker-compose.yml):**
- `db`: PostgreSQL 16-alpine — main application database
- `redis`: Redis 7-alpine — Celery broker/result-backend and rate limiter state (db 0), Evolution API cache (db 1)
- `web`: Django + Gunicorn on port 8000 (loopback only)
- `celery`: Celery worker (concurrency 2)
- `beat`: Celery Beat scheduler
- `evolution-api`: Self-hosted WhatsApp gateway (evoapicloud/evolution-api:latest), port 8080 (loopback only)

**Containers (frontend/docker-compose.yml):**
- `grafana`: Grafana 10.4.0 — dashboards and alerting UI, port 3000 (loopback only)

**Networking:**
- Docker network `firmasolar_obs` (external, shared) connects Grafana to the backend PostgreSQL container

## Platform Requirements

**Development:**
- Docker + Docker Compose
- Python 3.11 (for local runs without Docker)
- `.env` file copied from `.env.example`

**Production:**
- VPS running Docker (deployed to `monitoramento.firmasolar.com.br`)
- Reverse proxy (nginx/caddy) in front of gunicorn (port 8000) and grafana (port 3000)
- Two separate `docker compose` stacks: backend and frontend (grafana)

---

*Stack analysis: 2026-04-07*
