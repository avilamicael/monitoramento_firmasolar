---
title: Módulo — Coleta
tipo: modulo
tags: [coleta, celery, tasks, ingestao]
---

# Módulo: Coleta

Responsável pelo agendamento, execução e registro de todas as coletas de dados dos provedores.

**Arquivos:**
- `coleta/tasks.py` — Tasks Celery
- `coleta/ingestao.py` — Serviço de persistência
- `coleta/models.py` — LogColeta
- `coleta/admin.py` — Interface admin

---

## Model: LogColeta

Registro de auditoria imutável de cada ciclo de coleta.

```python
class LogColeta:
    id            : UUIDField (PK)
    credencial    : FK → CredencialProvedor
    status        : 'sucesso' | 'parcial' | 'erro' | 'auth_erro'
    usinas_coletadas     : IntegerField
    inversores_coletados : IntegerField
    alertas_sincronizados: IntegerField
    detalhe_erro  : TextField
    duracao_ms    : IntegerField
    iniciado_em   : DateTimeField (auto)

    indexes: (credencial, -iniciado_em)
    ordering: -iniciado_em
```

`LogColeta` é append-only — nenhum registro é atualizado, apenas inserido. O admin bloqueia `add` e `change`.

---

## Tasks Celery

### `disparar_coleta_geral()`

Agendada a cada **10 minutos** pelo Beat.

```python
credenciais = CredencialProvedor.objects.filter(ativo=True)
for cred in credenciais:
    coletar_dados_provedor.delay(str(cred.id))
```

### `coletar_dados_provedor(credencial_id)`

Task principal. Parâmetros:
- `bind=True` (acessa `self.request.retries`)
- `max_retries=3`
- `default_retry_delay=60`
- `time_limit=300s`, `soft_time_limit=240s`

Fluxo detalhado em [[arquitetura/fluxo-de-coleta]].

### `renovar_tokens_provedores()`

Agendada a cada **6 horas**. Renova tokens de sessão dos provedores stateful (Hoymiles, FusionSolar) proativamente, antes de expirarem.

### `limpar_snapshots_antigos()`

Agendada diariamente às **03:00**. Remove `SnapshotUsina` e `SnapshotInversor` com mais de 90 dias.

---

## Schedule (config/celery.py)

```python
beat_schedule = {
    'coletar-todos-provedores': {
        'task': 'coleta.tasks.disparar_coleta_geral',
        'schedule': crontab(minute='*/10'),
    },
    'renovar-tokens': {
        'task': 'coleta.tasks.renovar_tokens_provedores',
        'schedule': crontab(minute=0, hour='*/6'),
    },
    'limpar-snapshots-antigos': {
        'task': 'coleta.tasks.limpar_snapshots_antigos',
        'schedule': crontab(minute=0, hour=3),
    },
}
```

---

## ServicoIngestao

Classe responsável por persistir todos os dados coletados em transação atômica.

```python
ServicoIngestao(credencial)
    .upsert_usina(DadosUsina)         → Usina
    .criar_snapshot_usina(usina, DadosUsina) → SnapshotUsina
    .upsert_inversor(usina, DadosInversor)  → Inversor
    .criar_snapshot_inversor(inv, DadosInversor) → SnapshotInversor
    .sincronizar_alertas(alertas, usinas)
```

### Idempotência

O campo `coletado_em` dos snapshots é arredondado para janelas de 10 minutos:

```python
minutos = (dt.minute // 10) * 10
coletado_em = dt.replace(minute=minutos, second=0, microsecond=0)
```

`get_or_create(usina=usina, coletado_em=coletado_em)` garante que retries não geram duplicatas.

### Upsert de Usinas

```python
usina, criada = Usina.objects.get_or_create(
    id_usina_provedor=dados.id_usina_provedor,
    provedor=credencial.provedor,
    defaults={...}
)
if not criada:
    # atualiza nome e endereço se mudaram
```

---

## Backoff e Rate Limit

### Chave Redis de Backoff

```
coleta:backoff:{credencial_id}
TTL: 1800s (30 min)
```

Ativada quando `max_retries` é esgotado por `ProvedorErroRateLimit`. Enquanto a chave existir, a task retorna imediatamente sem tentar a coleta.

### Retry Exponencial

```python
raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
# retry 0: 60s
# retry 1: 120s
# retry 2: 240s
```

---

## Veja Também

- [[arquitetura/fluxo-de-coleta]]
- [[modulos/alertas]]
- [[modulos/provedores]]
