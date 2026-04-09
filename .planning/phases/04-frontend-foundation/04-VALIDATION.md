---
phase: 04
slug: frontend-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-09
---

# Phase 04 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Manual verification (frontend foundation — no test runner in this phase) |
| **Config file** | N/A |
| **Quick run command** | `cd frontend/admin && npm run build` |
| **Full suite command** | `cd frontend/admin && npm run build && npm run lint` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend/admin && npm run build`
- **After every plan wave:** Run `cd frontend/admin && npm run build && npm run lint`
- **Before `/gsd-verify-work`:** Build must succeed, no TypeScript errors
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 04-01-01 | 01 | 1 | FE-01, FE-02 | build | `npm run build` | ⬜ pending |
| 04-01-02 | 01 | 1 | FE-03, FE-04 | build | `npm run build` | ⬜ pending |
| 04-02-01 | 02 | 2 | FE-05 | build | `npm run build` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `react-router` — routing library
- [ ] `axios` — HTTP client
- [ ] `jwt-decode` — JWT payload decoding

*Existing infrastructure covers Vite, React, TypeScript, shadcn/ui.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Login redirects to dashboard | FE-03 | Requires running backend + frontend | Login with valid credentials, verify redirect |
| Token refresh transparent | FE-04 | Requires expired token scenario | Wait 15min or manually expire, verify auto-refresh |
| Protected route redirect | FE-02 | Requires browser interaction | Clear localStorage, navigate to /dashboard, verify redirect to /login |
| Sidebar navigation works | FE-05 | Visual verification | Click each nav item, verify route change |

---

## Validation Sign-Off

- [ ] All tasks have build verification
- [ ] No TypeScript errors
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
