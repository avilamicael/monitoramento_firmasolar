# Roadmap: Firma Solar — Painel Administrativo

**Milestone:** 1 — API REST + Frontend Admin
**Goal:** Administrador consegue ver e gerir usinas, garantias e alertas através de painel web próprio, sem depender do Grafana ou Django Admin.
**Created:** 2026-04-07

---

## Phases

- [x] **Phase 1: API Infrastructure** — DRF + JWT + CORS + GarantiaUsina model: fundação que todos os endpoints dependem
- [ ] **Phase 2: REST Endpoints** — Endpoints de usinas, inversores, alertas, garantias e logs de coleta
- [ ] **Phase 3: Analytics Endpoints** — Potência média, ranking de fabricantes e dados de mapa
- [ ] **Phase 4: Frontend Foundation** — React + Vite + autenticação JWT + layout base
- [ ] **Phase 5: Usinas & Garantias** — Listagem, detalhe, edição e gestão de garantia
- [ ] **Phase 6: Dashboard & Alertas** — Mapa, gráficos, ranking e gestão de alertas

---

## Phase Details

### Phase 1: API Infrastructure

**Goal:** A API REST está instalada, autenticável e segura — todo endpoint subsequente tem onde ser registrado.

**Depends on:** None

**Requirements:** API-01, API-02, API-03, API-04, API-05, API-06, GAR-01

**Scope:**
- Instalar e configurar `djangorestframework`, `djangorestframework-simplejwt` e `django-cors-headers` no projeto existente
- Definir autenticação JWT como padrão global em `DEFAULT_AUTHENTICATION_CLASSES` e `DEFAULT_PERMISSION_CLASSES`
- Configurar paginação padrão (ex: `PageNumberPagination`, `page_size=20`)
- Criar `backend_monitoramento/api/` como app Django dedicada à camada REST (urls, views, serializers)
- Registrar endpoints de autenticação: `POST /api/auth/token/` e `POST /api/auth/token/refresh/`
- Configurar `ACCESS_TOKEN_LIFETIME = 15 min` e `REFRESH_TOKEN_LIFETIME = 7 dias` com `ROTATE_REFRESH_TOKENS = True`
- Configurar CORS restrito: `CORS_ALLOWED_ORIGINS` lido de variável de ambiente; sem wildcard em prod
- Criar model `GarantiaUsina` com campos: `usina` (OneToOne FK para `Usina`), `data_inicio` (DateField), `meses` (PositiveIntegerField), `data_fim` (property calculada), `ativa` (property calculada), `observacoes` (TextField, blank)
- Gerar e aplicar migration reversível para `GarantiaUsina`
- Escrever testes para: login retorna access+refresh, refresh emite novo token, endpoint protegido rejeita 401 sem token, CORS bloqueia origem não listada

**Out of Scope:**
- Qualquer endpoint de negócio (usinas, inversores, alertas) — isso é Phase 2
- Validação de formato Fernet no startup — tech debt existente, não bloqueia este milestone

**Success Criteria** (o que deve ser VERDADEIRO ao fim desta fase):
1. `POST /api/auth/token/` com credenciais válidas retorna `access` e `refresh` tokens; com credenciais inválidas retorna 401
2. `POST /api/auth/token/refresh/` com refresh válido emite novo access token; token original não é reutilizável (rotação ativa)
3. Qualquer endpoint protegido retorna 401 para requisições sem header `Authorization: Bearer <token>`
4. Access token expira em 15 min; refresh expira em 7 dias (verificável via decode do JWT)
5. Requisição CORS de origem não configurada é bloqueada; origem configurada passa
6. `GarantiaUsina` existe no banco com todos os campos; `data_fim` e `ativa` calculados corretamente

**Plans:** 2 plans

Plans:
- [x] 01-01-PLAN.md — Instalar pacotes, configurar DRF+JWT+CORS, criar app api e model GarantiaUsina
- [x] 01-02-PLAN.md — Testes completos: auth JWT, CORS e GarantiaUsina

---

### Phase 2: REST Endpoints

**Goal:** Todo dado operacional do sistema — usinas, inversores, alertas, garantias e logs — é acessível via API REST autenticada.

**Depends on:** Phase 1

**Requirements:** USN-01, USN-02, USN-03, USN-04, USN-05, GAR-02, GAR-03, GAR-04, GAR-05, GAR-06, INV-01, INV-02, INV-03, ALT-01, ALT-02, ALT-03, ALT-04, LOG-01

**Scope:**
- **Usinas:** `GET /api/usinas/` com filtros por provedor, ativo e status de garantia; `GET /api/usinas/{id}/` com inversores e último snapshot; `PATCH /api/usinas/{id}/` para nome e capacidade; `GET /api/usinas/{id}/snapshots/` para histórico
- **Garantia:** `PUT /api/usinas/{id}/garantia/` para criar ou atualizar; `GET /api/garantias/` com filtros ativas/vencendo-em-30-dias/vencidas; resposta sempre inclui `dias_restantes` calculado no momento da requisição
- **Inversores:** `GET /api/inversores/` com filtros por usina, provedor e modelo; `GET /api/inversores/{id}/` com último snapshot completo (potência, tensão, corrente, temperatura, frequência); `GET /api/inversores/{id}/snapshots/` para histórico
- **Alertas:** `GET /api/alertas/` com filtros por estado, nível e usina; `GET /api/alertas/{id}/`; `PATCH /api/alertas/{id}/` para estado e anotações; campo `com_garantia` em todas as respostas de alerta
- **Logs:** `GET /api/coleta/logs/` retornando últimos ciclos com status e timestamp
- Garantir que `USN-04`: badge de status de garantia aparece na resposta da listagem de usinas (campo calculado `status_garantia`: `ativa` / `vencida` / `sem_garantia`)
- Garantir `GAR-05` e `GAR-06`: garantia não interfere na coleta de dados; apenas determina visibilidade no dashboard de garantia e geração de alertas
- Testes para cada endpoint: listagem, detalhe, filtros, autenticação obrigatória, e casos de borda (usina sem garantia, inversor sem snapshots)

**Out of Scope:**
- Endpoints de analytics (potência média, ranking, mapa) — isso é Phase 3
- Gestão de credenciais de provedores via API — continua no Django Admin

**Success Criteria** (o que deve ser VERDADEIRO ao fim desta fase):
1. Administrador obtém lista de usinas filtrada por provedor e/ou status de garantia em uma única requisição autenticada
2. Detalhe de usina retorna inversores associados e os dados do último snapshot coletado
3. `PUT /api/usinas/{id}/garantia/` cria ou substitui garantia; resposta imediata inclui `data_fim` e `dias_restantes`
4. `GET /api/garantias/?filtro=vencendo` retorna apenas garantias vencendo nos próximos 30 dias, com `dias_restantes` correto
5. `PATCH /api/alertas/{id}/` atualiza estado e anotações; campo `com_garantia` reflete situação real da usina no momento
6. Todos os endpoints retornam 401 sem token válido — sem exceções

**Plans:** 2 plans

Plans:
- [x] 01-01-PLAN.md — Instalar pacotes, configurar DRF+JWT+CORS, criar app api e model GarantiaUsina
- [ ] 01-02-PLAN.md — Testes completos: auth JWT, CORS e GarantiaUsina

---

### Phase 3: Analytics Endpoints

**Goal:** Os dados agregados para o dashboard analítico estão disponíveis via API — potência, ranking de fabricantes e coordenadas das usinas.

**Depends on:** Phase 2

**Requirements:** ANA-01, ANA-02, ANA-03

**Scope:**
- `GET /api/analytics/potencia/` retorna potência média geral de todas as usinas + potência média agrupada por provedor/fabricante, calculada sobre o snapshot mais recente de cada inversor
- `GET /api/analytics/ranking-fabricantes/` retorna top 5 provedores por quantidade de inversores ativos (com potência > 0 no último snapshot)
- `GET /api/analytics/mapa/` retorna todas as usinas com `lat`, `lng`, `provedor` e `status` (ativo/alerta) para renderização de marcadores
- Todos os endpoints protegidos por JWT
- Queries com `select_related` e `annotate` para evitar N+1; sem queries em loop
- Testes: valores agregados corretos, comportamento com usinas sem snapshot, retorno vazio quando não há dados

**Out of Scope:**
- Séries temporais de potência/temperatura (V2-06)
- Filtros avançados no endpoint de mapa (a filtragem será feita no frontend com os dados recebidos)

**Success Criteria** (o que deve ser VERDADEIRO ao fim desta fase):
1. `GET /api/analytics/potencia/` retorna potência média por fabricante em uma única chamada, sem N+1 no banco
2. `GET /api/analytics/ranking-fabricantes/` retorna exatamente os top 5, ordenados por contagem de inversores ativos
3. `GET /api/analytics/mapa/` retorna todas as usinas com coordenadas válidas; usinas sem `lat`/`lng` aparecem com campos nulos (não omitidas)
4. Os três endpoints rejeitam requisições sem token com 401

**Plans:** 2 plans

Plans:
- [x] 03-01-PLAN.md — Migration lat/lng, serializer de mapa, fixtures e testes RED (ANA-01/02/03)
- [x] 03-02-PLAN.md — Views de analytics (potencia, ranking, mapa) + URLs + testes GREEN

---

### Phase 4: Frontend Foundation

**Goal:** O projeto React está funcionando com autenticação JWT, roteamento protegido e layout base — pronto para receber qualquer página de conteúdo.

**Depends on:** Phase 3

**Requirements:** FE-01, FE-02, FE-03, FE-04, FE-05

**Scope:**
- Projeto React + Vite + TypeScript já existe em `frontend/admin/` com shadcn/ui configurado
- Instalar react-router e axios; configurar proxy Vite para dev
- Configurar react-router com rotas protegidas: rota pública `/login`, demais rotas exigem token válido
- Tela de login: formulário email/senha conectado à API JWT, validação, feedback de erro, armazenamento em localStorage
- Cliente HTTP (axios) com interceptor que injeta Bearer, faz refresh automático em 401, logout em 401 persistente
- AuthContext para gerenciar estado de autenticação (user, isAuthenticated, isLoading, login, logout)
- Layout base com sidebar adaptada (Dashboard, Usinas, Garantias, Alertas) e header com nome do usuário logado
- Configuração de proxy Vite para dev (`/api` → `http://localhost:8000`) e variável `VITE_API_URL` para prod

**Out of Scope:**
- Qualquer página de conteúdo (usinas, alertas, dashboard) — isso é Phase 5 e 6
- Gestão de múltiplos usuários — painel é admin único

**Success Criteria** (o que deve ser VERDADEIRO ao fim desta fase):
1. Acessar qualquer rota sem token redireciona para `/login`
2. Login com credenciais válidas redireciona para a rota inicial com layout completo visível
3. Token expirado em uso normal é renovado de forma transparente (usuário não percebe, requisição original é repetida com sucesso)
4. Refresh expirado ou inválido resulta em logout automático e redirecionamento para `/login`
5. Sidebar exibe os quatro destinos de navegação; header exibe nome do usuário autenticado

**Plans:** 2 plans

Plans:
- [x] 04-01-PLAN.md — Instalar deps, criar axios com interceptors, AuthContext, router com rotas protegidas e proxy Vite
- [x] 04-02-PLAN.md — Conectar login-form, sidebar, nav-main e nav-user aos contextos de auth e routing
**UI hint**: yes

---

### Phase 5: Usinas & Garantias

**Goal:** Administrador pode listar, visualizar, editar usinas e gerir garantias inteiramente pelo painel web.

**Depends on:** Phase 4

**Requirements:** FE-06, FE-07, FE-08, FE-09, FE-10, FE-11

**Scope:**
- **Listagem de usinas** (`/usinas`): tabela paginada com filtros por provedor e status; badge colorido de status de garantia (`ativa`, `vencida`, `sem garantia`); link para detalhe
- **Detalhe de usina** (`/usinas/:id`): dados da usina, lista de inversores com último snapshot (potência, tensão, corrente, temperatura, frequência)
- **Edição de usina**: formulário inline ou modal para atualizar nome e capacidade instalada, com feedback de sucesso/erro
- **Seção de garantias** (`/garantias`): listagem de todas as garantias com status, `data_fim` e `dias_restantes`; indicador visual vermelho se `dias_restantes < 30`
- **Formulário de garantia**: modal ou página `/garantias/:id/editar` para criar ou atualizar garantia por usina — campos: data início, duração em meses; `data_fim` calculada e exibida em tempo real no formulário

**Out of Scope:**
- Histórico de snapshots em gráfico (V2-06)
- Excluir usina via UI — operação crítica, continua no Django Admin

**Success Criteria** (o que deve ser VERDADEIRO ao fim desta fase):
1. Administrador filtra usinas por provedor e vê apenas as correspondentes, com badge de garantia correto
2. Detalhe de usina exibe inversores com os valores do último snapshot coletado
3. Edição de nome/capacidade salva via API e a listagem reflete o novo valor sem reload manual da página
4. Garantias vencendo em menos de 30 dias exibem indicador vermelho na listagem
5. Formulário de garantia cria/substitui via `PUT` e a listagem de garantias reflete o estado atualizado

**Plans:** 3 plans

Plans:
- [x] 05-01-PLAN.md — Instalar shadcn components, criar tipos TypeScript, hooks de data fetching e StatusGarantiaBadge
- [x] 05-02-PLAN.md — UsinasPage com tabela filtrada, UsinaDetalhePage com cards e inversores, UsinaEditDialog
- [x] 05-03-PLAN.md — GarantiasPage com tabela e indicador vermelho, GarantiaFormDialog com preview de data_fim
**UI hint**: yes

---

### Phase 6: Dashboard Analítico & Alertas

**Goal:** Administrador visualiza o estado analítico do parque solar (mapa, gráficos, ranking) e consegue gerir alertas diretamente pelo painel.

**Depends on:** Phase 5

**Requirements:** FE-12, FE-13, FE-14, FE-15, FE-16, FE-17, FE-18

**Scope:**
- **Dashboard** (`/`): gráfico de pizza (Recharts) de potência média por fabricante; tabela de ranking top 5 fabricantes por inversores ativos
- **Mapa** (`/` ou `/mapa`): mapa interativo react-leaflet com marcador por usina; cor do marcador reflete status (normal / alerta); clicar no fabricante no ranking filtra os marcadores no mapa para exibir apenas as usinas daquele provedor
- **Polling**: dados do dashboard atualizados automaticamente a cada 10 minutos (alinhado com o ciclo de coleta) usando `setInterval` ou React Query `refetchInterval`; sem WebSocket
- **Listagem de alertas** (`/alertas`): tabela com filtros por estado (ativo/em_atendimento/resolvido), nível e usina; coluna `Com Garantia` exibe status da garantia da usina no alerta
- **Detalhe de alerta** (`/alertas/:id`): dados completos do alerta; formulário para atualizar estado e adicionar anotações via `PATCH`

**Out of Scope:**
- Notificações em tempo real no painel (V2-01)
- Gráficos de séries temporais de potência/temperatura (V2-06)
- Exportação de relatórios (V2-03)

**Success Criteria** (o que deve ser VERDADEIRO ao fim desta fase):
1. Dashboard carrega gráfico de pizza e tabela de ranking com dados reais em menos de 3 segundos em conexão normal
2. Mapa exibe marcador para cada usina com coordenadas; clicar no fabricante no ranking filtra os marcadores para mostrar apenas usinas daquele provedor
3. Dados do dashboard são atualizados automaticamente a cada 10 minutos sem ação do usuário
4. Administrador filtra alertas por estado e visualiza claramente quais têm usina com garantia ativa
5. Atualização de estado e anotação de alerta persiste via API e a listagem reflete o novo estado imediatamente

**Plans:** 2 plans

Plans:
- [ ] 06-01-PLAN.md — Instalar pacotes, tipos TypeScript, hooks com polling, DashboardPage com pizza e ranking
- [ ] 06-02-PLAN.md — Mapa react-leaflet integrado ao ranking, AlertasPage com filtros, AlertaDetalhePage com PATCH
**UI hint**: yes

---

## Milestone Summary

| Phase | Goal | Requirements | Status |
|-------|------|--------------|--------|
| 1 — API Infrastructure | API REST instalada, autenticável e segura | API-01..06, GAR-01 (7 req) | Complete ✓ |
| 2 — REST Endpoints | Dados operacionais acessíveis via API | USN-01..05, GAR-02..06, INV-01..03, ALT-01..04, LOG-01 (18 req) | Not started |
| 3 — Analytics Endpoints | Dados agregados para dashboard disponíveis | ANA-01..03 (3 req) | Not started |
| 4 — Frontend Foundation | React com auth JWT + layout base funcionando | FE-01..05 (5 req) | Not started |
| 5 — Usinas & Garantias | Gestão de usinas e garantias pelo painel | FE-06..11 (6 req) | Not started |
| 6 — Dashboard & Alertas | Dashboard analítico e gestão de alertas | FE-12..18 (7 req) | Not started |

**Total phases:** 6
**Total v1 requirements:** 46
**Mapped:** 46/46 — coverage 100%
**Unmapped:** 0

**End-to-end capability delivered:**
Administrador acessa painel web próprio, autentica com JWT, visualiza usinas e seus status de garantia, edita dados operacionais, acompanha alertas com contexto de garantia, e monitora o parque solar inteiro em um mapa interativo com gráficos analíticos atualizados automaticamente — sem precisar abrir Grafana ou Django Admin.

---

## Build Order Rationale

The backend is a hard prerequisite for the frontend. The six phases enforce this:

1. Phase 1 establishes the auth contract — every subsequent phase depends on JWT being real.
2. Phase 2 delivers the operational data layer — `GarantiaUsina` (created in Phase 1) is consumed here.
3. Phase 3 adds the aggregated layer separately — analytics queries are complex enough to deserve isolation.
4. Phase 4 wires the frontend to the auth contract established in Phase 1.
5. Phase 5 consumes Phase 2 endpoints for CRUD operations.
6. Phase 6 consumes Phase 3 endpoints for the dashboard and Phase 2 for alerts.

Phases 1-3 can be validated independently via API client (e.g., curl or Postman) before any frontend work begins.

---

*Roadmap created: 2026-04-07*
