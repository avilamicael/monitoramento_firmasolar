---
title: Fluxo de Coleta
tipo: arquitetura
tags: [coleta, celery, fluxo, ingestao]
---

# Fluxo de Coleta

Descrição detalhada do caminho completo desde o disparo pelo Celery Beat até a persistência no banco.

---

## Visão Macro

```
Celery Beat (10 min)
        │
        ▼
disparar_coleta_geral()
        │
        ├──► coletar_dados_provedor(fusionsolar_id)
        ├──► coletar_dados_provedor(hoymiles_id)
        └──► coletar_dados_provedor(solis_id)
                        │
                        ▼
              [verificações de segurança]
                        │
                        ▼
                  Adaptador HTTP
               (auth + consultas)
                        │
                        ▼
               ServicoIngestao
             (upsert + snapshots)
                        │
                        ▼
               sincronizar_alertas()
                        │
                        ▼
             ServicoNotificacao
           (email / WhatsApp)
```

---

## Etapas Detalhadas de `coletar_dados_provedor()`

### 1. Carregamento de Credenciais

```python
credencial = CredencialProvedor.objects.get(pk=credencial_id, ativo=True)
credenciais_dict = descriptografar_credenciais(credencial.credenciais_enc)

# Mescla token em cache se existir (ex: XSRF-TOKEN do FusionSolar)
try:
    cache = credencial.cache_token
    dados_token = descriptografar_credenciais(cache.dados_token_enc)
    credenciais_dict.update(dados_token)
except CacheTokenProvedor.DoesNotExist:
    pass
```

### 2. Verificação de Backoff

Antes de qualquer requisição, verifica se o provedor está em backoff por rate limit:

```python
chave_backoff = f'coleta:backoff:{credencial_id}'
ttl_restante = redis.ttl(chave_backoff)
if ttl_restante > 0:
    return  # aguarda expirar (máx 30 min)
```

### 3. Verificação de Intervalo Mínimo

Para provedores com janela rígida (ex: FusionSolar com 900s):

```python
min_intervalo = adaptador.capacidades.min_intervalo_coleta_segundos
ultima_coleta = LogColeta.objects.filter(status='sucesso').first().iniciado_em
if (now() - ultima_coleta).seconds < min_intervalo:
    return  # muito cedo, aguarda próximo ciclo do Beat
```

### 4. Busca de Dados (HTTP)

```python
# Usinas — sempre
with LimitadorRequisicoes(provedor):
    dados_usinas = adaptador.buscar_usinas()

# Inversores — em paralelo com ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=limite_requisicoes) as executor:
    futuras = {executor.submit(adaptador.buscar_inversores, usina.id): usina.id
               for usina in dados_usinas}
    for futura in as_completed(futuras):
        inversores_por_usina[id_usina] = futura.result()

# Alertas — uma vez para toda a conta (alertas_por_conta=True)
# ou por usina (alertas_por_conta=False)
with LimitadorRequisicoes(provedor):
    dados_alertas = adaptador.buscar_alertas()
```

### 5. Persistência em Transação Atômica

```python
with transaction.atomic():
    for dados_usina in dados_usinas:
        usina = ingestao.upsert_usina(dados_usina)
        ingestao.criar_snapshot_usina(usina, dados_usina)

        for dados_inv in inversores_por_usina[dados_usina.id_usina_provedor]:
            inversor = ingestao.upsert_inversor(usina, dados_inv)
            ingestao.criar_snapshot_inversor(inversor, dados_inv)

    ingestao.sincronizar_alertas(dados_alertas, usinas_por_id_provedor)
```

### 6. Pós-processamento

- Token atualizado salvo no `CacheTokenProvedor` (criptografado)
- Flag `precisa_atencao` limpa se estava marcado
- `LogColeta` criado com status `'sucesso'`

---

## Idempotência dos Snapshots

Os snapshots são criados com `get_or_create` por `(usina, coletado_em)`. O campo `coletado_em` é **arredondado para a janela de 10 minutos**:

```python
def _arredondar_coletado_em(dt):
    minutos = (dt.minute // 10) * 10
    return dt.replace(minute=minutos, second=0, microsecond=0)
```

Isso significa que se a coleta rodar duas vezes dentro do mesmo intervalo de 10 min (retry após falha parcial, por exemplo), o segundo `get_or_create` simplesmente atualiza o snapshot existente em vez de criar um duplicado.

---

## Tratamento de Erros

| Erro | Comportamento |
|---|---|
| `ProvedorErroAuth` | Marca `precisa_atencao=True`, **sem retry**, registra `auth_erro` |
| `ProvedorErroRateLimit` | Retry com backoff exponencial: 60s → 120s → 240s. Após 3 tentativas: backoff de 30 min no Redis |
| `ProvedorErroRateLimit` em retry | Salva token atualizado antes de re-enfileirar (evita loop 305 → re-login → 407) |
| Exception genérica | Retry padrão Celery (60s), max 3 vezes |

---

## Rate Limiting Distribuído

O `LimitadorRequisicoes` usa Redis para garantir que múltiplos workers não excedam o limite de cada provedor:

| Provedor | Limite |
|---|---|
| FusionSolar | 1 req / 5s |
| Hoymiles | 5 req / 10s |
| Solis | 3 req / 5s |

---

## Sincronização de Alertas

Veja detalhes em [[modulos/alertas#Sincronização]].

Resumo:
1. Busca alertas ativos no banco para este provedor
2. Para cada alerta da API: cria ou atualiza
3. Alertas que sumiram da API → `estado='resolvido'`, `fim=now()`
4. Novos alertas ou escalonados → dispara [[modulos/notificacoes]]

---

## Veja Também

- [[modulos/coleta]]
- [[modulos/alertas]]
- [[arquitetura/visao-geral]]
