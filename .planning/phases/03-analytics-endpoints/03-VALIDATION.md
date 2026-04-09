---
phase: 03
slug: analytics-endpoints
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-09
---

# Phase 03 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-django |
| **Config file** | backend_monitoramento/pytest.ini |
| **Quick run command** | `cd backend_monitoramento && python3 -m pytest api/tests/test_analytics.py -x --tb=short` |
| **Full suite command** | `cd backend_monitoramento && python3 -m pytest api/tests/ --tb=short` |
| **Estimated runtime** | ~2 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend_monitoramento && python3 -m pytest api/tests/test_analytics.py -x --tb=short`
- **After every plan wave:** Run `cd backend_monitoramento && python3 -m pytest api/tests/ --tb=short`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 3 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | ANA-01 | T-3-01 | 401 sem token | unit | `pytest api/tests/test_analytics.py -k potencia` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | ANA-02 | T-3-02 | 401 sem token | unit | `pytest api/tests/test_analytics.py -k ranking` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | ANA-03 | T-3-03 | 401 sem token; lat/lng null aceitos | unit | `pytest api/tests/test_analytics.py -k mapa` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `api/tests/test_analytics.py` — stubs para ANA-01, ANA-02, ANA-03
- [ ] Migration para adicionar `latitude`/`longitude` ao model Usina

*Existing infrastructure covers test framework and conftest — only test file and migration needed.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 3s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
