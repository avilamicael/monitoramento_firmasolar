---
phase: 1
slug: api-infrastructure
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-07
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-django (já configurado) |
| **Config file** | `backend_monitoramento/pytest.ini` |
| **Quick run command** | `cd backend_monitoramento && pytest api/tests/ usinas/tests/test_garantia.py -x -q` |
| **Full suite command** | `cd backend_monitoramento && pytest -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend_monitoramento && pytest api/tests/ usinas/tests/test_garantia.py -x -q`
- **After every plan wave:** Run `cd backend_monitoramento && pytest -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 0 | API-01 | — | N/A | stub | `pytest api/tests/ -x -q` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | API-02 | — | Login com creds válidas → 200 + tokens | integration | `pytest api/tests/test_auth.py::test_login_retorna_tokens -x` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 1 | API-02 | — | Login com creds inválidas → 401 | integration | `pytest api/tests/test_auth.py::test_login_credenciais_invalidas -x` | ❌ W0 | ⬜ pending |
| 1-01-04 | 01 | 2 | API-03 | — | Refresh válido → novo access token | integration | `pytest api/tests/test_auth.py::test_refresh_emite_novo_access -x` | ❌ W0 | ⬜ pending |
| 1-01-05 | 01 | 2 | API-03 | T-1-01 | Token original não reutilizável após rotação | integration | `pytest api/tests/test_auth.py::test_refresh_token_rotacionado_invalido -x` | ❌ W0 | ⬜ pending |
| 1-01-06 | 01 | 2 | API-04 | — | Endpoint sem token → 401 | integration | `pytest api/tests/test_auth.py::test_endpoint_protegido_sem_token -x` | ❌ W0 | ⬜ pending |
| 1-01-07 | 01 | 2 | API-05 | T-1-02 | CORS bloqueia origem não listada | integration | `pytest api/tests/test_cors.py::test_cors_bloqueia_origem_invalida -x` | ❌ W0 | ⬜ pending |
| 1-01-08 | 01 | 2 | API-05 | — | CORS permite origem configurada | integration | `pytest api/tests/test_cors.py::test_cors_permite_origem_valida -x` | ❌ W0 | ⬜ pending |
| 1-01-09 | 01 | 3 | GAR-01 | — | `data_fim` calculada corretamente | unit | `pytest usinas/tests/test_garantia.py::test_garantia_data_fim_calculada -x` | ❌ W0 | ⬜ pending |
| 1-01-10 | 01 | 3 | GAR-01 | — | `ativa` True quando dentro do prazo | unit | `pytest usinas/tests/test_garantia.py::test_garantia_ativa_quando_dentro_do_prazo -x` | ❌ W0 | ⬜ pending |
| 1-01-11 | 01 | 3 | GAR-01 | — | `ativa` False quando vencida | unit | `pytest usinas/tests/test_garantia.py::test_garantia_inativa_quando_vencida -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend_monitoramento/api/__init__.py` — app Django precisa existir
- [ ] `backend_monitoramento/api/tests/__init__.py` — pacote de testes do app api
- [ ] `backend_monitoramento/api/tests/test_auth.py` — stubs para API-02, API-03, API-04
- [ ] `backend_monitoramento/api/tests/test_cors.py` — stubs para API-05
- [ ] `backend_monitoramento/usinas/tests/test_garantia.py` — stubs para GAR-01

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Access token expira em 15 min | API-06 | Requer esperar 15 min ou manipular clock | Decodificar JWT com `python -c "import base64, json; print(json.loads(base64.b64decode(token.split('.')[1]+'==')))"` e verificar `exp - iat == 900` |
| Refresh token expira em 7 dias | API-06 | Requer esperar 7 dias ou manipular clock | Decodificar JWT do refresh e verificar `exp - iat == 604800` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
