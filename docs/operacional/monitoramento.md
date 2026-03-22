---
title: Operacional — Monitoramento do Sistema
tipo: operacional
tags: [monitoramento, operacional, logs, saude]
---

# Monitoramento do Sistema

---

## Dashboard Principal

Acesse **https://monitoramento.firmasolar.com.br** → painel **DEV / Infra**.

O que observar:
- **Sem Coleta Recente**: deve estar em 0. Se > 0, algum provedor parou de coletar
- **Erro de Autenticação**: deve estar em 0. Se > 0, credencial inválida
- **Taxa de Sucesso (24h)**: deve estar acima de 90%
- **Log de Erros Recentes**: indica a causa raiz dos problemas

---

## Verificar Status dos Containers

```bash
ssh -i ~/.ssh/monitoramento_firmasolar.pem ubuntu@monitoramento.firmasolar.com.br

# Status de todos os containers
docker ps

# Status esperado:
# backend_monitoramento-web-1      Up X hours
# backend_monitoramento-celery-1   Up X hours
# backend_monitoramento-beat-1     Up X hours
# backend_monitoramento-db-1       Up X hours (healthy)
# backend_monitoramento-redis-1    Up X hours (healthy)
# frontend-grafana-1               Up X hours
```

---

## Logs em Tempo Real

```bash
cd ~/monitoramento_firmasolar/backend_monitoramento

# Todos os serviços
sudo docker compose logs -f

# Apenas o worker (coletas)
sudo docker compose logs -f celery

# Apenas o beat (agendador)
sudo docker compose logs -f beat

# Filtrar por provedor
sudo docker compose logs -f celery | grep -i fusionsolar
```

---

## Verificar Últimas Coletas

```bash
sudo docker compose exec web python manage.py shell -c "
from coleta.models import LogColeta
logs = LogColeta.objects.select_related('credencial').order_by('-iniciado_em')[:10]
for l in logs:
    print(f'{l.iniciado_em:%d/%m %H:%M} | {l.credencial.provedor:15} | {l.status:10} | usinas={l.usinas_coletadas} | {l.duracao_ms}ms')
" 2>/dev/null
```

---

## Verificar Alertas Ativos

```bash
sudo docker compose exec web python manage.py shell -c "
from alertas.models import Alerta
alertas = Alerta.objects.filter(estado='ativo').select_related('usina').order_by('-nivel', '-inicio')
print(f'{alertas.count()} alerta(s) ativo(s)')
for a in alertas[:10]:
    print(f'  [{a.nivel}] {a.usina.nome} — {a.mensagem[:60]}')
" 2>/dev/null
```

---

## Verificar Backoff de Rate Limit

```bash
sudo docker compose exec web python manage.py shell -c "
import redis
from django.conf import settings
from provedores.models import CredencialProvedor

r = redis.from_url(settings.REDIS_URL, decode_responses=True)
for cred in CredencialProvedor.objects.filter(ativo=True):
    chave = f'coleta:backoff:{cred.id}'
    ttl = r.ttl(chave)
    if ttl > 0:
        print(f'{cred.provedor}: em backoff por {ttl}s')
    else:
        print(f'{cred.provedor}: sem backoff')
" 2>/dev/null
```

---

## Saúde do Disco

```bash
# Ver uso de disco
df -h /

# Ver tamanho dos volumes Docker
du -sh ~/monitoramento_firmasolar/data/postgres/
du -sh ~/monitoramento_firmasolar/data/redis/
```

---

## Verificar SSL

```bash
sudo certbot certificates
# Deve mostrar: VALID: XX days
```

---

## Veja Também

- [[operacional/troubleshooting]]
- [[grafana/dashboards]]
- [[infraestrutura/deploy-vps]]
