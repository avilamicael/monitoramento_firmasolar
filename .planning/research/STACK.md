# Technology Stack

**Project:** Firma Solar — REST API + React Admin Panel
**Researched:** 2026-04-07
**Confidence:** HIGH (all versions verified against PyPI/npm/official docs)

---

## Context

This is an additive milestone on top of an existing Django 5.1 application.
The pipeline (Celery + PostgreSQL + Redis) is untouched.
This document covers only what is being added.

---

## Backend Additions

### Core REST Framework

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `djangorestframework` | `3.17.*` | ViewSets, Routers, Serializers, permission classes | Latest stable (3.17.1, March 2026). Requires Python 3.10+, Django 4.2–6.0 — compatible with existing Django 5.1. The only first-class REST layer for Django. |
| `djangorestframework-simplejwt` | `5.5.*` | JWT access + refresh tokens, token blacklisting | Latest stable (5.5.1, July 2025). Native DRF integration, actively maintained under Jazzband. Supports all security patterns needed: rotation, blacklisting, sliding tokens. |
| `django-cors-headers` | `4.9.*` | CORS middleware for React frontend | Latest stable (4.9.0, September 2025). Supports Django 4.2–6.0. Minimal, battle-tested. |
| `django-filter` | `25.2.*` | Query parameter filtering on ViewSets | Latest stable (25.2, October 2025). First-class DRF integration via `DjangoFilterBackend`. Provides both simple `filterset_fields` shorthand and full `FilterSet` class when complex logic is needed. |

### djangorestframework — ViewSets and Routers

Use `ModelViewSet` for all CRUD resources (Usina, Inversor, Alerta, Garantia).
Use `ReadOnlyModelViewSet` for analytics endpoints (no mutation allowed).
Register all ViewSets with `DefaultRouter` — it auto-generates list/detail URL patterns
and a browsable API root at `/api/`.

```python
# config/urls.py
from rest_framework.routers import DefaultRouter
from usinas.views import UsinaViewSet, InversorViewSet
from alertas.views import AlertaViewSet
from garantias.views import GarantiaViewSet

router = DefaultRouter()
router.register('usinas', UsinaViewSet)
router.register('inversores', InversorViewSet)
router.register('alertas', AlertaViewSet)
router.register('garantias', GarantiaViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/auth/', include('rest_framework_simplejwt.urls')),
    path('admin/', admin.site.urls),
]
```

Place all DRF apps under `backend_monitoramento/api/` or each in its domain app
(`usinas/views.py`, `usinas/serializers.py`). The second approach is consistent
with the existing modular structure — prefer it.

### simplejwt — JWT Configuration

**Recommended settings for `config/settings/base.py`:**

```python
from datetime import timedelta

SIMPLE_JWT = {
    # Access token: short-lived, stateless — if stolen, expires in minutes
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),

    # Refresh token: longer-lived, stored in httpOnly cookie — rotated on each use
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),

    # Issue a new refresh token on every refresh call
    # Old refresh token becomes invalid after one use
    "ROTATE_REFRESH_TOKENS": True,

    # Add the old refresh token to the blacklist after rotation
    # Requires 'rest_framework_simplejwt.token_blacklist' in INSTALLED_APPS
    "BLACKLIST_AFTER_ROTATION": True,

    "ALGORITHM": "HS256",
    "AUTH_HEADER_TYPES": ("Bearer",),
    "UPDATE_LAST_LOGIN": True,  # Update User.last_login on each token obtain
}
```

**Required INSTALLED_APPS addition:**

```python
INSTALLED_APPS = [
    # ... existing apps ...
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",  # enables blacklisting
    "django_filters",
    "corsheaders",
]
```

Run `python manage.py migrate` after adding `token_blacklist` — it creates
`OutstandingToken` and `BlacklistedToken` tables.

**REST_FRAMEWORK default authentication:**

```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
}
```

`IsAuthenticated` as default means every endpoint requires a valid JWT unless
overridden with `permission_classes = [AllowAny]` on the specific view.
The only public view is the token-obtain endpoint.

### JWT Token Storage — Security Decision

**Decision: httpOnly cookie for the refresh token; in-memory (JS variable) for the access token.**

Rationale:
- `localStorage` is vulnerable to XSS: any injected script can read it and exfiltrate tokens. This is not hypothetical — it is the standard attack vector against SPA auth.
- The access token lives in JS memory only (15 minutes lifetime). On page reload, a silent refresh call retrieves a new access token using the httpOnly cookie.
- The refresh token in an httpOnly cookie cannot be read by JavaScript, eliminating the theft vector.
- SameSite=Lax on the cookie blocks CSRF for the refresh endpoint because the refresh request is a same-site POST from the SPA.

**Implementation approach:** simplejwt does not natively set httpOnly cookies out of the box.
Override `TokenObtainPairView` and `TokenRefreshView` to set cookies in `finalize_response()`.
This is a documented pattern (confirmed from GitHub issues #71, #289 and community implementations).

```python
# usinas/views_auth.py (example, abbreviated)
class CookieTokenObtainPairView(TokenObtainPairView):
    def finalize_response(self, request, response, *args, **kwargs):
        if response.data.get("refresh"):
            response.set_cookie(
                "refresh_token",
                response.data["refresh"],
                httponly=True,
                secure=not settings.DEBUG,
                samesite="Lax",
                max_age=7 * 24 * 60 * 60,  # 7 days
            )
            del response.data["refresh"]  # do not expose refresh in body
        return super().finalize_response(request, response, *args, **kwargs)
```

**What NOT to use:** Do not store the access token in `localStorage`. Do not store the refresh token in `localStorage`. Do not use `sessionStorage` for the refresh token (does not survive tab duplication or bookmark navigation).

### django-cors-headers — Dev/Prod Configuration

```python
# config/settings/base.py
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # must be FIRST or before CommonMiddleware
    "django.middleware.common.CommonMiddleware",
    # ... rest of middleware ...
]
```

```python
# config/settings/dev.py
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",  # Vite dev server default port
    "http://127.0.0.1:5173",
]
CORS_ALLOW_CREDENTIALS = True  # required for httpOnly cookie to be sent
```

```python
# config/settings/prod.py
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    "https://monitoramento.firmasolar.com.br",  # production frontend origin
]
CORS_ALLOW_CREDENTIALS = True
```

**Critical rule:** Never combine `CORS_ALLOW_ALL_ORIGINS = True` with
`CORS_ALLOW_CREDENTIALS = True`. Browsers block this per spec — credentials require
explicit origins. This setting pair will silently fail.

### django-filter — ViewSet Integration

The `DEFAULT_FILTER_BACKENDS` setting above enables filtering globally.
Per-ViewSet configuration:

**Simple equality filters (shorthand):**
```python
class UsinaViewSet(ModelViewSet):
    queryset = Usina.objects.all()
    serializer_class = UsinaSerializer
    filterset_fields = ["provedor", "ativa", "fabricante"]
```

**Complex filters (custom FilterSet):**
```python
# usinas/filters.py
import django_filters
from .models import Usina

class UsinaFilterSet(django_filters.FilterSet):
    potencia_min = django_filters.NumberFilter(field_name="capacidade_kw", lookup_expr="gte")
    potencia_max = django_filters.NumberFilter(field_name="capacidade_kw", lookup_expr="lte")
    provedor = django_filters.CharFilter(lookup_expr="exact")

    class Meta:
        model = Usina
        fields = ["provedor", "ativa"]

# usinas/views.py
class UsinaViewSet(ModelViewSet):
    filterset_class = UsinaFilterSet
```

Do not mix `filterset_fields` and `filterset_class` on the same ViewSet — they are
mutually exclusive. Use `filterset_fields` only when all filters are simple equality
checks; use `filterset_class` for range filters, custom lookups, or related field
traversal.

---

## Frontend Stack

### Core

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| React | `18.*` | UI framework | React 19 is available but react-leaflet v4 requires React 18; v5 requires React 19. Use React 18 until react-leaflet v5 is stable and tested. |
| Vite | `6.*` (latest) | Build tool and dev server | Official shadcn/ui Vite setup guide targets Vite. Instant HMR, no CRA complexity. |
| TypeScript | `5.*` | Type safety | Required by shadcn/ui component scaffold. Eliminates runtime type bugs in API response handling. |
| React Router v7 | `7.*` | Client-side routing | Stable, file-based routing. TanStack Router is an alternative but introduces more setup overhead for this use case. |

### UI

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| shadcn/ui | latest (copy-paste) | Component library | Not a versioned package — components are copied into `src/components/ui/`. Uses Tailwind + Radix UI primitives. Official chart integration uses Recharts v3. |
| Tailwind CSS | `3.*` | Styling | Required by shadcn/ui. v4 is available but shadcn/ui Vite setup guide still targets v3 as of April 2026. |
| Recharts | `2.*` | Charts (analytics) | shadcn/ui chart components target Recharts v2 (not v3 yet in the CLI scaffold). The `chart` documentation says "now uses Recharts v3" for new installs — verify with `npx shadcn@latest add chart` output at project init time and pin accordingly. |

### Data Fetching and State

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| TanStack Query v5 | `5.*` | Server state, caching, polling | `refetchInterval` natively maps to the 10-min collection cycle. Handles stale-while-revalidate, deduplication, and error retries without manual logic. Requires React 18+. |
| Axios | `1.*` | HTTP client | Interceptors are the standard pattern for token refresh. The request/response interceptor system is more ergonomic than native `fetch` for this use case. |
| Zustand | `4.*` | Client state (auth, UI state) | Minimal boilerplate. Access token stored in Zustand store (in-memory only, not persisted). Refresh token in httpOnly cookie — Zustand does not touch it. |

### Maps

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| react-leaflet | `4.*` | Interactive map of plant locations | v4 requires React 18 (compatible). v5 requires React 19 — do NOT use v5 with this stack. v4 is the correct choice here. |
| leaflet | `1.9.*` | Leaflet core (peer dependency of react-leaflet v4) | Required peer dependency. |

**CSS import required — must be in `main.tsx` or `index.css`:**
```typescript
import "leaflet/dist/leaflet.css";
```

Forgetting this import causes broken map rendering (tiles load but controls and markers are invisible/mispositioned).

---

## Frontend Project Structure

```
frontend/
  src/
    api/                  # Axios instance + per-domain query hooks
      client.ts           # Axios instance with interceptors
      usinas.ts           # useUsinas(), useUsina(id) TanStack Query hooks
      alertas.ts
      analytics.ts
    components/
      ui/                 # shadcn/ui copied components (Button, Card, etc.)
      charts/             # Recharts wrappers using ChartContainer
      map/                # MapContainer wrapper, UsinaMarker
      layout/             # AppShell, Sidebar, Header
    pages/
      Dashboard.tsx
      Usinas.tsx
      Alertas.tsx
      Garantias.tsx
      Login.tsx
    store/
      auth.ts             # Zustand store: { accessToken, user, setTokens, logout }
    lib/
      utils.ts            # shadcn/ui cn() utility
    App.tsx
    main.tsx
  index.html
  vite.config.ts
  tailwind.config.ts
  components.json         # shadcn/ui config
```

---

## Auth Flow (Frontend)

### Login

1. POST `/api/auth/token/` with `{ username, password }`
2. Server returns `{ access: "..." }` in body; sets `refresh_token` httpOnly cookie
3. Store `access` token in Zustand (memory only, not localStorage)

### Authenticated Requests

Axios request interceptor reads access token from Zustand and sets `Authorization: Bearer <token>` on every request.

### Token Refresh

Axios response interceptor catches 401:
1. POST `/api/auth/token/refresh/` with `credentials: "include"` so the browser sends the httpOnly cookie
2. Server rotates refresh token (old is blacklisted), returns new access token
3. Interceptor updates Zustand with new access token, retries the original request
4. Use a failed-request queue to handle concurrent 401s without triggering multiple simultaneous refresh calls — this prevents race conditions

```typescript
// api/client.ts (pattern)
let isRefreshing = false;
let failedQueue: Array<{ resolve: Function; reject: Function }> = [];

axiosInstance.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((token) => {
          original.headers["Authorization"] = `Bearer ${token}`;
          return axiosInstance(original);
        });
      }
      original._retry = true;
      isRefreshing = true;
      try {
        const { data } = await axiosInstance.post(
          "/api/auth/token/refresh/",
          {},
          { withCredentials: true }  // sends httpOnly cookie
        );
        useAuthStore.getState().setAccessToken(data.access);
        processQueue(null, data.access);
        original.headers["Authorization"] = `Bearer ${data.access}`;
        return axiosInstance(original);
      } catch (err) {
        processQueue(err, null);
        useAuthStore.getState().logout();
        return Promise.reject(err);
      } finally {
        isRefreshing = false;
      }
    }
    return Promise.reject(error);
  }
);
```

### Polling (10-min Cycle Alignment)

```typescript
useQuery({
  queryKey: ["dashboard"],
  queryFn: fetchDashboard,
  refetchInterval: 10 * 60 * 1000,     // 10 minutes
  refetchIntervalInBackground: false,    // pause when tab is not active
  staleTime: 9 * 60 * 1000,            // don't refetch if data is less than 9 min old
})
```

---

## Recharts + shadcn/ui Charts

shadcn/ui ships chart components built on Recharts that are theme-aware.
The pattern uses `ChartContainer` as the wrapper:

```typescript
// Install via CLI: npx shadcn@latest add chart
// This copies ChartContainer, ChartTooltip, ChartTooltipContent into src/components/ui/chart.tsx

// Usage
<ChartContainer config={chartConfig} className="min-h-[200px]">
  <BarChart data={data}>
    <Bar dataKey="potencia" fill="var(--color-potencia)" />
    <ChartTooltip content={<ChartTooltipContent />} />
  </BarChart>
</ChartContainer>
```

Color tokens are defined in `globals.css` as CSS variables (`--chart-1` through `--chart-5`).
The `chartConfig` object maps data keys to colors and labels, decoupling data from presentation.

**Do not** import Recharts components directly and style them with Tailwind — always go through `ChartContainer` to get theme coherence with the rest of the shadcn/ui design system.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| JWT storage | httpOnly cookie (refresh) + memory (access) | localStorage for both | XSS vulnerability: localStorage is readable by any injected script |
| Map library | react-leaflet v4 + Leaflet | Google Maps, Mapbox | Paid APIs with usage limits; Leaflet is open source with no cost |
| Data fetching | TanStack Query v5 | SWR, Redux RTK Query | TanStack Query has native `refetchInterval` and more granular cache control for the multi-resource dashboard pattern |
| HTTP client | Axios | native fetch | Axios interceptors are more ergonomic for the token refresh queue pattern |
| Router | React Router v7 | TanStack Router | TanStack Router adds type-safety benefit but higher setup cost for this admin panel use case |
| React version | 18 | 19 | react-leaflet v5 (requires React 19) is recently released and not widely battle-tested; v4 + React 18 is the stable path |

---

## Installation

### Backend additions to `requirements/base.txt`

```
djangorestframework==3.17.*
djangorestframework-simplejwt==5.5.*
django-cors-headers==4.9.*
django-filter==25.2.*
```

### Frontend bootstrap

```bash
npm create vite@latest frontend-painel -- --template react-ts
cd frontend-painel
npx shadcn@latest init
npx shadcn@latest add chart card badge button table
npm install @tanstack/react-query axios zustand react-router-dom
npm install react-leaflet@4 leaflet @types/leaflet
```

---

## Sources

- [djangorestframework 3.17.1 — PyPI](https://pypi.org/project/djangorestframework/)
- [djangorestframework-simplejwt 5.5.1 — PyPI](https://pypi.org/project/djangorestframework-simplejwt/)
- [Simple JWT — Settings documentation](https://django-rest-framework-simplejwt.readthedocs.io/en/stable/settings.html)
- [django-cors-headers 4.9.0 — PyPI](https://pypi.org/project/django-cors-headers/)
- [django-filter 25.2 — PyPI](https://pypi.org/project/django-filter/)
- [DRF Filtering — django-filter DRF integration guide](https://django-filter.readthedocs.io/en/latest/guide/rest_framework.html)
- [shadcn/ui Chart component documentation](https://ui.shadcn.com/docs/components/radix/chart)
- [react-leaflet — Installation docs (v4 vs v5 peer deps)](https://react-leaflet.js.org/docs/start-installation/)
- [TanStack Query v5 — useQuery reference](https://tanstack.com/query/v5/docs/framework/react/reference/useQuery)
- [Allow httpOnly cookie storage — simplejwt GitHub issue #71](https://github.com/SimpleJWT/django-rest-framework-simplejwt/issues/71)
- [JWT Storage security comparison (2025)](https://stackinsight.dev/blog/jwt-storage-cookies-vs-localstorage-which-is-right-for-your-app/)
- [Axios interceptors JWT refresh pattern](https://codevoweb.com/react-query-context-api-axios-interceptors-jwt-auth/)
