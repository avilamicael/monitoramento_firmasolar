---
title: Firma Solar — Documentação
tipo: index
tags: [index, firma-solar]
---

# Firma Solar — Sistema de Monitoramento Solar

Sistema de monitoramento em tempo real de usinas solares distribuídas. Coleta dados de múltiplos fabricantes, sincroniza alertas, envia notificações e expõe dashboards operacionais via Grafana.

---

## Navegação

### Arquitetura
- [[arquitetura/visao-geral]] — Stack, componentes e responsabilidades
- [[arquitetura/fluxo-de-coleta]] — Fluxo completo desde o Beat até o banco
- [[arquitetura/decisoes]] — Decisões de arquitetura e seus motivos

### Provedores
- [[provedores/fusionsolar]] — Huawei FusionSolar (50 usinas)
- [[provedores/hoymiles]] — Hoymiles S-Cloud (69 usinas)
- [[provedores/solis]] — Solis Cloud (12 usinas)

### Módulos do Sistema
- [[modulos/coleta]] — Tasks Celery, ingestão, rate limiting
- [[modulos/alertas]] — Catálogo, supressão, estados
- [[modulos/notificacoes]] — Email e WhatsApp
- [[modulos/usinas]] — Models de usinas e inversores
- [[modulos/provedores]] — Credenciais, criptografia, registro

### Infraestrutura
- [[infraestrutura/docker]] — Docker Compose, imagens, rede
- [[infraestrutura/deploy-vps]] — Deploy na VPS Ubuntu (AWS)
- [[infraestrutura/nginx]] — Configuração do reverse proxy
- [[infraestrutura/variaveis-de-ambiente]] — Todas as variáveis documentadas

### Grafana
- [[grafana/dashboards]] — Painéis disponíveis e suas queries
- [[grafana/datasources]] — Datasource PostgreSQL

### Operacional
- [[operacional/credenciais]] — Como cadastrar e atualizar credenciais
- [[operacional/monitoramento]] — Como acompanhar o sistema
- [[operacional/troubleshooting]] — Problemas comuns e soluções

---

## Estado Atual

| Item | Valor |
|---|---|
| Provedores ativos | FusionSolar, Hoymiles, Solis |
| Total de usinas | 131 (50 + 69 + 12) |
| Intervalo de coleta | 10 min (Beat) |
| VPS | `monitoramento.firmasolar.com.br` (Ubuntu 24.04, AWS) |
| Grafana | https://monitoramento.firmasolar.com.br |
| Django Admin | SSH tunnel → `http://localhost:8001/admin` |

---

## Repositório

```
monitoramento_firmasolar/
├── backend_monitoramento/   # Django + Celery
├── frontend/                # Grafana
├── data/                    # Volumes Docker (não versionado)
├── docs/                    # Esta documentação
└── CLAUDE.md                # Instruções para o Claude Code
```
