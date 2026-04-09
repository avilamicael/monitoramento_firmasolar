---
phase: 05-usinas-garantias
plan: "02"
subsystem: frontend
tags: [react, shadcn, typescript, usinas, pagination, dialog]
dependency_graph:
  requires:
    - frontend/admin/src/types/usinas.ts
    - frontend/admin/src/hooks/use-usinas.ts
    - frontend/admin/src/components/usinas/StatusGarantiaBadge.tsx
  provides:
    - frontend/admin/src/pages/UsinasPage.tsx
    - frontend/admin/src/pages/UsinaDetalhePage.tsx
    - frontend/admin/src/components/usinas/UsinasTable.tsx
    - frontend/admin/src/components/usinas/UsinaEditDialog.tsx
  affects:
    - frontend/admin/src/App.tsx (rota usinas/:id ja existia do Plan 01)
tech_stack:
  added: []
  patterns:
    - PATCH exclusivo para mutacoes de usina (PUT retorna 405)
    - Optional chaining em dados nullable (ultimo_snapshot?)
    - Resetar page para 1 ao mudar qualquer filtro
    - void refetch() para re-fetch apos mutacao sem capturar Promise
key_files:
  created:
    - frontend/admin/src/components/usinas/UsinasTable.tsx
    - frontend/admin/src/components/usinas/UsinaEditDialog.tsx
  modified:
    - frontend/admin/src/pages/UsinasPage.tsx
    - frontend/admin/src/pages/UsinaDetalhePage.tsx
decisions:
  - "Paginacao usa aria-disabled + pointer-events-none em vez de atributo disabled nativo — PaginationLink nao expoe prop disabled diretamente"
  - "Select value='' para opcao 'Todos' permite reset limpo dos filtros sem undefined state"
  - "UsinaDetalhePage usa optional chaining (ultimo_snapshot?) mesmo dentro do bloco !== null — seguranca extra contra TypeScript strict"
metrics:
  duration: "~25 minutos"
  completed: "2026-04-09"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 2
---

# Phase 5 Plan 02: Paginas de Usinas Summary

**One-liner:** UsinasPage com tabela paginada e filtros por provedor/status, UsinaDetalhePage com cards de snapshot e inversores, e UsinaEditDialog com PATCH e feedback toast.

## Tasks Executadas

| Task | Nome | Commit | Arquivos Principais |
|------|------|--------|---------------------|
| 1 | UsinasTable e UsinasPage com filtros, paginacao e badge (FE-06) | 12e91f7 | UsinasTable.tsx, UsinasPage.tsx |
| 2 | UsinaEditDialog e UsinaDetalhePage (FE-07, FE-08) | 1fc751c | UsinaEditDialog.tsx, UsinaDetalhePage.tsx |

## O que foi feito

### Task 1 — UsinasTable e UsinasPage (FE-06)

**UsinasTable.tsx:** Tabela com 5 colunas usando componentes shadcn/ui:
- Nome: `<Link to="/usinas/{id}">` com `text-primary hover:underline`
- Provedor: texto simples
- Capacidade: `{kwp} kWp`
- Status Garantia: `<StatusGarantiaBadge />` com badge colorido
- Acoes: botao "Editar" (`variant="outline" size="sm"`) que chama `onEdit(usina)`
- Estado vazio: mensagem "Nenhuma usina encontrada" com `colSpan={5}`

**UsinasPage.tsx:** Pagina com filtros, tabela e paginacao:
- Select provedor: opcoes Todos / Solis / Growatt (values: '' / 'solis' / 'growatt')
- Select status_garantia: opcoes Todos / Ativa / Vencida / Sem Garantia
- Reset automatico de `page` para 1 ao mudar qualquer filtro
- Loading: spinner `Loader2Icon animate-spin`
- Error: mensagem em `text-destructive`
- Paginacao: PaginationPrevious/Next desabilitados via `pointer-events-none opacity-50` quando `data.previous/next === null`
- Texto "Pagina X de Y" calculado como `Math.ceil(count / 20)`
- Integra `<UsinaEditDialog>` com re-fetch automatico apos salvar

### Task 2 — UsinaEditDialog e UsinaDetalhePage (FE-07, FE-08)

**UsinaEditDialog.tsx:** Modal de edicao via PATCH:
- Props: `{ usina, open, onClose, onSuccess }`
- `useEffect` popula nome e capacidade quando `usina` muda
- Validacao local: nome nao vazio, capacidade > 0 como float valido
- `api.patch('/api/usinas/{id}/', { nome, capacidade_kwp })` — NUNCA api.put (405)
- Feedback: `toast.success` em sucesso, `toast.error` em falha (sonner)
- `onSuccess()` chamado apos PATCH bem-sucedido para disparar re-fetch na pagina pai
- `saving` state desabilita inputs e botoes durante requisicao

**UsinaDetalhePage.tsx:** Pagina de detalhe completa:
- `useParams<{ id: string }>()` para extrair id da URL
- `useUsina(id!)` para buscar UsinaDetalhe do backend
- Estados loading/error/not-found tratados explicitamente
- Link "Voltar para Usinas" com `ArrowLeftIcon` apontando para `/usinas`
- Card principal: nome (CardTitle), grid com provedor, capacidade, StatusGarantiaBadge, endereco, fuso_horario
- Card snapshot: exibe "Nenhum snapshot coletado ainda" se `ultimo_snapshot === null`; caso contrario grid com potencia, energia_hoje/mes/total, inversores_online/total, alertas, coletado_em formatado com `toLocaleString('pt-BR')`
- Optional chaining em todos os acessos a `ultimo_snapshot?.*`
- Tabela de inversores: numero_serie, modelo, id_inversor_provedor

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Completeness] Merge do main branch antes de implementar**

- **Found during:** Inicio da execucao
- **Issue:** Worktree `worktree-agent-aaa6f8b5` estava baseado em commit `4d3aec4` (Phase 02), sem nenhum arquivo do frontend/admin. O Plan 01 ja tinha criado tipos, hooks e componentes no branch main.
- **Fix:** `git merge main` (fast-forward) para trazer todos os arquivos do Plan 01 e 03 antes de implementar o Plan 02.
- **Impacto:** Zero — fast-forward limpo sem conflitos.

## Known Stubs

Nenhum stub. Todos os componentes consomem dados reais via hooks `useUsinas` e `useUsina`.

## Threat Surface Scan

Mitigacoes do threat model aplicadas conforme especificado:

| Threat | Status | Implementacao |
|--------|--------|---------------|
| T-05-04 Tampering (UsinaEditDialog) | Mitigado | Validacao local nome nao vazio + capacidade positiva; PATCH exclusivo (PUT bloqueia com 405 no backend) |
| T-05-05 Info Disclosure (UsinaDetalhePage) | Mitigado | Hook usa catch generico ("Erro ao carregar usina") — stack trace e mensagem do backend nunca expostos |
| T-05-06 DoS filtros (UsinasPage) | Accepted | Re-fetch a cada mudanca de filtro — risco aceito conforme threat model |

## Self-Check: PASSED

Arquivos verificados no disco:
- `frontend/admin/src/components/usinas/UsinasTable.tsx` — FOUND
- `frontend/admin/src/components/usinas/UsinaEditDialog.tsx` — FOUND
- `frontend/admin/src/pages/UsinasPage.tsx` — FOUND (substituido)
- `frontend/admin/src/pages/UsinaDetalhePage.tsx` — FOUND (substituido)

Commits verificados:
- `12e91f7` — feat(05-02): UsinasTable e UsinasPage
- `1fc751c` — feat(05-02): UsinaEditDialog e UsinaDetalhePage

Build: `npm run build` passou sem erros TypeScript (somente aviso de chunk size — nao e erro).
