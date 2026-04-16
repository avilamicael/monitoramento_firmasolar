---
title: Grafana — Dashboards
tipo: grafana
tags: [grafana, dashboards, paineis]
updated: 2026-04-15
---

# Dashboards Grafana

Todos os dashboards são provisionados automaticamente a partir de arquivos JSON em `frontend/grafana/dashboards/`. Alterações no JSON são aplicadas após restart do Grafana.

Estrutura em disco:

```
frontend/grafana/dashboards/
├── principal/
│   ├── monitoramento_alertas.json       # UID: alertas-monitoramento
│   └── suporte_tecnico.json             # UID: firma-solar-suporte
└── detalhes/
    ├── detalhe_lista_alertas.json       # UID: lista-alertas
    ├── detalhe_usina.json               # UID: detalhe-usina
    └── detalhe_usinas_afetadas.json     # UID: usinas-afetadas
```

> Todos os dashboards foram alinhados ao schema atual (2026-04-15):
> - Removidas referências a `em_atendimento` (o estado não existe mais — ver [[modulos/alertas]]).
> - Filtradas usinas `u.ativo = true` nas contagens.
> - Usa `COALESCE(NULLIF(a.categoria, ''), ca.tipo, 'sem_categoria')` para categoria efetiva (espelha o `categoria_efetiva` da API).
> - Colunas de duração formatadas com unidade `dtdurations`.
> - KPIs do painel principal atualizados para refletir os 4 níveis: crítico, importante, aviso e info.

---

## Monitoramento de Alertas (`monitoramento_alertas.json`)

**UID:** `alertas-monitoramento`
**Foco:** Acompanhamento de alertas ativos pelo operador.

### KPIs (primeira linha)

| Painel | Query resumida |
|---|---|
| Alertas Abertos | `COUNT(*) WHERE estado='ativo' AND u.ativo=true` |
| Críticos Ativos | `... AND nivel='critico'` |
| Importantes Ativos | `... AND nivel='importante'` |
| Avisos Ativos | `... AND nivel='aviso'` |
| Usinas Afetadas | `COUNT(DISTINCT usina_id)` |
| Resolvidos (últimas 24h) | `... WHERE estado='resolvido' AND fim > NOW() - INTERVAL '24h'` |

Cada KPI tem link clicável para o dashboard `lista-alertas` pré-filtrado.

### Distribuição de alertas abertos

- **Por Categoria** — usa `COALESCE(NULLIF(a.categoria, ''), ca.tipo, 'sem_categoria')` para categoria efetiva. Aceita alertas internos (coluna `categoria`) e do provedor (fallback para `catalogo_alarme.tipo`).
- **Por Nível de Severidade** — ordenado crítico → importante → aviso; `info` é excluído deste agrupamento.
- **Por Provedor** — agrupa por `usina.provedor`.

### Lista de alertas abertos

Tabela detalhada com nível colorido, usina, categoria efetiva, tempo aberto (formato `dtdurations`) e link para a usina. Filtra `u.ativo=true`.

### Histórico (últimos 30 dias)

- Novos alertas por categoria/dia
- Alertas criados vs resolvidos/dia

---

## DEV / Infra (`suporte_tecnico.json`)

**UID:** `firma-solar-suporte`
**Refresh:** 30 segundos
**Foco:** Saúde do sistema para o desenvolvedor/infraestrutura.

| Painel | Tipo | O que mostra |
|---|---|---|
| Provedores Ativos | Stat | Total de `CredencialProvedor` com `ativo=true` |
| Sem Coleta Recente (> 20 min) | Stat | Verde=0, Vermelho≥1 |
| Erro de Autenticação | Stat | Credenciais com `precisa_atencao=true` |
| Taxa de Sucesso (24h) | Stat | % de coletas com `status='sucesso'` |
| Última Coleta Bem-sucedida | Stat | Tempo relativo |
| Status por Provider | Table | Min. desde últ. sucesso, sucessos, falhas, duração média |
| Coletas no Tempo — Sucesso vs Erros | Timeseries | Agrupado a cada 15 min |
| Duração das Coletas (ms) | Timeseries | Média por provedor |
| Log de Erros Recentes | Table | Últimos 50 erros dos últimos 7 dias |
| Infraestrutura / VPS — Em breve | Row/placeholder | Futuras métricas de CPU/memória/disco |

---

## Detalhes (linkados por UID)

### `detalhe-usina` (`detalhe_usina.json`)

Ao clicar em uma usina (de qualquer lista), abre este dashboard com:
- Provedor, Capacidade instalada, Status atual, Alertas abertos
- Potência atual, Energia hoje
- Potência gerada (kW) ao longo do tempo
- Energia acumulada no dia (kWh)
- Alertas da usina (tabela)
- Inversores — status, estado ao longo do tempo
- Análise de geração — geração diária e potência como % da capacidade instalada

### `usinas-afetadas` (`detalhe_usinas_afetadas.json`)

Lista de usinas com pelo menos um alerta aberto. Resumo por usina, link para `detalhe-usina`.

### `lista-alertas` (`detalhe_lista_alertas.json`)

Lista completa de alertas com filtro via `?var-filtro=critico|importante|aviso|...`. Usa `dtdurations` nas colunas de tempo aberto.

---

## Datasource

Todos os dashboards usam o datasource `postgres-firmasolar` (PostgreSQL, acesso via rede Docker `firmasolar_obs`). Ver [[grafana/datasources]].

---

## Como Editar um Dashboard

1. Edite o JSON em `frontend/grafana/dashboards/<pasta>/<nome>.json`.
2. Commit e push para o repositório.
3. Na VPS: `git pull` + `docker compose restart grafana`.

**Atenção:** edições feitas diretamente na interface do Grafana são **perdidas** ao reiniciar se não forem exportadas para o JSON.

---

## Veja Também

- [[grafana/datasources]]
- [[modulos/coleta]]
- [[modulos/alertas]]
- [[modulos/usinas]]
