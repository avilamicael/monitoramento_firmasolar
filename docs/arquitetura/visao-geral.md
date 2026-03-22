---
title: Visão Geral da Arquitetura
tipo: arquitetura
tags: [arquitetura, stack, componentes]
---

# Visão Geral da Arquitetura

## Stack Tecnológica

| Camada | Tecnologia | Versão |
|---|---|---|
| Backend | Python / Django | 3.11 / 5.1 |
| Tarefas assíncronas | Celery | 5.4 |
| Broker / Cache | Redis | 7 |
| Banco de dados | PostgreSQL | 16 |
| Visualização | Grafana | 10.4 |
| Servidor web | Gunicorn + WhiteNoise | 23 / 6 |
| Reverse proxy | Nginx | — |
| Containers | Docker Compose | — |

---

## Componentes e Responsabilidades

```
┌─────────────────────────────────────────────────────────────────┐
│                         Internet                                │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTPS
                    ┌───────▼───────┐
                    │     Nginx     │  Reverse proxy + SSL (Let's Encrypt)
                    └───────┬───────┘
                            │ HTTP interno
                    ┌───────▼───────┐
                    │    Grafana    │  Dashboards (porta 3000)
                    └───────┬───────┘
                            │ PostgreSQL direto (rede Docker firmasolar_obs)
┌───────────────────────────▼─────────────────────────────────────┐
│                    Backend Monitoramento                        │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │ Gunicorn │  │  Celery  │  │  Celery  │  │   PostgreSQL  │  │
│  │  (web)   │  │ (worker) │  │  (beat)  │  │    (banco)    │  │
│  └──────────┘  └──────────┘  └──────────┘  └───────────────┘  │
│       │              │             │                │           │
│       └──────────────┴─────────────┴────────────────┘          │
│                              │                                  │
│                      ┌───────▼───────┐                         │
│                      │     Redis     │  Broker + Rate limiting  │
│                      └───────────────┘                         │
└─────────────────────────────────────────────────────────────────┘
                            │ HTTPS
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
  FusionSolar API      Hoymiles API         Solis API
  (Huawei intl.)       (S-Cloud)            (Cloud)
```

---

## Fluxo de Dados

1. **Celery Beat** dispara `disparar_coleta_geral()` a cada 10 minutos
2. **Celery Worker** executa `coletar_dados_provedor()` para cada provedor ativo
3. O **Adaptador** do provedor autentica, consulta e normaliza os dados
4. O **ServicoIngestao** persiste usinas, snapshots, inversores e alertas
5. **Notificações** são enviadas para alertas novos ou escalonados
6. **Grafana** lê diretamente do PostgreSQL para exibir os dashboards

---

## Apps Django

```
backend_monitoramento/
├── provedores/      # Credenciais, criptografia, adaptadores, rate limiting
├── usinas/          # Usinas, inversores e seus snapshots
├── alertas/         # Catálogo de alarmes, supressões, ocorrências
├── coleta/          # Tasks Celery, ingestão, log de coleta
├── notificacoes/    # Email e WhatsApp
└── config/          # Settings, URLs, Celery, WSGI
```

Cada app tem uma única responsabilidade. A comunicação entre apps é feita via ForeignKey e via serviços — nunca lógica de negócio em views.

---

## Rede Docker

Existe uma rede Docker compartilhada chamada `firmasolar_obs` que conecta o container `db` (backend) ao Grafana (frontend). Isso permite que o Grafana acesse o PostgreSQL diretamente sem expor a porta ao host.

```bash
# Criada uma única vez na VPS
docker network create firmasolar_obs
```

O container db do backend se conecta às redes `default` (interna ao compose) e `firmasolar_obs` (compartilhada). O Grafana se conecta apenas à `firmasolar_obs`.

---

## Segurança em Camadas

| Camada | Mecanismo |
|---|---|
| Credenciais dos provedores | Fernet (AES-128 simétrico), chave no `.env` |
| Tokens de sessão | Criptografados com a mesma chave Fernet |
| Comunicação externa | HTTPS (Let's Encrypt) |
| Django Admin | Acessível apenas via SSH tunnel (não exposto ao nginx) |
| Banco de dados | Não exposto fora da rede Docker |
| Redis | Não exposto fora da rede Docker |

---

## Veja Também

- [[arquitetura/fluxo-de-coleta]]
- [[arquitetura/decisoes]]
- [[infraestrutura/docker]]
- [[modulos/provedores]]
