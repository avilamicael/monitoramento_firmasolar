---
phase: 04-frontend-foundation
plan: "01"
subsystem: frontend
tags: [react, vite, axios, jwt, react-router, auth, sidebar]
dependency_graph:
  requires: []
  provides:
    - frontend/admin/src/lib/api.ts (instancia axios com interceptors de auth)
    - frontend/admin/src/contexts/auth.tsx (AuthContext + AuthProvider + useAuth)
    - frontend/admin/src/App.tsx (router com ProtectedLayout)
    - frontend/admin/src/main.tsx (entry point com AuthProvider)
  affects:
    - Plan 04-02 (wiring do login form usara useAuth().login)
    - Plans 05-x e 06-x (paginas de conteudo consumirao useAuth e instancia api)
tech_stack:
  added:
    - react-router@7.14.0 (roteamento SPA com rotas protegidas)
    - axios@1.15.0 (HTTP client com interceptors)
    - jwt-decode@4.0.0 (decodificacao local de JWT para verificar expiracao)
  patterns:
    - axios interceptor com flag _retry para prevenir loop de refresh
    - AuthContext com isLoading: true para prevenir flash de tela de login
    - ProtectedLayout com Outlet (react-router v7)
    - NavLink com end prop para active state na sidebar
key_files:
  created:
    - frontend/admin/src/lib/api.ts
    - frontend/admin/src/contexts/auth.tsx
    - frontend/admin/src/pages/LoginPage.tsx
    - frontend/admin/src/pages/DashboardPage.tsx
    - frontend/admin/src/pages/UsinasPage.tsx
    - frontend/admin/src/pages/GarantiasPage.tsx
    - frontend/admin/src/pages/AlertasPage.tsx
  modified:
    - frontend/admin/package.json (+ react-router, axios, jwt-decode)
    - frontend/admin/package-lock.json
    - frontend/admin/vite.config.ts (+ server.proxy /api -> localhost:8000)
    - frontend/admin/tsconfig.app.json (+ ignoreDeprecations 6.0)
    - frontend/admin/src/App.tsx (substituido: router + ProtectedLayout)
    - frontend/admin/src/main.tsx (+ AuthProvider wrap)
    - frontend/admin/src/components/nav-main.tsx (links planos com NavLink)
    - frontend/admin/src/components/app-sidebar.tsx (remover TeamSwitcher/NavProjects, 4 links reais)
    - frontend/admin/src/components/nav-user.tsx (iniciais dinamicas, logout)
decisions:
  - "Tokens JWT armazenados em localStorage (access_token, refresh_token) — decisao D-02 lockada"
  - "axios.post puro (nao instancia api) para chamada de refresh — previne loop de interceptor"
  - "isLoading: true como estado inicial do AuthContext — previne flash de tela de login"
  - "NavLink com end prop em '/' — Dashboard nao fica ativo em subrotas"
  - "Iniciais do usuario calculadas dinamicamente a partir do nome real (getInitials)"
metrics:
  duration: "7 minutes"
  completed_date: "2026-04-09"
  tasks_completed: 2
  tasks_total: 2
  files_created: 8
  files_modified: 9
---

# Phase 04 Plan 01: Frontend Foundation — Auth Infrastructure Summary

**One-liner:** Infraestrutura de auth JWT com axios interceptors (Bearer + refresh automatico), AuthContext com decodificacao local, router react-router v7 com ProtectedLayout + sidebar adaptada.

## What Was Built

### Task 1: Dependencias, Proxy Vite e Instancia Axios

- Instalados `react-router@7`, `axios@1`, `jwt-decode@4`
- `vite.config.ts` atualizado com `server.proxy` `/api` → `http://localhost:8000`
- `src/lib/api.ts` criado com:
  - Request interceptor: injeta `Authorization: Bearer {access_token}` de `localStorage`
  - Response interceptor: captura 401, tenta refresh via `axios.post` puro (nao a instancia `api` para evitar loop), salva novo `access` e `refresh` (ROTATE_REFRESH_TOKENS=True), repete requisicao original
  - Flag `_retry` previne loop infinito (T-04-04)
  - Em falha do refresh: limpa tokens e redireciona via `window.location.href = '/login'` (nao `useNavigate` — fora do contexto React)

### Task 2: AuthContext, Router e Paginas

- `src/contexts/auth.tsx`: AuthProvider com estado `{ user, isAuthenticated, isLoading: true }`, decodificacao local do JWT no mount (sem chamada de rede), `login()` via `/api/auth/token/`, `logout()` limpa localStorage
- `src/App.tsx`: `createBrowserRouter` com `ProtectedLayout` (verifica `isLoading` e `isAuthenticated`), 5 rotas (1 publica + 4 protegidas com sidebar)
- `src/main.tsx`: `AuthProvider` envolvendo `App`
- 5 paginas placeholder: LoginPage, DashboardPage, UsinasPage, GarantiasPage, AlertasPage
- `nav-main.tsx` reescrito com `NavLink` (links planos, sem Collapsible)
- `app-sidebar.tsx` adaptado: TeamSwitcher e NavProjects removidos, 4 links com icones Lucide (`LayoutDashboard`, `Zap`, `Shield`, `Bell`), header "Firma Solar"
- `nav-user.tsx` adaptado: iniciais dinamicas via `getInitials()`, logout conectado ao `useAuth()`

## Verification Results

```
npm run build: ✓ built in 653ms (sem erros TypeScript)
react-router em package.json: ✓
axios em package.json: ✓
jwt-decode em package.json: ✓
proxy em vite.config.ts: ✓
AuthProvider em main.tsx: ✓
ProtectedLayout em App.tsx: ✓
_retry em api.ts: ✓
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] TS6 deprecation de `baseUrl` em tsconfig.app.json**
- **Found during:** Task 1 (build falhou com TS5101)
- **Issue:** TypeScript 6.0 deprecou a opcao `baseUrl` em `tsconfig.app.json`; build bloqueado com erro `TS5101`
- **Fix:** Adicionado `"ignoreDeprecations": "6.0"` em `tsconfig.app.json`
- **Files modified:** `frontend/admin/tsconfig.app.json`
- **Commit:** 8178a5e

**2. [Rule 2 - Missing Critical] Logout no NavUser**
- **Found during:** Task 2 (adaptacao do nav-user.tsx)
- **Issue:** Template original tinha opcoes de menu inapropriadas (Upgrade to Pro, Account, Billing, Notifications) e sem logout funcional
- **Fix:** Simplificado para apenas "Sair" conectado ao `useAuth().logout()`; iniciais calculadas dinamicamente com `getInitials()`
- **Files modified:** `frontend/admin/src/components/nav-user.tsx`
- **Commit:** c98026c

**3. [Rule 2 - Missing Critical] Adaptacao do app-sidebar.tsx**
- **Found during:** Task 2 (ao implementar App.tsx com AppSidebar)
- **Issue:** O template sidebar-07 tinha TeamSwitcher e NavProjects incompativeis com o sistema (admin unico, sem multiplos times/projetos)
- **Fix:** Removidos TeamSwitcher e NavProjects; header simplificado com logo "Firma Solar"; NavUser recebe dados de `useAuth()`
- **Files modified:** `frontend/admin/src/components/app-sidebar.tsx`
- **Commit:** c98026c

## Known Stubs

| Stub | File | Reason |
|------|------|--------|
| "Em construcao — Phase 5" | src/pages/UsinasPage.tsx:5 | Intencional — conteudo sera implementado na Phase 5 |
| "Em construcao — Phase 5" | src/pages/GarantiasPage.tsx:5 | Intencional — conteudo sera implementado na Phase 5 |
| "Em construcao — Phase 6" | src/pages/DashboardPage.tsx:5 | Intencional — conteudo sera implementado na Phase 6 |
| "Em construcao — Phase 6" | src/pages/AlertasPage.tsx:5 | Intencional — conteudo sera implementado na Phase 6 |

Estes stubs sao placeholders explicitamente previstos pelo plano. Nao impedem o objetivo do plano (infraestrutura de auth e roteamento).

## Threat Surface Scan

Nenhuma superficie nova fora do threat model do plano. T-04-01..T-04-06 foram todos endereçados:
- T-04-02 (refresh token replay): refresh token salvo apos rotacao ✓
- T-04-03 (redirect tampering): redirect hardcoded para `/` nunca lê query params ✓
- T-04-04 (loop infinito no interceptor): flag `_retry` implementada ✓
- T-04-05 (token em console.log): nenhum `console.log` de tokens no codigo ✓

## Self-Check: PASSED

- `frontend/admin/src/lib/api.ts` — FOUND
- `frontend/admin/src/contexts/auth.tsx` — FOUND
- `frontend/admin/src/App.tsx` — FOUND (router + ProtectedLayout)
- `frontend/admin/src/main.tsx` — FOUND (AuthProvider)
- `frontend/admin/src/pages/` — FOUND (5 paginas)
- Commit 8178a5e — FOUND (Task 1)
- Commit c98026c — FOUND (Task 2)
- `npm run build` — PASSED sem erros
