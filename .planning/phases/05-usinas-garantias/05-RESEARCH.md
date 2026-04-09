# Phase 5: Usinas & Garantias - Research

**Researched:** 2026-04-09
**Domain:** React frontend — gestão de usinas e garantias com shadcn/ui + Axios
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01: Layout de listagem — Tabela shadcn (DataTable)**
Usar componente `Table` do shadcn/ui para listagens de usinas e garantias. Instalar `npx shadcn@latest add table` + `badge` + `dialog` + `select`. Paginação no cliente consumindo a API paginada do backend (`?page=N`).

**D-02: Edição de usina — Modal (Dialog)**
Formulário de edição em `Dialog` do shadcn. Campos: nome e capacidade_kwp. `PATCH /api/usinas/{id}/` com feedback de sucesso/erro. Listagem atualiza automaticamente após salvar (invalidar cache ou re-fetch).

**D-03: Formulário de garantia — Modal (Dialog)**
Modal para criar/editar garantia. Campos: data_inicio (date picker ou input date), meses (number). `PUT /api/usinas/{id}/garantia/`. Preview de `data_fim` calculada em tempo real no formulário (date-fns ou cálculo simples). Listagem de garantias atualiza após salvar.

**D-04: Badge de status de garantia — cores**
| Status | Cor | Classe Tailwind |
|--------|-----|-----------------|
| ativa | Verde | `bg-green-100 text-green-800` ou `variant="default"` verde |
| vencida | Vermelho | `bg-red-100 text-red-800` ou `variant="destructive"` |
| sem_garantia | Cinza | `bg-gray-100 text-gray-600` ou `variant="secondary"` |
Indicador especial: garantias com `dias_restantes < 30` exibem vermelho na listagem de garantias (FE-10).

**D-05: Detalhe de usina — layout com cards**
Página `/usinas/:id` com:
- Card principal: nome, provedor, capacidade, status garantia, último snapshot (potência, energia)
- Tabela de inversores: número série, modelo, último pac_kw, estado

**D-06: Componentes shadcn a instalar**
Planner decide a lista exata. Candidatos: `table`, `badge`, `dialog`, `select`, `pagination`, `toast` (feedback de sucesso/erro).

**D-07: Data fetching pattern**
Usar hooks customizados (`useUsinas`, `useUsina`, `useGarantias`) que encapsulam chamadas axios + estado (loading, error, data). Sem React Query nesta fase — fetch simples com `useEffect` + `useState`. Re-fetch manual após mutations.

### Claude's Discretion

- Componentes shadcn exatos a instalar
- Se usar `date-fns` para cálculo de data_fim ou cálculo manual
- Estrutura de pastas para hooks de data fetching
- Layout responsivo (mobile) — planner decide nível de suporte
- Se usar skeleton loading ou spinner durante fetch

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope

**Fora do escopo desta fase:**
- Histórico de snapshots em gráfico (V2-06)
- Exclusão de usina via UI — continua no Django Admin
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FE-06 | Listagem de usinas com filtros, paginação e badge de status de garantia | API `/api/usinas/` verificada — retorna `status_garantia`, `provedor`, `ativo`. Filtros disponíveis. Table + Badge shadcn a instalar. |
| FE-07 | Tela de detalhe de usina com inversores e último snapshot | API `/api/usinas/{id}/` verificada — retorna `inversores[]` e `ultimo_snapshot` aninhados. Rota `/usinas/:id` precisa ser adicionada ao App.tsx. |
| FE-08 | Formulário de edição de usina (nome, capacidade) | PATCH `/api/usinas/{id}/` aceita apenas `nome` e `capacidade_kwp`. Dialog shadcn a instalar. |
| FE-09 | Seção `/garantias` com listagem de todas as garantias e seus status | API `/api/garantias/` verificada — retorna `usina_nome`, `data_fim`, `dias_restantes`, `ativa`. GarantiasPage.tsx é placeholder. |
| FE-10 | Indicador visual de vencimento próximo (< 30 dias) | `dias_restantes` vem calculado pela API. Lógica condicional no frontend: `dias_restantes < 30 && ativa → vermelho`. |
| FE-11 | Formulário de criação/edição de garantia por usina (data início, duração em meses) | PUT `/api/usinas/{id}/garantia/` aceita `data_inicio`, `meses`, `observacoes`. Preview de `data_fim` em tempo real via cálculo JS nativo. |
</phase_requirements>

---

## Summary

O frontend em Phase 4 entregou a infraestrutura completa: axios com interceptors de refresh JWT, AuthContext, ProtectedLayout, roteamento com react-router v7, sidebar e layout. As páginas `UsinasPage` e `GarantiasPage` são placeholders de 8 linhas cada — serão inteiramente substituídas. A rota `/usinas/:id` ainda não existe no router e precisa ser adicionada.

O backend já entrega todos os contratos necessários: `GET /api/usinas/` com `status_garantia` calculado, `GET /api/usinas/{id}/` com `inversores[]` e `ultimo_snapshot` aninhados, `PATCH /api/usinas/{id}/` para edição, `PUT /api/usinas/{id}/garantia/` para upsert e `GET /api/garantias/` com `dias_restantes` calculado. Nenhum endpoint precisa ser criado — a fase é 100% frontend.

Os componentes shadcn `table`, `badge`, `dialog`, `select` e `pagination` precisam ser instalados. `toast` não existe no registry do estilo `radix-nova` em uso — o substituto correto é `sonner` (verificado via dry-run). `date-fns` não está instalado e não é necessário: `data_fim` já vem da API como string ISO e o cálculo de preview no formulário pode ser feito com `Date` nativo.

**Primary recommendation:** Criar os 3 hooks de data fetching (`useUsinas`, `useUsina`, `useGarantias`) como fundação antes de implementar as páginas. Instalar shadcn components em Wave 0.

---

## Standard Stack

### Core (já instalado)
| Library | Version | Purpose | Source |
|---------|---------|---------|--------|
| react | ^19.2.4 | UI framework | [VERIFIED: package.json] |
| react-router | ^7.14.0 | Roteamento + params | [VERIFIED: package.json] |
| axios | ^1.15.0 | HTTP client com interceptors JWT | [VERIFIED: package.json] |
| shadcn (CLI) | ^4.2.0 | Gerador de componentes UI | [VERIFIED: package.json] |
| radix-ui | ^1.4.3 | Primitivos acessíveis (base do shadcn) | [VERIFIED: package.json] |
| lucide-react | ^1.8.0 | Ícones | [VERIFIED: package.json] |
| tailwindcss | ^4.2.2 | Estilização | [VERIFIED: package.json] |

### Componentes shadcn a instalar (Wave 0)
| Componente | Status | Dry-run verificado | Comando |
|------------|--------|--------------------|---------|
| table | Ausente | ✓ — 1 arquivo novo | `npx shadcn@latest add table` |
| badge | Ausente | ✓ — 1 arquivo novo | `npx shadcn@latest add badge` |
| dialog | Ausente | ✓ — 1 arquivo novo (button já existe) | `npx shadcn@latest add dialog` |
| select | Ausente | ✓ — 1 arquivo novo | `npx shadcn@latest add select` |
| pagination | Ausente | ✓ — 1 arquivo novo (button já existe) | `npx shadcn@latest add pagination` |
| sonner | Ausente | ✓ — instala também `sonner` npm pkg + `next-themes` | `npx shadcn@latest add sonner` |

[VERIFIED: dry-run executado com `npx shadcn@latest add <componente> --dry-run` para cada um]

**Atenção crítica:** O estilo configurado no projeto é `radix-nova` (verificado em `components.json`). O componente `toast` **não existe** neste estilo — o dry-run retornou 404. O substituto correto é `sonner`. [VERIFIED: dry-run falhou para toast, passou para sonner]

### date-fns — NÃO necessário
`date-fns` não está instalado. Para o preview de `data_fim` no formulário de garantia, calcular com `Date` nativo:

```typescript
// Cálculo nativo — sem dependência extra
function calcularDataFim(dataInicio: string, meses: number): string {
  const d = new Date(dataInicio)
  d.setMonth(d.getMonth() + meses)
  return d.toLocaleDateString('pt-BR')
}
```

`data_fim` e `dias_restantes` já chegam calculados pela API em todas as respostas de garantia — o cálculo frontend é apenas para preview em tempo real no formulário antes de salvar.

**Installation (Wave 0):**
```bash
npx shadcn@latest add table badge dialog select pagination sonner
```

---

## API Contracts (verificados nos serializers)

### GET /api/usinas/ — UsinaListSerializer
```typescript
interface UsinaResumo {
  id: string              // UUID
  nome: string
  provedor: string        // 'solis' | outros
  capacidade_kwp: number
  ativo: boolean
  status_garantia: 'ativa' | 'vencida' | 'sem_garantia'  // campo calculado
  criado_em: string       // ISO 8601
  atualizado_em: string
}

interface PaginatedUsinas {
  count: number
  next: string | null
  previous: string | null
  results: UsinaResumo[]
}
```

**Filtros disponíveis** (via UsinaFilterSet — verificado no views/usinas.py):
- `?provedor=solis`
- `?ativo=true`
- `?status_garantia=ativa|vencida|sem_garantia`
- `?page=N` para paginação

[VERIFIED: usinas.py serializers lidos diretamente]

### GET /api/usinas/{id}/ — UsinaDetalheSerializer
```typescript
interface InversorResumo {
  id: string
  numero_serie: string
  modelo: string
  id_inversor_provedor: string
}

interface SnapshotUsina {
  id: string
  coletado_em: string
  data_medicao: string
  potencia_kw: number
  energia_hoje_kwh: number
  energia_mes_kwh: number
  energia_total_kwh: number
  status: string
  qtd_inversores: number
  qtd_inversores_online: number
  qtd_alertas: number
}

interface UsinaDetalhe {
  id: string
  nome: string
  provedor: string
  capacidade_kwp: number
  ativo: boolean
  fuso_horario: string
  endereco: string
  status_garantia: 'ativa' | 'vencida' | 'sem_garantia'
  ultimo_snapshot: SnapshotUsina | null
  inversores: InversorResumo[]
  criado_em: string
  atualizado_em: string
}
```

**Nota:** `ultimo_snapshot` pode ser `null` se a usina nunca foi coletada — o código deve tratar este caso. [VERIFIED: campo `read_only=True` sem required no serializer]

### PATCH /api/usinas/{id}/ — UsinaPatchSerializer
```typescript
// Request body — apenas estes dois campos aceitos
interface UsinaPatch {
  nome?: string
  capacidade_kwp?: number
}
```

PUT é bloqueado (405) para `/api/usinas/{id}/` — apenas PATCH. [VERIFIED: views/usinas.py método `update` bloqueia se `partial=False`]

### PUT /api/usinas/{id}/garantia/ — GarantiaUsinaEscritaSerializer
```typescript
// Request body
interface GarantiaInput {
  data_inicio: string   // 'YYYY-MM-DD'
  meses: number         // min_value=1
  observacoes?: string  // opcional, default ''
}

// Response — GarantiaUsinaSerializer
interface GarantiaUsina {
  id: string
  usina_id: string
  usina_nome: string
  data_inicio: string
  meses: number
  observacoes: string
  data_fim: string      // ISO 8601, calculado
  dias_restantes: number
  ativa: boolean
  criado_em: string
  atualizado_em: string
}
```

[VERIFIED: garantias.py serializers lidos diretamente]

### GET /api/garantias/ — GarantiaUsinaSerializer
```typescript
// Mesma interface GarantiaUsina acima
// Filtros disponíveis:
// ?filtro=ativas
// ?filtro=vencendo   (vencendo em 30 dias)
// ?filtro=vencidas
```

[VERIFIED: urls.py — GarantiaListView registrada em `/api/garantias/`]

---

## Architecture Patterns

### Estrutura de pastas recomendada

```
frontend/admin/src/
├── hooks/
│   ├── use-mobile.ts          # já existe
│   ├── use-usinas.ts          # CRIAR — useUsinas(), useUsina(id)
│   └── use-garantias.ts       # CRIAR — useGarantias()
├── pages/
│   ├── UsinasPage.tsx         # SUBSTITUIR placeholder
│   ├── UsinaDetalhePage.tsx   # CRIAR — rota /usinas/:id
│   └── GarantiasPage.tsx      # SUBSTITUIR placeholder
├── components/
│   ├── usinas/
│   │   ├── UsinasTable.tsx          # CRIAR — tabela + filtros
│   │   ├── UsinaEditDialog.tsx      # CRIAR — modal edição
│   │   └── StatusGarantiaBadge.tsx  # CRIAR — badge colorido
│   └── garantias/
│       ├── GarantiasTable.tsx       # CRIAR — tabela + indicadores
│       └── GarantiaFormDialog.tsx   # CRIAR — modal criar/editar
└── lib/
    └── api.ts                 # já existe — NÃO modificar
```

### Pattern 1: Custom Hook de Data Fetching (D-07)

```typescript
// src/hooks/use-usinas.ts
import { useState, useEffect, useCallback } from 'react'
import api from '@/lib/api'

interface UsinasParams {
  provedor?: string
  ativo?: boolean
  status_garantia?: string
  page?: number
}

export function useUsinas(params: UsinasParams = {}) {
  const [data, setData] = useState<PaginatedUsinas | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data: result } = await api.get('/api/usinas/', { params })
      setData(result)
    } catch {
      setError('Erro ao carregar usinas')
    } finally {
      setLoading(false)
    }
  }, [JSON.stringify(params)])

  useEffect(() => { fetch() }, [fetch])

  return { data, loading, error, refetch: fetch }
}
```

**Por que `JSON.stringify(params)` como dependência:** Evita loop infinito com objetos literais recriados a cada render. [ASSUMED — padrão comum, sem fonte verificada nesta sessão]

### Pattern 2: Dialog de Edição com Re-fetch

```typescript
// Após PATCH bem-sucedido, chamar refetch() do hook pai
// Evita manter cache stale — fetch simples sem React Query

function UsinaEditDialog({ usina, onSuccess }: Props) {
  const [saving, setSaving] = useState(false)

  async function handleSubmit(values: UsinaPatch) {
    setSaving(true)
    try {
      await api.patch(`/api/usinas/${usina.id}/`, values)
      toast.success('Usina atualizada')
      onSuccess()  // chama refetch() na página pai
    } catch {
      toast.error('Erro ao salvar')
    } finally {
      setSaving(false)
    }
  }
  // ...
}
```

### Pattern 3: Rota de detalhe com useParams

```typescript
// App.tsx — adicionar rota de detalhe:
{ path: 'usinas/:id', element: <UsinaDetalhePage /> }

// ROUTE_TITLES também deve ser atualizado:
'/usinas': 'Usinas'
// O detalhe terá breadcrumb dinâmico — tratar separadamente

// UsinaDetalhePage.tsx:
import { useParams } from 'react-router'
const { id } = useParams<{ id: string }>()
```

### Pattern 4: Badge de Status com variante controlada

```typescript
// src/components/usinas/StatusGarantiaBadge.tsx
// Não usar className inline nas páginas — centralizar aqui

type StatusGarantia = 'ativa' | 'vencida' | 'sem_garantia'

const CONFIG: Record<StatusGarantia, { label: string; className: string }> = {
  ativa: { label: 'Ativa', className: 'bg-green-100 text-green-800' },
  vencida: { label: 'Vencida', className: 'bg-red-100 text-red-800' },
  sem_garantia: { label: 'Sem Garantia', className: 'bg-gray-100 text-gray-600' },
}
```

### Pattern 5: Indicador de vencimento próximo (FE-10)

```typescript
// Na GarantiasTable — sem componente separado, lógica inline na célula
const isVencendoLogo = garantia.ativa && garantia.dias_restantes < 30

// Aplicar classe condicional na linha ou célula:
<TableRow className={isVencendoLogo ? 'bg-red-50' : ''}>
```

### Pattern 6: Preview de data_fim em tempo real (D-03)

```typescript
// Dentro do GarantiaFormDialog — state local, sem hook
const [dataInicio, setDataInicio] = useState('')
const [meses, setMeses] = useState(12)

const dataFimPreview = useMemo(() => {
  if (!dataInicio || !meses) return null
  const d = new Date(dataInicio + 'T00:00:00')  // evita timezone shift
  d.setMonth(d.getMonth() + meses)
  return d.toLocaleDateString('pt-BR')
}, [dataInicio, meses])
```

**Atenção:** `new Date('YYYY-MM-DD')` sem hora é interpretado como UTC e pode exibir o dia anterior em fuso negativo. Concatenar `'T00:00:00'` força interpretação local. [ASSUMED — comportamento conhecido do JS Date parsing]

### Anti-Patterns a Evitar

- **Lógica de negócio na página**: extrair em hooks e componentes — CLAUDE.md exige single responsibility
- **N+1 em re-renders**: não chamar `api.get` diretamente no render — sempre em `useEffect` dentro do hook
- **Hardcode de strings de status**: centralizar em constante ou tipo TypeScript (`StatusGarantia`)
- **Catch silencioso**: nunca `catch {}` sem setar `error` no estado ou exibir feedback — CLAUDE.md proíbe `except: pass` e equivalentes
- **PUT em vez de PATCH para usina**: a API bloqueia PUT para `/api/usinas/{id}/` com 405
- **PUT garantia sem usina_id**: o endpoint correto é `/api/usinas/{id}/garantia/`, não `/api/garantias/{id}/`

---

## Don't Hand-Roll

| Problema | Não construir | Usar em vez | Por quê |
|----------|---------------|-------------|---------|
| Tabela HTML com cabeçalho, zebra-stripe, hover | `<table>` manual | shadcn `Table` | Acessibilidade, consistência visual, responsividade |
| Modal com overlay, foco trapeado, Escape para fechar | `<div>` com z-index | shadcn `Dialog` | Radix Dialog implementa WAI-ARIA corretamente |
| Select/dropdown acessível | `<select>` HTML nativo | shadcn `Select` | Keyboard nav, styling cross-browser |
| Paginação com estados prev/next/disabled | botões manuais | shadcn `Pagination` | Consistência + acessibilidade |
| Toast/feedback de mutação | `alert()` ou estado booleano | `sonner` via shadcn | API simples, evita state de toast no componente |
| Badge com variantes de cor | `<span>` com className condicional | shadcn `Badge` | Usar variante `secondary`/`destructive` + customização via className |

---

## Common Pitfalls

### Pitfall 1: Rota `/usinas/:id` ausente no App.tsx
**O que acontece:** Navegar para detalhe de usina resulta em rota não encontrada ou fallback.
**Por que acontece:** App.tsx tem rotas `/usinas` e `/garantias` mas não tem `/usinas/:id`.
**Como evitar:** Adicionar `{ path: 'usinas/:id', element: <UsinaDetalhePage /> }` dentro dos `children` de `ProtectedLayout` como primeira tarefa.
**Sinal de alerta:** 404 ou redirect para `/` ao clicar no link de detalhe.

### Pitfall 2: `toast` não existe no estilo `radix-nova`
**O que acontece:** `npx shadcn@latest add toast` retorna 404.
**Por que acontece:** O projeto usa estilo `radix-nova` (verificado em `components.json`), que não tem `toast` no registry.
**Como evitar:** Usar `sonner` em vez de `toast`. `npx shadcn@latest add sonner` funciona e instala também o pacote npm `sonner`.
**Sinal de alerta:** Erro "item was not found" ao tentar adicionar `toast`.

### Pitfall 3: `ultimo_snapshot` pode ser `null`
**O que acontece:** `TypeError: Cannot read properties of null` ao acessar `usina.ultimo_snapshot.potencia_kw`.
**Por que acontece:** Usinas recém-cadastradas não têm snapshot — o campo é `null`.
**Como evitar:** Usar optional chaining: `usina.ultimo_snapshot?.potencia_kw ?? '—'`. Card de detalhe deve ter estado "sem dados de coleta ainda".

### Pitfall 4: useEffect com objeto de params recriado a cada render
**O que acontece:** Loop infinito de requests.
**Por que acontece:** `{ provedor, page }` é um objeto novo a cada render — useEffect dispara infinitamente.
**Como evitar:** No hook, usar `JSON.stringify(params)` como dependência, ou usar `useCallback`/`useMemo` nos params. [ASSUMED]

### Pitfall 5: Filtros de usina não refletem na URL
**O que acontece:** Refresh da página perde os filtros aplicados.
**Por que acontece:** Estado de filtro em `useState` local não persiste na URL.
**Decisão:** CONTEXT.md não exige filtros na URL — estado local em `useState` é suficiente para a fase. Não implementar `useSearchParams` (seria over-engineering).

### Pitfall 6: PATCH usina retorna `200` com o objeto completo
**O que acontece:** Desenvolvedor assume que a resposta do PATCH é apenas os campos enviados.
**Por que acontece:** DRF por padrão retorna o objeto serializado completo no PATCH.
**Como evitar:** Não ignorar a resposta — pode ser usada para atualizar o item na lista sem re-fetch completo (otimização opcional mas boa prática).

### Pitfall 7: Data input `type="date"` retorna string no formato `YYYY-MM-DD`
**O que acontece:** API espera `data_inicio` em `YYYY-MM-DD` — o input HTML date já entrega neste formato.
**Por que acontece:** Sem conversão necessária — mas `new Date(value)` sem sufixo de hora pode dar dia errado.
**Como evitar:** Enviar o valor do input diretamente para a API sem processar. Para o preview de `data_fim`, usar `new Date(value + 'T00:00:00')`.

---

## Router: Adições Necessárias ao App.tsx

O `App.tsx` atual precisa de duas mudanças:

1. **Nova rota de detalhe de usina:**
```typescript
// Adicionar dentro de children do ProtectedLayout:
{ path: 'usinas/:id', element: <UsinaDetalhePage /> }
```

2. **ROUTE_TITLES atualização** (para o breadcrumb):
```typescript
const ROUTE_TITLES: Record<string, string> = {
  '/': 'Dashboard',
  '/dashboard': 'Dashboard',
  '/usinas': 'Usinas',
  '/garantias': 'Garantias',
  '/alertas': 'Alertas',
  // '/usinas/:id' não cabe aqui — breadcrumb dinâmico tratado na UsinaDetalhePage
}
```

[VERIFIED: App.tsx lido — rota `/usinas/:id` ausente confirmada]

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Node.js / npm | Instalar shadcn components | ✓ | (WSL env) | — |
| shadcn CLI | `npx shadcn@latest add` | ✓ | 4.2.0 | — |
| Vite dev server proxy | `/api` → backend em dev | ✓ | Configurado em vite.config.ts | — |
| Backend API | Consumo de endpoints | [ASSUMED] rodando em localhost:8000 | — | Desenvolver com mocks se necessário |
| date-fns | Cálculo de data_fim | ✗ NÃO instalado | — | `Date` nativo (suficiente) |
| sonner (npm) | Toast notifications | ✗ NÃO instalado | — | Instalado automaticamente com `npx shadcn@latest add sonner` |
| next-themes | Dependência do sonner | ✗ NÃO instalado | — | Instalado automaticamente com sonner |

[VERIFIED: package.json e node_modules verificados]

**Missing dependencies with no fallback:** Nenhum item bloqueia a execução.

**Missing dependencies with fallback:** `sonner` e `next-themes` são instalados automaticamente pelo comando shadcn.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Nenhum instalado no projeto frontend |
| Config file | Nenhum (sem vitest.config.ts, jest.config.*, etc.) |
| Quick run command | N/A — Wave 0 deve instalar framework |
| Full suite command | N/A — Wave 0 deve instalar framework |

**Situação real:** O frontend não tem infraestrutura de testes. Não há arquivos `.test.tsx`, `.spec.tsx`, nem `vitest` ou `jest` no `package.json`. O backend tem `pytest` mas o frontend está sem cobertura.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| FE-06 | Filtros de usina refletem nos dados exibidos | unit (hook) | `vitest run src/hooks/use-usinas.test.ts` | ❌ Wave 0 |
| FE-07 | Detalhe de usina exibe inversores e snapshot | unit (component) | `vitest run src/pages/UsinaDetalhePage.test.tsx` | ❌ Wave 0 |
| FE-08 | Edição salva via API e lista atualiza | integration (manual) | manual — requer API real | — |
| FE-09 | Listagem de garantias exibe status e data_fim | unit (component) | `vitest run src/pages/GarantiasPage.test.tsx` | ❌ Wave 0 |
| FE-10 | Vencimento < 30 dias exibe indicador vermelho | unit (component) | `vitest run src/components/garantias/GarantiasTable.test.tsx` | ❌ Wave 0 |
| FE-11 | Preview data_fim atualiza em tempo real | unit (component) | `vitest run src/components/garantias/GarantiaFormDialog.test.tsx` | ❌ Wave 0 |

### Wave 0 Gaps

- [ ] Instalar framework de testes: `npm install -D vitest @testing-library/react @testing-library/user-event jsdom`
- [ ] Criar `vitest.config.ts` com `environment: 'jsdom'`
- [ ] Criar `src/test/setup.ts` com `@testing-library/jest-dom`
- [ ] `src/hooks/use-usinas.test.ts` — testa fetch, loading, error, refetch
- [ ] `src/components/usinas/StatusGarantiaBadge.test.tsx` — testa 3 variantes de cor
- [ ] `src/components/garantias/GarantiasTable.test.tsx` — testa indicador vermelho para dias_restantes < 30

**Alternativa pragmática:** Dado que Phase 4 (frontend foundation) não entregou testes e este é um painel admin interno, o planner pode optar por priorizar testes dos hooks e da lógica de badge/indicador, deixando testes de integração de formulário como manual. Esta decisão fica a critério do planner.

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Não | Já implementado em Phase 4 — interceptor axios injeta JWT |
| V3 Session Management | Não | Já implementado — refresh token com rotação em api.ts |
| V4 Access Control | Não | ProtectedLayout já redireciona não autenticados |
| V5 Input Validation | Sim — parcial | Campos de formulário: `nome` (text), `capacidade_kwp` (number), `data_inicio` (date), `meses` (number) |
| V6 Cryptography | Não | Nenhuma criptografia no frontend desta fase |

### Validação de inputs nos formulários

Os formulários de edição de usina e de garantia devem validar antes de enviar:

| Campo | Validação mínima | Onde validar |
|-------|-----------------|--------------|
| `nome` | required, não vazio | formulário local com estado de erro |
| `capacidade_kwp` | required, número positivo | formulário local |
| `data_inicio` | required, formato YYYY-MM-DD | input type="date" garante formato |
| `meses` | required, inteiro ≥ 1 | input type="number" min="1" |

A API já valida server-side (`meses: min_value=1`, `data_inicio: DateField`). A validação no frontend é para UX, não para segurança — o backend é a fonte de verdade.

**Não há risco de cross-tenant:** Painel é admin único. Não há filtro de tenant a verificar nesta fase.

---

## Assumptions Log

| # | Claim | Section | Risk se errado |
|---|-------|---------|----------------|
| A1 | `useCallback` com `JSON.stringify(params)` como dependência evita loop infinito | Architecture Patterns | Loop infinito de requests — alternativa: useMemo nos params ou parâmetros primitivos separados |
| A2 | `new Date(value + 'T00:00:00')` corrige problema de timezone no Date parsing | Common Pitfalls | Preview de data_fim pode mostrar dia errado em alguns fusos |
| A3 | Backend está rodando em localhost:8000 em desenvolvimento | Environment Availability | Todas as chamadas de API falham — desenvolver com dados mockados |
| A4 | `ultimo_snapshot` no serializer é o snapshot mais recente por FK `ultimo_snapshot` | API Contracts | Campo pode estar desatualizado se a FK não for atualizada pela coleta |

---

## Open Questions

1. **Breadcrumb dinâmico no detalhe de usina**
   - O que sabemos: `ROUTE_TITLES` em App.tsx é estático e não aceita params dinâmicos.
   - O que está incerto: Como exibir "Usinas > Nome da Usina" no header sem prop drilling ou Context.
   - Recomendação: Planner pode decidir entre (a) não ter breadcrumb de nome na Phase 5 — só exibir "Usinas", ou (b) passar o nome da usina via state do router na navegação. Opção (a) é mais simples e adequada para esta fase.

2. **Filtros de usinas por provedor — valores possíveis**
   - O que sabemos: o filtro aceita `?provedor=<valor>`. O serializer tem campo `provedor` como string livre.
   - O que está incerto: Quais valores de provedor existem no banco em produção (ex: `solis`, `growatt`, etc.).
   - Recomendação: Implementar o select de provedor como campo livre (text input) ou buscar lista de provedores distintos de `/api/usinas/?fields=provedor` — mas essa endpoint não garante distinct. Mais simples: hardcodar os provedores conhecidos (`solis`, `growatt`) ou deixar o filtro como input de texto.

3. **Paginação: client-side ou server-side**
   - O que sabemos: D-01 diz "Paginação no cliente consumindo a API paginada (`?page=N`)". A API retorna `count`, `next`, `previous`, `results`.
   - O que está incerto: "Paginação no cliente" pode significar (a) controlar página com `?page=N` na API, ou (b) carregar tudo e paginar localmente.
   - Recomendação: Interpretar como (a) — controlar `?page=N` via estado local no hook e passar para a API. Mais correto e escalável.

---

## Sources

### Primary (HIGH confidence)
- `/home/micael/firmasolar/frontend/admin/src/` — leitura direta de todos os arquivos fonte
- `/home/micael/firmasolar/backend_monitoramento/api/serializers/usinas.py` — contratos de API verificados
- `/home/micael/firmasolar/backend_monitoramento/api/serializers/garantias.py` — contratos de API verificados
- `/home/micael/firmasolar/backend_monitoramento/api/views/usinas.py` — ViewSet, filtros e actions verificados
- `/home/micael/firmasolar/backend_monitoramento/api/urls.py` — rotas verificadas
- `/home/micael/firmasolar/frontend/admin/components.json` — estilo `radix-nova` verificado
- `/home/micael/firmasolar/frontend/admin/package.json` — dependências verificadas
- dry-runs do shadcn CLI — componentes verificados por execução real

### Secondary (MEDIUM confidence)
- Comportamento do shadcn CLI com estilo `radix-nova` — verificado por execução de dry-run nesta sessão

### Tertiary (LOW confidence)
- Padrão `JSON.stringify(params)` como dependência de useEffect — treinamento, não verificado com docs React nesta sessão

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — package.json e node_modules verificados diretamente
- API contracts: HIGH — serializers e views lidos diretamente do código fonte
- Architecture patterns: MEDIUM — hooks pattern verificado no código existente; JSON.stringify trick é ASSUMED
- Pitfalls: HIGH — maioria verificada no código (rota ausente, toast ausente, ultimo_snapshot nullable)
- shadcn components: HIGH — dry-run executado para cada componente

**Research date:** 2026-04-09
**Valid until:** 2026-05-09 (dependências estáveis; shadcn registry pode mudar antes disso)
