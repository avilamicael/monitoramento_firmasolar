---
phase: 02-rest-endpoints
plan: 02
subsystem: backend/api
tags: [viewset, serializers, filters, garantias, usinas, tdd]
dependency_graph:
  requires: [02-01]
  provides: [UsinaViewSet, GarantiaListView, UsinaFilterSet, serializers usinas/garantias]
  affects: [02-03, 02-04]
tech_stack:
  added: []
  patterns:
    - ModelViewSet com http_method_names restricto (sem POST/DELETE)
    - SerializerMethodField para properties de model (data_fim, dias_restantes, ativa)
    - Filtro Python para @property nao mapeavel em ORM (status_garantia, vencendo/ativas/vencidas)
    - update() override para bloquear PUT principal enquanto permite @action com PUT
key_files:
  created:
    - backend_monitoramento/api/filters/usinas.py
    - backend_monitoramento/api/serializers/usinas.py
    - backend_monitoramento/api/serializers/garantias.py
    - backend_monitoramento/api/views/usinas.py
    - backend_monitoramento/api/views/garantias.py
  modified:
    - backend_monitoramento/api/urls.py
    - backend_monitoramento/api/tests/test_garantias.py
decisions:
  - "UsinaViewSet.update() bloqueado com 405 para PUT direto; partial=True (PATCH) delegado ao super()"
  - "http_method_names inclui 'put' para habilitar @action garantia, mas update() override bloqueia PUT no recurso principal"
  - "GarantiaUsinaSerializer usa SerializerMethodField para data_fim/dias_restantes/ativa — sao @property, nao colunas SQL"
  - "Filtro status_garantia e filtros de vigencia em garantias implementados em Python (data_fim e @property)"
metrics:
  duration_minutes: 25
  completed_date: "2026-04-09"
  tasks_completed: 2
  tasks_total: 2
  files_created: 5
  files_modified: 2
---

# Phase 02 Plan 02: Serializers, Views e Testes de Usinas e Garantias Summary

**One-liner:** UsinaViewSet completo com filtros (provedor/ativo/status_garantia), historico de snapshots paginado, upsert de garantia via @action; GarantiaListView com filtros ativas/vencendo/vencidas em Python; 33 testes novos passando (USN-01..05 e GAR-02..06).

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Serializers, filters, views e URLs de Usinas | 2a24f3d |
| 2 | Serializers, views e testes de Garantias | a0d6568 |

## What Was Done

**Task 1 — Usinas:**
- `api/filters/usinas.py`: UsinaFilterSet com filtros `provedor`, `ativo` (ORM) e `status_garantia` (Python, pois `data_fim` e @property)
- `api/serializers/usinas.py`: 4 serializers — UsinaListSerializer, UsinaDetalheSerializer (com inversores[] e ultimo_snapshot aninhados), UsinaPatchSerializer (restrito a nome/capacidade), SnapshotUsinaSerializer (sem payload_bruto)
- `api/views/usinas.py`: UsinaViewSet com GET/PATCH/PUT; POST e DELETE bloqueados (T-2-05); @action `snapshots` (PaginacaoSnapshots) e @action `garantia` (upsert)
- `api/urls.py`: DefaultRouter registrado com UsinaViewSet; path `garantias/` adicionado
- 21 testes USN-01..05 passando

**Task 2 — Garantias:**
- `api/serializers/garantias.py`: GarantiaUsinaSerializer (SerializerMethodField para data_fim/dias_restantes/ativa) + GarantiaUsinaEscritaSerializer (escrita segura)
- `api/views/garantias.py`: GarantiaListView com filtro Python ativas/vencidas/vencendo (30 dias)
- `api/tests/test_garantias.py`: 12 testes implementados (GAR-02..06) — substituindo os stubs com skip
- Correcao de desvio: `update()` override para bloquear PUT no recurso principal enquanto permite @action garantia

## Test Results

| Suite | Testes | Status |
|-------|--------|--------|
| test_usinas.py | 21 | PASSOU |
| test_garantias.py | 12 | PASSOU |
| test_auth.py | 7 | PASSOU |
| **Total** | **40** | **PASSOU** |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] PUT bloqueado em ModelViewSet mas necessario para @action garantia**
- **Found during:** Task 2 — test_criar_garantia falhou com 405
- **Issue:** `http_method_names = ['get', 'patch', 'head', 'options']` bloqueava PUT globalmente, impedindo `@action(methods=['put'], url_path='garantia')`
- **Fix:** Adicionado `'put'` ao `http_method_names` + override de `update()` que retorna 405 para PUT direto mas chama `super()` quando `partial=True` (PATCH). Isso preserva T-2-05 (sem substituicao total de usina via PUT) enquanto habilita o @action garantia.
- **Files modified:** `backend_monitoramento/api/views/usinas.py`
- **Commit:** a0d6568

## Known Stubs

Nenhum. Todos os 33 testes implementados neste plano estao com corpos reais e passando. Os demais stubs (test_inversores.py, test_alertas.py, test_logs.py) pertencem aos plans 02-03 e 02-04.

## Threat Surface

Nenhuma nova superficie de seguranca introduzida alem do previsto no threat_model do plano:
- T-2-03: payload_bruto excluido de SnapshotUsinaSerializer (fields explicitos)
- T-2-04: UsinaPatchSerializer com fields = ['nome', 'capacidade_kwp'] apenas
- T-2-05: POST e DELETE retornam 405; PUT direto em /api/usinas/{id}/ tambem retorna 405
- T-2-06: filtrar_status_garantia retorna queryset inalterado para valores nao reconhecidos

## Self-Check: PASSED

- [x] `api/filters/usinas.py` existe com UsinaFilterSet e metodo filtrar_status_garantia
- [x] `api/serializers/usinas.py` existe com 4 classes; sem payload_bruto nos fields
- [x] `api/serializers/garantias.py` existe com GarantiaUsinaSerializer e GarantiaUsinaEscritaSerializer
- [x] `api/views/usinas.py` existe com UsinaViewSet, @action snapshots e @action garantia
- [x] `api/views/garantias.py` existe com GarantiaListView
- [x] `api/urls.py` contem router.register usinas e path garantias/
- [x] Commit 2a24f3d existe (Task 1)
- [x] Commit a0d6568 existe (Task 2)
- [x] 40 testes passando (21 usinas + 12 garantias + 7 auth)
