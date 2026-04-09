---
phase: 03-analytics-endpoints
plan: "01"
subsystem: backend
tags: [analytics, migration, tdd, serializers, fixtures]
dependency_graph:
  requires: []
  provides: [migration-lat-lng, UsinaMapaSerializer, test-analytics-RED]
  affects: [usinas/models.py, api/serializers/analytics.py, api/tests/conftest.py]
tech_stack:
  added: []
  patterns: [ModelSerializer+SerializerMethodField, TDD-RED, pytest-fixtures]
key_files:
  created:
    - backend_monitoramento/usinas/migrations/0005_usina_add_lat_lng.py
    - backend_monitoramento/api/serializers/analytics.py
    - backend_monitoramento/api/tests/test_analytics.py
  modified:
    - backend_monitoramento/usinas/models.py
    - backend_monitoramento/api/serializers/__init__.py
    - backend_monitoramento/api/tests/conftest.py
decisions:
  - "UsinaMapaSerializer usa SerializerMethodField para status — derivado de ultimo_snapshot.status ou 'sem_dados'"
  - "Fixtures de analytics adicionadas ao conftest global (nao inline nos testes) para reuso entre testes de ANA-01/02/03"
  - "20 testes criados (minimo era 17) para cobertura completa dos comportamentos descritos no plano"
metrics:
  duration_minutes: 15
  completed_date: "2026-04-09"
  tasks_completed: 2
  files_changed: 6
---

# Phase 03 Plan 01: Migration lat/lng, UsinaMapaSerializer e Testes RED Summary

**One-liner:** Migration reversivel com campos lat/lng no model Usina, UsinaMapaSerializer com SerializerMethodField de status, e 20 testes RED cobrindo ANA-01/02/03 que falham com 404 aguardando implementacao no Plan 02.

## What Was Built

### Task 1: Migration lat/lng + serializer de mapa + fixtures de analytics

**Commit:** `648688d`

1. **Model Usina** — campos `latitude` e `longitude` adicionados (`FloatField(null=True, blank=True)`) conforme decisao D-01. Posicionados antes do campo `ativo`, como especificado no plano.

2. **Migration reversivel** — `0005_usina_add_lat_lng.py` gerada via `makemigrations`. Usa `AddField` com `null=True` — totalmente reversivel via `RemoveField` sem perda de dados. Usinas existentes recebem `NULL` automaticamente.

3. **UsinaMapaSerializer** — criado em `api/serializers/analytics.py`. Expoe `id, nome, provedor, latitude, longitude, ativo, status`. O campo `status` e calculado via `get_status()`: retorna `ultimo_snapshot.status` se existir, senao `'sem_dados'`.

4. **Exportacao** — `api/serializers/__init__.py` atualizado com `from .analytics import UsinaMapaSerializer`.

5. **Fixtures de analytics** — adicionadas ao `conftest.py` compartilhado:
   - `snapshot_usina_hoymiles` — SnapshotUsina 3.0 kW para usina_hoymiles
   - `inversor_hoymiles` — Inversor vinculado a usina_hoymiles
   - `snapshot_inversor_hoymiles` — SnapshotInversor pac_kw=2.5 para inversor_hoymiles
   - `inversor_inativo` — Inversor sem `ultimo_snapshot` (testa exclusao no ranking)
   - `inversor_pac_zero` — Inversor com snapshot `pac_kw=0.0` (testa exclusao no ranking)

### Task 2: Testes RED para ANA-01, ANA-02, ANA-03

**Commit:** `955ac1e`

Arquivo `api/tests/test_analytics.py` criado com **20 testes** em 3 classes:

| Classe | Requisito | Testes | Cobertura |
|--------|-----------|--------|-----------|
| `TestPotenciaMedia` | ANA-01 | 5 | auth, media_geral, por_provedor, sem_snapshots, exclusao usina sem snapshot |
| `TestRankingFabricantes` | ANA-02 | 7 | auth, ranking ordenado, limite top 5 (sem auth + com auth), exclui sem snapshot, exclui pac_zero, sem inversores |
| `TestMapaUsinas` | ANA-03 | 8 | auth, retorna_todas, sem_coords=null, com_coords, sem_paginacao, status, status_sem_dados, campos_obrigatorios |

**Status RED confirmado:** todos os 20 testes falham com 404 (endpoints `/api/analytics/*` nao existem).

**Suite existente intacta:** 72 testes continuam passando.

## Decisions Made

1. **`inversor_pac_zero` fixture usa `inv.save()` para vincular snapshot** — necessario para garantir que o `ultimo_snapshot` OneToOneField seja populado corretamente.

2. **`test_top_5_limite` separado em 2 testes** — um verifica 401 sem auth, outro verifica o limite de 5 resultados com auth. Isso torna o comportamento de cada caso explicitamente testado.

3. **`test_status_sem_dados_quando_sem_snapshot` adicionado** — comportamento extra alem do minimo do plano, cobrindo o caminho `sem_dados` do `UsinaMapaSerializer.get_status()`.

4. **`test_campos_obrigatorios` adicionado** — verifica presenca de todos os 7 campos na resposta, garantindo contrato da API antes da implementacao.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Worktree desincronizado — working tree sem arquivos da Phase 02**
- **Found during:** Task 1 (ao tentar fazer commit)
- **Issue:** O reset do HEAD para `a3d3e35d` nao restaurou os arquivos da Phase 02 no working tree do worktree. O checkout `HEAD -- .` restaurou os arquivos, mas um `views.py` legado (Phase 01) apareceu como arquivo nao rastreado e foi acidentalmente staged.
- **Fix:** `git rm --cached backend_monitoramento/api/views.py` + amend do commit para remover o arquivo. O `views.py` foi removido do disco.
- **Arquivos afetados:** nenhum arquivo de producao — apenas limpeza do worktree.
- **Commit:** `648688d` (commit amended)

## Known Stubs

Nenhum — Plan 01 e fase de TDD RED. Nenhum endpoint implementado intencionalmente. Os testes falham com 404, que e o comportamento esperado desta fase. O Plan 02 implementa as views e faz os testes passarem.

## Threat Flags

Nenhum — Plan 01 nao introduz endpoints ou rotas novas. A migration adiciona campos `lat/lng` ao model `Usina` mas nao expoe superficie de rede. A exposicao dos dados de localizacao (ANA-03) esta contemplada em T-3-03 do threat model do plano, mitigada por `IsAuthenticated` global.

## Self-Check: PASSED

- [x] `backend_monitoramento/usinas/migrations/0005_usina_add_lat_lng.py` existe
- [x] `backend_monitoramento/api/serializers/analytics.py` existe
- [x] `backend_monitoramento/api/tests/test_analytics.py` existe com 20 testes
- [x] Commit `648688d` existe: `feat(03-01): migration lat/lng, UsinaMapaSerializer e fixtures de analytics`
- [x] Commit `955ac1e` existe: `test(03-01): add failing tests (RED) for ANA-01, ANA-02, ANA-03`
- [x] 72 testes existentes passando
- [x] 20 testes de analytics falhando com 404 (RED confirmado)
