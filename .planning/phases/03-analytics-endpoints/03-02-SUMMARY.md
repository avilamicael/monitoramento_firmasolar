---
phase: 03-analytics-endpoints
plan: "02"
subsystem: backend
tags: [analytics, views, urls, tdd-green, aggregation, orm]
dependency_graph:
  requires: [03-01]
  provides: [PotenciaMediaView, RankingFabricantesView, MapaUsinasView, analytics-urls]
  affects: [api/views/analytics.py, api/views/__init__.py, api/urls.py]
tech_stack:
  added: []
  patterns: [APIView+Response, ListAPIView+pagination_class=None, values().annotate()+Avg+Count+F+Q, TDD-GREEN]
key_files:
  created:
    - backend_monitoramento/api/views/analytics.py
  modified:
    - backend_monitoramento/api/views/__init__.py
    - backend_monitoramento/api/urls.py
decisions:
  - "PotenciaMediaView usa APIView (nao ListAPIView) — retorna JSON customizado com media_geral_kw e por_provedor, nao queryset flat"
  - "RankingFabricantesView usa values(provedor=F('usina__provedor')) para renomear chave de usina__provedor para provedor no dict resultante"
  - "MapaUsinasView usa pagination_class=None para desabilitar paginacao — frontend precisa de todos os pontos do mapa de uma vez"
  - "Todos os 3 endpoints herdam IsAuthenticated global (DEFAULT_PERMISSION_CLASSES da Phase 1) — sem configuracao adicional necessaria"
metrics:
  duration_minutes: 12
  completed_date: "2026-04-09"
  tasks_completed: 2
  files_changed: 3
---

# Phase 03 Plan 02: Implementacao das Views de Analytics e Fase GREEN Summary

**One-liner:** 3 views de analytics implementadas (PotenciaMediaView com Avg, RankingFabricantesView com Count condicional top 5, MapaUsinasView sem paginacao), URLs registradas, e 20 testes TDD passando — suite completa 92/92 verde.

## What Was Built

### Task 1: PotenciaMediaView, RankingFabricantesView e MapaUsinasView

**Commit:** `f07f7fa`

1. **`api/views/analytics.py`** criado com 3 classes de view:

   - **`PotenciaMediaView(APIView)`** — ANA-01. Filtra usinas ativas com `ultimo_snapshot__isnull=False`, executa `aggregate(Avg('ultimo_snapshot__potencia_kw'))` para media geral e `values('provedor').annotate(media_kw=Avg(...), usinas_ativas=Count('id'))` para agrupamento por provedor. Zero N+1: `select_related('ultimo_snapshot')` aplicado antes da query.

   - **`RankingFabricantesView(APIView)`** — ANA-02. Parte de `Inversor.objects`, usa `values(provedor=F('usina__provedor'))` para renomear a chave (evita `usina__provedor` nos dicts — Pitfall 3 do RESEARCH.md), e `Count('id', filter=Q(ultimo_snapshot__isnull=False, ultimo_snapshot__pac_kw__gt=0))` para contar apenas inversores ativos segundo D-03. Slice `[:5]` no queryset (LIMIT no SQL, nao em Python).

   - **`MapaUsinasView(generics.ListAPIView)`** — ANA-03. `pagination_class = None` desabilita paginacao. `get_queryset()` retorna todas as usinas com `select_related('ultimo_snapshot')` para que `UsinaMapaSerializer.get_status()` nao gere N+1.

2. **`api/views/__init__.py`** atualizado com import das 3 views.

### Task 2: Registro de URLs e fase GREEN

**Commit:** `96313ff`

1. **`api/urls.py`** — 3 paths adicionados antes do `include(router.urls)`:
   - `analytics/potencia/` → `PotenciaMediaView`
   - `analytics/ranking-fabricantes/` → `RankingFabricantesView`
   - `analytics/mapa/` → `MapaUsinasView`

2. **Fase GREEN confirmada:** todos os 20 testes de `test_analytics.py` passam.

3. **Suite completa verde:** 92 testes passando (72 existentes + 20 analytics).

| Classe de Teste | Requisito | Testes | Status |
|-----------------|-----------|--------|--------|
| `TestPotenciaMedia` | ANA-01 | 5 | PASSOU |
| `TestRankingFabricantes` | ANA-02 | 7 | PASSOU |
| `TestMapaUsinas` | ANA-03 | 8 | PASSOU |

## Decisions Made

1. **`APIView` para potencia e ranking, `ListAPIView` para mapa** — potencia e ranking retornam JSON customizado (nao queryset flat), portanto `APIView` com `Response(dict)` e a escolha correta. Mapa retorna lista de objetos — `ListAPIView` com serializer e o padrao adequado.

2. **`values(provedor=F('usina__provedor'))` no ranking** — evita a chave `usina__provedor` com underscores duplos no dict resultante do ORM. Conforme Pitfall 3 do RESEARCH.md.

3. **`pagination_class = None` na view, nao global** — paginacao global continua ativa para os outros endpoints. Apenas `MapaUsinasView` desabilita, que e o comportamento correto para o endpoint de mapa.

## Deviations from Plan

None — plano executado exatamente como escrito. As 3 views foram implementadas seguindo os patterns do RESEARCH.md, os pitfalls foram evitados, e todos os testes passaram na primeira execucao sem ajustes.

## Known Stubs

Nenhum — todos os 3 endpoints estao completamente implementados e testados. Nenhum dado hardcoded, placeholder ou TODO nos arquivos criados.

## Threat Flags

Nenhum — os 3 endpoints introduzem superficie de rede prevista no threat model do plano (T-3-01, T-3-02, T-3-03). Todos protegidos por `IsAuthenticated` global herdado da configuracao da Phase 1. Confirmado pelos testes `test_requer_auth` de cada classe (401 sem token).

## Self-Check: PASSED

- [x] `backend_monitoramento/api/views/analytics.py` existe (90 linhas)
- [x] `backend_monitoramento/api/views/__init__.py` atualizado com imports de analytics
- [x] `backend_monitoramento/api/urls.py` contem `analytics/potencia/`, `analytics/ranking-fabricantes/`, `analytics/mapa/`
- [x] Commit `f07f7fa` existe: `feat(03-02): implementar PotenciaMediaView, RankingFabricantesView e MapaUsinasView`
- [x] Commit `96313ff` existe: `feat(03-02): registrar URLs de analytics e fazer testes GREEN`
- [x] 20 testes de analytics passando
- [x] 92 testes totais passando (suite completa verde)
