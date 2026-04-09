# Phase 6: Dashboard Analítico & Alertas - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Implementar o dashboard analítico (gráficos, ranking, mapa interativo com polling) e a gestão de alertas (listagem filtrada, detalhe, edição de estado/anotações). Última fase do milestone v1.

Páginas incluídas:
- `/` (Dashboard): gráfico de pizza Recharts (potência por fabricante), tabela ranking top 5, mapa react-leaflet com marcadores por usina
- `/alertas` — substituir placeholder com tabela filtrada (estado, nível, usina) + coluna com_garantia
- `/alertas/:id` — detalhe + formulário PATCH (estado, anotações)
- Polling automático a cada 10 min em todos os dados do dashboard

**Fora do escopo:** notificações tempo real (V2-01), séries temporais (V2-06), exportação relatórios (V2-03).

</domain>

<decisions>
## Implementation Decisions

### D-01: Gráfico de pizza — Recharts

Instalar `recharts`. Usar `PieChart` + `Pie` + `Cell` + `Tooltip` + `Legend` para mostrar potência média por fabricante/provedor. Dados do `GET /api/analytics/potencia/` campo `por_provedor[]`.

### D-02: Mapa interativo — react-leaflet

Instalar `react-leaflet` + `leaflet` + `@types/leaflet`. Usar `MapContainer` + `TileLayer` (OpenStreetMap) + `Marker` + `Popup`. Marcadores coloridos:
- Verde = usina ativa sem alertas
- Vermelho = usina com alertas ou problemas
- Cinza = usina inativa

Dados do `GET /api/analytics/mapa/`. Usinas sem lat/lng não renderizam marcador (API retorna null).

Interação ranking↔mapa: clicar em um fabricante no ranking filtra os marcadores para mostrar apenas usinas daquele provedor.

### D-03: Polling — setInterval 10 min

Usar `setInterval(refetch, 10 * 60 * 1000)` dentro dos hooks de dashboard. Sem React Query — manter consistência com Phase 5 (hooks simples com useState/useEffect). Cleanup no `useEffect` return.

### D-04: Alertas — tabela + detalhe + PATCH

Seguir mesmo pattern da Phase 5:
- Tabela com filtros (estado, nível, usina) via Select
- Coluna `com_garantia` com badge (Sim/Não)
- Link para `/alertas/:id` com detalhe completo
- Formulário de edição: Select para estado (ativo/em_atendimento/resolvido) + textarea para anotações
- `PATCH /api/alertas/{id}/` com `{ estado, anotacoes }`
- Toast de feedback via sonner

### D-05: Layout do dashboard — grid responsivo

Grid com:
- Linha 1: gráfico de pizza (50%) + ranking top 5 (50%)
- Linha 2: mapa (100% width)

Claude's Discretion no layout exato (gap, breakpoints mobile).

### D-06: Rota `/alertas/:id` — adicionar no router

Adicionar rota no App.tsx para detalhe de alerta, similar a `/usinas/:id`.

### D-07: Hooks de data fetching

Criar:
- `useAnalyticsPotencia()` — GET /api/analytics/potencia/ com polling
- `useAnalyticsRanking()` — GET /api/analytics/ranking-fabricantes/ com polling
- `useAnalyticsMapa()` — GET /api/analytics/mapa/ com polling
- `useAlertas()` — GET /api/alertas/ com filtros
- `useAlerta(id)` — GET /api/alertas/{id}/

### D-08: Cores do gráfico de pizza

Usar paleta distinta por provedor. Cores sugeridas: `['#8884d8', '#82ca9d', '#ffc658', '#ff7300', '#0088fe']`. Claude's Discretion nos valores exatos.

### Claude's Discretion

- Layout responsivo do dashboard (breakpoints, gap)
- Se agrupar hooks de analytics em um único arquivo ou separar
- Centro inicial do mapa (calcular média das coordenadas ou fixo no Brasil)
- Zoom inicial do mapa
- Se mostrar contagem de usinas por provedor no tooltip do gráfico

</decisions>

<canonical_refs>
## Canonical References

### Frontend existente
- `frontend/admin/src/App.tsx` — router (adicionar /alertas/:id)
- `frontend/admin/src/pages/DashboardPage.tsx` — placeholder a substituir
- `frontend/admin/src/pages/AlertasPage.tsx` — placeholder a substituir
- `frontend/admin/src/hooks/use-usinas.ts` — pattern de hook a seguir
- `frontend/admin/src/lib/api.ts` — axios instance
- `frontend/admin/src/components/ui/` — componentes shadcn disponíveis

### Backend API
- `backend_monitoramento/api/views/analytics.py` — 3 endpoints de analytics
- `backend_monitoramento/api/views/alertas.py` — AlertaViewSet (filtros, PATCH)
- `backend_monitoramento/api/serializers/alertas.py` — formato de resposta
- `backend_monitoramento/api/urls.py` — rotas

### Decisões anteriores
- `.planning/phases/05-usinas-garantias/05-CONTEXT.md` — patterns de tabela, modal, hooks
- `.planning/phases/04-frontend-foundation/04-CONTEXT.md` — axios, auth, router
- `.planning/phases/03-analytics-endpoints/03-CONTEXT.md` — endpoints de analytics

### Roadmap
- `.planning/ROADMAP.md` — Phase 6 scope e success criteria
- `.planning/REQUIREMENTS.md` — FE-12..18

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Hooks pattern (`useUsinas`, `useGarantias`) — copiar para analytics e alertas
- `StatusGarantiaBadge` — reutilizar na coluna com_garantia dos alertas
- Componentes shadcn: Table, Badge, Dialog, Select, Pagination, Sonner — todos instalados
- `UsinasTable` / `GarantiasTable` — pattern de tabela a seguir

### Integration Points
- `DashboardPage.tsx` — substituir placeholder
- `AlertasPage.tsx` — substituir placeholder
- `App.tsx` — adicionar rota `/alertas/:id`
- `package.json` — instalar recharts, react-leaflet, leaflet

</code_context>

<specifics>
## Specific Ideas

- Ranking: clicar em fabricante → state `selectedProvedor` → filtra marcadores do mapa
- Mapa: tile layer OpenStreetMap gratuito, sem API key
- Polling: 10 min (600_000 ms), alinhado com ciclo de coleta do backend
- Alertas: `com_garantia` é boolean na API, mostrar como badge "Sim"/"Não"
- PATCH alertas aceita apenas `estado` e `anotacoes`
- Leaflet CSS precisa ser importado (`leaflet/dist/leaflet.css`)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-dashboard-anal-tico-alertas*
*Context gathered: 2026-04-09*
