---
title: Grafana — Datasources
tipo: grafana
tags: [grafana, datasource, postgresql]
---

# Datasources Grafana

## PostgreSQL (`postgres-firmasolar`)

Único datasource configurado. O Grafana acessa o PostgreSQL do backend diretamente via rede Docker `firmasolar_obs`.

**Arquivo:** `frontend/grafana/provisioning/datasources/postgres.yml`

```yaml
apiVersion: 1
datasources:
  - name: PostgreSQL
    uid: postgres-firmasolar
    type: postgres
    url: ${DB_HOST}:5432
    database: ${DB_NOME}
    user: ${DB_USUARIO}
    secureJsonData:
      password: ${DB_SENHA}
    jsonData:
      sslmode: disable
      maxOpenConns: 10
      maxIdleConns: 2
      connMaxLifetime: 14400
      postgresVersion: 1600
      timescaledb: false
```

As variáveis `DB_HOST`, `DB_NOME`, `DB_USUARIO` e `DB_SENHA` são injetadas pelo docker-compose a partir do `frontend/.env`.

### Hostname do banco

O Grafana acessa o banco pelo hostname `backend_monitoramento-db-1`, que é o nome do container Docker do serviço `db` do backend. Isso funciona porque os dois compose files compartilham a rede `firmasolar_obs`.

---

## Provisioning de Dashboards

**Arquivo:** `frontend/grafana/provisioning/dashboards/dashboard.yml`

```yaml
apiVersion: 1
providers:
  - name: firma_solar
    orgId: 1
    folder: Firma Solar
    type: file
    disableDeletion: false
    editable: true
    options:
      path: /var/lib/grafana/dashboards
```

Os arquivos JSON em `frontend/grafana/dashboards/` são mapeados para `/var/lib/grafana/dashboards` no container (volume read-only).

---

## Futuro: Prometheus (VPS)

Quando o Node Exporter for instalado na VPS para monitorar CPU, memória e disco, será necessário:

1. Instalar Prometheus na VPS (ou adicionar ao docker-compose)
2. Adicionar datasource Prometheus ao Grafana:

```yaml
# frontend/grafana/provisioning/datasources/prometheus.yml
datasources:
  - name: Prometheus
    uid: prometheus-firmasolar
    type: prometheus
    url: http://prometheus:9090
```

3. Criar painéis no dashboard DEV/Infra usando o datasource Prometheus

---

## Veja Também

- [[grafana/dashboards]]
- [[infraestrutura/docker]]
