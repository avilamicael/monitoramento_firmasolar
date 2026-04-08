# Architecture Patterns: DRF API + React Frontend

**Domain:** Solar monitoring admin panel — REST layer over existing Django pipeline
**Researched:** 2026-04-07
**Confidence:** HIGH (direct codebase analysis; patterns are standard DRF)

---

## Existing System Snapshot (What Must Not Break)

The current pipeline is a WSGI-only Django 5.1 project with no REST layer:

```
Celery Beat (10 min)
  → coletar_dados_provedor (Celery worker)
    → AdaptadorProvedor (Solis/Hoymiles/FusionSolar)
      → ServicoIngestao (atomic transaction)
        → PostgreSQL (Usina, SnapshotUsina, Inversor, SnapshotInversor, Alerta)
          → transaction.on_commit → enviar_notificacao_alerta (Celery)
```

Entry points that exist today: `celery beat`, `celery worker`, `gunicorn config.wsgi`, `manage.py`.
The only HTTP surface is `/admin/`. The `web` container (Gunicorn, port 8000) is underused — it serves only Django Admin today and will host the API without any container changes.

---

## Recommended Architecture

### Component Boundaries

```
┌──────────────────────────────────────────────────────────┐
│  React SPA (firmasolar/frontend/painel/)                 │
│  Vite + shadcn/ui + Recharts + react-leaflet             │
│  Communicates: HTTP/JSON over /api/v1/                   │
└──────────────────────┬───────────────────────────────────┘
                       │ JWT Bearer token
                       ▼
┌──────────────────────────────────────────────────────────┐
│  Django (Gunicorn :8000) — existing web container        │
│  ├── /admin/        → Django Admin (unchanged)           │
│  └── /api/v1/       → DRF (new)                         │
│      ├── auth/      → simplejwt (login, refresh)         │
│      ├── usinas/    → UsinaViewSet (read)                │
│      ├── inversores/→ InversorViewSet (read)             │
│      ├── alertas/   → AlertaViewSet (read + PATCH estado)│
│      ├── garantias/ → GarantiaViewSet (CRUD)             │
│      └── analytics/ → read-only function-based views     │
└──────────┬───────────────────────────────────────────────┘
           │ ORM (shared DB connection pool)
           ▼
┌──────────────────────────────────────────────────────────┐
│  PostgreSQL — existing, unchanged schema                  │
│  Written by: Celery workers (pipeline, always running)   │
│  Read by:    Gunicorn workers (API requests)             │
└──────────────────────────────────────────────────────────┘
```

The Celery pipeline and the REST API are **fully independent consumers of the same database**. Adding DRF does not touch any Celery task, model, or service class.

---

## Question-by-Question Decisions

### 1. Where to Place the DRF API

**Decision: a new dedicated `api` app.**

Do NOT scatter serializers and API views across the existing domain apps (`usinas`, `alertas`, etc.).

Rationale:
- The existing apps have a single, stable responsibility (data + business logic). Adding HTTP serialization concerns would violate that.
- A single `api/` app provides one place to find all REST-related code without hunting across apps.
- The domain apps already export their models cleanly. The `api` app imports from them as read-only consumers.
- When the API evolves (v2, new endpoints), all changes are isolated to one app.

Structure:
```
backend_monitoramento/api/
├── __init__.py
├── apps.py
├── urls.py               # router.register() calls
├── autenticacao/
│   └── views.py          # simplejwt TokenObtainPairView wrapper if needed
├── usinas/
│   ├── serializers.py
│   └── views.py
├── inversores/
│   ├── serializers.py
│   └── views.py
├── alertas/
│   ├── serializers.py
│   └── views.py
├── garantias/
│   ├── serializers.py
│   └── views.py
└── analytics/
    └── views.py          # function-based views with @api_view
```

Sub-directories within `api/` are justified because each resource has independent serializers and views. A flat structure (all serializers in one file) becomes unmaintainable beyond 3 resources.

### 2. URL Structure and Versioning

**Decision: `/api/v1/` prefix, hardcoded in `config/urls.py`.**

```python
# config/urls.py
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('api.urls')),
]
```

Rationale for `/api/v1/` over `/api/`:
- This is an internal admin panel, so a breaking v2 is unlikely in the short term — but the cost of including `v1` is zero.
- If the React frontend is ever rewritten or a mobile app is added, having the version in the URL allows running v1 and v2 in parallel without consumer downtime.
- Django's `include()` makes adding a `path('api/v2/', include('api_v2.urls'))` trivial later.

There is no need for content-negotiation-based versioning (Accept: application/vnd.api+json; version=2) — URL versioning is simpler and adequate for this use case.

### 3. React Project Placement

**Decision: Monorepo — `firmasolar/frontend/painel/` alongside the existing `frontend/grafana/`.**

```
firmasolar/
├── backend_monitoramento/   # Django project (existing)
├── frontend/
│   ├── grafana/             # existing Grafana dashboards
│   └── painel/              # NEW — React SPA (Vite)
├── data/
└── docs/
```

Rationale:
- The repo already has a `frontend/` directory with Grafana config. The React project belongs there, not in a separate repo.
- A separate repo would require coordinating two git histories, two CI pipelines, and cross-repo issue tracking for a single admin panel. That overhead is not justified for a solo/small team project.
- Monorepo allows one `docker-compose.yml` to define the entire system (backend + frontend build).
- The React app is a pure SPA (static files after `vite build`). It is served by Nginx in production, completely decoupled from Django at runtime. The monorepo is a development convenience, not a deployment coupling.

Trade-off acknowledged: If the React project grows into a multi-product frontend or requires a separate deployment pipeline, migration to a separate repo is straightforward (git subtree split).

### 4. Django Settings Integration for DRF

**Minimal changes — additive only, no existing keys touched.**

In `config/settings/base.py`, add a new section after the existing `APPS_LOCAIS` block:

```python
# ── DRF e API ──────────────────────────────────────────────────────────────────
THIRD_PARTY_APPS = [
    'rest_framework',
    'corsheaders',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + APPS_LOCAIS + ['api']

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
}

from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
}

CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',')
```

CORS middleware must be inserted **before** `SessionMiddleware` in the existing `MIDDLEWARE` list:

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',      # ADD HERE — must be before SessionMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    ...
]
```

The existing Celery settings (`CELERY_BROKER_URL`, `CELERY_BEAT_SCHEDULE`, `REDIS_URL`, `CHAVE_CRIPTOGRAFIA`) are untouched. The Celery workers share the same `base.py` settings file but ignore the DRF/CORS configuration entirely — it has no effect on worker processes.

In `config/settings/dev.py`, add:
```python
CORS_ALLOW_ALL_ORIGINS = True  # dev only — Vite dev server on :5173
```

In `config/settings/prod.py`, `CORS_ALLOWED_ORIGINS` is driven by the environment variable, e.g.:
```
CORS_ALLOWED_ORIGINS=https://monitoramento.firmasolar.com.br
```

New packages to add to `requirements/base.txt`:
```
djangorestframework==3.15.*
djangorestframework-simplejwt==5.3.*
django-cors-headers==4.4.*
```

### 5. Serializer Design: Nested vs. Separate Endpoints

**Decision: Separate endpoints with selective inline embedding, not deep nesting.**

The models form a hierarchy: `Usina → Inversor → SnapshotInversor`. A fully nested serializer approach (return all inversores with all their snapshots inside each usina) creates two problems:
1. Uncontrolled payload size — a usina with 20 inversores and 144 daily snapshots each would return thousands of objects per request.
2. Inflexibility — the dashboard needs usinas with only their `ultimo_snapshot`, not full snapshot history.

**Concrete pattern:**

`GET /api/v1/usinas/` — list view includes only the denormalized `ultimo_snapshot` inline:
```
Usina {
  id, nome, capacidade_kwp, provedor, status, ativo, endereco,
  ultimo_snapshot: { potencia_kw, energia_hoje_kwh, status, coletado_em }
}
```

`GET /api/v1/usinas/{id}/` — detail view adds inline inversor list (current state only, no history):
```
Usina {
  ...all fields...,
  ultimo_snapshot: { ...full snapshot fields... },
  inversores: [{ id, modelo, numero_serie, ultimo_snapshot: { pac_kw, estado } }]
}
```

`GET /api/v1/usinas/{id}/snapshots/` — separate nested route for historical time series (paginated). This is a `@action(detail=True)` on `UsinaViewSet`.

`GET /api/v1/inversores/{id}/snapshots/` — same pattern for inversor history.

This design keeps list payloads small (safe for polling at 10-min interval) while making detail views rich enough to avoid a second request in most cases.

The `payload_bruto` field (JSONField on all snapshot models) must be **excluded** from all serializers. It contains raw provider data that is internal-only and can be hundreds of KB.

### 6. Analytics Endpoints

**Decision: Function-based views with `@api_view(['GET'])` and explicit `select_related`/`annotate` queries.**

ViewSets are appropriate when you have a resource with CRUD operations and a natural router path. Analytics endpoints are computations, not resources — they do not map to a model instance and have no `list`/`retrieve`/`create`/`update` semantic. Using ViewSets for analytics introduces artificial routing overhead and makes the intent less readable.

Pattern for analytics views:
```python
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def potencia_total(request):
    resultado = (
        Usina.objects
        .filter(ativo=True)
        .select_related('ultimo_snapshot')
        .aggregate(total=Sum('ultimo_snapshot__potencia_kw'))
    )
    return Response(resultado)
```

Performance rules for all analytics queries:
- Always use `annotate()` + `aggregate()` in the database — never pull rows into Python and sum in code.
- Use `select_related('ultimo_snapshot')` on Usina queries that need current state — avoids N+1 (one query instead of N+1 where N = number of plants).
- For ranking queries (e.g., fabricante mais usado), use `values('provedor').annotate(count=Count('id'))` — single query, no Python loops.
- The `SnapshotUsina` table grows at ~6 rows/hour/usina. Time-range queries must always filter on the indexed `coletado_em` column. Never aggregate without a time filter.
- Analytics views that aggregate across all snapshots in a time range should be considered candidates for database-level materialized views or caching in a later phase — but this is not needed for initial implementation at the current scale.

Place all analytics views in `api/analytics/views.py` with their URL patterns registered manually in `api/urls.py` (not through the router).

### 7. Docker Compose Integration (React)

**Development:**

The Vite dev server runs on the host (not in Docker) during development — this is simpler and faster:
```bash
cd frontend/painel
npm run dev  # starts :5173 with HMR
```

The React dev server proxies `/api/` to `http://localhost:8000` via Vite config:
```js
// vite.config.ts
export default {
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    }
  }
}
```

No Docker changes needed for the development workflow.

**Production:**

Add a new `frontend` service to `docker-compose.yml` that serves the built React SPA via Nginx:

```yaml
frontend:
  image: nginx:alpine
  volumes:
    - ./frontend/painel/dist:/usr/share/nginx/html:ro
    - ./frontend/nginx.conf:/etc/nginx/conf.d/default.conf:ro
  ports:
    - "127.0.0.1:3000:80"
  restart: unless-stopped
```

The `nginx.conf` must handle client-side routing (React Router):
```nginx
location / {
  try_files $uri $uri/ /index.html;
}
```

The build step (`npm run build`) produces the `dist/` directory. This is a manual step in the deploy workflow — the container mounts the pre-built output, it does not build inside Docker. This keeps the Docker image small and avoids Node.js in production containers.

The reverse proxy (Nginx on the VPS host, not the container) routes traffic:
- `monitoramento.firmasolar.com.br` → port 3000 (React frontend)
- `monitoramento.firmasolar.com.br/api/` → port 8000 (Django)
- `monitoramento.firmasolar.com.br/admin/` → port 8000 (Django Admin)

---

## Build Order Implications

These are hard dependencies — each item requires the previous to be complete:

1. **DRF + settings integration** — must be done before any serializer or view exists. This is the foundation (`pip install`, `INSTALLED_APPS`, middleware, urls.py skeleton).

2. **GarantiaUsina model + migration** — the model is new and blocks the garantias endpoints. Migration must be run and verified before the serializer references it.

3. **Authentication endpoints** (`/api/v1/auth/token/`, `/api/v1/auth/token/refresh/`) — must exist and be testable before any other endpoint is built. The React app cannot make authenticated requests without this.

4. **Read-only resource endpoints** (usinas, inversores, alertas) — can be built in parallel once authentication works. Each is independent.

5. **Analytics endpoints** — depend on read-only resource endpoints being stable (the analytics queries reference the same models). Can start after step 4 is done.

6. **GarantiaUsina CRUD endpoints** — depends on step 2 (model + migration).

7. **React project scaffold** (Vite + shadcn/ui setup, routing, auth context) — can start once authentication endpoint (step 3) returns a valid JWT. Does not require all backend endpoints to exist.

8. **React feature pages** — each page depends on its specific API endpoint being stable. Dashboard depends on analytics; garantia page depends on step 6.

---

## Component Communication Table

| From | To | Protocol | Auth |
|------|----|----------|------|
| React SPA | DRF API | HTTP/JSON | JWT Bearer |
| DRF API | PostgreSQL | Django ORM | DB credentials (env) |
| Celery workers | PostgreSQL | Django ORM | DB credentials (env) |
| Celery Beat | Celery workers | Redis broker | Redis URL (env) |
| DRF API | Redis | (none — no direct Redis use) | — |
| React SPA | Celery | (no direct contact) | — |
| Grafana | PostgreSQL | direct DB read | DB credentials |

The React SPA and the Celery pipeline have no direct interaction. The API is the exclusive HTTP interface for the frontend. Grafana continues accessing PostgreSQL directly — this is unchanged.

---

## Anti-Patterns to Avoid

### Adding API views to existing domain apps
Adding `serializers.py` and API `views.py` inside `usinas/`, `alertas/`, etc. scatters HTTP concerns across domain modules. The domain apps' responsibility is data and business logic, not serialization. One `api/` app owns all REST surface.

### Deep nested serializers with full snapshot history
Returning `usina → [inversor → [snapshots]]` inline causes unbounded payload sizes. Use shallow nesting (current state only) plus separate paginated endpoints for history.

### Reading `payload_bruto` in API responses
The `payload_bruto` JSONField exists for debugging and audit. It contains raw provider responses, is never structured consistently across providers, and can be hundreds of KB per row. It must be explicitly excluded from every serializer using `exclude = ['payload_bruto']` or by listing only the fields to include.

### Aggregating snapshots without a time filter
`SnapshotUsina` and `SnapshotInversor` are append-only time-series tables. Without a `coletado_em` filter, aggregate queries will scan the entire table. Always require a time range (default: last 24h) on any query against snapshot tables.

### Running Node.js in the production Docker container
The React app is a static SPA after `vite build`. It needs only Nginx to serve. Including Node.js in the production image adds ~300MB and a Node.js attack surface for no benefit.

### CORS_ALLOW_ALL_ORIGINS in production
The `dev.py` setting `CORS_ALLOW_ALL_ORIGINS = True` is acceptable for local development but must never appear in `prod.py`. Production must use the explicit `CORS_ALLOWED_ORIGINS` environment variable.

---

## Scalability Considerations

At the current scale (single VPS, ~10–50 usinas, admin-only panel), none of the following are blockers. They are listed for awareness as the system grows.

| Concern | Now | If scale grows |
|---------|-----|----------------|
| Gunicorn workers | 2 workers handles API + Admin | Increase `--workers` before adding replicas |
| Analytics query time | Fast at <50 usinas | Add DB indexes on analytics-specific filters; consider materialized views at 500+ usinas |
| JWT secret rotation | Single `SECRET_KEY` | Add `SIMPLE_JWT['SIGNING_KEY']` env var separate from `DJANGO_SECRET_KEY` |
| React polling interval | 10 min aligned with collection cycle | No change needed until real-time requirement appears |
| SnapshotUsina table growth | ~6 rows/hour/usina | Existing `limpar_snapshots_antigos` task (Celery Beat, daily at 3h) handles retention |

---

## Sources

- Direct analysis of `backend_monitoramento/config/settings/base.py` — INSTALLED_APPS, MIDDLEWARE, existing Celery config
- Direct analysis of `backend_monitoramento/docker-compose.yml` — container topology, port bindings
- Direct analysis of `backend_monitoramento/usinas/models.py` and `alertas/models.py` — data shape for serializer design
- Direct analysis of `backend_monitoramento/config/urls.py` — current URL surface
- DRF documentation patterns: https://www.django-rest-framework.org/api-guide/routers/
- simplejwt documentation: https://django-rest-framework-simplejwt.readthedocs.io/
- django-cors-headers documentation: https://github.com/adamchainz/django-cors-headers
- Confidence: HIGH — all structural decisions based on direct codebase inspection, not training data assumptions
