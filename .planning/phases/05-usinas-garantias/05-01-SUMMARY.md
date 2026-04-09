---
phase: 05-usinas-garantias
plan: "01"
subsystem: frontend
tags: [react, shadcn, typescript, hooks, routing]
dependency_graph:
  requires: []
  provides:
    - frontend/admin/src/types/usinas.ts
    - frontend/admin/src/types/garantias.ts
    - frontend/admin/src/hooks/use-usinas.ts
    - frontend/admin/src/hooks/use-garantias.ts
    - frontend/admin/src/components/usinas/StatusGarantiaBadge.tsx
  affects:
    - frontend/admin/src/App.tsx
tech_stack:
  added:
    - shadcn/ui table
    - shadcn/ui badge
    - shadcn/ui dialog
    - shadcn/ui select
    - shadcn/ui pagination
    - shadcn/ui sonner
  patterns:
    - Custom hooks com useCallback + JSON.stringify(params) para evitar loop infinito
    - Catch generico sem expor detalhes do backend (T-05-01)
    - Rota mais especifica (usinas/:id) antes da rota pai (usinas) no router
key_files:
  created:
    - frontend/admin/src/types/usinas.ts
    - frontend/admin/src/types/garantias.ts
    - frontend/admin/src/hooks/use-usinas.ts
    - frontend/admin/src/hooks/use-garantias.ts
    - frontend/admin/src/components/usinas/StatusGarantiaBadge.tsx
    - frontend/admin/src/pages/UsinaDetalhePage.tsx
    - frontend/admin/src/components/ui/table.tsx
    - frontend/admin/src/components/ui/badge.tsx
    - frontend/admin/src/components/ui/dialog.tsx
    - frontend/admin/src/components/ui/select.tsx
    - frontend/admin/src/components/ui/pagination.tsx
    - frontend/admin/src/components/ui/sonner.tsx
  modified:
    - frontend/admin/src/App.tsx
decisions:
  - "Usar JSON.stringify(params) como dependencia do useCallback em vez de params diretamente — evita loop infinito quando objeto literal e recriado a cada render"
  - "Rota usinas/:id inserida ANTES de usinas no array children para evitar conflito de matching no react-router"
  - "StatusGarantiaBadge usa constante CONFIG (nao inline) para mapeamento status -> label/className — mais facil de estender"
  - "Toaster renderizado no App() raiz para habilitar toast.success/error em qualquer componente filho"
metrics:
  duration: "~20 minutos"
  completed: "2026-04-09"
  tasks_completed: 3
  tasks_total: 3
  files_created: 13
  files_modified: 1
---

# Phase 5 Plan 01: Fundacao UI Usinas/Garantias Summary

**One-liner:** 6 componentes shadcn instalados + tipos TypeScript, hooks de data fetching e badge de status prontos para consumo dos Plans 02 e 03.

## Tasks Executadas

| Task | Nome | Commit | Arquivos Principais |
|------|------|--------|---------------------|
| 1 | Instalar shadcn e criar tipos TS | 48bf9c9 | types/usinas.ts, types/garantias.ts, 6x components/ui/ |
| 2 | Hooks de data fetching e StatusGarantiaBadge | ba88f8e | use-usinas.ts, use-garantias.ts, StatusGarantiaBadge.tsx |
| 3 | Rota /usinas/:id e Toaster no App | 6a789a9 | App.tsx, UsinaDetalhePage.tsx |

## O que foi feito

### Task 1 — Componentes shadcn e tipos TypeScript

Instalados via `npx shadcn@latest add table badge dialog select pagination sonner`:
- `table.tsx`, `badge.tsx`, `dialog.tsx`, `select.tsx`, `pagination.tsx`, `sonner.tsx`

Tipos criados refletindo exatamente os serializers DRF do backend:

**usinas.ts:** `StatusGarantia` (tipo literal union), `UsinaResumo`, `InversorResumo`, `SnapshotUsina`, `UsinaDetalhe`, `PaginatedUsinas`, `UsinaPatch`

**garantias.ts:** `GarantiaUsina`, `GarantiaInput`, `PaginatedGarantias`

### Task 2 — Hooks de data fetching e StatusGarantiaBadge

**useUsinas(params):** Aceita filtros `provedor`, `ativo`, `status_garantia`, `page`. Retorna `{ data: PaginatedUsinas | null, loading, error, refetch }`.

**useUsina(id):** Busca detalhe de usina por ID. Retorna `{ data: UsinaDetalhe | null, loading, error, refetch }`.

**useGarantias(params):** Aceita filtros `filtro` ('ativas'|'vencendo'|'vencidas') e `page`. Retorna `{ data: PaginatedGarantias | null, loading, error, refetch }`.

**StatusGarantiaBadge:** Componente com 3 variantes visuais via constante CONFIG:
- `ativa` → badge verde (`bg-green-100 text-green-800`)
- `vencida` → badge vermelho (`bg-red-100 text-red-800`)
- `sem_garantia` → badge cinza (`bg-gray-100 text-gray-600`)

### Task 3 — Rota /usinas/:id e Toaster

`UsinaDetalhePage.tsx` criado como placeholder (Plan 02 substituira o conteudo completo).

`App.tsx` atualizado:
- Import de `UsinaDetalhePage` e `Toaster`
- Rota `usinas/:id` inserida antes de `usinas` no array de filhos do router
- `<Toaster />` renderizado ao lado do `RouterProvider` para feedback global de mutacoes

## Deviations from Plan

None — plano executado exatamente como escrito.

## Known Stubs

- `frontend/admin/src/pages/UsinaDetalhePage.tsx` — placeholder intencional. Plan 02 substituira com implementacao completa da pagina de detalhe.

## Threat Surface Scan

Nenhuma nova superficie de segurança introduzida alem do documentado no threat model do plano:
- T-05-01 (mitigado): hooks usam catch generico sem expor detalhes do backend
- T-05-02 (accepted): tipos TypeScript sao compile-time only
- T-05-03 (accepted): rota /usinas/:id herda protecao do ProtectedLayout existente

## Self-Check: PASSED

Todos os 12 arquivos criados confirmados no disco. 3 commits verificados (48bf9c9, ba88f8e, 6a789a9). Rota usinas/:id e Toaster presentes no App.tsx. 3 variantes visuais do StatusGarantiaBadge confirmadas.
