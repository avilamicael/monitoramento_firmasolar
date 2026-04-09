---
phase: 06-dashboard-anal-tico-alertas
plan: 01
subsystem: frontend-dashboard
tags: [recharts, react-leaflet, polling, analytics, hooks, typescript]
dependency_graph:
  requires:
    - backend_monitoramento/api/views/analytics.py
    - backend_monitoramento/api/views/alertas.py
    - frontend/admin/src/lib/api.ts
  provides:
    - frontend/admin/src/types/analytics.ts
    - frontend/admin/src/types/alertas.ts
    - frontend/admin/src/hooks/use-analytics.ts
    - frontend/admin/src/hooks/use-alertas.ts
    - frontend/admin/src/components/dashboard/PotenciaPieChart.tsx
    - frontend/admin/src/components/dashboard/RankingTable.tsx
    - frontend/admin/src/pages/DashboardPage.tsx
  affects:
    - frontend/admin/src/pages/DashboardPage.tsx (substituido)
tech_stack:
  added:
    - recharts@3.8.1
    - react-leaflet@5.0.0
    - leaflet@1.9.4
    - "@types/leaflet@1.9.21"
  patterns:
    - useState + useCallback + useEffect hook pattern (existente, estendido com setInterval polling)
    - Recharts PieChart com Cell + ResponsiveContainer
    - shadcn Table para ranking clicavel
key_files:
  created:
    - frontend/admin/src/types/analytics.ts
    - frontend/admin/src/types/alertas.ts
    - frontend/admin/src/hooks/use-analytics.ts
    - frontend/admin/src/hooks/use-alertas.ts
    - frontend/admin/src/components/dashboard/PotenciaPieChart.tsx
    - frontend/admin/src/components/dashboard/RankingTable.tsx
  modified:
    - frontend/admin/src/pages/DashboardPage.tsx
    - frontend/admin/package.json
decisions:
  - "Tooltip formatter do Recharts usa typeof value === 'number' para ser compativel com ValueType | undefined do tipo TypeScript estrito"
  - "Loading state unificado (potenciaLoading || rankingLoading) para evitar layout shift parcial"
  - "Error state por card com botao retry — falha de um endpoint nao bloqueia o outro"
metrics:
  duration: "~20min"
  completed: "2026-04-09"
  tasks_completed: 2
  files_created: 6
  files_modified: 2
---

# Phase 06 Plan 01: Tipos, Hooks com Polling e Dashboard Base — Summary

**One-liner:** Tipos TypeScript completos para analytics e alertas, hooks com polling setInterval de 10min, e DashboardPage com grafico de pizza Recharts e tabela de ranking shadcn clicavel com dados reais da API.

---

## What Was Built

### Task 1: Pacotes, Tipos e Hooks (commit `989e3ca`)

**Pacotes instalados:**
- `recharts@3.8.1` — grafico de pizza PieChart
- `react-leaflet@5.0.0` + `leaflet@1.9.4` — mapa interativo (Plan 02)
- `@types/leaflet@1.9.21` — tipos TypeScript para leaflet

**Tipos criados:**
- `types/analytics.ts`: `ProvedorPotencia`, `PotenciaResponse`, `ProvedorRanking`, `RankingResponse`, `MapaUsina`
- `types/alertas.ts`: `EstadoAlerta`, `NivelAlerta`, `AlertaResumo`, `AlertaDetalhe`, `AlertaPatch`, `PaginatedAlertas`

**Hooks criados:**
- `hooks/use-analytics.ts`: `useAnalyticsPotencia`, `useAnalyticsRanking`, `useAnalyticsMapa` — todos com `setInterval(600_000ms)` e `clearInterval` no cleanup
- `hooks/use-alertas.ts`: `useAlertas(params)` com JSON.stringify para deps dinamicas, `useAlerta(id)` — sem polling (alertas nao precisam de auto-refresh)

### Task 2: Componentes e DashboardPage (commit `5e98015`)

**Componentes criados:**
- `components/dashboard/PotenciaPieChart.tsx`: Recharts ResponsiveContainer + PieChart + Pie + Cell + Tooltip + Legend; filtra `media_kw null/zero`; paleta `['#8884d8', '#82ca9d', '#ffc658', '#ff7300', '#0088fe']`
- `components/dashboard/RankingTable.tsx`: shadcn Table com rows clicaveis; toggle de `selectedProvedor` (clique no mesmo fabricante deseleciona)

**DashboardPage substituido:**
- Layout `grid grid-cols-1 md:grid-cols-2 gap-6`
- Usa `useAnalyticsPotencia()` e `useAnalyticsRanking()`
- Exibe `media_geral_kw` no header do card de potencia
- Loading: `Loader2Icon` spinner centralizado enquanto qualquer hook carrega
- Error: mensagem por card com botao "Tentar novamente" (retry inline)
- Estado `selectedProvedor: string | null` declarado e pronto para o mapa (Plan 02)
- Placeholder `{/* MapaUsinas sera adicionado no Plan 02 */}`

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Formatter do Tooltip Recharts com tipo incompativel**
- **Found during:** Task 2, `npm run build`
- **Issue:** `formatter={(value: number) => ...}` falha no build porque o tipo de `value` em Recharts e `ValueType | undefined`, nao `number`
- **Fix:** Usar `typeof value === 'number'` guard antes de chamar `.toFixed(2)`
- **Files modified:** `frontend/admin/src/components/dashboard/PotenciaPieChart.tsx`
- **Commit:** `5e98015` (incluido no mesmo commit da task)

---

## Verification Results

| Check | Result |
|-------|--------|
| `npx tsc --noEmit` | Passa (apenas warning pre-existente de baseUrl deprecated no tsconfig.json — nao e erro nosso) |
| `npm run build` | Sucesso — `built in 1.50s` |
| recharts em package.json | `^3.8.1` |
| react-leaflet em package.json | `^5.0.0` |
| leaflet em package.json | `^1.9.4` |
| @types/leaflet em devDependencies | `^1.9.21` |
| setInterval 600_000ms nos hooks | 3 ocorrencias em use-analytics.ts |
| clearInterval no cleanup | 3 cleanups em use-analytics.ts |
| useAnalyticsPotencia e useAnalyticsRanking em DashboardPage | Confirmado |
| selectedProvedor state no DashboardPage | Confirmado |

---

## Known Stubs

Nenhum stub — os componentes recebem dados reais dos hooks que chamam a API. O placeholder do mapa e um comentario JSX explicito, nao um stub de dado.

---

## Threat Flags

Nenhuma superficie de seguranca nova introduzida. Todos os endpoints consumidos ja existiam e estao protegidos por JWT via interceptor axios (T-06-01 no threat model do plano).

---

## Self-Check

### Files exist:

- `/home/micael/firmasolar/frontend/admin/src/types/analytics.ts` — FOUND
- `/home/micael/firmasolar/frontend/admin/src/types/alertas.ts` — FOUND
- `/home/micael/firmasolar/frontend/admin/src/hooks/use-analytics.ts` — FOUND
- `/home/micael/firmasolar/frontend/admin/src/hooks/use-alertas.ts` — FOUND
- `/home/micael/firmasolar/frontend/admin/src/components/dashboard/PotenciaPieChart.tsx` — FOUND
- `/home/micael/firmasolar/frontend/admin/src/components/dashboard/RankingTable.tsx` — FOUND
- `/home/micael/firmasolar/frontend/admin/src/pages/DashboardPage.tsx` — FOUND (substituido)

### Commits exist:

- `989e3ca` — FOUND (feat(06-01): instalar recharts/react-leaflet, criar tipos e hooks com polling)
- `5e98015` — FOUND (feat(06-01): implementar PotenciaPieChart, RankingTable e DashboardPage)

## Self-Check: PASSED
