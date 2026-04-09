# Phase 04: Frontend Foundation - Research

**Researched:** 2026-04-09
**Domain:** React 19 + Vite 8 + react-router v7 + axios + JWT auth
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Projeto React em `frontend/admin/` (NÃO `frontend/painel/`)
- **D-02:** Token storage — localStorage (`access_token`, `refresh_token`)
- **D-03:** HTTP client — axios com instância em `src/lib/api.ts`; request interceptor injeta Bearer; response interceptor faz refresh em 401 e logout em falha do refresh
- **D-04:** Auth state — `AuthContext` + `AuthProvider` em `src/contexts/auth.tsx`; estado `{ user: { email, name } | null, isAuthenticated: boolean, isLoading: boolean }`; hook `useAuth()`
- **D-05:** Sidebar — adaptar sidebar-07 existente: remover TeamSwitcher, remover NavProjects, 4 destinos (Dashboard `/`, Usinas `/usinas`, Garantias `/garantias`, Alertas `/alertas`), ícones Lucide `LayoutDashboard`/`Zap`/`Shield`/`Bell`
- **D-06:** Roteamento — react-router-dom v7; `/login` pública; `/dashboard`, `/usinas`, `/garantias`, `/alertas` protegidas; `ProtectedRoute` com `Outlet`; layout com sidebar apenas em rotas protegidas
- **D-07:** Proxy Vite — `server.proxy` `/api` → `http://localhost:8000`; variável `VITE_API_URL` para prod
- **D-08:** Login form — adaptar login-01 existente: remover forgot/Google/signup; conectar ao `useAuth().login()`; mostrar erro; redirecionar para `/` após login

### Claude's Discretion

- Estrutura de pastas dentro de `src/` (pages, contexts, lib, hooks)
- Se usar lazy loading nas rotas ou importação direta
- Componente de loading/spinner durante verificação de token
- Se extrair o header como componente separado ou manter inline no layout

### Deferred Ideas (OUT OF SCOPE)

- Nenhum item deferido — discussão ficou dentro do escopo
- Páginas de conteúdo (usinas, alertas, dashboard) — Phase 5 e 6
- Gestão de múltiplos usuários — admin único

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FE-01 | Projeto React criado com Vite + TypeScript + shadcn/ui configurado | Ja entregue; setup existente verificado no package.json |
| FE-02 | Roteamento configurado (react-router) com rotas protegidas por autenticação | Padrão `ProtectedRoute` + `createBrowserRouter` documentado com react-router v7 |
| FE-03 | Tela de login com formulário, validação e armazenamento seguro do token | Template login-01 existente + wiring com AuthContext |
| FE-04 | Cliente HTTP configurado com interceptor para refresh automático e logout em 401 persistente | Padrão axios interceptor com flag `_retry` documentado |
| FE-05 | Layout base com sidebar de navegação e header com usuário logado | Template sidebar-07 existente + adaptação com useAuth() |

</phase_requirements>

---

## Summary

O projeto React em `frontend/admin/` já existe com Vite 8, React 19, TypeScript 6, shadcn/ui (Radix + Nova preset), Tailwind CSS 4 e Lucide React. Os templates `sidebar-07` e `login-01` estão instalados como componentes estáticos. O `App.tsx` atual é o template padrão do Vite (não serve para nada) e precisa ser substituído completamente.

O trabalho desta fase é inteiramente de wiring: instalar dois pacotes (`react-router` e `axios`), criar as abstrações de autenticação (`AuthContext`, instância axios), configurar o roteador, e conectar os templates existentes à lógica real. Nenhum componente UI precisa ser criado do zero — apenas adaptados.

O ponto de atenção crítico é que o CONTEXT.md menciona `react-router-dom v7`, mas em v7 o pacote foi unificado: `react-router` e `react-router-dom` publicam o mesmo código na versão `7.14.0`. A instalação correta é `npm install react-router` (não `react-router-dom`). Ambos funcionam, mas `react-router` é o nome canônico a partir da v7.

**Primary recommendation:** Instalar `react-router@7` e `axios@1`, criar AuthContext com decodificação local do JWT para verificar expiração no mount, e adaptar os templates existentes com o mínimo de modificações necessárias.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| react-router | 7.14.0 | Roteamento SPA com rotas protegidas | Decisão D-06; padrão oficial React Router |
| axios | 1.15.0 | HTTP client com interceptors | Decisão D-03; suporte a interceptors é nativo |

[VERIFIED: npm registry — `npm view react-router version` retornou 7.14.0; `npm view axios version` retornou 1.15.0]

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| jwt-decode | 4.0.0 | Decodificar JWT no cliente para ler expiração | Verificação de token no mount sem chamada de API |

[VERIFIED: npm registry — `npm view jwt-decode version` retornou 4.0.0]

### Já instalados (não reinstalar)

| Library | Versão no package.json | Status |
|---------|----------------------|--------|
| react | ^19.2.4 | Instalado |
| react-dom | ^19.2.4 | Instalado |
| lucide-react | ^1.8.0 | Instalado |
| radix-ui | ^1.4.3 | Instalado |
| tailwindcss | ^4.2.2 | Instalado (via Vite plugin) |
| vite | ^8.0.4 | Instalado |
| typescript | ~6.0.2 | Instalado |

[VERIFIED: `frontend/admin/package.json` lido diretamente]

### Alternativas Consideradas

| Em vez de | Poderia usar | Tradeoff |
|-----------|-------------|----------|
| axios | fetch nativo | fetch não tem interceptors nativos; seria necessário wrapper custom — violaria "Don't Hand-Roll" |
| jwt-decode | chamar `/api/auth/token/verify/` | Adiciona latência de rede no mount; jwt-decode faz decodificação local sem verificação de assinatura (suficiente para checar expiração) |
| react-router v7 | TanStack Router | Decisão D-06 é lockada; não reconsiderar |

**Installation:**
```bash
cd frontend/admin
npm install react-router@7 axios@1 jwt-decode@4
```

---

## Architecture Patterns

### Recommended Project Structure

```
frontend/admin/src/
├── components/          # Componentes UI existentes (shadcn — NÃO modificar estrutura)
│   ├── ui/              # Primitivos shadcn (button, card, input, etc.)
│   ├── app-sidebar.tsx  # Adaptar: remover TeamSwitcher e NavProjects
│   ├── login-form.tsx   # Adaptar: remover forgot/Google/signup, adicionar state
│   ├── nav-main.tsx     # Adaptar: NavLink com active state
│   └── nav-user.tsx     # Adaptar: consumir useAuth()
├── contexts/
│   └── auth.tsx         # AuthContext + AuthProvider + useAuth() hook
├── lib/
│   ├── api.ts           # Instância axios configurada com interceptors
│   └── utils.ts         # cn() helper (já existe — NÃO tocar)
├── hooks/
│   └── use-mobile.ts    # Já existe — NÃO tocar
├── pages/
│   ├── LoginPage.tsx    # Wrapper da LoginForm com layout centrado
│   ├── DashboardPage.tsx # Placeholder — apenas título (Phase 5/6 preenche)
│   ├── UsinasPage.tsx    # Placeholder
│   ├── GarantiasPage.tsx # Placeholder
│   └── AlertasPage.tsx   # Placeholder
├── App.tsx              # SUBSTITUIR: montar RouterProvider
└── main.tsx             # SUBSTITUIR: wrap com AuthProvider
```

### Pattern 1: AuthContext com Decodificação Local de JWT

**O que é:** No mount do AuthProvider, ler `access_token` do localStorage e usar `jwtDecode` para checar expiração sem chamada de rede.

**Quando usar:** Permite verificar autenticação instantaneamente no carregamento da página — evita flash de conteúdo não autenticado e chamada extra de API.

**Importante:** `jwtDecode` não verifica assinatura — apenas decodifica o payload. Para este caso de uso (verificar expiração) é suficiente e correto.

```typescript
// src/contexts/auth.tsx
// Source: padrão estabelecido — jwt-decode 4.x API verificada
import { jwtDecode } from 'jwt-decode'

interface JWTPayload {
  exp: number
  email: string
  // simplejwt inclui estes campos por padrão
}

function isTokenValid(token: string | null): boolean {
  if (!token) return false
  try {
    const { exp } = jwtDecode<JWTPayload>(token)
    return exp * 1000 > Date.now()
  } catch {
    return false
  }
}
```

[ASSUMED: `jwtDecode` de `jwt-decode@4` é named export (não default). API verificada como breaking change do v3 para v4]

### Pattern 2: Axios Interceptor com Refresh e Flag `_retry`

**O que é:** O response interceptor captura 401, tenta refresh uma vez (flag `_retry`), repete a requisição original com novo token. Se refresh falhar, logout e redirect.

**Problema crítico a evitar:** Sem a flag `_retry`, o interceptor entra em loop infinito porque a requisição de refresh em si pode retornar 401.

**Problema de concorrência:** Se múltiplas requisições simultâneas receberem 401, o refresh é chamado múltiplas vezes. A solução canônica usa uma queue (Promise pendente) — mas para este projeto (admin único, baixo volume) a flag `_retry` simples é suficiente.

```typescript
// src/lib/api.ts
// Source: padrão consolidado da comunidade, verificado em múltiplas fontes
import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
})

// Request interceptor: injeta token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor: refresh em 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      try {
        const refresh = localStorage.getItem('refresh_token')
        const { data } = await axios.post('/api/auth/token/refresh/', { refresh })
        localStorage.setItem('access_token', data.access)
        // simplejwt com ROTATE_REFRESH_TOKENS=True devolve novo refresh
        if (data.refresh) {
          localStorage.setItem('refresh_token', data.refresh)
        }
        original.headers.Authorization = `Bearer ${data.access}`
        return api(original)
      } catch {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default api
```

[VERIFIED: backend settings.py confirmado — `ROTATE_REFRESH_TOKENS = True` e `BLACKLIST_AFTER_ROTATION = True`. O endpoint de refresh devolve novo `access` E novo `refresh`]

### Pattern 3: ProtectedRoute com Outlet (react-router v7)

**O que é:** Componente de layout que verifica autenticação e renderiza `<Outlet />` (filhos) se autenticado, ou `<Navigate>` se não.

```typescript
// Inline no arquivo de rotas ou componente separado
import { Navigate, Outlet } from 'react-router'
import { useAuth } from '@/contexts/auth'

function ProtectedLayout() {
  const { isAuthenticated, isLoading } = useAuth()
  if (isLoading) return <LoadingSpinner />
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <AppLayout><Outlet /></AppLayout>
}
```

[CITED: reactrouter.com — padrão de nested routes com Outlet é a abordagem canônica para protected routes em v7]

### Pattern 4: createBrowserRouter com Nested Routes

```typescript
// src/App.tsx
import { createBrowserRouter, RouterProvider } from 'react-router'

const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    element: <ProtectedLayout />,
    children: [
      { path: '/',         element: <DashboardPage /> },
      { path: '/dashboard', element: <DashboardPage /> },
      { path: '/usinas',    element: <UsinasPage /> },
      { path: '/garantias', element: <GarantiasPage /> },
      { path: '/alertas',   element: <AlertasPage /> },
    ],
  },
])

export default function App() {
  return <RouterProvider router={router} />
}
```

[CITED: reactrouter.com — `createBrowserRouter` é a API canônica desde v6.4+, mantida em v7]

### Pattern 5: NavMain com NavLink para Active State

**Problema identificado:** O `nav-main.tsx` atual usa `<a href>` comum e Collapsible (para sub-itens). Para os 4 links desta fase (sem sub-itens), o NavMain deve ser adaptado para usar `NavLink` do react-router, que adiciona automaticamente `data-[active=true]` ou classe `active` baseado na rota atual.

**Abordagem:** Para a sidebar simplificada (4 links sem sub-itens), criar uma versão nova do NavMain sem Collapsible — links diretos com `NavLink`.

[CITED: reactrouter.com/api/components/NavLink — NavLink aplica classe/estilo `active` automaticamente]

### Anti-Patterns a Evitar

- **`useNavigate` dentro do interceptor axios:** O interceptor vive fora do contexto React — `useNavigate` não funciona fora de componentes. Usar `window.location.href = '/login'` no interceptor é a abordagem correta.
- **Verificar token em toda página individualmente:** Centralizar no `ProtectedLayout` — evita duplicação.
- **Axios com `baseURL` absoluta em dev:** Usar `baseURL: ''` + proxy Vite para dev. O proxy reescreve `/api/*` → `http://localhost:8000/api/*`. Em prod, `VITE_API_URL` aponta para `https://monitoramento.firmasolar.com.br`.
- **Importar de `react-router-dom` em v7:** Em v7, o pacote canônico é `react-router`. Ambos `react-router` e `react-router-dom` publicam o mesmo código, mas importar de `react-router` é a prática correta.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Active route highlight na sidebar | Lógica manual com `location.pathname` | `NavLink` do react-router | NavLink aplica classe/atributo active automaticamente, inclusive em sub-rotas |
| Decodificação JWT para expiração | Parser de JWT manual | `jwt-decode@4` | JWT tem edge cases (padding base64url, campos opcionais) |
| Retry de requisições em 401 | Retry logic manual | Padrão `_retry` no interceptor axios | A flag é simples mas cobre o caso sem loop infinito |
| CSS condicional de classes | Concatenação de strings | `cn()` via `@/lib/utils` | Já existe no projeto — usar o que está lá |

**Key insight:** Todo o trabalho visual já existe nos templates shadcn. Resistir à tentação de reescrever componentes — apenas adaptar dados e conectar à lógica.

---

## Common Pitfalls

### Pitfall 1: Flash de conteúdo não autenticado no carregamento

**O que dá errado:** `isAuthenticated` começa como `false`, o router renderiza redirect para `/login`, depois o AuthContext verifica o token e atualiza — o usuário vê um flash de `/login` mesmo estando autenticado.

**Por que acontece:** Estado inicial do Context é `false` antes da verificação assíncrona.

**Como evitar:** Usar o estado `isLoading: true` como estado inicial. O `ProtectedLayout` mostra um spinner enquanto `isLoading === true`, só redireciona quando `isLoading === false && !isAuthenticated`.

**Sinais de alerta:** Flash rápido da tela de login ao recarregar uma rota protegida.

### Pitfall 2: Loop infinito no interceptor de refresh

**O que dá errado:** O interceptor chama `POST /api/auth/token/refresh/`, que retorna 401 (refresh inválido), o interceptor captura esse 401 e tenta refresh novamente — loop infinito.

**Por que acontece:** Sem a flag `_retry`, o interceptor intercepta a própria requisição de refresh.

**Como evitar:** A flag `original._retry = true` garante que a requisição já sofreu uma tentativa de refresh e não tentará novamente.

**Sinais de alerta:** Browser travado, múltiplas requisições para `/api/auth/token/refresh/` no DevTools.

### Pitfall 3: CORS em dev — proxy Vite não configurado

**O que dá errado:** Frontend chama `http://localhost:8000/api/...` diretamente → browser bloqueia por CORS (porta diferente).

**Por que acontece:** O backend CORS está configurado para `http://localhost:5173`, mas se o frontend chamar diretamente a porta 8000, o browser faz uma preflight que falha dependendo do header.

**Como evitar:** Configurar o proxy Vite (D-07). Com o proxy, o frontend chama `/api/...` (mesma origem), o Vite encaminha para `http://localhost:8000/api/...` no servidor — sem CORS porque é server-to-server.

**Sinais de alerta:** Erro `CORS policy: No 'Access-Control-Allow-Origin' header` no console.

### Pitfall 4: ROTATE_REFRESH_TOKENS ignora atualização do refresh no cliente

**O que dá errado:** Backend tem `ROTATE_REFRESH_TOKENS = True` — cada refresh devolve um NOVO `refresh` token. Se o frontend salvar apenas o `access` e ignorar o novo `refresh`, o refresh token original é blacklistado e o próximo refresh falha.

**Por que acontece:** Documentação de simplejwt não é óbvia sobre isso. O refresh novo está na resposta como `data.refresh`.

**Como evitar:** No interceptor, após refresh bem-sucedido, verificar se `data.refresh` existe e salvar em localStorage. O backend já faz isso (confirmado em `settings/base.py`).

**Sinais de alerta:** Logout automático após ~15 minutos (tempo de expiração do access token) apesar de o usuário estar ativo.

### Pitfall 5: NavMain com Collapsible quebra links diretos

**O que dá errado:** O template `nav-main.tsx` usa `Collapsible` para expandir sub-itens. Para links diretos (sem sub-itens), o Collapsible adiciona o chevron desnecessário e o comportamento de expandir confunde.

**Por que acontece:** O template foi feito para menus hierárquicos, não flat.

**Como evitar:** Para os 4 links desta fase (sem sub-itens), reescrever o NavMain com `SidebarMenuButton as={NavLink}` diretamente, sem Collapsible.

---

## Code Examples

### Vite Proxy (D-07)

```typescript
// frontend/admin/vite.config.ts — adicionar bloco server
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

### AuthProvider (D-04)

```typescript
// src/contexts/auth.tsx — estrutura completa
import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { jwtDecode } from 'jwt-decode'
import api from '@/lib/api'

interface User { email: string; name: string }
interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
}
interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true,  // começa true — evita flash
  })

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (token && isTokenValid(token)) {
      const payload = jwtDecode<{ email: string; name?: string }>(token)
      setState({
        user: { email: payload.email, name: payload.name ?? payload.email },
        isAuthenticated: true,
        isLoading: false,
      })
    } else {
      setState({ user: null, isAuthenticated: false, isLoading: false })
    }
  }, [])

  async function login(email: string, password: string) {
    const { data } = await api.post('/api/auth/token/', { username: email, password })
    localStorage.setItem('access_token', data.access)
    localStorage.setItem('refresh_token', data.refresh)
    const payload = jwtDecode<{ email: string; name?: string }>(data.access)
    setState({
      user: { email: payload.email, name: payload.name ?? email },
      isAuthenticated: true,
      isLoading: false,
    })
  }

  function logout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    setState({ user: null, isAuthenticated: false, isLoading: false })
  }

  return <AuthContext.Provider value={{ ...state, login, logout }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth deve ser usado dentro de AuthProvider')
  return ctx
}

function isTokenValid(token: string): boolean {
  try {
    const { exp } = jwtDecode<{ exp: number }>(token)
    return exp * 1000 > Date.now()
  } catch {
    return false
  }
}
```

### main.tsx com AuthProvider

```typescript
// src/main.tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { AuthProvider } from '@/contexts/auth'
import App from './App.tsx'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AuthProvider>
      <App />
    </AuthProvider>
  </StrictMode>,
)
```

**Nota:** RouterProvider fica dentro de App.tsx, fora do AuthProvider. O AuthProvider não depende do router, mas o router precisa do AuthProvider (para ProtectedLayout usar useAuth). A ordem correta é AuthProvider envolvendo App que contém RouterProvider.

### NavMain adaptado para links diretos

```typescript
// src/components/nav-main.tsx — versão para links flat sem sub-itens
import { NavLink } from 'react-router'
import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar'

export function NavMain({ items }: {
  items: { title: string; url: string; icon?: React.ReactNode }[]
}) {
  return (
    <SidebarGroup>
      <SidebarGroupLabel>Navegação</SidebarGroupLabel>
      <SidebarMenu>
        {items.map((item) => (
          <SidebarMenuItem key={item.title}>
            <SidebarMenuButton asChild tooltip={item.title}>
              <NavLink to={item.url} end={item.url === '/'}>
                {item.icon}
                <span>{item.title}</span>
              </NavLink>
            </SidebarMenuButton>
          </SidebarMenuItem>
        ))}
      </SidebarMenu>
    </SidebarGroup>
  )
}
```

**Nota:** `end` prop no NavLink para `/` evita que o link Dashboard fique ativo em todas as rotas (porque `/` é prefixo de tudo).

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `react-router-dom` como pacote separado | `react-router` unifica tudo | v7 (Nov 2024) | Instalar `react-router` — `react-router-dom` re-exporta o mesmo código |
| `jwtDecode` como default export (v3) | `{ jwtDecode }` como named export (v4) | jwt-decode v4.0.0 | Import precisa ser named: `import { jwtDecode } from 'jwt-decode'` |
| `<BrowserRouter>` como component wrapper | `createBrowserRouter` + `RouterProvider` | react-router v6.4+ | Habilita data layer (loaders, actions) — padrão recomendado |

**Deprecated/outdated:**
- `react-router-dom`: ainda funciona em v7 (re-exporta react-router), mas o nome canônico é `react-router`
- Default export `jwtDecode` (v3): quebra silenciosamente — usar named export

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | JWT payload de simplejwt inclui `email` como campo | Code Examples (AuthProvider) | Se o campo tiver nome diferente (ex: `user_email`), `jwtDecode` retorna undefined para `email`. Verificar payload real após login |
| A2 | `jwt-decode@4` usa named export `{ jwtDecode }` | Standard Stack, Code Examples | Se API for diferente, todos os imports de jwtDecode quebram |
| A3 | `name` não existe no JWT payload do simplejwt por padrão | Code Examples | Fallback `payload.name ?? email` cobre este caso — baixo risco |

**A2 é crítico:** O changelog de jwt-decode v4 documenta a mudança de default para named export — verificar antes de codificar.

---

## Open Questions

1. **Campos do JWT payload do simplejwt**
   - O que sabemos: simplejwt inclui `user_id`, `exp`, `iat`, `jti` por padrão. O campo de email depende da configuração de serializer.
   - O que não está claro: `email` está incluído no payload padrão do projeto? Ou apenas `user_id`?
   - Recomendação: Na implementação, fazer um `console.log(jwtDecode(token))` para confirmar os campos antes de assumir `email`. Se apenas `user_id` estiver disponível, usar uma chamada a `/api/auth/user/` ou similar para obter o email — ou ajustar o serializer do simplejwt no backend.

2. **Header com nome do usuário (FE-05)**
   - O que sabemos: `NavUser` mostra nome/email; o componente aceita `{ name, email, avatar }`.
   - O que não está claro: `avatar` não existe — o componente exibe `AvatarFallback` com texto "CN" hardcoded. Deve ser as iniciais do nome real.
   - Recomendação: Adaptar `NavUser` para calcular iniciais do nome e remover a prop `avatar` ou passar string vazia.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | npm install, vite dev | Verificar | — | — |
| npm | Instalar react-router, axios | Implícito (package.json existe) | — | — |
| Django backend em localhost:8000 | Proxy Vite em dev | Depende do ambiente | — | Testar autenticação em prod se backend não estiver local |

**Nota:** O backend precisa estar rodando em `localhost:8000` para testar o fluxo de login em desenvolvimento. O CORS do backend está configurado para `http://localhost:5173` (default Vite) — sem necessidade de alteração.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Nenhum configurado — FE-01..05 são testes manuais/smoke |
| Config file | Nenhum |
| Quick run command | `npm run dev` (verificação visual) |
| Full suite command | N/A |

**Justificativa para ausência de testes automatizados:**

FE-01..05 são requisitos de infraestrutura de frontend que se validam pelo comportamento do browser, não por testes unitários:
- FE-02 (rotas protegidas): verificar que acessar `/usinas` sem token redireciona para `/login`
- FE-03 (login): verificar que login com credenciais válidas redireciona e persiste token
- FE-04 (refresh automático): verificar que token expirado é renovado transparentemente (requer esperar 15 min ou alterar token manualmente)
- FE-05 (sidebar + header): verificar visualmente que sidebar exibe 4 links e header mostra nome do usuário

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | Viável? |
|--------|----------|-----------|-------------------|---------|
| FE-01 | Setup React + shadcn configurado | smoke | `npm run build` compila sem erros | ✅ |
| FE-02 | Rotas protegidas redirecionam | manual | Navegar para `/usinas` sem token | Manual |
| FE-03 | Login wiring funciona | manual | Fazer login com credenciais reais | Manual |
| FE-04 | Refresh automático de token | manual | Forçar 401 com token alterado | Manual |
| FE-05 | Layout sidebar + header visíveis | manual | Verificar após login | Manual |

### Wave 0 Gaps

- Nenhuma infra de testes automatizados necessária para esta fase
- Critério de aceitação: `npm run build` sem erros de TypeScript + verificação manual das 5 success criteria do ROADMAP.md

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | JWT via simplejwt (backend) + localStorage (frontend conforme D-02) |
| V3 Session Management | yes | localStorage com access (15min) + refresh (7d) |
| V4 Access Control | yes | ProtectedRoute — toda rota protegida verifica isAuthenticated |
| V5 Input Validation | yes | Campos de login (email, password) são required; erros de API exibidos ao usuário |
| V6 Cryptography | no | Não há crypto no frontend — tokens são opacos para o cliente |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Token em localStorage (XSS risk) | Information Disclosure | Painel admin-only — risco aceito conforme D-02; mitigar XSS com política de CSP no servidor |
| Refresh token replay | Elevation of Privilege | ROTATE_REFRESH_TOKENS + BLACKLIST_AFTER_ROTATION no backend já cobre |
| Redirect para URL arbitrária após login | Tampering | Redirecionar sempre para `/` ou rota hardcoded, nunca ler URL de query param |
| Exposição de token em logs | Information Disclosure | Nunca logar tokens no console; interceptor não deve logar `Authorization` header |

**Nota sobre XSS e localStorage:** O CONTEXT.md (D-02) registra a decisão de usar localStorage com justificativa explícita (painel admin-only, single user). Esta decisão é lockada — não reconsiderar.

---

## Sources

### Primary (HIGH confidence)
- `frontend/admin/package.json` — versões instaladas verificadas diretamente
- `frontend/admin/vite.config.ts` — config atual lida diretamente
- `frontend/admin/src/components/*.tsx` — templates existentes lidos diretamente
- `backend_monitoramento/config/settings/base.py` — CORS, JWT lifetimes, ROTATE_REFRESH_TOKENS confirmados
- `backend_monitoramento/api/urls.py` — endpoints disponíveis confirmados

### Secondary (MEDIUM confidence)
- [reactrouter.com — Protected Routes](https://reactrouter.com/) — padrão ProtectedRoute + Outlet documentado oficialmente
- [reactrouter.com — NavLink](https://reactrouter.com/api/components/NavLink) — active state automático documentado
- npm registry — versões verificadas: react-router@7.14.0, axios@1.15.0, jwt-decode@4.0.0

### Tertiary (LOW confidence)
- [DEV Community — JWT Refresh com Axios Interceptors](https://dev.to/ayon_ssp/jwt-refresh-with-axios-interceptors-in-react-2bnk) — padrão `_retry` confirmado por múltiplas fontes, mas código específico não verificado via Context7
- [shadcn/ui — Sidebar active state issue](https://github.com/shadcn-ui/ui/issues/9134) — issue de bug de `isActive` padrão identificada, solução documentada

---

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — versões verificadas via npm registry
- Architecture: HIGH — padrões confirmados em docs oficiais + código existente lido
- Pitfalls: MEDIUM — alguns verificados em múltiplas fontes, JWT payload fields é ASSUMED
- Security: HIGH — backend confirmado, decisões lockadas no CONTEXT.md

**Research date:** 2026-04-09
**Valid until:** 2026-05-09 (bibliotecas estáveis; react-router v7 em maturidade)
