# Phase 4: Frontend Foundation - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Entregar o frontend React funcionando com autenticação JWT, roteamento protegido e layout base — pronto para receber páginas de conteúdo nas Phases 5 e 6.

**IMPORTANTE — Setup já feito pelo usuário:**
O projeto React + Vite + TypeScript já foi criado manualmente em `frontend/admin/` (NÃO `frontend/painel/` como o roadmap originalmente previa). O shadcn/ui está configurado com:
- Template `sidebar-07` (sidebar com nav-main, nav-projects, nav-user, team-switcher)
- Template `login-01` (formulário de login com email/senha)
- Componentes UI base: button, card, input, label, dropdown-menu, avatar, skeleton, tooltip, breadcrumb, separator, collapsible, sheet, sidebar, field

**O que esta fase DEVE entregar (não incluído no setup):**
- Instalar react-router-dom e axios
- Configurar roteamento com rotas protegidas (rota pública `/login`, demais exigem token)
- Wiring do login-form com a API JWT (`POST /api/auth/token/`)
- Cliente HTTP (axios) com interceptor de refresh automático
- AuthContext para gerenciar estado de autenticação
- Adaptar sidebar-07 com links reais (Dashboard, Usinas, Garantias, Alertas)
- Header com nome do usuário autenticado
- Proxy Vite para dev (`/api` → `http://localhost:8000`)
- Variável `VITE_API_URL` para prod

**Fora do escopo:** páginas de conteúdo (usinas, alertas, dashboard) → Phases 5 e 6.

</domain>

<decisions>
## Implementation Decisions

### D-01: Pasta do projeto — `frontend/admin/`

O projeto React está em `frontend/admin/`, não em `frontend/painel/` como o roadmap previa. Esta é a localização definitiva — todos os planos devem usar este caminho.

### D-02: Token storage — localStorage

Tokens JWT (access e refresh) armazenados em `localStorage`:
- `localStorage.setItem('access_token', token)`
- `localStorage.setItem('refresh_token', token)`

Justificativa: painel admin-only, single user, conveniência de sobreviver ao fechamento de tab.

### D-03: HTTP client — axios com interceptors

Usar `axios` como cliente HTTP. Criar instância configurada em `src/lib/api.ts`:
- `baseURL` via `import.meta.env.VITE_API_URL || ''`
- Request interceptor: injeta `Authorization: Bearer {access_token}` em todas as requisições
- Response interceptor: em 401, tenta refresh via `POST /api/auth/token/refresh/`; se refresh falhar, faz logout e redireciona para `/login`
- A requisição original que recebeu 401 é repetida automaticamente após refresh bem-sucedido

### D-04: Auth state — React Context

Criar `AuthContext` + `AuthProvider` em `src/contexts/auth.tsx`:
- Estado: `{ user: { email, name } | null, isAuthenticated: boolean, isLoading: boolean }`
- Actions: `login(email, password)`, `logout()`, `refreshToken()`
- No mount: verificar se há token no localStorage e validar com uma chamada leve (ou decodificar JWT para checar expiração)
- Expor via `useAuth()` hook

### D-05: Sidebar — adaptar template sidebar-07

O template shadcn sidebar-07 já está instalado com dados de exemplo. Adaptar:
- Remover `TeamSwitcher` (não há múltiplos times — admin único)
- Substituir `navMain` com: Dashboard (`/`), Usinas (`/usinas`), Garantias (`/garantias`), Alertas (`/alertas`)
- Remover `NavProjects` (não aplicável)
- `NavUser` deve mostrar o nome/email do usuário autenticado via `useAuth()`
- Ícones Lucide: `LayoutDashboard`, `Zap`, `Shield`, `Bell`

### D-06: Roteamento — react-router-dom v7

Estrutura de rotas:
- `/login` — rota pública (LoginPage)
- `/` — redirect para `/dashboard` ou página inicial
- `/dashboard`, `/usinas`, `/garantias`, `/alertas` — rotas protegidas (requerem token)
- Componente `ProtectedRoute` que verifica `isAuthenticated` e redireciona para `/login`
- Layout com sidebar aplicado apenas nas rotas protegidas

### D-07: Proxy Vite para desenvolvimento

Em `vite.config.ts`, adicionar:
```ts
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
}
```

Para produção: variável `VITE_API_URL` aponta para `https://monitoramento.firmasolar.com.br`.

### D-08: Login form — adaptar template login-01

O template shadcn login-01 já está instalado. Adaptar:
- Remover "Forgot your password?" link (admin único, reset via Django Admin)
- Remover "Login with Google" button (não aplicável)
- Remover "Don't have an account? Sign up" (admin único)
- Conectar form ao `useAuth().login(email, password)`
- Mostrar erro de validação quando credenciais falham
- Redirecionar para `/` após login bem-sucedido

### Claude's Discretion

- Estrutura de pastas dentro de `src/` (pages, contexts, lib, hooks) — planner decide
- Se usar lazy loading nas rotas ou importação direta — planner decide
- Componente de loading/spinner durante verificação de token — planner decide
- Se extrair o header como componente separado ou manter inline no layout — planner decide

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Setup existente (ler para entender o que já existe)
- `frontend/admin/package.json` — dependências instaladas
- `frontend/admin/src/App.tsx` — template padrão do Vite (será substituído)
- `frontend/admin/src/components/app-sidebar.tsx` — sidebar-07 template com dados de exemplo
- `frontend/admin/src/components/login-form.tsx` — login-01 template
- `frontend/admin/src/components/nav-main.tsx` — navegação principal
- `frontend/admin/src/components/nav-user.tsx` — seção do usuário na sidebar
- `frontend/admin/vite.config.ts` — config atual do Vite (já tem Tailwind + alias)
- `frontend/admin/src/index.css` — tema shadcn/ui configurado

### Backend API (endpoints que o frontend consome)
- `backend_monitoramento/api/urls.py` — todas as rotas disponíveis
- `backend_monitoramento/config/settings/base.py` — CORS config, JWT lifetimes

### Roadmap e Requisitos
- `.planning/ROADMAP.md` — Phase 4 scope e success criteria
- `.planning/REQUIREMENTS.md` — FE-01..05

### Decisões de fases anteriores
- `.planning/phases/02-rest-endpoints/02-CONTEXT.md` — padrões de API que o frontend consome
- `.planning/phases/03-analytics-endpoints/03-CONTEXT.md` — endpoints de analytics

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `login-form.tsx` — formulário de login pronto, precisa apenas de wiring com auth
- `app-sidebar.tsx` — sidebar completa, precisa substituir dados de exemplo
- `nav-user.tsx` — dropdown do usuário, precisa conectar com auth context
- `nav-main.tsx` — navegação principal, precisa atualizar itens
- Componentes UI shadcn: Button, Card, Input, Label, DropdownMenu, Avatar, etc.
- `src/lib/utils.ts` — helper `cn()` para classes condicionais
- `src/hooks/use-mobile.ts` — hook para detectar mobile

### Established Patterns
- shadcn/ui com Radix + Tailwind CSS 4
- Alias `@/` configurado para `src/`
- Lucide React para ícones

### Integration Points
- `App.tsx` — ponto de entrada principal (substituir template por router)
- `main.tsx` — wrap com providers (AuthProvider, BrowserRouter)
- `vite.config.ts` — adicionar proxy `/api`

</code_context>

<specifics>
## Specific Ideas

- O login é email/senha contra `POST /api/auth/token/` (JWT simplejwt)
- Access token expira em 15 min, refresh em 7 dias com rotação (configurado na Phase 1)
- CORS está configurado no backend para aceitar localhost em dev
- O sidebar deve ter exatamente 4 destinos: Dashboard, Usinas, Garantias, Alertas
- Não há gestão de múltiplos usuários — é um admin único

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-frontend-foundation*
*Context gathered: 2026-04-09*
