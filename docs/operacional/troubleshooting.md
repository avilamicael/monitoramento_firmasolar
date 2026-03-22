---
title: Operacional — Troubleshooting
tipo: operacional
tags: [troubleshooting, erros, debug, operacional]
---

# Troubleshooting

---

## Coleta parou de funcionar

**Sintoma:** Painel "Sem Coleta Recente" > 0, logs sem atividade.

**1. Verificar se os containers estão rodando:**
```bash
docker ps | grep backend
```
Se algum estiver parado: `sudo docker compose restart [servico]`

**2. Verificar logs do celery:**
```bash
cd ~/monitoramento_firmasolar/backend_monitoramento
sudo docker compose logs --tail 50 celery
```

**3. Verificar se o Beat está disparando:**
```bash
sudo docker compose logs --tail 20 beat
# Deve mostrar: "Scheduler: Sending due task coletar-todos-provedores"
```

**4. Verificar backoff ativo:**
```bash
sudo docker compose exec web python manage.py shell -c "
import redis
from django.conf import settings
r = redis.from_url(settings.REDIS_URL, decode_responses=True)
chaves = r.keys('coleta:backoff:*')
for c in chaves:
    print(c, r.ttl(c), 's restantes')
"
```
Se houver backoff ativo, aguarde o TTL expirar ou limpe: `r.delete(chave)`

---

## Credencial marcada como `precisa_atencao`

**Sintoma:** Painel "Erro de Autenticação" > 0, coleta do provedor parou.

**Causa:** A API retornou credenciais inválidas (senha mudou, token expirou).

**Solução:**
1. Verificar no portal do provedor se a senha/token foi alterado
2. Atualizar as credenciais → ver [[operacional/credenciais]]
3. O flag é limpo automaticamente na próxima coleta bem-sucedida

---

## FusionSolar: failCode=407 constante

**Sintoma:** Logs com `ProvedorErroRateLimit`, backoff repetido, horas sem coleta.

**Causas possíveis:**
1. Usuário compartilhado entre sistemas → usar usuário dedicado
2. Intervalo `min_intervalo_coleta_segundos` muito baixo

**Verificar:**
```bash
sudo docker compose logs celery | grep -i "407\|rate limit\|backoff"
```

**Solução temporária (aumentar intervalo):**
Em `provedores/fusionsolar/adaptador.py`, linha `min_intervalo_coleta_segundos`:
- 900 (15 min) → padrão com usuário dedicado
- 1800 (30 min) → se ainda houver rate limit
- 2100 (35 min) → se usuário compartilhado

Após alterar: commit, push, pull na VPS, rebuild e restart.

---

## Grafana sem dados / dashboard em branco

**Sintoma:** Dashboards aparecem mas sem dados, ou erro "no data".

**1. Verificar se o datasource está funcionando:**
Grafana → Configuration → Data Sources → PostgreSQL → Test

**2. Verificar se o Grafana consegue conectar ao banco:**
```bash
cd ~/monitoramento_firmasolar/frontend
sudo docker compose logs grafana | grep -i "error\|postgres\|connect"
```

**3. Verificar se a rede compartilhada existe:**
```bash
sudo docker network ls | grep firmasolar_obs
sudo docker network inspect firmasolar_obs
```
O container `backend_monitoramento-db-1` e `frontend-grafana-1` devem aparecer.

---

## Grafana: arquivos estáticos sem carregar (CSS/JS)

**Sintoma:** Interface do Grafana aparece sem estilos.

**Solução:** Verificar se o Grafana está apontando para a URL correta:
```bash
# No docker-compose do frontend, verificar:
GF_SERVER_ROOT_URL=https://monitoramento.firmasolar.com.br
```

---

## Django Admin: arquivos estáticos sem carregar

**Sintoma:** Admin Django sem CSS/JS (interface quebrada).

**Solução:** Garantir que o `collectstatic` rodou:
```bash
sudo docker compose exec web python manage.py collectstatic --noinput --clear
sudo docker compose restart web
```

---

## Container `web` não sobe (migration error)

**Sintoma:** Container sobe e cai, logs com erro de migration.

**Verificar:**
```bash
sudo docker compose logs web | head -30
```

**Se for migration pendente:**
```bash
sudo docker compose exec web python manage.py showmigrations
sudo docker compose exec web python manage.py migrate
```

---

## Redis não conecta

**Sintoma:** Erros de conexão ao Redis nos logs do celery.

**Verificar:**
```bash
sudo docker compose exec redis redis-cli ping
# Deve retornar: PONG
```

Se o container Redis estiver parado:
```bash
sudo docker compose up -d redis
```

---

## Banco de dados cheio (disco)

**Sintoma:** Erros de "no space left" no PostgreSQL.

**Verificar espaço:**
```bash
df -h /
du -sh ~/monitoramento_firmasolar/data/postgres/
```

**Liberar espaço (snapshots antigos):**
```bash
# Limpeza automática roda às 3h, mas pode forçar:
sudo docker compose exec web python manage.py shell -c "
from coleta.tasks import limpar_snapshots_antigos
resultado = limpar_snapshots_antigos()
print(resultado)
"
```

**Vacuum no PostgreSQL:**
```bash
sudo docker compose exec db psql -U solar -d monitoramento -c "VACUUM ANALYZE;"
```

---

## Veja Também

- [[operacional/monitoramento]]
- [[operacional/credenciais]]
- [[infraestrutura/docker]]
