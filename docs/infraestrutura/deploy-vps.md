---
title: Infraestrutura — Deploy na VPS
tipo: infraestrutura
tags: [deploy, vps, aws, ubuntu, producao]
---

# Deploy na VPS

## Especificações da VPS

| Campo | Valor |
|---|---|
| Provider | AWS (EC2) |
| OS | Ubuntu 24.04 LTS |
| Hostname | `monitoramento.firmasolar.com.br` |
| Usuário SSH | `ubuntu` |
| Chave SSH | `monitoramento_firmasolar.pem` |
| Disco | 30 GB |
| Diretório do projeto | `~/monitoramento_firmasolar/` |

---

## Acesso SSH

```bash
# Conexão direta
ssh -i ~/Documents/monitoramento_firmasolar.pem ubuntu@monitoramento.firmasolar.com.br

# SSH tunnel para Django Admin
ssh -i ~/Documents/monitoramento_firmasolar.pem \
    -L 8001:127.0.0.1:8000 \
    ubuntu@monitoramento.firmasolar.com.br
# Depois acesse: http://localhost:8001/admin
```

**No WSL:** a chave `.pem` fica em `/mnt/c/Users/Usuario/Documents/`. Copiar para `~/.ssh/` e ajustar permissões:
```bash
cp /mnt/c/Users/Usuario/Documents/monitoramento_firmasolar.pem ~/.ssh/
chmod 600 ~/.ssh/monitoramento_firmasolar.pem
```

---

## Acessos da Aplicação

| Interface | URL | Usuário |
|---|---|---|
| Grafana | https://monitoramento.firmasolar.com.br | `admin` |
| Django Admin | SSH tunnel → `http://localhost:8001/admin` | `admin` |

---

## Estrutura de Arquivos na VPS

```
~/monitoramento_firmasolar/
├── backend_monitoramento/
│   ├── .env                  ← NÃO versionado
│   ├── docker-compose.yml
│   └── ...
├── frontend/
│   ├── .env                  ← NÃO versionado
│   ├── docker-compose.yml
│   └── ...
└── data/
    ├── postgres/             ← volume Docker (não versionado)
    └── redis/                ← volume Docker (não versionado)
```

---

## Processo de Deploy Inicial

### 1. Instalar Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu
# Fazer logout e login novamente para o grupo ter efeito
```

### 2. Clonar o Repositório

```bash
git clone https://github.com/avilamicael/monitoramento_firmasolar.git
cd monitoramento_firmasolar
```

### 3. Criar Rede Docker

```bash
sudo docker network create firmasolar_obs
```

### 4. Criar Diretórios de Dados

```bash
mkdir -p data/postgres data/redis
```

### 5. Criar Arquivo .env do Backend

```bash
cat > backend_monitoramento/.env << 'EOF'
DJANGO_SECRET_KEY=<gerar com python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())">
DEBUG=false
ALLOWED_HOSTS=monitoramento.firmasolar.com.br,localhost

DB_NOME=monitoramento
DB_USUARIO=solar
DB_SENHA=<senha forte>
DB_HOST=localhost
DB_PORTA=5432

REDIS_URL=redis://redis:6379/0

CHAVE_CRIPTOGRAFIA=<gerar com python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">
EOF
```

### 6. Criar Arquivo .env do Frontend

```bash
cat > frontend/.env << 'EOF'
GF_ADMIN_USER=admin
GF_ADMIN_PASSWORD=<senha forte>

DB_NOME=monitoramento
DB_USUARIO=solar
DB_SENHA=<mesma senha do backend>
EOF
```

### 7. Build e Start do Backend

```bash
cd backend_monitoramento
sudo docker compose build
sudo docker compose up -d
```

### 8. Start do Frontend

```bash
cd ../frontend
sudo docker compose up -d
```

### 9. Configurar Credenciais dos Provedores

```bash
cd ../backend_monitoramento

# FusionSolar (tem management command dedicado)
sudo docker compose exec web python manage.py fusionsolar_credenciais \
    --usuario api_firmasolar --system-code "senha" --testar

# Hoymiles e Solis (via shell)
sudo docker compose exec web python manage.py shell
```

```python
from provedores.cripto import criptografar_credenciais
from provedores.models import CredencialProvedor

CredencialProvedor.objects.create(
    provedor='hoymiles',
    credenciais_enc=criptografar_credenciais({'username': '...', 'password': '...'}),
    ativo=True
)

CredencialProvedor.objects.create(
    provedor='solis',
    credenciais_enc=criptografar_credenciais({'api_key': '...', 'app_secret': '...'}),
    ativo=True
)
```

### 10. Criar Superusuário Django

```bash
sudo docker compose exec web python manage.py createsuperuser \
    --username admin --email admin@firmasolar.com.br
```

---

## Processo de Atualização (Deploy de Novo Código)

```bash
cd ~/monitoramento_firmasolar

# 1. Pull do código novo
git pull origin main

# 2. Rebuild apenas do backend (se mudou código Python)
cd backend_monitoramento
sudo docker compose build web celery beat

# 3. Restart com novo código
sudo docker compose up -d --force-recreate web celery beat

# 4. Grafana não precisa rebuild (usa imagem oficial)
# Reiniciar apenas se mudou configuração de provisioning
cd ../frontend
sudo docker compose restart grafana
```

---

## SSL (Let's Encrypt)

Certificado gerenciado pelo Certbot, válido até **20/06/2026**.

```bash
# Verificar status
sudo certbot certificates

# Renovação automática (Certbot timer já configurado)
sudo certbot renew --dry-run

# Verificar timer
systemctl status certbot.timer
```

---

## Veja Também

- [[infraestrutura/nginx]]
- [[infraestrutura/docker]]
- [[infraestrutura/variaveis-de-ambiente]]
- [[operacional/troubleshooting]]
