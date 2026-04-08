---
phase: 01-api-infrastructure
plan: 02
subsystem: api/tests
tags: [pytest, jwt, cors, garantia, django-db, sqlite]

# Dependency graph
requires: [01-01]
provides:
  - Suite de testes automatizados cobrindo API-02 a API-06 e GAR-01
  - 7 testes de autenticacao JWT (login, refresh, blacklist, protecao, lifetimes)
  - 2 testes de CORS (bloqueio e permissao de origem)
  - 8 testes de GarantiaUsina (data_fim, bissexto, ativa, dias_restantes, str, persistencia)
  - Settings de teste com SQLite em memoria para CI sem PostgreSQL
  - Migration merge 0004 resolvendo conflito entre 0002_garantiausina e 0003_snapshotinversor
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - pytest-django com settings dedicados de teste (SQLite em memoria)
    - Fixtures de usuario via django_user_model (sem hardcoding de credenciais)
    - Testes de CORS via settings fixture para isolamento por teste
    - Testes de model sem salvar no banco (instanciacao direta para properties calculadas)
    - Migration merge para resolver branches paralelas de migracao

key-files:
  created:
    - backend_monitoramento/api/tests/__init__.py
    - backend_monitoramento/api/tests/test_auth.py
    - backend_monitoramento/api/tests/test_cors.py
    - backend_monitoramento/usinas/tests/__init__.py
    - backend_monitoramento/usinas/tests/test_garantia.py
    - backend_monitoramento/config/settings/test.py
    - backend_monitoramento/usinas/migrations/0004_merge_garantiausina_snapshotinversor.py
  modified:
    - backend_monitoramento/pytest.ini

key-decisions:
  - "Settings de teste com SQLite em memoria: PostgreSQL nao disponivel localmente; SQLite suficiente para testar logica de negocio e JWT"
  - "pytest.ini aponta para config.settings.test: isolamento de testes sem depender de .env ou servicos externos"
  - "Migration merge 0004 criada manualmente: resolve conflito entre branch GarantiaUsina (plan 01) e branch SnapshotInversor (modificacoes em andamento)"

# Metrics
duration: 15min
completed: 2026-04-08
---

# Phase 01 Plan 02: Test Suite Summary

**17 testes automatizados cobrindo autenticacao JWT, CORS e GarantiaUsina — suite completa verde com SQLite em memoria, sem dependencia de PostgreSQL local**

## Performance

- **Duration:** ~15 min
- **Completed:** 2026-04-08
- **Tasks:** 2
- **Files created:** 7
- **Files modified:** 1
- **Tests:** 17/17 passing

## Accomplishments

- 7 testes JWT: login valido/invalido, refresh, rotacao com blacklist, protecao 401 sem/com token, lifetimes (15min/7d)
- 2 testes CORS: bloqueio de origem invalida, permissao de origem configurada
- 8 testes GarantiaUsina: data_fim calculada, fim de mes bissexto, ativa/inativa, dias_restantes positivo/zero, __str__, persistencia no banco
- Settings de teste dedicados com SQLite em memoria (sem PostgreSQL local necessario)
- Migration merge 0004 para resolver conflito de migracao preexistente

## Task Commits

1. **Task 1: Testes de autenticacao JWT + settings de teste** - `c2bc982` (test)
2. **Task 2: Testes de CORS e GarantiaUsina** - `3543c02` (test)

## Files Created/Modified

- `backend_monitoramento/api/tests/__init__.py` - Modulo de testes da app api
- `backend_monitoramento/api/tests/test_auth.py` - 7 testes JWT (TestAutenticacaoJWT)
- `backend_monitoramento/api/tests/test_cors.py` - 2 testes CORS (TestCORS)
- `backend_monitoramento/usinas/tests/__init__.py` - Modulo de testes da app usinas
- `backend_monitoramento/usinas/tests/test_garantia.py` - 8 testes GarantiaUsina (TestGarantiaUsina)
- `backend_monitoramento/config/settings/test.py` - Settings com SQLite em memoria, PASSWORD_HASHERS MD5, logging silenciado
- `backend_monitoramento/usinas/migrations/0004_merge_garantiausina_snapshotinversor.py` - Migration merge
- `backend_monitoramento/pytest.ini` - DJANGO_SETTINGS_MODULE atualizado para config.settings.test

## Decisions Made

- **SQLite em memoria para testes**: PostgreSQL nao disponivel localmente (igual ao plan 01). Criar settings dedicado de teste e a abordagem correta — testes de logica de negocio e JWT nao precisam de PostgreSQL.
- **Migration merge manual**: Duas branches de migracao paralelas (0002_garantiausina do plan 01 e 0002_snapshotinversor_tensao_corrente existente) causavam conflito. Migration merge 0004 resolve sem alterar comportamento.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Settings de teste com SQLite em memoria**
- **Found during:** Task 1 — primeiro run de testes
- **Issue:** pytest.ini apontava para config.settings.dev que usa PostgreSQL (Connection refused localmente)
- **Fix:** Criado config/settings/test.py com SQLite em memoria; pytest.ini atualizado para usa-lo
- **Files modified:** backend_monitoramento/config/settings/test.py, backend_monitoramento/pytest.ini
- **Commit:** c2bc982

**2. [Rule 3 - Blocking] Migration merge para resolver conflito**
- **Found during:** Task 1 — apos fix dos settings, detectado conflito de migracoes ao criar banco de teste
- **Issue:** Duas migracoes 0002 com dependencies em 0001_initial (0002_garantiausina e 0002_snapshotinversor_tensao_corrente)
- **Fix:** Criada migration merge 0004 dependendo dos dois leaf nodes (0002_garantiausina e 0003_snapshotinversor_frequencia_temperatura)
- **Files modified:** backend_monitoramento/usinas/migrations/0004_merge_garantiausina_snapshotinversor.py
- **Commit:** c2bc982

**3. [Rule 1 - Bug] Campo credenciais_enc como string na fixture**
- **Found during:** Task 2 — ao revisar model CredencialProvedor antes de implementar
- **Issue:** Plano estimava credenciais_enc=b'test' (bytes), mas o campo e TextField (string)
- **Fix:** Fixture usa credenciais_enc='enc_placeholder' (string)
- **Files modified:** backend_monitoramento/usinas/tests/test_garantia.py
- **Commit:** 3543c02

## Requirements Coverage

| Requirement | Tests | Status |
|-------------|-------|--------|
| API-02 | test_login_retorna_tokens, test_login_credenciais_invalidas | Covered |
| API-03 | test_refresh_emite_novo_access, test_refresh_token_rotacionado_invalido | Covered |
| API-04 | test_endpoint_protegido_sem_token, test_endpoint_protegido_com_token | Covered |
| API-05 | test_cors_bloqueia_origem_invalida, test_cors_permite_origem_valida | Covered |
| API-06 | test_token_lifetimes | Covered |
| GAR-01 | 8 testes TestGarantiaUsina | Covered |

## Known Stubs

None — todos os testes testam comportamento real sem placeholders.

## Threat Flags

None — arquivos criados sao exclusivamente de teste; nenhuma nova superficie de ataque introduzida.

---
*Phase: 01-api-infrastructure*
*Completed: 2026-04-08*

## Self-Check: PASSED

- FOUND: backend_monitoramento/api/tests/__init__.py
- FOUND: backend_monitoramento/api/tests/test_auth.py
- FOUND: backend_monitoramento/api/tests/test_cors.py
- FOUND: backend_monitoramento/usinas/tests/__init__.py
- FOUND: backend_monitoramento/usinas/tests/test_garantia.py
- FOUND: backend_monitoramento/config/settings/test.py
- FOUND: backend_monitoramento/usinas/migrations/0004_merge_garantiausina_snapshotinversor.py
- FOUND commit: c2bc982
- FOUND commit: 3543c02
