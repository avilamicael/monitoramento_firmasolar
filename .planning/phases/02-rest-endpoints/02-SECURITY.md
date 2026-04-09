---
phase: 02-rest-endpoints
threats_total: 13
threats_closed: 13
threats_open: 0
status: SECURED
asvs_level: 1
verified_date: "2026-04-09"
---

# Security Audit — Phase 02: REST Endpoints

## Summary

All 13 registered threats verified as CLOSED. No unregistered threat flags detected in SUMMARY files.

## Threat Verification

| Threat ID | Severity | Disposition | Evidence |
|-----------|----------|-------------|----------|
| T-2-01 | medium | mitigate | `filterset_class` declarado em todos os ViewSets: `UsinaFilterSet` (views/usinas.py:32), `InversorFilterSet` (views/inversores.py:27), `AlertaFilterSet` (views/alertas.py:22). ListAPIViews sem filtro global. |
| T-2-02 | low | mitigate | `from .views import PingView, LogColetaListView` em urls.py:5; `PingView` definida em views/__init__.py:8. Import funciona. |
| T-2-03 | high | mitigate | `SnapshotUsinaSerializer.Meta.fields` declarado explicitamente sem `payload_bruto` (serializers/usinas.py:10-14). Nenhum serializer usa `fields='__all__'`. |
| T-2-04 | high | mitigate | `UsinaPatchSerializer.Meta.fields = ['nome', 'capacidade_kwp']` (serializers/usinas.py:75). Campos extras ignorados pelo DRF. |
| T-2-05 | medium | mitigate | `UsinaViewSet.http_method_names = ['get', 'patch', 'put', 'head', 'options']` (views/usinas.py:31). POST e DELETE ausentes. PUT bloqueado no recurso principal pelo `update()` override (views/usinas.py:46-54) que retorna 405 quando `partial=False`. |
| T-2-06 | medium | mitigate | `filtrar_status_garantia()` retorna `queryset` inalterado para valores nao reconhecidos (filters/usinas.py:55). Sem erro, sem bypass. |
| T-2-07 | high | mitigate | `SnapshotInversorSerializer.Meta.fields` sem `payload_bruto` (serializers/inversores.py:10-17). `AlertaListSerializer.Meta.fields` sem `payload_bruto` (serializers/alertas.py:13-18). `AlertaDetalheSerializer.Meta.fields` sem `payload_bruto` (serializers/alertas.py:41-48). |
| T-2-08 | high | mitigate | `AlertaPatchSerializer.Meta.fields = ['estado', 'anotacoes']` (serializers/alertas.py:68-69). Campos extras bloqueados pelo DRF. |
| T-2-09 | medium | mitigate | `InversorViewSet.http_method_names = ['get', 'head', 'options']` (views/inversores.py:25). `AlertaViewSet.http_method_names = ['get', 'patch', 'head', 'options']` (views/alertas.py:21). POST e DELETE ausentes em ambos. |
| T-2-10 | medium | mitigate | `AlertaViewSet.get_queryset()` usa `select_related('usina', 'usina__garantia', 'catalogo_alarme')` (views/alertas.py:29-31). Um JOIN resolve `com_garantia` para toda a listagem. |
| T-2-11 | high | mitigate | `LogColetaListView.permission_classes = [IsAuthenticated]` (views/logs.py:16). Endpoint retorna 401 sem JWT valido. |
| T-2-12 | medium | accept | Campo `detalhe_erro` exposto intencionalmente para admins autenticados (proposito de auditoria declarado no plano). Protegido por `IsAuthenticated` em LogColetaListView. Risco aceito com justificativa documentada em 02-04-PLAN.md. |
| T-2-13 | low | mitigate | `LogColetaListView.pagination_class = PaginacaoSnapshots` (views/logs.py:17). `PaginacaoSnapshots.page_size = 100` (pagination.py:7). `select_related('credencial')` evita N+1 (views/logs.py:22). |

## Accepted Risks Log

| Threat ID | Severity | Justification | Owner |
|-----------|----------|---------------|-------|
| T-2-12 | medium | `detalhe_erro` pode conter stack traces de erros de coleta. Aceito porque: (1) acessivel apenas com JWT valido de admin, (2) proposito declarado e log de auditoria operacional, (3) sem dados de usuario final expostos. Documentado em 02-04-PLAN.md threat_model. | Equipe |

## Unregistered Flags

Nenhum. As secoes `## Threat Surface` dos SUMMARY files de todos os 4 planos confirmam que nenhuma nova superficie de seguranca foi introduzida alem do previsto no threat_register.

## Notes

- T-2-05: A decisao de incluir `'put'` em `http_method_names` foi necessaria para habilitar o `@action garantia`. O override de `update()` preserva a protecao bloqueando PUT no recurso principal (`/api/usinas/{id}/`). Esta decisao esta documentada em 02-02-SUMMARY.md.
- T-2-01: `GarantiaListView` e `LogColetaListView` sao `ListAPIView` (nao ViewSets) e nao utilizam `DjangoFilterBackend` — `GarantiaListView` implementa filtragem manual via `query_params`, `LogColetaListView` nao possui filtros. Ambas estao fora do escopo de risco de T-2-01.
