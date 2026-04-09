# Phase 5: Usinas & Garantias - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Implementar as telas de gestão de usinas e garantias no painel React. O administrador pode listar, filtrar, visualizar detalhe, editar usinas e criar/editar garantias — tudo pelo browser.

Páginas incluídas:
- `/usinas` — listagem com tabela paginada, filtros, badges de garantia
- `/usinas/:id` — detalhe com inversores e último snapshot
- Modal de edição de usina (nome, capacidade)
- `/garantias` — listagem com status, dias_restantes, indicador de vencimento
- Modal de criação/edição de garantia por usina

**Fora do escopo:** histórico de snapshots em gráfico (V2-06), exclusão de usina (Django Admin).

</domain>

<decisions>
## Implementation Decisions

### D-01: Layout de listagem — Tabela shadcn (DataTable)

Usar componente `Table` do shadcn/ui para listagens de usinas e garantias. Instalar `npx shadcn@latest add table` + `badge` + `dialog` + `select`. Paginação no cliente consumindo a API paginada do backend (`?page=N`).

### D-02: Edição de usina — Modal (Dialog)

Formulário de edição em `Dialog` do shadcn. Campos: nome e capacidade_kwp. `PATCH /api/usinas/{id}/` com feedback de sucesso/erro. Listagem atualiza automaticamente após salvar (invalidar cache ou re-fetch).

### D-03: Formulário de garantia — Modal (Dialog)

Modal para criar/editar garantia. Campos: data_inicio (date picker ou input date), meses (number). `PUT /api/usinas/{id}/garantia/`. Preview de `data_fim` calculada em tempo real no formulário (date-fns ou cálculo simples). Listagem de garantias atualiza após salvar.

### D-04: Badge de status de garantia — cores

| Status | Cor | Classe Tailwind |
|--------|-----|-----------------|
| ativa | Verde | `bg-green-100 text-green-800` ou `variant="default"` verde |
| vencida | Vermelho | `bg-red-100 text-red-800` ou `variant="destructive"` |
| sem_garantia | Cinza | `bg-gray-100 text-gray-600` ou `variant="secondary"` |

Indicador especial: garantias com `dias_restantes < 30` exibem vermelho na listagem de garantias (FE-10).

### D-05: Detalhe de usina — layout com cards

Página `/usinas/:id` com:
- Card principal: nome, provedor, capacidade, status garantia, último snapshot (potência, energia)
- Tabela de inversores: número série, modelo, último pac_kw, estado

### D-06: Componentes shadcn a instalar

Planner decide a lista exata. Candidatos: `table`, `badge`, `dialog`, `select`, `pagination`, `toast` (feedback de sucesso/erro).

### D-07: Data fetching pattern

Usar hooks customizados (`useUsinas`, `useUsina`, `useGarantias`) que encapsulam chamadas axios + estado (loading, error, data). Sem React Query nesta fase — fetch simples com `useEffect` + `useState`. Re-fetch manual após mutations.

### Claude's Discretion

- Componentes shadcn exatos a instalar
- Se usar `date-fns` para cálculo de data_fim ou cálculo manual
- Estrutura de pastas para hooks de data fetching
- Layout responsivo (mobile) — planner decide nível de suporte
- Se usar skeleton loading ou spinner durante fetch

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Frontend existente (ler para entender patterns)
- `frontend/admin/src/lib/api.ts` — instância axios com interceptors
- `frontend/admin/src/contexts/auth.tsx` — AuthContext pattern
- `frontend/admin/src/App.tsx` — router e ProtectedLayout
- `frontend/admin/src/pages/UsinasPage.tsx` — placeholder a substituir
- `frontend/admin/src/pages/GarantiasPage.tsx` — placeholder a substituir
- `frontend/admin/src/components/ui/` — componentes shadcn disponíveis

### Backend API (contratos que o frontend consome)
- `backend_monitoramento/api/urls.py` — rotas disponíveis
- `backend_monitoramento/api/serializers/usinas.py` — formato de resposta de usinas
- `backend_monitoramento/api/serializers/garantias.py` — formato de resposta de garantias
- `backend_monitoramento/api/views/usinas.py` — ViewSet com filtros e actions
- `backend_monitoramento/api/views/garantias.py` — GarantiaListView

### Decisões anteriores
- `.planning/phases/04-frontend-foundation/04-CONTEXT.md` — axios, auth, routing patterns
- `.planning/phases/02-rest-endpoints/02-CONTEXT.md` — contratos de API (D-04 status_garantia, D-05 filtros)

### Roadmap
- `.planning/ROADMAP.md` — Phase 5 scope e success criteria
- `.planning/REQUIREMENTS.md` — FE-06..11

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `api.ts` — axios instance com auth interceptors (usar para todas as chamadas)
- Componentes shadcn UI: Button, Card, Input, Label, Dialog (precisa instalar), Table (precisa instalar), Badge (precisa instalar)
- `useAuth()` hook para dados do usuário
- Router com rotas `/usinas` e `/garantias` já configuradas

### Established Patterns
- Pages em `src/pages/` como componentes exportados
- shadcn/ui com Tailwind CSS 4
- Axios para data fetching via `api.get()`, `api.patch()`, `api.put()`

### Integration Points
- `UsinasPage.tsx` — substituir placeholder
- `GarantiasPage.tsx` — substituir placeholder
- `App.tsx` — adicionar rota `/usinas/:id` para detalhe

</code_context>

<specifics>
## Specific Ideas

- A API retorna `status_garantia` com valores exatos: "ativa", "vencida", "sem_garantia" (D-04 da Phase 2)
- Filtros da listagem de usinas: `?provedor=solis`, `?ativo=true`, `?status_garantia=ativa`
- Filtros de garantias: `?filtro=ativas`, `?filtro=vencendo`, `?filtro=vencidas`
- PATCH usina aceita apenas `nome` e `capacidade_kwp`
- PUT garantia: `{ data_inicio, meses, observacoes }` em `/api/usinas/{id}/garantia/`
- Detalhe de usina retorna `inversores[]` e `ultimo_snapshot` aninhados

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-usinas-garantias*
*Context gathered: 2026-04-09*
