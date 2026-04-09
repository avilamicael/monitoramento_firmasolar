# Phase 6: Dashboard Analítico & Alertas — Research

**Researched:** 2026-04-09
**Domain:** React, Recharts, react-leaflet, hooks com polling, gestão de alertas
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01 Gráfico de pizza:** Usar `recharts` — `PieChart` + `Pie` + `Cell` + `Tooltip` + `Legend`. Dados de `GET /api/analytics/potencia/` campo `por_provedor[]`.
- **D-02 Mapa interativo:** Usar `react-leaflet` + `leaflet` + `@types/leaflet`. `MapContainer` + `TileLayer` (OpenStreetMap) + `Marker` + `Popup`. Cores: verde = ativa sem alertas, vermelho = com alertas/problemas, cinza = inativa. Dados de `GET /api/analytics/mapa/`. Usinas sem lat/lng não rendem marcador.
- **D-03 Polling:** `setInterval(refetch, 10 * 60 * 1000)` dentro dos hooks. Sem React Query — manter consistência com Phase 5.
- **D-04 Alertas:** Tabela com filtros (estado, nível, usina) via Select; coluna `com_garantia` com badge Sim/Não; link para `/alertas/:id`; formulário PATCH com estado + textarea anotações; toast via sonner.
- **D-05 Layout dashboard:** Grid: Linha 1 pizza (50%) + ranking (50%), Linha 2 mapa (100%). Breakpoints móveis a critério de Claude.
- **D-06 Rota `/alertas/:id`:** Adicionar no App.tsx, similar a `/usinas/:id`.
- **D-07 Hooks:** `useAnalyticsPotencia`, `useAnalyticsRanking`, `useAnalyticsMapa`, `useAlertas`, `useAlerta(id)`.
- **D-08 Cores:** Paleta sugerida `['#8884d8', '#82ca9d', '#ffc658', '#ff7300', '#0088fe']`. Valores exatos a critério de Claude.

### Claude's Discretion

- Layout responsivo do dashboard (breakpoints, gap)
- Se agrupar hooks de analytics em um único arquivo ou separar
- Centro inicial do mapa (calcular média das coordenadas ou fixo no Brasil)
- Zoom inicial do mapa
- Se mostrar contagem de usinas por provedor no tooltip do gráfico

### Deferred Ideas (OUT OF SCOPE)

- Notificações em tempo real (V2-01)
- Séries temporais (V2-06)
- Exportação de relatórios (V2-03)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FE-12 | Gráfico de pizza de potência média por fabricante (Recharts) | API responde `por_provedor[]` com `provedor`, `media_kw`, `usinas_ativas`. Recharts 3.8.1 instalável. |
| FE-13 | Tabela de ranking dos top 5 fabricantes por inversores ativos | API responde `ranking[]` com `provedor`, `inversores_ativos`. Tabela shadcn existente. |
| FE-14 | Mapa interativo de usinas com marcadores (react-leaflet) | API responde array plano com `id`, `nome`, `provedor`, `latitude`, `longitude`, `ativo`, `status`. react-leaflet 5.0.0 disponível. |
| FE-15 | Filtro no mapa por fabricante, integrado ao ranking | Estado `selectedProvedor` no componente pai filtra lista de marcadores antes de renderizar. |
| FE-16 | Dados do dashboard atualizados via polling a cada 10 minutos | `setInterval` no `useEffect` dos hooks, cleanup no return. |
| FE-17 | Listagem de alertas com filtros e indicação de garantia ativa | API suporta filtros `estado`, `nivel`, `usina`. Campo `com_garantia` boolean já serializado. |
| FE-18 | Tela de detalhe de alerta com formulário para atualizar estado e anotações | `PATCH /api/alertas/{id}/` aceita `estado` e `anotacoes`. Serializer `AlertaPatchSerializer` já implementado. |
</phase_requirements>

---

## Summary

Esta é a última fase do milestone v1 e é puramente frontend. Toda a infraestrutura backend necessária já existe e está implementada: os três endpoints de analytics (`/api/analytics/potencia/`, `/api/analytics/ranking-fabricantes/`, `/api/analytics/mapa/`) e o `AlertaViewSet` com filtros e PATCH já estão prontos. A rota `/api/alertas/{id}/` não requer nenhuma mudança no backend.

O trabalho se concentra em três áreas: (1) instalar dois pacotes novos (`recharts` e `react-leaflet` + `leaflet` + `@types/leaflet`), (2) criar hooks de data fetching seguindo exatamente o padrão estabelecido em `use-usinas.ts` e `use-garantias.ts`, adicionando a lógica de polling via `setInterval`, e (3) substituir os dois placeholders (`DashboardPage.tsx` e `AlertasPage.tsx`) por implementações reais, além de adicionar a página `AlertaDetalhePage.tsx` e a rota no router.

O projeto já possui todos os componentes shadcn necessários instalados (Table, Badge, Select, Dialog, Pagination, Sonner). O padrão de código é bem estabelecido e consistente — há pouca ambiguidade de implementação.

**Recomendação principal:** Dividir em dois planos: Plano 1 — instalar pacotes + criar tipos TypeScript + criar hooks com polling; Plano 2 — implementar componentes e páginas (DashboardPage, mapa, AlertasPage, AlertaDetalhePage, rota).

---

## Standard Stack

### Core

| Biblioteca | Versão | Propósito | Por que padrão |
|-----------|--------|-----------|----------------|
| recharts | 3.8.1 | Gráfico de pizza PieChart | Decisão D-01 — mais popular lib de charts para React |
| react-leaflet | 5.0.0 | Wrapper React para Leaflet | Decisão D-02 — open-source, sem custo de API |
| leaflet | 1.9.4 | Engine de mapa subjacente | Peer dependency do react-leaflet |
| @types/leaflet | 1.9.21 | Tipos TypeScript para leaflet | Leaflet não tem tipos próprios |

### Suporte (já instalados)

| Biblioteca | Versão atual | Propósito |
|-----------|-------------|-----------|
| axios | 1.15.0 | HTTP client com interceptors JWT |
| sonner | 2.0.7 | Toast notifications |
| react-router | 7.14.0 | Roteamento SPA |
| shadcn/ui components | — | Table, Badge, Select, Dialog, Pagination |
| lucide-react | 1.8.0 | Ícones |

**Instalação dos novos pacotes:**
```bash
cd frontend/admin
npm install recharts react-leaflet leaflet
npm install --save-dev @types/leaflet
```

**Versões verificadas:**
- recharts: 3.8.1 [VERIFIED: npm registry]
- react-leaflet: 5.0.0 [VERIFIED: npm registry]
- leaflet: 1.9.4 [VERIFIED: npm registry]
- @types/leaflet: 1.9.21 [VERIFIED: npm registry]

---

## Architecture Patterns

### Estrutura de arquivos a criar

```
frontend/admin/src/
├── types/
│   ├── analytics.ts          # PotenciaResponse, RankingResponse, MapaUsina
│   └── alertas.ts            # AlertaResumo, AlertaDetalhe, AlertaPatch, PaginatedAlertas
├── hooks/
│   ├── use-analytics.ts      # useAnalyticsPotencia, useAnalyticsRanking, useAnalyticsMapa
│   └── use-alertas.ts        # useAlertas, useAlerta
├── components/
│   ├── dashboard/
│   │   ├── PotenciaPieChart.tsx    # PieChart Recharts
│   │   ├── RankingTable.tsx        # Tabela top 5 clicável
│   │   └── MapaUsinas.tsx          # MapContainer react-leaflet
│   └── alertas/
│       ├── AlertasTable.tsx        # Tabela com filtros e badge com_garantia
│       └── AlertaEstadoForm.tsx    # Formulário PATCH estado + anotações
└── pages/
    ├── DashboardPage.tsx     # Substituir placeholder — layout grid
    ├── AlertasPage.tsx       # Substituir placeholder — tabela + filtros
    └── AlertaDetalhePage.tsx # Nova página — detalhe + formulário
```

### Padrão 1: Hook com polling (decisão D-03)

O padrão segue exatamente `use-usinas.ts` e `use-garantias.ts`, acrescentando `setInterval` para polling.

```typescript
// Fonte: use-usinas.ts (codebase verificado)
import { useState, useEffect, useCallback, useRef } from 'react'
import api from '@/lib/api'

const POLL_INTERVAL = 10 * 60 * 1000 // 10 minutos

export function useAnalyticsPotencia() {
  const [data, setData] = useState<PotenciaResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await api.get('/api/analytics/potencia/')
      setData(response.data)
    } catch {
      setError('Erro ao carregar dados de potência')
    } finally {
      setLoading(false)
    }
  }, []) // sem parâmetros dinâmicos — sem JSON.stringify necessário

  useEffect(() => {
    void fetch()
    const timer = setInterval(() => void fetch(), POLL_INTERVAL)
    return () => clearInterval(timer) // cleanup obrigatório
  }, [fetch])

  return { data, loading, error, refetch: fetch }
}
```

**Nota:** Hooks sem parâmetros dinâmicos (analytics) não precisam do padrão `JSON.stringify(params)` usado em `useUsinas`. Apenas `useAlertas` (com filtros) precisará.

### Padrão 2: Tipos TypeScript para as APIs

```typescript
// types/analytics.ts
export interface ProvedorPotencia {
  provedor: string
  media_kw: number | null
  usinas_ativas: number
}

export interface PotenciaResponse {
  media_geral_kw: number | null
  por_provedor: ProvedorPotencia[]
}

export interface ProvedorRanking {
  provedor: string
  inversores_ativos: number
}

export interface RankingResponse {
  ranking: ProvedorRanking[]
}

export interface MapaUsina {
  id: string
  nome: string
  provedor: string
  latitude: number | null
  longitude: number | null
  ativo: boolean
  status: string // 'sem_dados' | valor do ultimo_snapshot.status
}
```

```typescript
// types/alertas.ts
export type EstadoAlerta = 'ativo' | 'em_atendimento' | 'resolvido'
export type NivelAlerta = 'info' | 'aviso' | 'importante' | 'critico'

export interface AlertaResumo {
  id: string
  usina: string           // UUID
  usina_nome: string
  mensagem: string
  nivel: NivelAlerta
  estado: EstadoAlerta
  inicio: string
  fim: string | null
  com_garantia: boolean
  criado_em: string
  atualizado_em: string
}

export interface AlertaDetalhe extends AlertaResumo {
  catalogo_alarme: number | null
  id_alerta_provedor: string
  equipamento_sn: string
  sugestao: string
  anotacoes: string
}

export interface AlertaPatch {
  estado?: EstadoAlerta
  anotacoes?: string
}

export interface PaginatedAlertas {
  count: number
  next: string | null
  previous: string | null
  results: AlertaResumo[]
}
```

### Padrão 3: Recharts PieChart

```typescript
// Fonte: padrão Recharts PieChart com Cell [ASSUMED — training knowledge]
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'

const CORES = ['#8884d8', '#82ca9d', '#ffc658', '#ff7300', '#0088fe']

// data = por_provedor[] com media_kw e usinas_ativas
<ResponsiveContainer width="100%" height={300}>
  <PieChart>
    <Pie
      data={data}
      dataKey="media_kw"
      nameKey="provedor"
      cx="50%"
      cy="50%"
      outerRadius={100}
      label
    >
      {data.map((_, index) => (
        <Cell key={index} fill={CORES[index % CORES.length]} />
      ))}
    </Pie>
    <Tooltip formatter={(value: number) => [`${value.toFixed(2)} kW`, 'Potência média']} />
    <Legend />
  </PieChart>
</ResponsiveContainer>
```

**Cuidado:** `media_kw` pode ser `null` para provedores sem dados. Filtrar antes de passar ao gráfico: `data.filter(p => p.media_kw !== null)`.

### Padrão 4: react-leaflet MapContainer

```typescript
// Leaflet CSS DEVE ser importado — sem ele os tiles não renderizam
import 'leaflet/dist/leaflet.css'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import L from 'leaflet'

// CRÍTICO: ícone padrão do Leaflet quebra com bundlers (Vite/webpack)
// Solução: redefinir manualmente
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: new URL('leaflet/dist/images/marker-icon-2x.png', import.meta.url).href,
  iconUrl: new URL('leaflet/dist/images/marker-icon.png', import.meta.url).href,
  shadowUrl: new URL('leaflet/dist/images/marker-shadow.png', import.meta.url).href,
})

// Marcadores coloridos via DivIcon
function criarIcone(cor: 'verde' | 'vermelho' | 'cinza') {
  const cores = { verde: '#22c55e', vermelho: '#ef4444', cinza: '#9ca3af' }
  return L.divIcon({
    className: '',
    html: `<div style="width:12px;height:12px;border-radius:50%;background:${cores[cor]};border:2px solid white;box-shadow:0 1px 3px rgba(0,0,0,0.4)"></div>`,
    iconSize: [12, 12],
    iconAnchor: [6, 6],
  })
}
```

**Centro padrão do mapa:** `-15.0, -47.0` (centro do Brasil) com zoom inicial `5`. Claude pode calcular média das coordenadas recebidas da API se preferir.

### Padrão 5: Interação ranking ↔ mapa (FE-15)

Estado `selectedProvedor` vive em `DashboardPage` e é passado para `RankingTable` e `MapaUsinas`. Filtro aplicado localmente no frontend — sem nova requisição.

```typescript
// Em DashboardPage
const [selectedProvedor, setSelectedProvedor] = useState<string | null>(null)

// Marcadores filtrados antes de renderizar
const usinasFiltradas = selectedProvedor
  ? mapaData.filter(u => u.provedor === selectedProvedor)
  : mapaData
```

Clicar no mesmo fabricante já selecionado deseleciona (toggle).

### Padrão 6: AlertaEstadoForm — PATCH com toast

Seguir exatamente o padrão de `UsinaEditDialog`:
- Estado local do formulário com `useState`
- `api.patch('/api/alertas/${id}/', payload)` usando a instância axios com Bearer
- `toast.success` / `toast.error` do sonner
- `isSubmitting` para desabilitar botão durante request

### Anti-Patterns a Evitar

- **Não passar `setLoading(true)` dentro do `setInterval` sem cleanup:** O timer deve ser cancelado no return do `useEffect`. Já modelado no padrão acima.
- **Não confiar em data.results sem verificar `null`:** Usar `data?.results ?? []`.
- **Não renderizar `<MapContainer>` sem altura CSS definida:** O contêiner Leaflet precisa de `height` explícita (ex: `h-96` Tailwind ou `style={{ height: '400px' }}`).
- **Não esquecer `leaflet/dist/leaflet.css`:** Sem esse import, os tiles do OpenStreetMap ficam visualmente quebrados.
- **Não esquecer o fix do ícone padrão do Leaflet:** É um bug conhecido com bundlers modernos (Vite). Sem o fix, os marcadores aparecem quebrados.

---

## Don't Hand-Roll

| Problema | Não construir | Usar | Por que |
|---------|--------------|------|---------|
| Gráfico de pizza | SVG customizado | `recharts` PieChart | Responsividade, tooltip, legend, acessibilidade |
| Mapa interativo | Canvas + tiles manual | `react-leaflet` + `leaflet` | Projeções cartográficas, clustering, eventos de mapa |
| Toast de feedback | `alert()` / componente próprio | `sonner` (já instalado) | Já integrado, padrão do projeto |
| Tabela de alertas | `<table>` sem shadcn | shadcn `Table` | Consistência visual com Phase 5 |
| Badge com_garantia | Texto inline | shadcn `Badge` | Consistência com `StatusGarantiaBadge` existente |

**Insight-chave:** O padrão de hook (`useState` + `useCallback` + `useEffect`) já está consolidado em duas implementações (`use-usinas.ts`, `use-garantias.ts`). Copiar e adaptar — não reinventar.

---

## Common Pitfalls

### Pitfall 1: Leaflet CSS não importado

**O que acontece:** Os tiles do mapa aparecem sem estilo — azulejos fora de posição, layer de controles quebrado.
**Por que acontece:** Leaflet usa CSS para posicionar tiles e controles. Com bundlers como Vite, o CSS não é auto-importado.
**Como evitar:** Adicionar `import 'leaflet/dist/leaflet.css'` no componente que renderiza o `MapContainer` ou no `MapaUsinas.tsx`.
**Sinal de alerta:** Mapa renderiza mas os tiles aparecem deslocados ou sobrepostos.

### Pitfall 2: Ícones padrão do Leaflet quebram com Vite

**O que acontece:** Os marcadores padrão do Leaflet aparecem como ícones quebrados (imagem not found).
**Por que acontece:** O Leaflet usa `require()` para importar imagens de ícone — incompatível com o sistema de módulos ES do Vite.
**Como evitar:** Redefinir `L.Icon.Default` manualmente usando `new URL(..., import.meta.url).href` para cada imagem, ou usar `L.divIcon` custom (abordagem preferida neste projeto pois já precisamos de cores diferentes por status).
**Sinal de alerta:** Console mostra 404 para `marker-icon.png`.

### Pitfall 3: MapContainer sem altura definida

**O que acontece:** O mapa renderiza com altura zero — completamente invisível.
**Por que acontece:** `MapContainer` usa 100% da altura do elemento pai. Se o pai não tem altura definida, o mapa colapsa.
**Como evitar:** Sempre definir `style={{ height: '400px' }}` ou classe Tailwind `h-96` no `MapContainer`.

### Pitfall 4: Memory leak no polling

**O que acontece:** Componente desmontado continua chamando `setData`, gerando warnings React ("Can't perform a React state update on an unmounted component").
**Por que acontece:** `setInterval` não é cancelado quando o componente é removido do DOM.
**Como evitar:** Sempre retornar `() => clearInterval(timer)` no cleanup do `useEffect`.

### Pitfall 5: `media_kw` null no gráfico de pizza

**O que acontece:** Recharts pode renderizar fatias com valor null ou exibir erros.
**Por que acontece:** `PotenciaMediaView` exclui usinas sem snapshot do cálculo, mas um provedor pode ter média `null` se todos os inversores estiverem offline.
**Como evitar:** Filtrar `por_provedor.filter(p => p.media_kw !== null && p.media_kw > 0)` antes de passar ao `PieChart`.

### Pitfall 6: Estado local do formulário de alerta não sincronizado

**O que acontece:** Usuário navega para o detalhe, edita, e ao voltar os dados estão desatualizados.
**Por que acontece:** `useAlerta(id)` armazena dados em state local — após PATCH, o state do hook não é atualizado automaticamente.
**Como evitar:** Chamar `refetch()` após PATCH bem-sucedido (mesmo padrão de `UsinaEditDialog`).

---

## Code Examples

### Hook com polling (verificado contra padrão existente no projeto)

```typescript
// Fonte: use-usinas.ts (codebase — VERIFIED)
// Adição do setInterval para polling conforme D-03
export function useAnalyticsRanking() {
  const [data, setData] = useState<RankingResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await api.get('/api/analytics/ranking-fabricantes/')
      setData(response.data)
    } catch {
      setError('Erro ao carregar ranking')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void fetch()
    const timer = setInterval(() => void fetch(), 600_000)
    return () => clearInterval(timer)
  }, [fetch])

  return { data, loading, error, refetch: fetch }
}
```

### PATCH de alerta com toast (padrão confirmado)

```typescript
// Fonte: padrão de UsinaEditDialog.tsx (codebase — VERIFIED)
import { toast } from 'sonner'
import api from '@/lib/api'

async function handleSubmit(id: string, payload: AlertaPatch) {
  setIsSubmitting(true)
  try {
    await api.patch(`/api/alertas/${id}/`, payload)
    toast.success('Alerta atualizado com sucesso')
    refetch() // re-busca o detalhe
  } catch {
    toast.error('Erro ao atualizar alerta')
  } finally {
    setIsSubmitting(false)
  }
}
```

### Rota `/alertas/:id` no App.tsx

```typescript
// App.tsx — adicionar dentro de children do ProtectedLayout
{ path: 'alertas/:id', element: <AlertaDetalhePage /> },
{ path: 'alertas', element: <AlertasPage /> },

// ROUTE_TITLES — adicionar entrada para breadcrumb dinâmico
// Nota: pathname dinâmico tipo /alertas/uuid não tem entrada estática.
// Resolver com useMatch ou simplesmente não mostrar título customizado
// para rotas de detalhe (comportamento atual: exibe 'Firma Solar').
```

---

## State of the Art

| Abordagem antiga | Abordagem atual | Impacto |
|-----------------|----------------|---------|
| Leaflet diretamente (sem wrapper) | react-leaflet 5.x com hooks React | Compatibilidade React 19 sem refs manuais |
| Recharts v1/v2 | Recharts 3.x (API estável) | `ResponsiveContainer` obrigatório para responsividade |
| React Query para polling | setInterval manual (decisão D-03) | Consistência com Phase 5 — sem dependência extra |

**Deprecated/Desatualizado:**
- `react-leaflet` v4 não suporta React 19 (`react: ^19.2.4` do projeto). Usar v5.0.0.
- Recharts v2 mudou a API de `Pie` — verificar que não se usa `dataKey` em `<Pie>` para agrupar por cor (isso se faz com `Cell`).

---

## Assumptions Log

| # | Afirmação | Seção | Risco se Errado |
|---|-----------|-------|-----------------|
| A1 | `react-leaflet` 5.0.0 suporta React 19 sem breaking changes | Standard Stack | Incompatibilidade pode exigir workaround ou versão diferente |
| A2 | `media_kw` pode ser null no response de `/api/analytics/potencia/` quando provedor sem snapshots | Common Pitfalls | Se nunca for null, o filtro é desnecessário mas inofensivo |
| A3 | `ultimo_snapshot.status` pode retornar valores além de 'sem_dados' — precisa mapear para cores do mapa | Architecture Patterns | Marcadores podem ter cor incorreta se valores de status forem inesperados |
| A4 | Recharts 3.8.1 usa `ResponsiveContainer` para responsividade obrigatoriamente | Code Examples | Gráfico pode não redimensionar sem ele |

---

## Open Questions

1. **Quais valores pode ter `status` de `UsinaMapaSerializer`?**
   - O que sabemos: `get_status` retorna `'sem_dados'` ou `obj.ultimo_snapshot.status`
   - O que está incerto: Quais são os valores possíveis de `ultimo_snapshot.status`? O model `SnapshotUsina` define o campo `status` como CharField — os choices não foram verificados
   - Recomendação: No `MapaUsinas.tsx`, tratar "qualquer valor não-'normal'" como vermelho (fail-safe) para evitar marcadores cinza incorretos
   - Ação: O planner deve verificar `usinas/models.py` para os choices de `status` do snapshot

2. **Breakpoint mobile do dashboard grid**
   - O que sabemos: D-05 diz "Claude's Discretion nos breakpoints mobile"
   - O que está incerto: Se o mapa (100% width, ~400px altura) fica usável em mobile
   - Recomendação: `grid-cols-1 md:grid-cols-2` para Linha 1, mapa sempre full width. Em mobile, empilhar tudo verticalmente.

---

## Environment Availability

| Dependência | Requerida por | Disponível | Versão | Fallback |
|-------------|--------------|-----------|--------|---------|
| Node.js | npm install | ✓ | 24.14.0 | — |
| npm | recharts, react-leaflet | ✓ | (inferido do Node 24) | — |
| Backend `/api/analytics/potencia/` | FE-12, FE-13, FE-16 | Implementado | Fase 3 | — |
| Backend `/api/analytics/mapa/` | FE-14, FE-15 | Implementado | Fase 3 | — |
| Backend `/api/alertas/` | FE-17, FE-18 | Implementado | Fase 2 | — |
| OpenStreetMap tiles | FE-14 | ✓ (gratuito, sem API key) | — | — |

**Dependências ausentes com fallback:** Nenhuma.
**Dependências ausentes sem fallback:** Nenhuma — todas disponíveis.

---

## Validation Architecture

### Test Framework

| Propriedade | Valor |
|------------|-------|
| Framework | Nenhum configurado no frontend (frontend é Phase 6 final, sem testes automatizados definidos) |
| Config file | N/A |
| Quick run command | N/A |
| Full suite command | N/A |

**Nota:** O projeto tem `nyquist_validation: true` mas nenhum framework de testes foi instalado para o frontend. FE-12 a FE-18 são requisitos de UI — os testes relevantes são manuais/visuais. O backend (fases 1-3) tem seus próprios testes pytest. Para esta fase, a validação se dá pelos **Success Criteria do ROADMAP.md**:

| Req ID | Comportamento | Tipo de Teste | Comando | Arquivo |
|--------|--------------|---------------|---------|---------|
| FE-12 | Gráfico pizza renderiza com dados reais | Manual (visual) | — | — |
| FE-13 | Tabela ranking mostra top 5 | Manual (visual) | — | — |
| FE-14 | Mapa mostra marcadores para usinas com coordenadas | Manual (visual) | — | — |
| FE-15 | Clicar no ranking filtra marcadores do mapa | Manual (interação) | — | — |
| FE-16 | Dados atualizados automaticamente a cada 10 min | Manual (espera ou mock de timer) | — | — |
| FE-17 | Filtros de alertas funcionam; coluna com_garantia exibe badge | Manual (visual) | — | — |
| FE-18 | PATCH estado/anotações persiste e reflete na listagem | Manual (end-to-end) | — | — |

### Wave 0 Gaps

- [ ] Nenhum framework de teste frontend instalado — `nyquist_validation` para frontend não se aplica nesta fase sem configuração prévia. Testes são manuais via browser.

*(Recomendação ao planner: não incluir task de instalar framework de testes — está fora do escopo desta fase.)*

---

## Security Domain

| Categoria ASVS | Aplica | Controle |
|---------------|--------|---------|
| V2 Autenticação | Não (já implementado em Fase 4) | Interceptor axios JWT existente |
| V3 Sessão | Não (já implementado) | localStorage com refresh automático |
| V4 Controle de Acesso | Sim — PATCH de alerta deve só funcionar autenticado | Bearer token injetado pelo interceptor axios |
| V5 Validação de Input | Sim — `estado` deve ser um dos 3 valores válidos | Validação no backend (DRF choices field) |
| V6 Criptografia | Não | — |

### Padrões de Ameaça

| Padrão | STRIDE | Mitigação padrão |
|--------|--------|-----------------|
| PATCH para estado inválido | Tampering | Backend rejeita via DRF choices validation — frontend pode adicionar Select com opções fixas |
| Rota `/alertas/:id` acessível sem auth | Elevation of Privilege | `ProtectedLayout` no router já cobre — backend retorna 401 sem token |
| ID de alerta manipulado na URL | Tampering | Backend valida ownership via queryset autenticado |

---

## Sources

### Primary (HIGH confidence)
- Codebase (`/home/micael/firmasolar/frontend/admin/`) — use-usinas.ts, use-garantias.ts, UsinasPage.tsx, UsinasTable.tsx, App.tsx, api.ts, package.json [VERIFIED: Read tool]
- Codebase (`/home/micael/firmasolar/backend_monitoramento/`) — analytics.py, alertas.py, serializers/alertas.py, serializers/analytics.py, filters/alertas.py, models/Alerta [VERIFIED: Read tool]
- npm registry — versões de recharts (3.8.1), react-leaflet (5.0.0), leaflet (1.9.4), @types/leaflet (1.9.21) [VERIFIED: npm view]

### Secondary (MEDIUM confidence)
- CONTEXT.md da Fase 6 — decisões D-01 a D-08 [VERIFIED: Read tool]
- REQUIREMENTS.md — FE-12 a FE-18 [VERIFIED: Read tool]

### Tertiary (LOW confidence)
- Padrão de fix de ícone Leaflet com Vite — `new URL(..., import.meta.url)` [ASSUMED: training knowledge — pitfall amplamente documentado na comunidade]
- Compatibilidade react-leaflet 5.0.0 com React 19 [ASSUMED: training knowledge — versão recente, não verificado com docs oficiais]

---

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — versões verificadas via npm registry
- Architecture Patterns: HIGH — baseado em código existente do projeto (use-usinas.ts, UsinasPage.tsx)
- Pitfalls: MEDIUM — Pitfalls 1-4 são bem conhecidos (Leaflet+Vite), pitfall 5-6 inferidos da API

**Research date:** 2026-04-09
**Valid until:** 2026-05-09 (recharts e react-leaflet são estáveis)
