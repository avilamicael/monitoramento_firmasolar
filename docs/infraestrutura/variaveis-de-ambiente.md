---
title: Infraestrutura — Variáveis de Ambiente
tipo: infraestrutura
tags: [env, configuracao, segurança]
---

# Variáveis de Ambiente

Todas as variáveis usadas pelo sistema. Os arquivos `.env` **nunca são versionados**.

---

## Backend (`backend_monitoramento/.env`)

### Django

| Variável | Obrigatória | Descrição |
|---|---|---|
| `DJANGO_SECRET_KEY` | ✅ | Chave secreta Django. Gerar com `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DEBUG` | ✅ | `false` em produção, `true` em desenvolvimento |
| `ALLOWED_HOSTS` | ✅ | Hosts permitidos separados por vírgula. Ex: `monitoramento.firmasolar.com.br,localhost` |

### PostgreSQL

| Variável | Padrão | Descrição |
|---|---|---|
| `DB_NOME` | `monitoramento` | Nome do banco |
| `DB_USUARIO` | `solar` | Usuário do banco |
| `DB_SENHA` | — | Senha do banco (**obrigatória**) |
| `DB_HOST` | `localhost` | Host do banco. Em container: sobrescrito para `db` pelo docker-compose |
| `DB_PORTA` | `5432` | Porta do banco |

### Redis / Celery

| Variável | Padrão | Descrição |
|---|---|---|
| `REDIS_URL` | `redis://localhost:6379/0` | URL do Redis. Em container: sobrescrito para `redis://redis:6379/0` |

### Criptografia

| Variável | Obrigatória | Descrição |
|---|---|---|
| `CHAVE_CRIPTOGRAFIA` | ✅ | Chave Fernet para criptografar credenciais dos provedores. Gerar com `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. **Não perder — sem ela as credenciais no banco são ilegíveis.** |

### Notificações — Email

| Variável | Padrão | Descrição |
|---|---|---|
| `EMAIL_HOST` | — | Servidor SMTP. Ex: `smtp.gmail.com` |
| `EMAIL_PORTA` | `587` | Porta SMTP (TLS) |
| `EMAIL_USUARIO` | — | Endereço de email |
| `EMAIL_SENHA` | — | Senha ou app password |
| `NOTIFICACAO_EMAIL_DE` | — | Remetente. Ex: `noreply@firmasolar.com.br` |

### Notificações — WhatsApp

| Variável | Padrão | Descrição |
|---|---|---|
| `WHATSAPP_PROVEDOR` | `meta` | `meta` (Meta Cloud API) ou `evolution` (self-hosted) |
| `WHATSAPP_API_TOKEN` | — | Token da Meta Cloud API |
| `WHATSAPP_PHONE_ID` | — | Phone ID da Meta Cloud API |
| `WHATSAPP_EVOLUTION_URL` | — | URL da instância Evolution API |
| `WHATSAPP_EVOLUTION_TOKEN` | — | Token da Evolution API |
| `WHATSAPP_EVOLUTION_INSTANCIA` | `firma-solar` | Nome da instância Evolution |

---

## Frontend (`frontend/.env`)

| Variável | Padrão | Descrição |
|---|---|---|
| `GF_ADMIN_USER` | `admin` | Usuário admin do Grafana |
| `GF_ADMIN_PASSWORD` | — | Senha admin do Grafana (**obrigatória**) |
| `DB_NOME` | — | Nome do banco (mesmo do backend) |
| `DB_USUARIO` | — | Usuário do banco (mesmo do backend) |
| `DB_SENHA` | — | Senha do banco (mesmo do backend) |

---

## Variáveis Injetadas pelo docker-compose

Estas variáveis **não precisam** estar no `.env` — o docker-compose as injeta automaticamente:

| Serviço | Variável | Valor injetado |
|---|---|---|
| web, celery, beat | `DB_HOST` | `db` (nome do serviço) |
| web, celery, beat | `REDIS_URL` | `redis://redis:6379/0` |
| grafana | `DB_HOST` | `backend_monitoramento-db-1` |
| grafana | `DB_PORT` | `5432` |

---

## Como Gerar Valores Seguros

```bash
# Django SECRET_KEY
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Fernet key (CHAVE_CRIPTOGRAFIA)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Senha aleatória segura
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## Veja Também

- [[infraestrutura/deploy-vps]]
- [[infraestrutura/docker]]
- [[modulos/provedores#Criptografia]]
