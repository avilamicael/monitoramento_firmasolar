---
phase: 2
slug: rest-endpoints
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-09
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-django 4.x |
| **Config file** | `backend_monitoramento/pytest.ini` |
| **Settings** | `config.settings.test` (SQLite :memory:) |
| **Quick run command** | `cd backend_monitoramento && pytest api/tests/ -x --tb=short` |
| **Full suite command** | `cd backend_monitoramento && pytest --tb=short` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend_monitoramento && pytest api/tests/ -x --tb=short`
- **After every plan wave:** Run `cd backend_monitoramento && pytest --tb=short`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 2-W0-01 | W0 | 0 | USN-01..05 | — | N/A | unit stub | `pytest api/tests/test_usinas.py --collect-only` | ❌ W0 | ⬜ pending |
| 2-W0-02 | W0 | 0 | GAR-02..06 | — | N/A | unit stub | `pytest api/tests/test_garantias.py --collect-only` | ❌ W0 | ⬜ pending |
| 2-W0-03 | W0 | 0 | INV-01..03 | — | N/A | unit stub | `pytest api/tests/test_inversores.py --collect-only` | ❌ W0 | ⬜ pending |
| 2-W0-04 | W0 | 0 | ALT-01..04 | — | N/A | unit stub | `pytest api/tests/test_alertas.py --collect-only` | ❌ W0 | ⬜ pending |
| 2-W0-05 | W0 | 0 | LOG-01 | — | N/A | unit stub | `pytest api/tests/test_logs.py --collect-only` | ❌ W0 | ⬜ pending |
| 2-01-01 | 01 | 1 | USN-01 | — | 401 sem token | integration | `pytest api/tests/test_usinas.py -x` | ✅ W0 | ⬜ pending |
| 2-01-02 | 01 | 1 | USN-02 | — | 401 sem token | integration | `pytest api/tests/test_usinas.py::TestUsinaDetalhe -x` | ✅ W0 | ⬜ pending |
| 2-01-03 | 01 | 1 | USN-03 | — | 401 sem token | integration | `pytest api/tests/test_usinas.py::TestUsinaPatch -x` | ✅ W0 | ⬜ pending |
| 2-01-04 | 01 | 1 | USN-04 | — | status_garantia calculado | integration | `pytest api/tests/test_usinas.py -x -k status_garantia` | ✅ W0 | ⬜ pending |
| 2-01-05 | 01 | 1 | USN-05 | — | 401 sem token | integration | `pytest api/tests/test_usinas.py::TestUsinaSnapshots -x` | ✅ W0 | ⬜ pending |
| 2-02-01 | 02 | 1 | GAR-02 | — | 401 sem token | integration | `pytest api/tests/test_garantias.py::TestGarantiaUpsert -x` | ✅ W0 | ⬜ pending |
| 2-02-02 | 02 | 1 | GAR-03 | — | 401 sem token | integration | `pytest api/tests/test_garantias.py::TestGarantiaFiltros -x` | ✅ W0 | ⬜ pending |
| 2-02-03 | 02 | 1 | GAR-04 | — | dias_restantes correto | integration | `pytest api/tests/test_garantias.py -x -k dias_restantes` | ✅ W0 | ⬜ pending |
| 2-02-04 | 02 | 1 | GAR-05/06 | — | garantia não bloqueia coleta | integration | `pytest api/tests/test_garantias.py::TestGarantiaVisibilidade -x` | ✅ W0 | ⬜ pending |
| 2-03-01 | 03 | 2 | INV-01 | — | 401 sem token | integration | `pytest api/tests/test_inversores.py -x` | ✅ W0 | ⬜ pending |
| 2-03-02 | 03 | 2 | INV-02 | — | 401 sem token | integration | `pytest api/tests/test_inversores.py::TestInversorDetalhe -x` | ✅ W0 | ⬜ pending |
| 2-03-03 | 03 | 2 | INV-03 | — | 401 sem token | integration | `pytest api/tests/test_inversores.py::TestInversorSnapshots -x` | ✅ W0 | ⬜ pending |
| 2-04-01 | 04 | 2 | ALT-01 | — | 401 sem token | integration | `pytest api/tests/test_alertas.py -x` | ✅ W0 | ⬜ pending |
| 2-04-02 | 04 | 2 | ALT-02 | — | 401 sem token | integration | `pytest api/tests/test_alertas.py::TestAlertaDetalhe -x` | ✅ W0 | ⬜ pending |
| 2-04-03 | 04 | 2 | ALT-03 | — | 401 sem token | integration | `pytest api/tests/test_alertas.py::TestAlertaPatch -x` | ✅ W0 | ⬜ pending |
| 2-04-04 | 04 | 2 | ALT-04 | — | com_garantia em todas respostas | integration | `pytest api/tests/test_alertas.py -x -k com_garantia` | ✅ W0 | ⬜ pending |
| 2-05-01 | 05 | 3 | LOG-01 | — | 401 sem token | integration | `pytest api/tests/test_logs.py -x` | ✅ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `api/tests/conftest.py` — fixtures compartilhadas (credencial, usina, inversor, garantia, alerta, tokens JWT)
- [ ] `api/tests/test_usinas.py` — stubs para USN-01..05
- [ ] `api/tests/test_garantias.py` — stubs para GAR-02..06
- [ ] `api/tests/test_inversores.py` — stubs para INV-01..03
- [ ] `api/tests/test_alertas.py` — stubs para ALT-01..04
- [ ] `api/tests/test_logs.py` — stub para LOG-01
- [ ] `requirements/base.txt` — adicionar `django-filter==25.2`

*Wave 0 deve ser completado antes de qualquer tarefa de implementação.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Filtro status_garantia Python vs SQL | GAR-05/06 | data_fim é @property, não coluna SQL | Confirmar via Django shell: `GarantiaUsina.objects.filter(data_fim__gte=date.today())` retorna FieldError |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
