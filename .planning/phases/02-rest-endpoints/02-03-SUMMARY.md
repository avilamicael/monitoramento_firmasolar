---
phase: 02-rest-endpoints
plan: 03
subsystem: backend/api
tags: [viewset, serializers, filters, inversores, alertas, tdd, com_garantia]
dependency_graph:
  requires: [02-01, 02-02]
  provides: [InversorViewSet, AlertaViewSet, InversorFilterSet, AlertaFilterSet, serializers inversores/alertas]
  affects: [02-04]
tech_stack:
  added: []
  patterns:
    - ModelViewSet com http_method_names restricto (sem POST/DELETE em inversores; sem POST/DELETE em alertas)
    - SerializerMethodField para com_garantia via select_related (zero N+1)
    - AlertaPatchSerializer com fields restrito a [estado, anotacoes] — previne mass assignment
    - action snapshots em InversorViewSet com PaginacaoSnapshots (page_size=100)
key_files:
  created:
    - backend_monitoramento/api/serializers/inversores.py
    - backend_monitoramento/api/serializers/alertas.py
    - backend_monitoramento/api/filters/inversores.py
    - backend_monitoramento/api/filters/alertas.py
    - backend_monitoramento/api/views/inversores.py
    - backend_monitoramento/api/views/alertas.py
  modified:
    - backend_monitoramento/api/urls.py
    - backend_monitoramento/api/tests/test_inversores.py
    - backend_monitoramento/api/tests/test_alertas.py
decisions:
  - "InversorViewSet: http_method_names=['get','head','options'] — POST/DELETE bloqueados; inversores geridos pela coleta"
  - "AlertaViewSet: http_method_names=['get','patch','head','options'] — POST/DELETE bloqueados; PATCH restrito a estado/anotacoes"
  - "com_garantia calculado via SerializerMethodField com try/except GarantiaUsina.DoesNotExist — evita AttributeError quando usina nao tem garantia"
  - "select_related('usina__garantia') no AlertaViewSet.get_queryset — um JOIN resolve com_garantia para toda a listagem sem N+1"
metrics:
  duration_minutes: 15
  completed_date: "2026-04-09"
  tasks_completed: 2
  tasks_total: 2
  files_created: 6
  files_modified: 3
---

# Phase 02 Plan 03: Inversores e Alertas Endpoints Summary

**One-liner:** InversorViewSet com filtros (usina/provedor/modelo) e historico paginado de snapshots; AlertaViewSet com PATCH restrito (estado/anotacoes), campo com_garantia via select_related sem N+1, filtros por estado/nivel/usina; 26 novos testes passando (INV-01..03 e ALT-01..04).

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Serializers, filters, views e testes de Inversores | f5ddb24 |
| 2 | Serializers, filters, views e testes de Alertas | b6a87ca |

## What Was Done

**Task 1 — Inversores:**
- `api/serializers/inversores.py`: 3 serializers — SnapshotInversorSerializer (sem payload_bruto), InversorListSerializer (com usina_nome), InversorDetalheSerializer (com ultimo_snapshot aninhado completo)
- `api/filters/inversores.py`: InversorFilterSet com filtros `usina` (UUID), `provedor` (exact) e `modelo` (icontains)
- `api/views/inversores.py`: InversorViewSet read-only (POST/DELETE 405) com `select_related('usina', 'ultimo_snapshot')` e `@action snapshots` usando PaginacaoSnapshots
- `api/urls.py`: `router.register('inversores', InversorViewSet, basename='inversor')` adicionado
- 11 testes INV-01..03 passando

**Task 2 — Alertas:**
- `api/serializers/alertas.py`: 3 serializers — AlertaListSerializer (com com_garantia e usina_nome), AlertaDetalheSerializer (campos completos + com_garantia), AlertaPatchSerializer (fields=['estado','anotacoes'] apenas)
- `api/filters/alertas.py`: AlertaFilterSet com filtros `estado` (exact), `nivel` (exact), `usina` (UUID)
- `api/views/alertas.py`: AlertaViewSet com GET/PATCH; `select_related('usina', 'usina__garantia', 'catalogo_alarme')` para evitar N+1 em com_garantia
- `api/urls.py`: `router.register('alertas', AlertaViewSet, basename='alerta')` adicionado
- 15 testes ALT-01..04 passando

## Test Results

| Suite | Testes | Status |
|-------|--------|--------|
| test_inversores.py | 11 | PASSOU |
| test_alertas.py | 15 | PASSOU |
| test_usinas.py | 21 | PASSOU |
| test_garantias.py | 12 | PASSOU |
| test_auth.py | 7 | PASSOU |
| test_cors.py | 2 | PASSOU |
| test_logs.py | 3 skipped | Aguardando Plan 04 |
| **Total** | **68 passando, 3 skipped** | **PASSOU** |

## Deviations from Plan

Nenhum. Plano executado exatamente como especificado. Todos os artifacts do `must_haves` foram entregues conforme as interfaces e critérios de aceite.

## Known Stubs

Nenhum. Todos os 26 testes implementados neste plano estão com corpos reais e passando. Os stubs remanescentes (test_logs.py com 3 testes marcados skip) pertencem ao Plan 02-04.

## Threat Surface

Todas as ameaças do threat_model cobertas sem nova superfície introduzida:
- T-2-07: payload_bruto excluído de SnapshotInversorSerializer, AlertaListSerializer e AlertaDetalheSerializer (fields explícitos)
- T-2-08: AlertaPatchSerializer com fields=['estado','anotacoes'] — campos extras ignorados pelo DRF
- T-2-09: InversorViewSet http_method_names=['get','head','options']; AlertaViewSet http_method_names=['get','patch','head','options']
- T-2-10: get_queryset() usa select_related('usina__garantia') — um JOIN por requisição, sem N+1

## Self-Check: PASSED

- [x] `api/serializers/inversores.py` existe com SnapshotInversorSerializer, InversorListSerializer, InversorDetalheSerializer
- [x] `api/serializers/inversores.py` não contém 'payload_bruto' em nenhum fields
- [x] `api/serializers/alertas.py` existe com AlertaListSerializer, AlertaDetalheSerializer, AlertaPatchSerializer
- [x] `api/serializers/alertas.py` não contém 'payload_bruto' em nenhum fields
- [x] `api/serializers/alertas.py` AlertaPatchSerializer.Meta.fields == ['estado', 'anotacoes']
- [x] `api/filters/inversores.py` existe com InversorFilterSet (campos usina, provedor, modelo)
- [x] `api/filters/alertas.py` existe com AlertaFilterSet (campos estado, nivel, usina)
- [x] `api/views/inversores.py` existe com InversorViewSet e http_method_names=['get','head','options']
- [x] `api/views/alertas.py` existe com AlertaViewSet e select_related('usina','usina__garantia')
- [x] `api/urls.py` contém router.register inversores e router.register alertas
- [x] Commit f5ddb24 existe (Task 1)
- [x] Commit b6a87ca existe (Task 2)
- [x] 68 testes passando (suite completa)
