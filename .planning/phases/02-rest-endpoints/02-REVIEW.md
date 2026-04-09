---
phase: 02-rest-endpoints
reviewed: 2026-04-09T00:00:00Z
depth: standard
files_reviewed: 21
files_reviewed_list:
  - backend_monitoramento/api/filters/alertas.py
  - backend_monitoramento/api/filters/inversores.py
  - backend_monitoramento/api/filters/usinas.py
  - backend_monitoramento/api/pagination.py
  - backend_monitoramento/api/serializers/alertas.py
  - backend_monitoramento/api/serializers/garantias.py
  - backend_monitoramento/api/serializers/inversores.py
  - backend_monitoramento/api/serializers/logs.py
  - backend_monitoramento/api/serializers/usinas.py
  - backend_monitoramento/api/tests/conftest.py
  - backend_monitoramento/api/tests/test_alertas.py
  - backend_monitoramento/api/tests/test_garantias.py
  - backend_monitoramento/api/tests/test_inversores.py
  - backend_monitoramento/api/tests/test_logs.py
  - backend_monitoramento/api/tests/test_usinas.py
  - backend_monitoramento/api/urls.py
  - backend_monitoramento/api/views/alertas.py
  - backend_monitoramento/api/views/garantias.py
  - backend_monitoramento/api/views/inversores.py
  - backend_monitoramento/api/views/logs.py
  - backend_monitoramento/api/views/usinas.py
findings:
  critical: 2
  warning: 4
  info: 3
  total: 9
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-04-09
**Depth:** standard
**Files Reviewed:** 21
**Status:** issues_found

## Summary

The REST endpoints layer is well-structured overall. Domain separation into views/serializers/filters packages is clean, `select_related` is consistently applied, `payload_bruto` exclusion is enforced everywhere, and authentication is required on all endpoints. The test suite covers the primary happy-path and 401/405 scenarios thoroughly.

Two critical issues were found: the `PingView` endpoint has no authentication guard, creating an unintentional public endpoint, and the `UsinaViewSet` places `'put'` in `http_method_names` to support the `garantia` custom action, but this inadvertently makes `PUT /api/usinas/{id}/` reachable (the `update()` override blocks it with a 405, but the method is still routed and executed before returning, leaving the door open to future regressions if the override is removed or bypassed). Four warnings cover logic errors and missing validation. Three info items address minor quality improvements.

---

## Critical Issues

### CR-01: `PingView` has no authentication — unintended public endpoint

**File:** `backend_monitoramento/api/views/__init__.py:8-12`

**Issue:** `PingView` inherits from `APIView` without overriding `permission_classes`. DRF's default permission is determined by `DEFAULT_PERMISSION_CLASSES` in settings, which may or may not require authentication. The docstring says "Retorna 200 se token valido", implying the intent is to verify authentication. If `DEFAULT_PERMISSION_CLASSES` is `AllowAny` (common in early development settings), this is a public endpoint that reveals liveness to unauthenticated callers. No test enforces a 401 without a token.

**Fix:**
```python
from rest_framework.permissions import IsAuthenticated

class PingView(APIView):
    """Endpoint minimo para verificar autenticacao. Retorna 200 se token valido."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({'status': 'ok'})
```

---

### CR-02: `PUT 'put'` in `http_method_names` enables full-replace route on the main resource

**File:** `backend_monitoramento/api/views/usinas.py:31`

**Issue:** `http_method_names = ['get', 'patch', 'put', 'head', 'options']` was added to allow `PUT /api/usinas/{id}/garantia/`. This also enables routing of `PUT /api/usinas/{id}/` to `update()`. The `update()` override currently returns `HTTP_405_METHOD_NOT_ALLOWED` when `partial=False`, but this relies on a fragile guard in a method that will be called. If the override is ever removed, refactored, or bypassed (e.g., via a mixin ordering change), `PUT /api/usinas/{id}/` would silently become a full-replace operation.

The safer design is to remove `'put'` from the top-level `http_method_names` and annotate the `garantia` action explicitly, or use a separate `APIView` for the garantia upsert.

**Fix (preferred — separate the garantia endpoint):**
```python
# Remove 'put' from ViewSet:
http_method_names = ['get', 'patch', 'head', 'options']

# Remove the update() override.

# Register garantia as a standalone view in urls.py:
path('usinas/<uuid:pk>/garantia/', GarantiaUpsertView.as_view(), name='usina-garantia'),
```

Alternatively, if keeping the action inside the ViewSet, document the risk explicitly and add a regression test that `PUT /api/usinas/{id}/` (without the `garantia/` suffix) returns 405.

---

## Warnings

### WR-01: `filtrar_status_garantia` — cross-tenant data loaded without scoping

**File:** `backend_monitoramento/api/filters/usinas.py:39-52`

**Issue:** `GarantiaUsina.objects.select_related('usina').all()` fetches every `GarantiaUsina` in the database to filter by Python-level property. This is the documented trade-off for `@property`-based filtering, but there is no tenant/scope guard — a future multi-tenant context would silently expose data from other tenants. The comment in the code acknowledges the approach but does not acknowledge the tenant risk. CLAUDE.md explicitly requires multi-tenancy filtering to never rely on client-supplied IDs and for every data query to include a tenant filter.

**Fix:** Add a comment marking this as a known single-tenant assumption:
```python
# AVISO ARQUITETURAL: este filtro carrega todas as GarantiaUsina do banco.
# Em ambiente multi-tenant, substituir por queryset.filter(usina__credencial=self.request.user.credencial)
# antes de avaliar a propriedade Python. (Projeto ainda single-tenant — revisitar em T-3.)
```
If multi-tenancy is already in scope, apply scoping now rather than deferring it.

---

### WR-02: `GarantiaListView.get_queryset` — same cross-tenant load issue

**File:** `backend_monitoramento/api/views/garantias.py:31`

**Issue:** `GarantiaUsina.objects.select_related('usina').all()` loads all guarantees in the database via `list(qs)` to evaluate `@property` filters. Same single-tenant assumption as WR-01. Consistent risk and the same mitigation applies.

**Fix:** Same architectural comment as WR-01. If multi-tenancy is needed, scope the base queryset to the authenticated user's credential before calling `list(qs)`.

---

### WR-03: `AlertaViewSet` — PATCH response uses `AlertaDetalheSerializer` but writes with `AlertaPatchSerializer`

**File:** `backend_monitoramento/api/views/alertas.py:33-38`

**Issue:** `get_serializer_class` returns `AlertaPatchSerializer` for `partial_update`, which is correct for writing. However, DRF's `partial_update` method calls `get_serializer` both to validate input and to serialize the response. With `AlertaPatchSerializer`, the 200 response to a PATCH only contains `estado` and `anotacoes`, not the full alerta representation. Tests at lines 139-161 only assert `response.status_code == 200` and then call `refresh_from_db()` — they do not assert on the response body. If callers expect a full representation after PATCH, they will be surprised.

**Fix:** Override `update` (or `partial_update`) to serialize the response with `AlertaDetalheSerializer`:
```python
def partial_update(self, request, *args, **kwargs):
    kwargs['partial'] = True
    instance = self.get_object()
    serializer = AlertaPatchSerializer(instance, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(AlertaDetalheSerializer(instance, context={'request': request}).data)
```

---

### WR-04: `UsinaPatchSerializer` — no validation on `capacidade_kwp`

**File:** `backend_monitoramento/api/serializers/usinas.py:70-75`

**Issue:** `UsinaPatchSerializer` allows patching `capacidade_kwp` without any minimum-value constraint. A caller can set `capacidade_kwp=0` or a negative value, which would be semantically invalid (a solar plant with zero or negative capacity). DRF will accept any float that the underlying model field accepts.

**Fix:**
```python
class UsinaPatchSerializer(serializers.ModelSerializer):
    capacidade_kwp = serializers.FloatField(min_value=0.001, required=False)

    class Meta:
        model = Usina
        fields = ['nome', 'capacidade_kwp']
```

---

## Info

### IN-01: `get_com_garantia` duplicated in `AlertaListSerializer` and `AlertaDetalheSerializer`

**File:** `backend_monitoramento/api/serializers/alertas.py:22-31` and `52-58`

**Issue:** The `get_com_garantia` method body is identical in both serializers. CLAUDE.md prohibits code duplication.

**Fix:** Extract into a mixin:
```python
class ComGarantiaMixin:
    def get_com_garantia(self, obj) -> bool:
        try:
            return obj.usina.garantia.ativa
        except GarantiaUsina.DoesNotExist:
            return False

class AlertaListSerializer(ComGarantiaMixin, serializers.ModelSerializer):
    ...

class AlertaDetalheSerializer(ComGarantiaMixin, serializers.ModelSerializer):
    ...
```

---

### IN-02: `get_status_garantia` duplicated in `UsinaListSerializer` and `UsinaDetalheSerializer`

**File:** `backend_monitoramento/api/serializers/usinas.py:38-44` and `62-67`

**Issue:** Same body in both serializers. Same CLAUDE.md violation as IN-01.

**Fix:** Same mixin pattern:
```python
class StatusGarantiaMixin:
    def get_status_garantia(self, obj) -> str:
        try:
            garantia = obj.garantia
        except GarantiaUsina.DoesNotExist:
            return 'sem_garantia'
        return 'ativa' if garantia.ativa else 'vencida'
```

---

### IN-03: `test_lista_logs_sem_token_retorna_401` accepts 401 or 403

**File:** `backend_monitoramento/api/tests/test_logs.py:46`

**Issue:** `assert response.status_code in [401, 403]` is looser than the equivalent tests in every other test file, all of which assert `== 401`. The inconsistency means a configuration change that causes 403 here would silently pass even though all other endpoints correctly return 401. The intent should be a strict 401.

**Fix:**
```python
assert response.status_code == 401
```

---

_Reviewed: 2026-04-09_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
