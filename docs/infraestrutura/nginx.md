---
title: Infraestrutura — Nginx
tipo: infraestrutura
tags: [nginx, proxy, ssl, https]
---

# Nginx

Atua como reverse proxy HTTPS na frente do Grafana. O Django Admin não é exposto publicamente.

---

## Configuração Atual

**Arquivo:** `/etc/nginx/sites-enabled/monitoramento.firmasolar.com.br`

```nginx
server {
    server_name monitoramento.firmasolar.com.br;

    # Proxy para o Grafana (porta 3000)
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_cache_bypass $http_upgrade;
    }

    # Headers de segurança
    server_tokens off;
    add_header X-Content-Type-Options 'nosniff';
    add_header X-Frame-Options 'SAMEORIGIN';
    add_header Referrer-Policy 'strict-origin-when-cross-origin';

    # SSL (gerenciado pelo Certbot)
    listen [::]:443 ssl ipv6only=on;
    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/monitoramento.firmasolar.com.br/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/monitoramento.firmasolar.com.br/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
}

# Redirect HTTP → HTTPS
server {
    if ($host = monitoramento.firmasolar.com.br) {
        return 301 https://$host$request_uri;
    }
    listen 80;
    listen [::]:80;
    server_name monitoramento.firmasolar.com.br;
    return 404;
}
```

---

## O que está exposto publicamente

| Path | Destino | Observação |
|---|---|---|
| `/*` | Grafana `:3000` | Autenticação do próprio Grafana |

## O que NÃO está exposto

| Serviço | Motivo |
|---|---|
| Django Admin (`:8000`) | Acessível apenas via SSH tunnel |
| PostgreSQL (`:5432`) | Rede Docker interna |
| Redis (`:6379`) | Rede Docker interna |

---

## Comandos Úteis

```bash
# Testar configuração
sudo nginx -t

# Recarregar após mudança
sudo systemctl reload nginx

# Ver logs de acesso
sudo tail -f /var/log/nginx/access.log

# Ver logs de erro
sudo tail -f /var/log/nginx/error.log
```

---

## Adicionar Django Admin ao Nginx (futuro)

Se necessário expor o admin publicamente (ex: para time sem acesso SSH):

```nginx
location /django-admin/ {
    proxy_pass http://127.0.0.1:8000/admin/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    # Restringir por IP se possível:
    # allow 200.100.X.X;
    # deny all;
}
```

Também adicionar ao `ALLOWED_HOSTS` e configurar `CSRF_TRUSTED_ORIGINS` no Django.

---

## Veja Também

- [[infraestrutura/deploy-vps]]
- [[infraestrutura/docker]]
