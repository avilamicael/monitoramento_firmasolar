# Firma Solar — Painel Administrativo

## What This Is

Sistema web de monitoramento e gestão de usinas solares. O backend coleta dados automaticamente de inversores (Solis, Hoymiles, FusionSolar) a cada 10 minutos via Celery e armazena no PostgreSQL. O frontend React dará aos administradores visibilidade analítica e controle operacional sobre as usinas — substituindo o Grafana como interface principal.

## Core Value

O administrador deve conseguir ver rapidamente quais usinas estão com problemas e quais estão dentro da garantia, sem precisar acessar ferramentas técnicas como Grafana.

## Requirements

### Validated

- ✓ Coleta de dados automática a cada 10 min (Celery Beat) — existente
- ✓ Suporte a 3 provedores: Solis, Hoymiles, FusionSolar — existente
- ✓ Alertas com notificação por e-mail e WhatsApp — existente
- ✓ Persistência em PostgreSQL (Usina, Inversor, SnapshotUsina, SnapshotInversor) — existente
- ✓ Supressão inteligente de alertas — existente
- ✓ Criptografia de credenciais dos provedores em repouso (Fernet) — existente
- ✓ API REST com autenticação JWT (DRF + simplejwt + CORS) — Validated in Phase 1
- ✓ Model GarantiaUsina com lógica de vigência por usina — Validated in Phase 1
- ✓ Endpoints REST para usinas, inversores, alertas, garantias e logs — Validated in Phase 2 (72 testes passando)

### Active

- [ ] Endpoints REST para analytics (potência média, ranking, mapa)
- [ ] Dashboard analítico: potência média, ranking de fabricantes, mapa de clientes
- [ ] Gestão de garantia: criar, editar período, visualizar status por usina
- [ ] Frontend React (Vite + shadcn/ui) com roteamento e autenticação JWT
- [ ] Mapa interativo de usinas com filtro por fabricante (react-leaflet)
- [ ] Gráficos analíticos com Recharts
- [ ] Polling de dados no frontend (intervalo alinhado com coleta de 10 min)

### Out of Scope

- WebSocket / push em tempo real — polling é suficiente dado ciclo de 10 min
- App mobile — não previsto neste milestone
- Multi-tenancy por cliente final — painel é para administrador interno
- Google Maps — Leaflet foi escolhido (open source, sem custo)
- Notificações em tempo real no frontend — alertas chegam via WhatsApp/e-mail

## Context

**Arquitetura atual:**
```
Celery Beat (10 min) → Provedores (Solis/Hoymiles/FusionSolar) → PostgreSQL → Grafana
```

**Arquitetura alvo:**
```
[mesmo pipeline de coleta] → PostgreSQL → DRF REST API → React Frontend
```

O backend já existe e funciona em produção em `monitoramento.firmasolar.com.br`. O Django roda via Gunicorn na porta 8000, atrás de reverse proxy. Não há ASGI — o backend é WSGI puro. O Grafana continuará rodando como ferramenta de diagnóstico interno, mas o painel React será a interface principal.

**Pendência no backend antes do frontend:**
- DRF não está instalado
- Nenhum endpoint REST existe (só `/admin/`)
- Sem CORS configurado
- Model GarantiaUsina não existe

## Constraints

- **Tech Stack Backend**: Django 5.1 + DRF + simplejwt + django-cors-headers — não mudar ORM nem framework
- **Tech Stack Frontend**: React + Vite + shadcn/ui + Recharts + react-leaflet — decisão tomada
- **Segurança**: Multi-tenancy implícito: o painel é admin-only; toda query deve filtrar dados corretamente; JWT obrigatório em todos os endpoints exceto login
- **Deploy**: VPS com Docker Compose; não fazer deploy automático — apenas commit+push
- **Migrations**: Reversíveis sempre que possível; GarantiaUsina é nova tabela (sem risco de perda)
- **Backend first**: A API REST deve estar funcional e testada antes de iniciar o frontend

## Key Decisions

| Decisão | Racional | Outcome |
|---------|----------|---------|
| DRF + simplejwt para autenticação | Padrão Django, integração nativa com ORM existente | ✓ Implemented (Phase 1) |
| react-leaflet para mapa | Open source, sem custo, boa integração React | — Pending |
| Recharts para gráficos | Integra nativamente com shadcn/ui | — Pending |
| Polling para atualização de dados | Ciclo de coleta é 10 min; WebSocket seria overkill | — Pending |
| /garantias como rota separada | Separação de concerns; dashboard analítico fica limpo | — Pending |
| WSGI (sem ASGI) | Backend existente é WSGI puro; não há benefício em migrar agora | — Pending |

## Evolution

Este documento evolui a cada transição de fase e marco de milestone.

**Após cada fase** (via `/gsd-transition`):
1. Requisitos invalidados? → Mover para Out of Scope com motivo
2. Requisitos validados? → Mover para Validated com referência da fase
3. Novos requisitos? → Adicionar em Active
4. Decisões a registrar? → Adicionar em Key Decisions
5. "What This Is" ainda preciso? → Atualizar se houver desvio

**Após cada milestone** (via `/gsd-complete-milestone`):
1. Revisão completa de todas as seções
2. Core Value — ainda é a prioridade certa?
3. Auditar Out of Scope — motivos ainda válidos?
4. Atualizar Context com estado atual

---
*Last updated: 2026-04-09 após conclusão da Phase 02 (rest-endpoints) — 72 testes, 18 requisitos entregues*
