---
title: Módulo — Coleta
tipo: modulo
tags: [coleta, celery, tasks, ingestao, configuracao]
updated: 2026-04-15
---

# Módulo: Coleta

Responsável pelo agendamento, execução e registro de todas as coletas de dados dos provedores, pela configuração global do sistema (singleton `ConfiguracaoSistema`) e pela auto-pausa de usinas inativas.

**Arquivos:**
- `coleta/tasks.py` — Tasks Celery (`disparar_coleta_geral`, `coletar_dados_provedor`, `renovar_tokens_provedores`, `limpar_snapshots_antigos`, `_pausar_usinas_inativas`)
- `coleta/ingestao.py` — Serviço de persistência (`ServicoIngestao`)
- `coleta/models.py` — `ConfiguracaoSistema` (singleton) + `LogColeta`
- `coleta/admin.py` — Admin

---

## Model: ConfiguracaoSistema (singleton)

Parâmetros globais do sistema — singleton (`pk=1` forçado no `save()`, `delete()` desabilitado). Acesso via `ConfiguracaoSistema.obter()` (cria com defaults na primeira chamada).

```python
class ConfiguracaoSistema:
    dias_sem_comunicacao_pausar : PositiveIntegerField  # default 60
    meses_garantia_padrao       : PositiveIntegerField  # default 12
    dias_aviso_garantia_proxima : PositiveIntegerField  # default 30
    dias_aviso_garantia_urgente : PositiveIntegerField  # default 7
    atualizado_em               : DateTimeField
```

| Campo | Uso |
|---|---|
| `dias_sem_comunicacao_pausar` | Usinas sem snapshot há mais deste número de dias são marcadas `ativo=False` no início do próximo ciclo de coleta (ver `_pausar_usinas_inativas`). |
| `meses_garantia_padrao` | Duração da [[modulos/usinas#GarantiaUsina]] criada automaticamente pelo `upsert_usina` ao registrar a usina pela primeira vez. |
| `dias_aviso_garantia_proxima` | Patamar "aviso" do alerta interno `garantia_expirando` (ver [[modulos/alertas#Alertas internos]]). |
| `dias_aviso_garantia_urgente` | Patamar "importante" do mesmo alerta (nível escala a partir deste limiar). |

**Endpoint REST:** `/api/configuracoes/` — GET/PUT/PATCH, restrito a `is_staff=True`. Sem list/create nem id na URL (é singleton).

**Frontend:** página `/configuracoes` (menu Gestão, só staff).

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

Agendada pelo Beat a cada **30 minutos**. Para cada `CredencialProvedor` ativa, verifica o `intervalo_coleta_minutos` próprio (default 30, mínimo 30) e só dispara `coletar_dados_provedor.delay(cred.id)` se o tempo desde o último `LogColeta` tiver atingido esse intervalo.

> O Beat dispara a cada 30 min, mas o intervalo efetivo por provedor é configurável em `CredencialProvedor.intervalo_coleta_minutos`. Provedores como FusionSolar também respeitam `min_intervalo_coleta_segundos` declarado nas suas `CapacidadesProvedor`.

### `_pausar_usinas_inativas(provedor)`

Helper chamado no início de `coletar_dados_provedor` antes de qualquer requisição. Lê `ConfiguracaoSistema.dias_sem_comunicacao_pausar` e desativa (`ativo=False`) usinas do provedor cujo `ultimo_snapshot.coletado_em` seja mais antigo que o limite. Usinas sem nenhum snapshot ainda registrado são ignoradas (recém-criadas). **Reativação é manual** (Django admin ou `AtivoToggleButton` na página da usina).

### `coletar_dados_provedor(credencial_id)`

Task principal. Parâmetros:
- `bind=True` (acessa `self.request.retries`)
- `max_retries=3`
- `default_retry_delay=60`
- `time_limit=300s`, `soft_time_limit=240s`

Fluxo:
1. Carrega credencial + token em cache (se houver)
2. Chama `_pausar_usinas_inativas(credencial.provedor)`
3. Verifica `min_intervalo_coleta_segundos` (skip se muito cedo)
4. Busca usinas, inversores (ThreadPool) e alertas via adaptador
5. Em transação atômica:
   - Para cada usina **não pausada**: `upsert_usina`, `criar_snapshot_usina`, upsert/snapshot dos inversores, `analisar_usina` (alertas internos)
   - `sincronizar_alertas(dados_alertas, usinas_por_id_provedor)`
6. Persiste token novo em `CacheTokenProvedor`
7. Limpa `precisa_atencao` se estava marcado
8. Registra `LogColeta(status='sucesso', ...)`

Tratamento de erros:

| Erro | Comportamento |
|---|---|
| `ProvedorErroAuth` | Marca `precisa_atencao=True`, **sem retry**, `LogColeta.status='auth_erro'` |
| `ProvedorErroRateLimit` | Persiste token atualizado (evita loop 305→re-login→407), **sem retry** — o próximo ciclo do Beat verifica o `min_intervalo` e tenta novamente no momento correto; `LogColeta.status='erro'` |
| Exception genérica | Retry padrão Celery (60s), max 3 vezes |

Detalhe completo em [[arquitetura/fluxo-de-coleta]].

### `renovar_tokens_provedores()`

Agendada a cada **6 horas**. Itera pelos `CacheTokenProvedor` ativos e chama `adaptador.renovar_token(dados_token)` — falha marca a credencial como `precisa_atencao=True`.

### `limpar_snapshots_antigos()`

Agendada diariamente às **03:00**. Remove `SnapshotUsina` e `SnapshotInversor` com mais de 90 dias.

---

## Schedule (config/celery.py)

```python
beat_schedule = {
    'coletar-todos-provedores': {
        'task': 'coleta.tasks.disparar_coleta_geral',
        'schedule': crontab(minute='*/30'),
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
    .upsert_usina(DadosUsina)            → Usina      # cria GarantiaUsina padrão se usina for nova
    .criar_snapshot_usina(usina, ...)     → SnapshotUsina
    .upsert_inversor(usina, ...)          → Inversor
    .criar_snapshot_inversor(inv, ...)    → SnapshotInversor
    .sincronizar_alertas(alertas, mapa_usinas)
```

### Idempotência

O campo `coletado_em` dos snapshots é arredondado para janelas de 10 minutos:

```python
def _arredondar_coletado_em(dt, minutos=10):
    total = int(dt.timestamp())
    janela = minutos * 60
    return datetime.fromtimestamp((total // janela) * janela, tz=utc)
```

`get_or_create(usina=usina, coletado_em=coletado_em)` garante que retries não geram duplicatas.

### Upsert de Usinas + auto-criação de garantia

```python
usina, criada = Usina.objects.get_or_create(
    id_usina_provedor=dados.id_usina_provedor,
    provedor=credencial.provedor,
    defaults={...},
)
if criada:
    config = ConfiguracaoSistema.obter()
    GarantiaUsina.objects.get_or_create(
        usina=usina,
        defaults={
            'data_inicio': dj_timezone.localdate(),
            'meses': config.meses_garantia_padrao,
            'observacoes': 'Garantia padrão criada automaticamente no primeiro registro da usina.',
        },
    )
```

Regra: toda usina nova nasce com garantia de `meses_garantia_padrao` (default 12) a partir da data do primeiro registro. `get_or_create` garante idempotência — não sobrescreve garantias manuais pré-existentes.

### Sincronização de alertas do provedor

Executada por `ServicoIngestao.sincronizar_alertas()` ao final de cada coleta. Delega análise de alertas internos para [[modulos/alertas]]. Resumo:

- Catálogo: `get_or_create` por `(provedor, id_alarme_provedor)` — auto-infere categoria via `alertas/categorizacao.py`
- Supressão global (`catalogo.suprimido`) e por `RegraSupressao` (`todas` ou `usina`, respeita `ativo_ate`)
- Supressão inteligente: `sistema_desligado` durante desligamento gradual ao entardecer (ver `alertas/supressao_inteligente.py`) — só aplica se não houver alerta já aberto para o mesmo ID
- Novos alertas → `transaction.on_commit` agenda `enviar_notificacao_alerta.delay(id, 'novo')`
- Escalonamento de nível → `on_commit` agenda como `'escalado'`
- Alertas que sumiram do provedor neste ciclo → `estado='resolvido'`, `fim=now()` (apenas `origem='provedor'`)

---

## Rate Limit / Retentativas

Ver [[modulos/provedores#Rate Limiting]]. Resumo:

- Rate limit por provedor é garantido pelo `LimitadorRequisicoes` (Redis).
- Em `ProvedorErroRateLimit`, a task **não retenta** — o próximo ciclo do Beat respeita o `min_intervalo_coleta_segundos` do adaptador (900s para FusionSolar).

---

## Veja Também

- [[arquitetura/fluxo-de-coleta]]
- [[arquitetura/decisoes]]
- [[modulos/alertas]]
- [[modulos/usinas]]
- [[modulos/provedores]]
