---
phase: 06-dashboard-anal-tico-alertas
plan: 02
subsystem: frontend-dashboard-alertas
tags: [react-leaflet, leaflet, shadcn, alertas, mapa, patch, toast, typescript]
dependency_graph:
  requires:
    - frontend/admin/src/hooks/use-analytics.ts
    - frontend/admin/src/hooks/use-alertas.ts
    - frontend/admin/src/types/analytics.ts
    - frontend/admin/src/types/alertas.ts
    - frontend/admin/src/pages/DashboardPage.tsx
    - frontend/admin/src/pages/AlertasPage.tsx
    - backend_monitoramento/api/views/alertas.py
    - backend_monitoramento/api/serializers/alertas.py
  provides:
    - frontend/admin/src/components/dashboard/MapaUsinas.tsx
    - frontend/admin/src/components/alertas/AlertasTable.tsx
    - frontend/admin/src/components/alertas/AlertaEstadoForm.tsx
    - frontend/admin/src/pages/AlertaDetalhePage.tsx
  affects:
    - frontend/admin/src/pages/DashboardPage.tsx (mapa adicionado)
    - frontend/admin/src/pages/AlertasPage.tsx (substituido por implementacao real)
    - frontend/admin/src/App.tsx (rota alertas/:id adicionada)
tech_stack:
  added: []
  patterns:
    - react-leaflet MapContainer+TileLayer+Marker+Popup com L.divIcon customizado
    - Filtro estado/nivel via Select com value="all" para ausencia de filtro (Radix requirement)
    - PATCH com api.patch + toast.success/error do sonner
    - useEffect com alerta.id como dep para sincronizar estado do formulario apos refetch
key_files:
  created:
    - frontend/admin/src/components/dashboard/MapaUsinas.tsx
    - frontend/admin/src/components/alertas/AlertasTable.tsx
    - frontend/admin/src/components/alertas/AlertaEstadoForm.tsx
    - frontend/admin/src/pages/AlertaDetalhePage.tsx
  modified:
    - frontend/admin/src/pages/DashboardPage.tsx
    - frontend/admin/src/pages/AlertasPage.tsx
    - frontend/admin/src/App.tsx
decisions:
  - "L.divIcon customizado usado em vez do icone padrao do Leaflet (bug conhecido com Vite — icone padrao quebra o bundler)"
  - "SelectItem value='all' (nao string vazia) para opcao Todos/Todas — Radix Select crasha com value vazio"
  - "Rota alertas/:id posicionada antes de alertas no router — react-router requer rotas mais especificas primeiro"
  - "useEffect dep em alerta.id (nao alerta inteiro) para evitar loop infinito ao sincronizar state do formulario"
metrics:
  duration: "~25min"
  completed: "2026-04-09"
  tasks_completed: 3
  files_created: 4
  files_modified: 3
---

# Phase 06 Plan 02: Mapa Interativo e Gestao de Alertas — Summary

**One-liner:** Mapa react-leaflet com marcadores coloridos por status integrado ao ranking do dashboard, e paginas de alertas com tabela filtrada (estado/nivel), badge com_garantia, e formulario PATCH com toast de feedback.

---

## What Was Built

### Task 1: MapaUsinas e DashboardPage (commit `09707f6`)

**Componente criado:**
- `components/dashboard/MapaUsinas.tsx`:
  - Importa `leaflet/dist/leaflet.css` no topo (critico para tiles funcionarem com Vite)
  - `MapContainer` centrado em `[-15.0, -47.0]` (Brasil), zoom 5
  - TileLayer do OpenStreetMap (sem API key)
  - `L.divIcon` customizado — evita bug de icone padrao do Leaflet com Vite
  - `criarIcone(cor)` retorna DivIcon com circulo colorido 14x14px
  - `getCorMarcador(usina)`: verde (normal), vermelho (aviso/offline/construcao), cinza (inativo/sem_dados)
  - Filtra usinas sem `latitude !== null && longitude !== null` antes de renderizar marcadores
  - Popup com nome, provedor e status da usina
  - Estado vazio: mensagem "Nenhuma usina com coordenadas disponíveis"

**DashboardPage atualizado:**
- Adicionado `useAnalyticsMapa()` aos hooks existentes
- `usinasFiltradas` calculado por `selectedProvedor` (filtro ranking -> mapa)
- Card "Mapa de Usinas" na Linha 2 (largura total) com Badge de filtro ativo e botao X para limpar
- Error state com botao retry para o hook do mapa
- Placeholder do Plan 01 removido

### Task 2: AlertasPage, AlertaDetalhePage, componentes e rota (commit `0387001`)

**AlertasTable.tsx:**
- Tabela shadcn com colunas: Usina (link para /alertas/:id), Mensagem, Nivel, Estado, Com Garantia, Data
- Badges de nivel: `critico` -> destructive, `importante` -> orange-100/orange-800, `aviso` -> secondary, `info` -> outline
- Badge com_garantia: "Sim" (verde) ou "Nao" (secondary cinza)
- Estado formatado: `ativo` -> "Ativo", `em_atendimento` -> "Em atendimento", `resolvido` -> "Resolvido"
- Data formatada: `toLocaleDateString('pt-BR')`
- Estado vazio: "Nenhum alerta encontrado"

**AlertaEstadoForm.tsx:**
- Select shadcn com opcoes fixas de estado (ativo/em_atendimento/resolvido)
- Textarea nativa com classes Tailwind (min-h-[100px], rounded-md, border-input)
- `api.patch(/api/alertas/{id}/, { estado, anotacoes })` com isSubmitting desabilita botao
- `toast.success` em sucesso, `toast.error` em falha (sonner)
- `useEffect([alerta.id])` sincroniza estado/anotacoes quando alerta prop muda apos refetch

**AlertasPage.tsx (substituido):**
- Filtros lado a lado: Select de estado e nivel com `value="all"` para "Todos" (Radix requirement)
- Filtros nao passam param quando "all" (valor `undefined` para o hook)
- Resetar `page=1` ao trocar filtro
- Paginacao shadcn com calculo `Math.ceil(count / PAGE_SIZE)`
- Loading state inline, error state com retry

**AlertaDetalhePage.tsx (criado):**
- `useParams<{ id: string }>()` para obter UUID
- Loading state com Skeleton shadcn
- Error state com botao retry
- Null state "Alerta nao encontrado"
- Card de informacoes: usina, estado, equipamento, id_alerta_provedor, inicio, fim, sugestao
- Card "Atualizar Alerta" com `<AlertaEstadoForm alerta={data} onSuccess={refetch} />`
- Botao "Voltar" com `useNavigate` -> `/alertas`

**App.tsx:**
- Import de `AlertaDetalhePage` adicionado
- Rota `alertas/:id` posicionada ANTES de `alertas` nos children do ProtectedLayout

### Task 3: Checkpoint de verificacao visual (auto-aprovado — modo --auto)

**Itens de verificacao para revisao humana:**
1. Dashboard (`/`): grafico pizza exibe potencia por fabricante, ranking top 5, clicar fabricante filtra mapa, marcadores coloridos (verde/vermelho/cinza), popup com nome da usina ao clicar
2. Alertas (`/alertas`): tabela com todas as colunas, filtros estado/nivel funcionam, badge com_garantia
3. Detalhe (`/alertas/:id`): informacoes completas, formulario PATCH, toast de sucesso, botao Voltar

---

## Deviations from Plan

### Auto-fixed Issues

Nenhum. Plano executado exatamente como especificado.

### Notas de implementacao

**1. value="all" nos SelectItem de filtros**
- Usado `value="all"` (nao `value=""`) para opcao "Todos" nos filtros de estado e nivel
- Radix Select crasha silenciosamente com `value=""` (pitfall documentada na instrucao do executor)
- Logica: `estado === 'all' ? undefined : estado` para nao passar param ao hook

---

## Verification Results

| Check | Result |
|-------|--------|
| `npx tsc --noEmit` | Apenas warning pre-existente de baseUrl deprecated — sem erros novos |
| `npm run build` | Sucesso — `built in 1.06s` |
| `leaflet/dist/leaflet.css` importado no topo de MapaUsinas.tsx | Confirmado (linha 1) |
| `L.divIcon` customizado (nao icone padrao) | Confirmado |
| Filtro por selectedProvedor em DashboardPage | Confirmado (usinasFiltradas) |
| Badge com_garantia Sim/Nao em AlertasTable | Confirmado |
| `api.patch` em AlertaEstadoForm | Confirmado (linha 42) |
| `toast.success` / `toast.error` do sonner | Confirmado |
| Rota `alertas/:id` antes de `alertas` no App.tsx | Confirmado (linha 84) |
| AlertaDetalhePage usa `useParams` + `useAlerta(id)` | Confirmado |

---

## Known Stubs

Nenhum. Todos os componentes consomem dados reais dos hooks que chamam a API.

---

## Threat Flags

Nenhuma superficie de seguranca nova alem do ja modelado no threat model do plano.
- T-06-05: Select com opcoes fixas implementado (mitigacao confirmada)
- T-06-06: ProtectedLayout ja envolve todas as rotas (mitigacao existente)
- T-06-10: React escapa HTML automaticamente no JSX (mitigacao confirmada)

---

## Self-Check

### Files exist:
- `/home/micael/firmasolar/frontend/admin/src/components/dashboard/MapaUsinas.tsx` — FOUND
- `/home/micael/firmasolar/frontend/admin/src/components/alertas/AlertasTable.tsx` — FOUND
- `/home/micael/firmasolar/frontend/admin/src/components/alertas/AlertaEstadoForm.tsx` — FOUND
- `/home/micael/firmasolar/frontend/admin/src/pages/AlertaDetalhePage.tsx` — FOUND
- `/home/micael/firmasolar/frontend/admin/src/pages/AlertasPage.tsx` — FOUND (substituido)
- `/home/micael/firmasolar/frontend/admin/src/pages/DashboardPage.tsx` — FOUND (atualizado)
- `/home/micael/firmasolar/frontend/admin/src/App.tsx` — FOUND (atualizado)

### Commits exist:
- `09707f6` — feat(06-02): implementar MapaUsinas com react-leaflet e integrar no DashboardPage
- `0387001` — feat(06-02): implementar AlertasPage, AlertaDetalhePage e rota alertas/:id

## Self-Check: PASSED
