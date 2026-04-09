---
phase: 04-frontend-foundation
plan: "02"
subsystem: frontend
tags: [react, auth, login-form, sidebar, nav-user, react-router]
dependency_graph:
  requires:
    - plan: 04-01
      provides: [AuthContext, useAuth, ProtectedLayout, App.tsx router]
  provides:
    - frontend/admin/src/components/login-form.tsx (formulario conectado ao AuthContext)
    - frontend/admin/src/pages/LoginPage.tsx (redirect se ja autenticado)
    - frontend/admin/src/components/nav-user.tsx (logout com navigate explicito)
  affects:
    - Plans 05-x e 06-x (paginas de conteudo que usam o layout com sidebar funcional)
tech_stack:
  added: []
  patterns:
    - Form controlado com useState para email/password/error/loading
    - Mensagem de erro generica no catch (nao expoe detalhes internos — T-04-08)
    - Redirect hardcoded para / apos login (nunca de query param — T-04-03)
    - Redirect explicito para /login apos logout via useNavigate
    - LoginPage verifica isLoading antes de isAuthenticated para evitar flash
key_files:
  created: []
  modified:
    - frontend/admin/src/components/login-form.tsx
    - frontend/admin/src/pages/LoginPage.tsx
    - frontend/admin/src/components/nav-user.tsx
decisions:
  - "login-form usa Label + Input diretos (sem Field/FieldGroup) — componentes Field do shadcn eram desnecessariamente complexos para este form simples"
  - "nav-user ja estava adaptado pelo Plan 01; apenas adicionado navigate('/login') explicito apos logout()"
  - "app-sidebar e nav-main ja estavam completos do Plan 01 — nenhuma alteracao necessaria"
metrics:
  duration: "8 minutes"
  completed_date: "2026-04-09"
  tasks_completed: 1
  tasks_total: 2
  files_created: 0
  files_modified: 3
---

# Phase 04 Plan 02: Frontend Foundation — Auth Wiring Summary

**One-liner:** Login form conectado ao AuthContext (useAuth().login + navigate + error state), LoginPage com redirect-if-authenticated, nav-user com navigate explicito apos logout.

## What Was Built

### Task 1: Adaptar login-form, LoginPage e nav-user

**login-form.tsx — reescrito:**
- Estados controlados: `email`, `password`, `error`, `loading` via `useState`
- `const { login } = useAuth()` + `const navigate = useNavigate()`
- `handleSubmit`: preventDefault → setLoading(true) → `await login(email, password)` → `navigate('/', { replace: true })`
- Catch: `setError('Credenciais invalidas. Verifique email e senha.')` (mensagem generica — T-04-08)
- UI: titulo "Firma Solar", descricao "Acesse o painel administrativo", botao "Entrar"/"Entrando..." com `disabled={loading}`
- Removidos: "Forgot your password?", "Login with Google", "Don't have an account? Sign up"

**LoginPage.tsx — atualizado:**
- `const { isAuthenticated, isLoading } = useAuth()`
- Se `isLoading`: renderiza spinner (`Loader2Icon`)
- Se `isAuthenticated`: `return <Navigate to="/" replace />`
- Caso contrario: renderiza layout com `<LoginForm />`

**nav-user.tsx — pequeno ajuste:**
- Adicionado `useNavigate` de `react-router`
- onClick de "Sair": `logout(); navigate('/login', { replace: true })` em vez de apenas `logout()`

**Ja prontos pelo Plan 01 (sem alteracoes):**
- `app-sidebar.tsx`: sem TeamSwitcher/NavProjects, 4 links reais, useAuth para dados do usuario
- `nav-main.tsx`: NavLink com `end` prop, sem Collapsible, label "Navegacao"

## Verification Results

```
npm run build: built in 598ms (sem erros TypeScript)
TeamSwitcher em app-sidebar.tsx: 0 ocorrencias
NavProjects em app-sidebar.tsx: 0 ocorrencias
Collapsible em nav-main.tsx: 0 ocorrencias
NavLink em nav-main.tsx: 3 ocorrencias
useAuth em login-form.tsx: 2 ocorrencias
useAuth em nav-user.tsx: 2 ocorrencias
Forgot em login-form.tsx: 0 ocorrencias
Google em login-form.tsx: 0 ocorrencias
handleSubmit em login-form.tsx: 2 ocorrencias
navigate em login-form.tsx: 2 ocorrencias
setError em login-form.tsx: 3 ocorrencias
disabled={loading} em login-form.tsx: 1 ocorrencia
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Substituicao de Field/FieldGroup por Label+Input padrao**
- **Found during:** Task 1 (reescrita do login-form)
- **Issue:** O template original usava `Field`, `FieldGroup`, `FieldLabel`, `FieldDescription` do shadcn — componentes com complexidade desnecessaria para um form simples de 2 campos. O componente Field nao e um input em si e requer hierarquia especifica para funcionar corretamente.
- **Fix:** Substituido por `Label` + `Input` diretos (componentes shadcn padrao), com `div` para layout — mais simples, mais legivel e igualmente correto
- **Files modified:** `frontend/admin/src/components/login-form.tsx`
- **Commit:** 497d74f

**2. [Observacao] Plan 01 ja havia implementado app-sidebar, nav-main e nav-user**
- O SUMMARY do Plan 01 confirmou que esses 3 componentes foram totalmente adaptados na wave anterior.
- nav-user recebeu apenas o ajuste do `navigate('/login')` explicito apos logout.
- Nenhum retrabalho necessario.

## Known Stubs

Nenhum stub novo introduzido neste plano. Os stubs de paginas placeholder (UsinasPage, GarantiasPage, DashboardPage, AlertasPage) foram documentados no Plan 01 e permanecem intencionais.

## Threat Surface Scan

Nenhuma superficie nova fora do threat model. Mitigacoes do plano aplicadas:
- T-04-07 (credenciais via HTTPS): proxy Vite em dev, HTTPS em prod ✓
- T-04-08 (information disclosure no error): mensagem generica no catch ✓
- T-04-09 (logout limpa sessao): logout() remove localStorage + navigate('/login') ✓
- T-04-10 (ProtectedLayout bypass): LoginPage verifica isAuthenticated; redirect funciona em ambas direcoes ✓

## Self-Check: PASSED

- `frontend/admin/src/components/login-form.tsx` — FOUND, contem useAuth + handleSubmit + navigate
- `frontend/admin/src/pages/LoginPage.tsx` — FOUND, contem Navigate + isAuthenticated check
- `frontend/admin/src/components/nav-user.tsx` — FOUND, contem navigate('/login') apos logout
- Commit 497d74f — FOUND
- `npm run build` — PASSED sem erros
