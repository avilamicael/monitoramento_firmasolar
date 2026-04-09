---
phase: 02-rest-endpoints
plan: 04
subsystem: backend/api
tags: [serializer, listview, logs, coleta, jwt, tdd, LOG-01]
dependency_graph:
  requires: [02-01, 02-02, 02-03]
  provides: [LogColetaSerializer, LogColetaListView, GET /api/coleta/logs/]
  affects: []
tech_stack:
  added: []
  patterns:
    - ListAPIView com IsAuthenticated e PaginacaoSnapshots (page_size=100)
    - SerializerMethodField para provedor_nome via get_provedor_display()
    - select_related('credencial') para evitar N+1 em campo calculado
    - read_only_fields em todos os campos (log imutavel por natureza)
key_files:
  created:
    - backend_monitoramento/api/serializers/logs.py
    - backend_monitoramento/api/views/logs.py
  modified:
    - backend_monitoramento/api/serializers/__init__.py
    - backend_monitoramento/api/views/__init__.py
    - backend_monitoramento/api/urls.py
    - backend_monitoramento/api/tests/test_logs.py
decisions:
  - "URLs absolutas nos testes em vez de reverse('api:log-coleta-list') — namespace 'api' nao registrado no urlconf de teste; consistente com padrao de todos os outros testes da fase"
  - "Fixtures client/tokens/credencial do conftest existente reutilizadas — nao foram criadas api_client/token_usuario (nao existem no projeto)"
metrics:
  duration_minutes: 12
  completed_date: "2026-04-09"
  tasks_completed: 4
  tasks_total: 4
  files_created: 2
  files_modified: 4
---

# Phase 02 Plan 04: Logs de Coleta Summary

**One-liner:** LogColetaListView com autenticacao JWT obrigatoria, paginacao PaginacaoSnapshots, select_related para evitar N+1 em provedor_nome, e 4 testes cobrindo LOG-01 (lista autenticada, 401 sem token, lista vazia, detalhe_erro).

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 04-01 | LogColetaSerializer com provedor_nome e campos de auditoria | 629ab1d |
| 04-02 | LogColetaListView com IsAuthenticated e select_related | 87569d3 |
| 04-03 | Registrar rota GET /api/coleta/logs/ em urls.py | 36b335c |
| 04-04 | Implementar testes para LOG-01 (4 testes, 72/72 passando) | bf7cda7 |

## What Was Done

**Task 04-01 — Serializer:**
- `api/serializers/logs.py`: ModelSerializer com fields explícitos (id, provedor_nome, status, usinas_coletadas, inversores_coletados, alertas_sincronizados, detalhe_erro, duracao_ms, iniciado_em)
- `provedor_nome` via `SerializerMethodField` + `get_provedor_nome()` chamando `credencial.get_provedor_display()`
- `read_only_fields = fields` — log de auditoria é imutável
- `api/serializers/__init__.py` exporta `LogColetaSerializer`

**Task 04-02 — View:**
- `api/views/logs.py`: `LogColetaListView(ListAPIView)` com `permission_classes = [IsAuthenticated]`
- `pagination_class = PaginacaoSnapshots` (page_size=100, herdado de Plan 01)
- `get_queryset()` com `select_related('credencial')` — um JOIN evita N+1 para toda a listagem
- `api/views/__init__.py` exporta `LogColetaListView`

**Task 04-03 — Rota:**
- `api/urls.py`: `path('coleta/logs/', LogColetaListView.as_view(), name='log-coleta-list')`
- Rota sem prefixo `/api/` — prefixo adicionado pelo urls.py raiz

**Task 04-04 — Testes:**
- `test_lista_logs_autenticado`: cria 2 logs, verifica count=2, ordenacao mais-recente-primeiro, campos status/iniciado_em/provedor_nome
- `test_lista_logs_sem_token_retorna_401`: verifica 401/403 sem JWT
- `test_lista_logs_vazia`: caso de borda com count=0
- `test_detalhe_erro_presente_quando_preenchido`: verifica campo detalhe_erro no resultado

## Test Results

| Suite | Testes | Status |
|-------|--------|--------|
| test_logs.py | 4 | PASSOU |
| test_alertas.py | 15 | PASSOU |
| test_inversores.py | 11 | PASSOU |
| test_usinas.py | 21 | PASSOU |
| test_garantias.py | 12 | PASSOU |
| test_auth.py | 7 | PASSOU |
| test_cors.py | 2 | PASSOU |
| **Total** | **72** | **PASSOU** |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] URLs absolutas em vez de reverse('api:log-coleta-list')**
- **Found during:** Task 04-04
- **Issue:** O plano especificava `reverse('api:log-coleta-list')` mas o namespace `api` nao esta registrado no urlconf de teste — levaria a `NoReverseMatch` em todos os 4 testes
- **Fix:** Substituido por URLs absolutas `/api/coleta/logs/` — padrao identico ao de todos os outros testes da fase (test_alertas.py, test_inversores.py, test_usinas.py, test_garantias.py)
- **Files modified:** backend_monitoramento/api/tests/test_logs.py
- **Commit:** bf7cda7

**2. [Rule 1 - Bug] Fixtures api_client/token_usuario substituidas por client/tokens**
- **Found during:** Task 04-04
- **Issue:** O plano mencionava `api_client` e `token_usuario` mas essas fixtures nao existem no conftest.py do projeto; as fixtures reais sao `client` (Django test client) e `tokens` (dict com access/refresh)
- **Fix:** Adaptado ao padrao real do conftest existente
- **Files modified:** backend_monitoramento/api/tests/test_logs.py
- **Commit:** bf7cda7

## Known Stubs

Nenhum. Todos os 4 testes implementados estao com corpos reais e passando. Nenhum skip remanescente em test_logs.py.

## Threat Surface

Todas as ameacas do threat_model cobertas:
- T-2-11: `permission_classes = [IsAuthenticated]` em LogColetaListView; teste explicito `test_lista_logs_sem_token_retorna_401` confirma 401
- T-2-12: `detalhe_erro` acessivel apenas com JWT valido (IsAuthenticated global)
- T-2-13: `pagination_class = PaginacaoSnapshots` (page_size=100, max=500); `select_related('credencial')` previne N+1

## Self-Check: PASSED

- [x] `api/serializers/logs.py` existe com `class LogColetaSerializer`
- [x] `api/serializers/logs.py` contem `fields = [` com `'id'`, `'status'`, `'iniciado_em'`
- [x] `api/serializers/logs.py` contem `provedor_nome` com `SerializerMethodField` e `get_provedor_nome`
- [x] `api/serializers/logs.py` NAO contem `payload_bruto`
- [x] `api/serializers/__init__.py` contem `from .logs import LogColetaSerializer`
- [x] `api/views/logs.py` existe com `class LogColetaListView`
- [x] `api/views/logs.py` contem `permission_classes = [IsAuthenticated]`
- [x] `api/views/logs.py` contem `select_related('credencial')`
- [x] `api/views/__init__.py` contem `from .logs import LogColetaListView`
- [x] `api/urls.py` contem `coleta/logs/`
- [x] `api/urls.py` contem `LogColetaListView.as_view()`
- [x] `api/tests/test_logs.py` contem `class TestLogColetaList`
- [x] `api/tests/test_logs.py` contem `test_lista_logs_sem_token_retorna_401`
- [x] Commit 629ab1d existe (Task 04-01)
- [x] Commit 87569d3 existe (Task 04-02)
- [x] Commit 36b335c existe (Task 04-03)
- [x] Commit bf7cda7 existe (Task 04-04)
- [x] 72 testes passando (suite completa, 0 skipped)
