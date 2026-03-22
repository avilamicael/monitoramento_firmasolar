---
title: Grafana — Dashboards
tipo: grafana
tags: [grafana, dashboards, paineis]
---

# Dashboards Grafana

Todos os dashboards são provisionados automaticamente a partir de arquivos JSON em `frontend/grafana/dashboards/`. Alterações no JSON são aplicadas após restart do Grafana.

---

## DEV / Infra (`suporte_tecnico.json`)

**UID:** `firma-solar-suporte`
**Refresh:** 30 segundos
**Foco:** Saúde do sistema para o desenvolvedor/infraestrutura

### Painéis

| Painel | Tipo | O que mostra |
|---|---|---|
| Provedores Ativos | Stat | Total de credenciais com `ativo=true` |
| Sem Coleta Recente (>20 min) | Stat | Provedores sem sucesso nos últimos 20 min. Verde=0, Vermelho≥1 |
| Erro de Autenticação | Stat | Credenciais com `precisa_atencao=true` |
| Taxa de Sucesso (24h) | Stat | % de coletas com `status='sucesso'` nas últimas 24h |
| Erros nas Últimas 24h | Stat | Contagem de `erro` + `auth_erro` nas últimas 24h |
| Última Coleta Bem-sucedida | Stat | Timestamp relativo ("há 3 minutos") |
| Status por Provider | Table | Por provedor: credencial, min. desde últ. sucesso, sucessos, falhas, duração média |
| Coletas no Tempo | Timeseries | Sucesso / Erro / Parcial agrupados a cada 15 min |
| Duração das Coletas (ms) | Timeseries | Duração média por provedor ao longo do tempo |
| Log de Erros Recentes | Table | Últimos 50 erros dos últimos 7 dias com mensagem completa |
| Infraestrutura (row) | Row | Placeholder para métricas de VPS (CPU, memória, disco) |

---

## Solar (`solar.json`)

**UID:** `firma-solar-solar`
**Foco:** Produção de energia das usinas

Painéis incluem:
- Potência total atual (kW)
- Energia gerada hoje (kWh)
- Usinas online vs offline
- Histórico de geração
- Ranking de usinas por produção

---

## Alertas (`alertas.json`)

**UID:** `firma-solar-alertas`
**Foco:** Acompanhamento de alertas e problemas

Painéis incluem:
- Alertas ativos por nível (crítico, importante, aviso)
- Histórico de alertas
- Usinas com mais ocorrências

---

## Conexões (`conexoes.json`)

**UID:** `firma-solar-conexoes`
**Foco:** Status de conectividade dos provedores

---

## Datasource

Todos os dashboards usam o datasource `postgres-firmasolar` (PostgreSQL). Ver [[grafana/datasources]].

---

## Como Editar um Dashboard

1. Edite o JSON em `frontend/grafana/dashboards/nome.json`
2. Commit e push para o repositório
3. Na VPS: `git pull` + `docker compose restart grafana`

Ou edite diretamente no Grafana e exporte o JSON (botão "Share" > "Export").

**Atenção:** Edições feitas diretamente na interface do Grafana são **perdidas** ao reiniciar se não forem exportadas para o JSON.

---

## Queries PostgreSQL Mais Usadas

**Status atual por provedor:**
```sql
SELECT
    c.provedor AS "Provider",
    CASE WHEN c.precisa_atencao THEN 'atencao' ELSE 'ok' END AS "Credencial",
    ROUND(EXTRACT(EPOCH FROM (NOW() - MAX(
        CASE WHEN l.status = 'sucesso' THEN l.iniciado_em END
    ))) / 60, 1) AS "Min. desde últ. sucesso",
    COUNT(CASE WHEN l.status = 'sucesso'
               AND l.iniciado_em > NOW() - INTERVAL '24 hours' THEN 1 END) AS "Sucessos 24h"
FROM provedores_credencialprovedor c
LEFT JOIN coleta_logcoleta l ON l.credencial_id = c.id
WHERE c.ativo = true
GROUP BY c.provedor, c.precisa_atencao;
```

**Timeline de coletas:**
```sql
SELECT
    $__timeGroupAlias(l.iniciado_em, '15m'),
    COUNT(CASE WHEN l.status = 'sucesso' THEN 1 END) AS "Sucesso",
    COUNT(CASE WHEN l.status IN ('erro', 'auth_erro') THEN 1 END) AS "Erro"
FROM coleta_logcoleta l
WHERE $__timeFilter(l.iniciado_em)
GROUP BY 1 ORDER BY 1;
```

---

## Veja Também

- [[grafana/datasources]]
- [[modulos/coleta#Model: LogColeta]]
- [[modulos/usinas#Queries Úteis]]
