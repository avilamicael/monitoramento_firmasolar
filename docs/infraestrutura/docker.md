---
title: Infraestrutura — Docker
tipo: infraestrutura
tags: [docker, compose, containers]
---

# Docker

O sistema é composto por dois `docker-compose.yml` independentes que compartilham uma rede Docker externa.

---

## Estrutura de Containers

```
backend_monitoramento/
├── db          postgres:16-alpine     banco de dados
├── redis       redis:7-alpine         broker + rate limiting
├── web         build local            Django + Gunicorn
├── celery      build local            Celery Worker
└── beat        build local            Celery Beat

frontend/
└── grafana     grafana/grafana:10.4.0 dashboards
```

---

## Rede Compartilhada

```bash
# Criada uma única vez
docker network create firmasolar_obs
```

O container `db` (backend) e o `grafana` (frontend) se conectam a esta rede, permitindo que o Grafana acesse o PostgreSQL pelo hostname `backend_monitoramento-db-1` sem expor a porta ao host.

```yaml
# backend_monitoramento/docker-compose.yml
db:
  networks:
    - default        # rede interna do compose
    - firmasolar_obs # compartilhada com Grafana

# frontend/docker-compose.yml
grafana:
  networks:
    - firmasolar_obs
```

---

## Dockerfile (backend)

```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod

WORKDIR /app

COPY requirements/base.txt requirements/base.txt
RUN pip install --no-cache-dir -r requirements/base.txt

COPY . .
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
```

### entrypoint.sh

```bash
#!/bin/sh
set -e

echo "Rodando migrations..."
python manage.py migrate --noinput

echo "Coletando arquivos estáticos..."
python manage.py collectstatic --noinput --clear

exec "$@"
```

O entrypoint roda migrations e collectstatic a cada start. O `exec "$@"` passa o comando do `docker-compose.yml` (gunicorn, celery, etc.).

---

## docker-compose.yml (backend)

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: ${DB_NOME}
      POSTGRES_USER: ${DB_USUARIO}
      POSTGRES_PASSWORD: ${DB_SENHA}
    volumes:
      - ../data/postgres:/var/lib/postgresql/data
    healthcheck:
      test: pg_isready -U ${DB_USUARIO} -d ${DB_NOME}
    networks: [default, firmasolar_obs]
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - ../data/redis:/data
    healthcheck:
      test: redis-cli ping
    restart: unless-stopped

  web:
    build: .
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 60
    ports:
      - "127.0.0.1:8000:8000"    # apenas localhost
    env_file: .env
    environment:
      - DB_HOST=db
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      db: {condition: service_healthy}
      redis: {condition: service_healthy}
    restart: unless-stopped

  celery:
    build: .
    command: celery -A config worker -l info --concurrency 2
    env_file: .env
    environment:
      - DB_HOST=db
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      db: {condition: service_healthy}
      redis: {condition: service_healthy}
    restart: unless-stopped

  beat:
    build: .
    command: celery -A config beat -l info
    env_file: .env
    environment:
      - DB_HOST=db
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      db: {condition: service_healthy}
      redis: {condition: service_healthy}
    restart: unless-stopped

networks:
  firmasolar_obs:
    external: true
```

---

## docker-compose.yml (frontend)

```yaml
services:
  grafana:
    image: grafana/grafana:10.4.0
    volumes:
      - ./grafana/provisioning:/etc/grafana/provisioning:ro
      - ./grafana/dashboards:/var/lib/grafana/dashboards:ro
      - grafana_data:/var/lib/grafana
    env_file: .env
    environment:
      - GF_SECURITY_ADMIN_USER=${GF_ADMIN_USER:-admin}
      - GF_SECURITY_ADMIN_PASSWORD=${GF_ADMIN_PASSWORD}
      - GF_SERVER_ROOT_URL=https://monitoramento.firmasolar.com.br
      - GF_USERS_ALLOW_SIGN_UP=false
      - GF_ANALYTICS_REPORTING_ENABLED=false
      - GF_SECURITY_DISABLE_GRAVATAR=true
      - DB_HOST=backend_monitoramento-db-1
      - DB_PORT=5432
      - DB_NOME=${DB_NOME}
      - DB_USUARIO=${DB_USUARIO}
      - DB_SENHA=${DB_SENHA}
    ports:
      - "127.0.0.1:3000:3000"    # apenas localhost
    networks: [firmasolar_obs]
    restart: unless-stopped

volumes:
  grafana_data:

networks:
  firmasolar_obs:
    external: true
```

---

## Volumes de Dados

```
monitoramento_firmasolar/
└── data/
    ├── postgres/    ← dados do PostgreSQL
    └── redis/       ← dados do Redis (persistência do Beat schedule)
```

Estes diretórios **não são versionados** (`.gitignore`). Na VPS ficam em `~/monitoramento_firmasolar/data/`.

---

## Comandos Úteis

```bash
# Ver status de todos os containers
docker ps

# Logs em tempo real (backend)
cd ~/monitoramento_firmasolar/backend_monitoramento
docker compose logs -f

# Logs de um serviço específico
docker compose logs -f celery

# Restart de um serviço
docker compose restart celery

# Rebuild após mudança de código
docker compose build web
docker compose up -d --force-recreate web

# Executar comando no container web
docker compose exec web python manage.py [comando]

# Shell do Django
docker compose exec web python manage.py shell
```

---

## Veja Também

- [[infraestrutura/deploy-vps]]
- [[infraestrutura/variaveis-de-ambiente]]
