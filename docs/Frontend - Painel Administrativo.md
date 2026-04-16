---
title: Frontend — Painel Administrativo
tipo: frontend
tags: [frontend, react, vite, shadcn, painel, spa]
updated: 2026-04-15
---

# Frontend — Painel Administrativo

SPA React/Vite/shadcn em `frontend/admin/`. Autenticação via JWT (SimpleJWT). Roteamento via `react-router`.

---

## Rotas

| Path | Componente | Acesso |
|---|---|---|
| `/login` | `LoginPage` | público |
| `/dashboard` | `DashboardPage` | autenticado |
| `/usinas` | `UsinasPage` | autenticado |
| `/usinas/:id` | `UsinaDetalhePage` | autenticado |
| `/garantias` | `GarantiasPage` | autenticado |
| `/alertas` | `AlertasPage` | autenticado |
| `/alertas/:id` | `AlertaDetalhePage` | autenticado |
| `/notificacoes` | `NotificacoesPage` | autenticado |
| `/configuracoes` | `ConfiguracoesPage` | staff |
| `/provedores` | `ProvedoresPage` | staff |
| `/gestao-notificacoes` | `GestaoNotificacoesPage` | staff |

---

## Autenticação (JWT)

- Login via `POST /api/auth/token/` → armazena access/refresh no client.
- Após login e em cada reload, busca `GET /api/auth/me/` para popular o contexto com `id`, `email`, `name`, `is_staff`, etc.
- Access token de 12h, refresh de 90d com rotação (ver [[arquitetura/decisoes#ADR-016]]).
- Refresh automático ao receber 401 em chamada autenticada.

---

## Principais páginas

### `/usinas/:id` — Detalhe da Usina

- Cabeçalho com nome, provedor, capacidade e `status_garantia`.
- **Botão Pausar/Retomar coleta** (`AtivoToggleButton`) — PATCH `/api/usinas/{id}/` com `ativo=false|true`. Não precisa mais do Django admin para reativar usinas pausadas por inatividade.
- **Dialog de edição** — permite ajustar `nome`, `capacidade_kwp` e `tensao_sobretensao_v` (180–280V). O limite é específico por usina porque a tensão nominal varia conforme a região da rede.
- Último snapshot, inversores com grandezas elétricas, alertas abertos/histórico.

### `/alertas` — Listagem de Alertas

- Tabela ordenada por **severidade + data/hora** (crítico → importante → aviso → info).
- Coluna "Data" exibe data + horário.
- Filtros por nível, estado, provedor, origem, categoria.
- Badge `com_garantia` por alerta.
- `categoria_efetiva` exibida: para alertas internos usa `Alerta.categoria`; para alertas do provedor, faz fallback para `catalogo_alarme.tipo`.

### `/provedores` — Gestão de provedores (staff)

- Lista `CredencialProvedor` com provedor, status (ativo, atenção) e intervalo de coleta.
- CRUD completo via API REST (`/api/provedores/`).
- **Form dinâmico por provedor** — consulta `/api/provedores/meta/` e renderiza campos definidos em `provedores/campos.py` (mesma fonte usada pelo Django admin).
- Botão "Forçar coleta" → `POST /api/provedores/{id}/forcar-coleta/`.

### `/configuracoes` — Configuração do Sistema (staff)

- Edita a singleton `ConfiguracaoSistema` via `/api/configuracoes/`.
- Campos:
  - `dias_sem_comunicacao_pausar` (default 60)
  - `meses_garantia_padrao` (default 12)
  - `dias_aviso_garantia_proxima` (default 30)
  - `dias_aviso_garantia_urgente` (default 7)

### `/gestao-notificacoes` — Canais de notificação (staff)

- Três canais: **email**, **WhatsApp** e **webhook** (novo).
- CRUD via `/api/notificacoes-config/`.
- Para cada canal: ativo, destinatários (um por linha ou separados por vírgula) e quais níveis notificar (crítico, importante, aviso, info).
- Webhook faz POST JSON (ver [[modulos/notificacoes#Backend: Webhook]]).

### `/notificacoes` + Sino no header

- Badge do sino mostra contagem de **não lidas** (polling de 60s em `/api/notificacoes/nao-lidas-count/`).
- Clique no sino abre lista curta; clique em uma notificação redireciona para `link` e marca como lida.
- Página `/notificacoes` lista todas, com filtro `?apenas_nao_lidas=true` e bulk "marcar todas como lidas".

---

## Integração com backend

| Endpoint backend | Páginas que usam |
|---|---|
| `/api/auth/token/`, `/api/auth/me/` | Login, contexto |
| `/api/usinas/`, `/api/usinas/{id}/` | Usinas, detalhe |
| `/api/garantias/` | Garantias |
| `/api/alertas/`, `/api/alertas/{id}/` | Alertas |
| `/api/coleta/logs/` | Dashboard |
| `/api/configuracoes/` | Configurações |
| `/api/provedores/`, `/api/provedores/meta/` | Provedores |
| `/api/notificacoes/`, `/api/notificacoes/nao-lidas-count/` | Sino, página |
| `/api/notificacoes-config/` | Gestão de notificações |
| `/api/analytics/...` | Dashboard (gráficos) |

---

## Veja Também

- [[modulos/alertas]]
- [[modulos/notificacoes]]
- [[modulos/usinas]]
- [[modulos/provedores]]
- [[arquitetura/decisoes]]
