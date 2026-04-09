---
phase: 05-usinas-garantias
plan: "03"
subsystem: frontend
tags: [react, shadcn, typescript, garantias, table, dialog, pagination]
dependency_graph:
  requires:
    - frontend/admin/src/types/garantias.ts
    - frontend/admin/src/hooks/use-garantias.ts
    - frontend/admin/src/lib/api.ts
  provides:
    - frontend/admin/src/components/garantias/GarantiasTable.tsx
    - frontend/admin/src/components/garantias/GarantiaFormDialog.tsx
    - frontend/admin/src/pages/GarantiasPage.tsx
  affects:
    - frontend/admin/src/pages/GarantiasPage.tsx
tech_stack:
  added: []
  patterns:
    - useMemo para calculo de dataFimPreview sem date-fns (calculo manual com Date nativo)
    - T00:00:00 suffix em strings de data para evitar timezone shift no Date constructor
    - Validacao local antes de submit para mitigar tampering (T-05-07)
    - Erro generico no catch sem expor detalhes do backend (T-05-09)
key_files:
  created:
    - frontend/admin/src/components/garantias/GarantiasTable.tsx
    - frontend/admin/src/components/garantias/GarantiaFormDialog.tsx
  modified:
    - frontend/admin/src/pages/GarantiasPage.tsx
decisions:
  - "useMemo com [dataInicio, meses] como dependencias para calcular dataFimPreview sem instalar date-fns"
  - "T00:00:00 suffix no Date constructor para evitar off-by-one de timezone ao parsear datas YYYY-MM-DD"
  - "Coluna Dias Restantes exibe o numero + Badge Vencendo inline quando proximo; coluna Status exibe badge de status geral separado"
  - "npm install executado no worktree (node_modules estava vazio) — Rule 3 (bloqueio de build)"
metrics:
  duration: "~25 minutos"
  completed: "2026-04-09"
  tasks_completed: 2
  tasks_total: 3
  files_created: 2
  files_modified: 1
---

# Phase 5 Plan 03: Pagina de Garantias — Tabela, Filtros e Modal Summary

**One-liner:** GarantiasTable com indicador vermelho para vencimento proximo, GarantiasPage com filtros e paginacao, e GarantiaFormDialog com preview de data_fim em tempo real via useMemo.

## Tasks Executadas

| Task | Nome | Commit | Arquivos Principais |
|------|------|--------|---------------------|
| 1 | GarantiasTable e GarantiasPage com filtros e indicador vermelho (FE-09, FE-10) | 00d2389 | GarantiasTable.tsx, GarantiasPage.tsx |
| 2 | GarantiaFormDialog com preview de data_fim em tempo real (FE-11) | 32ad2bd | GarantiaFormDialog.tsx |
| 3 | Verificacao visual (checkpoint) | — | Aguardando verificacao humana |

## O que foi feito

### Task 1 — GarantiasTable e GarantiasPage (FE-09, FE-10)

**GarantiasTable.tsx** (73 linhas):
- 7 colunas: Usina, Data Inicio, Data Fim, Meses, Dias Restantes, Status, Acoes
- Indicador de vencimento proximo (FE-10): quando `garantia.ativa && garantia.dias_restantes < 30`, aplica `className="bg-red-50"` na `TableRow` inteira e exibe Badge "Vencendo" inline na coluna Dias Restantes
- Coluna Status separada com `StatusBadge`: Ativa (verde), Vencendo (vermelho), Vencida (vermelho)
- Formatacao de datas com `new Date(dataStr + 'T00:00:00').toLocaleDateString('pt-BR')` para evitar timezone shift
- Estado vazio: `<TableCell colSpan={7}>Nenhuma garantia encontrada</TableCell>`

**GarantiasPage.tsx** (103 linhas):
- Estados: `filtro` (string, default ''), `page` (number, default 1), `editingGarantia` (GarantiaUsina | null)
- `useGarantias({ filtro, page })` com reset de page=1 ao mudar filtro
- Select de filtro com 4 opcoes: Todas / Ativas / Vencendo em 30 dias / Vencidas
- Loading: spinner animado centralizado
- Error: bloco com borda destrutiva e mensagem
- Paginacao com PaginationPrevious/Next, disabled baseado em `data.previous` / `data.next`
- Texto "Pagina N de M" calculado com `Math.ceil(count / PAGE_SIZE)`
- `<GarantiaFormDialog>` renderizado com `open={!!editingGarantia}`

### Task 2 — GarantiaFormDialog (FE-11)

**GarantiaFormDialog.tsx** (158 linhas):
- Props: `{ garantia: GarantiaUsina | null, open, onClose, onSuccess }`
- `useEffect` popula campos quando `garantia` prop muda (ou reseta para defaults)
- **Preview em tempo real:** `useMemo` com `[dataInicio, meses]` calcula `dataFimPreview` usando `new Date(dataInicio + 'T00:00:00')` + `setMonth(getMonth() + parseInt(meses))` — sem dependencia de date-fns
- Validacao local: data_inicio obrigatoria e meses >= 1 (mitigacao T-05-07)
- `api.put('/api/usinas/${garantia.usina_id}/garantia/', ...)` — endpoint correto, NAO /api/garantias/
- Feedback via `toast.success` / `toast.error` (sonner)
- Catch generico sem expor detalhes do backend (mitigacao T-05-09)
- `onSuccess()` chamado apos PUT bem-sucedido → listagem re-fetcha automaticamente

### Task 3 — Checkpoint (Pendente)

Task 3 e um `checkpoint:human-verify` que requer verificacao visual pelo usuario. Em modo auto, as Tasks 1 e 2 foram executadas completamente e commitadas. A verificacao visual deve ser feita manualmente:

**Passos de verificacao:**
1. Rodar `cd frontend/admin && npm run dev` e acessar `http://localhost:5173/garantias`
2. Verificar tabela com 7 colunas: Usina, Data Inicio, Data Fim, Meses, Dias Restantes, Status, Acoes
3. Usar filtro "Vencendo em 30 dias" — linhas devem ter fundo vermelho (bg-red-50)
4. Clicar "Editar" em uma garantia — modal deve abrir com campos preenchidos
5. Alterar data ou meses — preview de data_fim deve atualizar em tempo real
6. Salvar — toast de sucesso e tabela atualizada

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Bloqueio] Instalar dependencias no worktree**
- **Found during:** Task 1 (verificacao de build)
- **Issue:** O worktree tinha `node_modules/` vazio (apenas `.tmp/`), causando falha no `npm run build` com erros de tipos vite/client e node
- **Fix:** Executado `npm install` no diretorio do worktree (`frontend/admin`)
- **Commit:** Nao aplicavel (dependencias instaladas, nao commitadas)

## Known Stubs

Nenhum stub — os 3 componentes estao completamente implementados e conectados ao hook `useGarantias` e ao endpoint `/api/usinas/{id}/garantia/`.

## Threat Surface Scan

Nenhuma nova superficie de seguranca alem do documentado no threat model do plano:
- T-05-07 (mitigado): validacao local antes de submit — data_inicio obrigatoria, meses >= 1. Input type="date" garante YYYY-MM-DD.
- T-05-08 (accepted): sem log de auditoria de edicao — admin unico, aceitavel para v1.
- T-05-09 (mitigado): catch generico sem expor detalhes do backend. Dados admin-only.
- T-05-10 (accepted): preview JS pode diferir ligeiramente do calculo server-side para meses com dias variados. API e fonte de verdade.

## Self-Check: PASSED

- `frontend/admin/src/components/garantias/GarantiasTable.tsx` — criado e confirmado
- `frontend/admin/src/components/garantias/GarantiaFormDialog.tsx` — criado e confirmado
- `frontend/admin/src/pages/GarantiasPage.tsx` — substituido e confirmado
- Commit 00d2389 — verificado via `git log`
- Commit 32ad2bd — verificado via `git log`
- `npm run build` compilou sem erros TypeScript
