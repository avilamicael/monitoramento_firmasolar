# Requirements: Firma Solar — Painel Administrativo

**Defined:** 2026-04-07
**Core Value:** O administrador deve conseguir ver rapidamente quais usinas estão com problemas e quais estão dentro da garantia, sem precisar acessar ferramentas técnicas como Grafana.

---

## v1 Requirements

### API Base (Infraestrutura REST)

- [ ] **API-01**: Sistema instala e configura djangorestframework com paginação padrão e autenticação JWT como default
- [ ] **API-02**: Endpoint de login retorna access token e refresh token (`POST /api/auth/token/`)
- [ ] **API-03**: Endpoint de refresh emite novo access token sem re-autenticação (`POST /api/auth/token/refresh/`)
- [ ] **API-04**: Todos os endpoints (exceto login/refresh) rejeitam requisições sem token válido com 401
- [ ] **API-05**: CORS configurado para aceitar apenas o domínio do frontend (dev: localhost, prod: domínio real)
- [ ] **API-06**: Access token expira em 15 minutos; refresh token em 7 dias com rotação automática

### Usinas (Gestão)

- [ ] **USN-01**: Administrador lista todas as usinas com filtros por provedor, status ativo e status de garantia
- [ ] **USN-02**: Administrador visualiza detalhe de uma usina (capacidade, provedor, inversores, última coleta)
- [ ] **USN-03**: Administrador atualiza nome e capacidade instalada de uma usina
- [ ] **USN-04**: Listagem de usinas exibe status de garantia de forma visualmente clara (ativa / vencida / sem garantia)
- [ ] **USN-05**: Endpoint retorna histórico temporal de snapshots de uma usina

### Garantia

- [ ] **GAR-01**: Model `GarantiaUsina` criado com campos: usina (FK 1-1), data_inicio, meses, data_fim (calculado), ativa (calculado), observacoes
- [ ] **GAR-02**: Administrador cria ou atualiza garantia de uma usina via `PUT /api/usinas/{id}/garantia/`
- [ ] **GAR-03**: Endpoint lista todas as garantias com filtros: ativas, vencendo em 30 dias, vencidas
- [ ] **GAR-04**: Resposta da garantia inclui dias restantes calculados no momento da requisição
- [ ] **GAR-05**: Usina sem garantia: dados coletados normalmente, sem alertas, não aparece no dashboard de garantia
- [ ] **GAR-06**: Usina com garantia ativa: dados coletados, alertas gerados, aparece no dashboard de garantia

### Inversores

- [ ] **INV-01**: Administrador lista inversores com filtro por usina, provedor e modelo
- [ ] **INV-02**: Administrador visualiza detalhe de inversor com último snapshot (potência, tensão, corrente, temperatura, frequência)
- [ ] **INV-03**: Endpoint retorna histórico de snapshots de um inversor

### Alertas

- [ ] **ALT-01**: Administrador lista alertas com filtros por estado (ativo/reconhecido/resolvido), nível e usina
- [ ] **ALT-02**: Administrador visualiza detalhe de um alerta
- [ ] **ALT-03**: Administrador atualiza estado e anotações de um alerta
- [ ] **ALT-04**: Listagem de alertas indica se a usina está dentro da garantia (campo `com_garantia`)

### Analytics (Dashboard)

- [ ] **ANA-01**: Endpoint retorna potência média geral de todas as usinas e potência média agrupada por fabricante/provedor
- [ ] **ANA-02**: Endpoint retorna top 5 fabricantes por quantidade de inversores ativos (ranking)
- [ ] **ANA-03**: Endpoint retorna todas as usinas com lat/lng, provedor e status para renderização no mapa

### Logs de Coleta

- [ ] **LOG-01**: Administrador visualiza os últimos ciclos de coleta com status (sucesso/falha) e timestamp

### Frontend — Infraestrutura

- [ ] **FE-01**: Projeto React criado com Vite + TypeScript + shadcn/ui configurado
- [ ] **FE-02**: Roteamento configurado (react-router-dom) com rotas protegidas por autenticação
- [ ] **FE-03**: Tela de login com formulário, validação e armazenamento seguro do token
- [ ] **FE-04**: Cliente HTTP configurado com interceptor para refresh automático de token e logout em 401 persistente
- [ ] **FE-05**: Layout base com sidebar de navegação e header com usuário logado

### Frontend — Gestão de Usinas

- [ ] **FE-06**: Listagem de usinas com filtros, paginação e badge de status de garantia
- [ ] **FE-07**: Tela de detalhe de usina com inversores e último snapshot
- [ ] **FE-08**: Formulário de edição de usina (nome, capacidade)

### Frontend — Garantia

- [ ] **FE-09**: Seção `/garantias` com listagem de todas as garantias e seus status
- [ ] **FE-10**: Indicador visual de vencimento próximo (ex: vermelho se < 30 dias)
- [ ] **FE-11**: Formulário de criação/edição de garantia por usina (data início, duração em meses)

### Frontend — Dashboard Analítico

- [ ] **FE-12**: Gráfico de pizza de potência média por fabricante (Recharts)
- [ ] **FE-13**: Tabela de ranking dos top 5 fabricantes por inversores ativos
- [ ] **FE-14**: Mapa interativo de usinas com marcadores (react-leaflet)
- [ ] **FE-15**: Filtro no mapa por fabricante, integrado ao ranking (clicar no ranking filtra o mapa)
- [ ] **FE-16**: Dados do dashboard atualizados via polling a cada 10 minutos

### Frontend — Alertas

- [ ] **FE-17**: Listagem de alertas com filtros e indicação de garantia ativa
- [ ] **FE-18**: Tela de detalhe de alerta com formulário para atualizar estado e anotações

---

## v2 Requirements

### Melhorias futuras (fora do escopo atual)

- **V2-01**: Notificações em tempo real no painel (WebSocket / Server-Sent Events)
- **V2-02**: Gestão de usuários e permissões (multi-usuário com roles)
- **V2-03**: Exportação de relatórios em PDF/CSV
- **V2-04**: Dashboard público para clientes finais (read-only, por usina)
- **V2-05**: App mobile (React Native ou PWA)
- **V2-06**: Gráficos de séries temporais (histórico de potência/temperatura por inversor)

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| WebSocket / push em tempo real | Polling é suficiente para ciclo de 10 min; evita complexidade ASGI |
| Multi-tenancy por cliente final | Painel é admin interno apenas |
| App mobile | Web-first; mobile é v2+ |
| Google Maps | Leaflet foi escolhido (open source, sem custo de API) |
| OAuth / SSO | JWT simples é suficiente para admin interno |
| Gestão de provedores/credenciais via UI | Gerenciado via Django admin existente |
| Histórico de séries temporais no dashboard | Grafana já cobre isso internamente |

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| API-01..06 | Phase 1 | Pending |
| GAR-01 | Phase 1 | Pending |
| USN-01..05 | Phase 2 | Pending |
| GAR-02..06 | Phase 2 | Pending |
| INV-01..03 | Phase 2 | Pending |
| ALT-01..04 | Phase 2 | Pending |
| LOG-01 | Phase 2 | Pending |
| ANA-01..03 | Phase 3 | Pending |
| FE-01..05 | Phase 4 | Pending |
| FE-06..08 | Phase 5 | Pending |
| FE-09..11 | Phase 5 | Pending |
| FE-12..16 | Phase 6 | Pending |
| FE-17..18 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 43 total
- Mapped to phases: 43
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-07*
*Last updated: 2026-04-07 após inicialização*
