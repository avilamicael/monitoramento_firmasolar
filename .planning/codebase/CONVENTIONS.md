# Coding Conventions

**Analysis Date:** 2026-04-07

## Language and Locale

All code, identifiers, docstrings, log messages, comments, model field names, and variable names are written in **Portuguese (pt-BR)**. English is used only for Python built-ins, framework APIs, and third-party library names.

Examples:
- `coletar_dados_provedor` not `collect_provider_data`
- `usinas_por_id_provedor` not `plants_by_provider_id`
- `ProvedorErroAuth` not `ProviderAuthError`

## Naming Patterns

**Files:**
- `snake_case` for all Python files: `ingestao.py`, `supressao_inteligente.py`, `autenticacao.py`
- File names use Portuguese words: `adaptador.py`, `consultas.py`, `limitador.py`, `registro.py`
- Test files prefixed with `test_`: `test_supressao_inteligente.py`

**Classes:**
- `PascalCase` in Portuguese: `ServicoIngestao`, `ServicoNotificacao`, `HoymilesAdaptador`, `LimitadorRequisicoes`
- Abstract base classes suffixed by concept role: `AdaptadorProvedor`, `BackendNotificacao`
- Django models named as singular nouns: `Usina`, `Alerta`, `CatalogoAlarme`, `SnapshotUsina`

**Functions:**
- `snake_case` verbs in Portuguese: `buscar_usinas()`, `criptografar_credenciais()`, `inferir_categoria()`
- Private helpers prefixed with `_`: `_para_float()`, `_normalizar_status()`, `_carregar_backends()`
- Boolean-returning functions use Portuguese verb conjugation: `e_desligamento_gradual()`, `esta_ativa()`, `precisa_renovar_token()`

**Variables:**
- `snake_case` in Portuguese: `dados_usinas`, `credenciais_dict`, `id_alerta_provedor`
- Loop variables are descriptive: `for dados_usina in dados_usinas`, `for config in configuracoes`
- Module-level constants use `UPPER_SNAKE_CASE`: `_LIMIAR_PCT_CAPACIDADE`, `_JANELA_HORAS`, `LIMITES`
- Private module-level constants prefixed with `_`: `_STATUS_MAP`, `_NIVEL_ALERTA_MAP`, `_BACKENDS_MAP`

**Django Model Fields:**
- `snake_case` in Portuguese: `id_usina_provedor`, `capacidade_kwp`, `coletado_em`, `energia_hoje_kwh`
- Audit fields consistently named: `criado_em` (auto_now_add), `atualizado_em` (auto_now)
- Boolean flags named descriptively: `suprimido`, `criado_auto`, `nivel_sobrescrito`, `precisa_atencao`

**Dataclass Fields:**
- `snake_case` in Portuguese with physical units in suffix where applicable: `potencia_atual_kw`, `tensao_ac_v`, `frequencia_hz`, `temperatura_c`

## Module-Level Structure

Files follow a consistent internal layout:

1. Module docstring (purpose + usage context)
2. Standard library imports
3. Third-party imports (Django, requests, etc.)
4. Local imports
5. Module-level constants/maps (`_CONSTANT = ...`)
6. Functions/classes

Visual separators using `# ── Section ──` are used in files with multiple conceptual sections:
```python
# ── Estruturas de dados ────────────────────────────────────────────────────────
# ── Contrato ABC ───────────────────────────────────────────────────────────────
```

## Import Organization

**Order:**
1. Standard library (`from datetime import datetime`, `import logging`)
2. Third-party / Django (`from django.db import models`, `import requests`)
3. Local project imports (`from provedores.base import AdaptadorProvedor`)

**Circular import avoidance:**
- Lazy imports inside functions when circular risk exists, always documented with a comment
- Example in `coleta/ingestao.py`: `from notificacoes.tasks import enviar_notificacao_alerta` inside `sincronizar_alertas()`
- Registry pattern (`provedores/registro.py`) uses `_carregar_provedores()` for lazy loading

## Docstrings

Every module has a file-level docstring explaining:
- What the module does
- Responsibilities (bullet list for complex modules)
- Usage examples or integration context

Every public class has a docstring. Every non-trivial method/function has a docstring.

Docstrings use Google-style `Args:` and `Returns:` blocks for functions with parameters:
```python
def inferir_categoria(mensagem: str, provedor: str, id_tipo: str = '') -> str:
    """
    Retorna a categoria mais provável para um tipo de alarme.
    ...
    Args:
        mensagem: texto descritivo do alarme (nome original do provedor)
        provedor: 'solis', 'hoymiles' ou 'fusionsolar'
        id_tipo:  id do tipo no provedor (para Hoymiles é o nome do flag)
    """
```

## Comments

Comments explain **why**, not what:
```python
# Critério duplo porque o campo state é inconsistente na API Solis —
# o mesmo alarme pode aparecer como state='0' (ativo) ou state='2' (resolvido)
# em coletas diferentes. alarmEndTime preenchido é o sinal mais confiável.
```

Inline comments for data transformations with units or domain meaning:
```python
potencia_w / 1000 if potencia_w else 0.0  # W → kW
```

Numbered step lists in complex orchestration functions:
```python
# 1. Buscar usinas
# 2. Buscar inversores em paralelo (fora da transação — são chamadas HTTP)
# 3. Buscar alertas
# 4. Persistir tudo em transação atômica
```

## Type Annotations

Full type annotations on all function signatures using Python 3.10+ union syntax:
```python
def buscar_alertas(self, id_usina_provedor: str | None = None) -> list[DadosAlerta]:
def get_adaptador(chave_provedor: str, credenciais: dict) -> AdaptadorProvedor:
def _timestamp_ms_para_datetime(ts_ms) -> datetime | None:
```

Dataclasses use typed fields throughout (`provedores/base.py`).

## Error Handling

**Explicit exception hierarchy** defined in `provedores/excecoes.py`:
- `ProvedorErro` — base, retriable
- `ProvedorErroAuth(ProvedorErro)` — no retry, requires manual attention
- `ProvedorTokenExpirado(ProvedorErroAuth)` — force re-login
- `ProvedorErroRateLimit(ProvedorErro)` — backoff retry
- `ProvedorErroDados(ProvedorErro)` — invalid response format

**Catch-and-log pattern** for non-critical failures where processing must continue:
```python
try:
    backend.enviar(dados, destinatarios)
except Exception as exc:
    logger.error('Backend %s falhou para alerta %s: %s', config.canal, alerta.id, exc)
```

**Explicit re-raise** when a task should retry via Celery:
```python
raise self.retry(exc=exc)
```

**Never silence exceptions silently** — every `except` block logs at least `logger.error(...)` or `logger.warning(...)`.

One accepted exception: `except Exception: pass` in `coleta/tasks.py` line 210 for a token-save fallback during rate-limit handling. The surrounding comment explains the rationale.

## Logging

Standard pattern in every module:
```python
logger = logging.getLogger(__name__)
```

Log format uses `%s` positional args (not f-strings) for deferred formatting:
```python
logger.info('%s: coleta concluída — %d usinas, %d inversores, %d alertas em %dms',
            credencial.provedor, len(dados_usinas), total_inversores, len(dados_alertas), duracao_ms)
```

Log levels:
- `logger.debug` — tracing/diagnostics (suppression decisions, token checks)
- `logger.info` — successful operations (coleta completed, token renewed, records resolved)
- `logger.warning` — non-fatal problems (no usinas found, inversor fetch error, missing backend)
- `logger.error` — failures requiring attention (auth errors, backend failures, unexpected exceptions)

## Data Models

**UUIDs as primary keys** on all main models (`Usina`, `Inversor`, `Alerta`, `SnapshotUsina`, `SnapshotInversor`):
```python
id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
```

**Choices as lists of tuples** on model fields, defined at class level:
```python
NIVEL_CHOICES = [
    ('info', 'Info'),
    ('aviso', 'Aviso'),
    ('importante', 'Importante'),
    ('critico', 'Crítico'),
]
```

**Domain constants** for ordering/lookup defined as class-level dicts:
```python
_NIVEL_ORDEM = {'info': 0, 'aviso': 1, 'importante': 2, 'critico': 3}
```

**`objects = models.Manager()`** declared explicitly on models that use custom queries.

**`verbose_name` and `verbose_name_plural`** on every model's `Meta` class.

**`__str__`** defined on every model.

**Composite indexes** declared on `Meta.indexes` for query-heavy fields.

## Django ORM Patterns

**`get_or_create`** for idempotent upserts:
```python
usina, _ = Usina.objects.get_or_create(
    id_usina_provedor=dados.id_usina_provedor,
    provedor=self.credencial.provedor,
    defaults={...},
)
```

**`update_fields`** for partial saves to avoid race conditions:
```python
usina.save(update_fields=campos_alterados + ['atualizado_em'])
```

**`.filter(...).update(...)`** for bulk updates without loading objects:
```python
Alerta.objects.filter(pk=alerta.pk).update(notificacao_enviada=True)
```

**`transaction.on_commit`** for post-commit side effects (Celery task dispatch):
```python
transaction.on_commit(
    lambda aid=alerta_id: enviar_notificacao_alerta.delay(aid, 'novo')
)
```

**`transaction.atomic()`** wraps all DB writes in a single collection cycle.

## Dataclass Usage

Business data transferred between layers uses `@dataclass` from `provedores/base.py`:
- `DadosUsina`, `DadosInversor`, `DadosAlerta`, `CapacidadesProvedor`, `DadosNotificacao`
- All dataclasses use `field(default_factory=dict)` for mutable defaults

Adapters normalize provider-specific API responses into these dataclasses before returning.

## Configuration

All configuration via `os.environ.get()` with safe defaults in `config/settings/base.py`. No hardcoded values that differ by environment.

Settings split into:
- `config/settings/base.py` — shared settings
- `config/settings/dev.py` — development overrides
- `config/settings/prod.py` — production overrides

---

*Convention analysis: 2026-04-07*
