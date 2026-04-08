# External Integrations

**Analysis Date:** 2026-04-07

## APIs & External Services

**Solar Inverter Providers (data collection):**

- **Huawei FusionSolar** — Solar plant monitoring data (usinas, inversores, alertas)
  - SDK/Client: `requests.Session` with custom auth (cookie-based XSRF-TOKEN)
  - Auth: Session login (username + system_code), token cached in DB (`CacheTokenProvedor`)
  - Base URL: `https://intl.fusionsolar.huawei.com/thirdData`
  - Key endpoints: `/login`, `/getStationList`, `/getDevRealKpi`, `/getAlarmList`
  - Rate limit: 1 req/5s (enforced via Redis-backed `LimitadorRequisicoes`)
  - Re-login: automatic on HTTP 401 or `failCode=305` in response
  - Implementation: `backend_monitoramento/provedores/fusionsolar/`

- **Hoymiles S-Cloud** — Solar plant monitoring data (usinas, inversores, alertas)
  - SDK/Client: `requests` with multi-step password hashing (MD5+SHA256 or Argon2 for v3)
  - Auth: Token-based (`POST /iam/pub/3/auth/login`), token cached in DB
  - Base URL: `https://neapi.hoymiles.com`
  - Key endpoints: `/iam/pub/3/auth/pre-insp`, `/iam/pub/3/auth/login`, `/pvm-data/api/0/module/data/down_module_day_data`
  - Rate limit: 5 req/10s (enforced via Redis-backed `LimitadorRequisicoes`)
  - Implementation: `backend_monitoramento/provedores/hoymiles/`

- **Solis Cloud** — Solar plant monitoring data (usinas, inversores, alertas)
  - SDK/Client: `requests` with stateless HMAC-SHA1 request signing per call
  - Auth: API key + app secret; each request signed with `Authorization: API {api_key}:{hmac_signature}`
  - Base URL: `https://www.soliscloud.com:13333`
  - Rate limit: 3 req/5s (enforced via Redis-backed `LimitadorRequisicoes`)
  - Implementation: `backend_monitoramento/provedores/solis/`

**WhatsApp Notification (two providers, runtime-configurable):**

- **Meta Cloud API** — WhatsApp message delivery
  - SDK/Client: `requests.post` to `https://graph.facebook.com/v19.0/{phone_id}/messages`
  - Auth: Bearer token (`WHATSAPP_API_TOKEN`)
  - Env vars: `WHATSAPP_PROVEDOR=meta`, `WHATSAPP_API_TOKEN`, `WHATSAPP_PHONE_ID`
  - Implementation: `backend_monitoramento/notificacoes/backends/whatsapp.py` (`_enviar_meta`)

- **Evolution API (self-hosted)** — WhatsApp message delivery via self-hosted gateway
  - Container: `evoapicloud/evolution-api:latest` running as a sidecar in `backend_monitoramento/docker-compose.yml`
  - Internal URL: `http://evolution-api:8080` (Docker service name)
  - Auth: `apikey` header (`WHATSAPP_EVOLUTION_TOKEN`)
  - Env vars: `WHATSAPP_PROVEDOR=evolution`, `WHATSAPP_EVOLUTION_URL`, `WHATSAPP_EVOLUTION_TOKEN`, `WHATSAPP_EVOLUTION_INSTANCIA`
  - Implementation: `backend_monitoramento/notificacoes/backends/whatsapp.py` (`_enviar_evolution`)

**Email (SMTP):**
- Any SMTP server (defaults to `smtp.gmail.com:587` in `.env.example`)
- Django's built-in `send_mail` via `django.core.mail`
- Auth: `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD`
- Env vars: `EMAIL_HOST`, `EMAIL_PORTA`, `EMAIL_USUARIO`, `EMAIL_SENHA`, `NOTIFICACAO_EMAIL_DE`
- Implementation: `backend_monitoramento/notificacoes/backends/email.py`

**Error Tracking:**
- **Sentry** — Exception monitoring in production
  - SDK: `sentry-sdk==2.*` (installed only in `requirements/prod.txt`)
  - No explicit Sentry `init()` call found in settings — likely auto-configured or not yet fully wired

## Data Storage

**Databases:**
- **PostgreSQL 16** (main application database)
  - Engine: `django.db.backends.postgresql` via `psycopg2-binary`
  - Connection env vars: `DB_NOME`, `DB_USUARIO`, `DB_SENHA`, `DB_HOST`, `DB_PORTA`
  - Container: `db` service in `backend_monitoramento/docker-compose.yml`
  - Data volume: `../data/postgres`
  - Grafana reads directly from this database via the `firmasolar_obs` Docker network

- **PostgreSQL — Evolution API database** (separate DB in same PostgreSQL instance)
  - Database name: `evolution`
  - Used by the Evolution API container (Prisma ORM internally)
  - Connection: `postgresql://${DB_USUARIO}:${DB_SENHA}@db:5432/evolution`

**Caching / Message Broker:**
- **Redis 7** — Dual purpose
  - DB 0: Celery broker URL and result backend (`REDIS_URL=redis://redis:6379/0`); also used by `LimitadorRequisicoes` for sliding window rate limiting per provider
  - DB 1: Evolution API cache (`CACHE_REDIS_URI=redis://redis:6379/1`)
  - Container: `redis` service in `backend_monitoramento/docker-compose.yml`
  - Data volume: `../data/redis`

**File Storage:**
- Static files: served locally via WhiteNoise (`staticfiles/` directory)
- Evolution API instance data: `../data/evolution` volume

**Caching:**
- No application-level cache (no Django caching framework configured)
- Redis used only for Celery and rate limiting

## Authentication & Identity

**Auth Provider:**
- Django's built-in authentication (`django.contrib.auth`)
- No third-party auth provider (no OAuth, no JWT)
- Admin interface protected by Django session auth

**Provider Credential Storage:**
- Credentials stored encrypted in PostgreSQL (`provedores.CredencialProvedor.credenciais_enc`)
- Encryption: Fernet symmetric encryption (`cryptography` library)
- Key: `CHAVE_CRIPTOGRAFIA` env var
- Implementation: `backend_monitoramento/provedores/cripto.py`

**Token Cache:**
- Session tokens for FusionSolar and Hoymiles stored encrypted in `provedores.CacheTokenProvedor`
- Refreshed every 6h by `renovar_tokens_provedores` Celery task

## Monitoring & Observability

**Dashboards:**
- **Grafana 10.4.0** — Primary UI for monitoring data
  - Datasource: PostgreSQL (direct DB read via `firmasolar_obs` network)
  - Provisioning: `frontend/grafana/provisioning/datasources/postgres.yml`
  - Dashboards: JSON files in `frontend/grafana/dashboards/`
  - Container port: 3000 (loopback only, behind reverse proxy)
  - URL: `https://monitoramento.firmasolar.com.br`

**Error Tracking:**
- Sentry SDK installed in production (`sentry-sdk==2.*`)

**Logs:**
- Development: formatted text to stdout (`{levelname} {name}: {message}`)
- Production: structured JSON to stdout (one JSON line per log event, via `FormataJSON` formatter in `config/settings/prod.py`)
- No external log aggregation service configured

## CI/CD & Deployment

**Hosting:**
- VPS at `monitoramento.firmasolar.com.br`
- Accessed via SSH

**CI Pipeline:**
- None detected (no GitHub Actions, CircleCI, etc.)

**Deployment:**
- Manual: `git pull` + Docker Compose restart on VPS (per CLAUDE.md — never automatic)

## Webhooks & Callbacks

**Incoming:**
- None detected (no webhook receiver endpoints found)

**Outgoing:**
- WhatsApp messages sent outbound (Meta Cloud API or Evolution API) when alerts trigger
- Email sent outbound via SMTP when alerts trigger

## Rate Limiting Architecture

Provider API rate limits are enforced centrally in `backend_monitoramento/provedores/limitador.py` using Redis sliding window counters shared across all Celery workers:

| Provider    | Limit        | Notes                              |
|-------------|-------------|-------------------------------------|
| Solis       | 3 req/5s    | Documented by Solis                |
| Hoymiles    | 5 req/10s   | Empirically determined             |
| FusionSolar | 1 req/5s    | Strict; also has min collection interval |
| Solarman    | 10 req/60s  | Defined but no Solarman adapter yet |

---

*Integration audit: 2026-04-07*
