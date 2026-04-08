---
phase: 01-api-infrastructure
reviewed: 2026-04-08T00:00:00Z
depth: standard
files_reviewed: 15
files_reviewed_list:
  - backend_monitoramento/api/__init__.py
  - backend_monitoramento/api/apps.py
  - backend_monitoramento/api/views.py
  - backend_monitoramento/api/urls.py
  - backend_monitoramento/api/tests/test_auth.py
  - backend_monitoramento/api/tests/test_cors.py
  - backend_monitoramento/usinas/models.py
  - backend_monitoramento/usinas/migrations/0002_garantiausina.py
  - backend_monitoramento/usinas/migrations/0004_merge_garantiausina_snapshotinversor.py
  - backend_monitoramento/usinas/tests/test_garantia.py
  - backend_monitoramento/requirements/base.txt
  - backend_monitoramento/config/settings/base.py
  - backend_monitoramento/config/settings/test.py
  - backend_monitoramento/config/urls.py
  - backend_monitoramento/pytest.ini
findings:
  critical: 1
  warning: 3
  info: 2
  total: 6
status: advisory
---

# Phase 01: Code Review Report

**Reviewed:** 2026-04-08
**Depth:** standard
**Files Reviewed:** 15
**Status:** advisory — nenhum bloqueador de deploy, mas dois pontos devem ser corrigidos antes da fase 02

## Summary

A infraestrutura de API foi implementada com solidez geral: JWT configurado corretamente (15min access / 7d refresh com blacklist e rotacao), CORS sem wildcard via env var, app `api` modular, e `GarantiaUsina` com properties calculadas sem desnormalizacao. A suite de testes cobre os requisitos declarados.

Os problemas encontrados concentram-se em dois riscos operacionais reais: um `SECRET_KEY` com fallback hardcoded que permite que a aplicacao suba em producao com chave insegura se o env var nao estiver configurado, e um teste de lifetimes de token que pode falhar de forma intermitente por depender de arimetica de timestamp sem margem de tolerancia.

---

## Critical Issues

### CR-01: SECRET_KEY com fallback hardcoded permite execucao insegura em producao

**File:** `backend_monitoramento/config/settings/base.py:7`

**Issue:** O valor padrao `'changeme-defina-no-env'` e uma string conhecida e estatica. Se `DJANGO_SECRET_KEY` nao estiver definida no ambiente de deploy (erro de configuracao, rollback de .env, deploy em novo servidor), a aplicacao sobe silenciosamente com uma chave previsivel. Isso compromete assinaturas de sessao, CSRF tokens, e qualquer dado criptografado com a chave Django. O problema e que nao ha nenhum mecanismo de fail-fast.

**Fix:** Remover o fallback e falhar explicitamente na inicializacao se o env var nao estiver definido:

```python
# config/settings/base.py
import os
import sys

_secret = os.environ.get('DJANGO_SECRET_KEY')
if not _secret:
    print(
        'ERRO: DJANGO_SECRET_KEY nao definida. '
        'Defina a variavel de ambiente antes de iniciar.',
        file=sys.stderr,
    )
    sys.exit(1)

SECRET_KEY = _secret
```

Alternativa mais Djangonica usando `ImproperlyConfigured`:

```python
from django.core.exceptions import ImproperlyConfigured

_secret = os.environ.get('DJANGO_SECRET_KEY')
if not _secret:
    raise ImproperlyConfigured(
        'DJANGO_SECRET_KEY nao definida. '
        'Defina a variavel de ambiente antes de iniciar.'
    )
SECRET_KEY = _secret
```

O settings de teste (`config/settings/test.py`) deve definir um valor fixo para CI:

```python
# config/settings/test.py
SECRET_KEY = 'test-secret-key-somente-para-testes'
```

---

## Warnings

### WR-01: test_token_lifetimes e fragil — falha intermitente por precisao de timestamp

**File:** `backend_monitoramento/api/tests/test_auth.py:89-101`

**Issue:** O teste decodifica o payload JWT manualmente e afirma `exp - iat == 900` (exatamente 15 minutos em segundos). O simplejwt usa `datetime.now()` para calcular `iat` e `exp` internamente, e dependendo da granularidade do clock ou de qualquer arredondamento interno da biblioteca, a diferenca pode ser 899 ou 901 segundos. Nao ha margem de tolerancia.

Adicionalmente, se `iat` nao estiver presente no payload (o simplejwt pode omiti-lo dependendo da configuracao), o teste levanta `KeyError` sem mensagem clara.

**Fix:** Usar uma verificacao com margem e incluir acesso defensivo:

```python
def test_token_lifetimes(self, tokens):
    """API-06: Access token expira em ~15 min; refresh em ~7 dias."""
    def decode_payload(token):
        payload = token.split('.')[1]
        payload += '=' * (4 - len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))

    access_payload = decode_payload(tokens['access'])
    assert 'exp' in access_payload and 'iat' in access_payload
    duracao_access = access_payload['exp'] - access_payload['iat']
    assert 895 <= duracao_access <= 905, f'Esperado ~900s, obtido {duracao_access}s'

    refresh_payload = decode_payload(tokens['refresh'])
    assert 'exp' in refresh_payload and 'iat' in refresh_payload
    duracao_refresh = refresh_payload['exp'] - refresh_payload['iat']
    assert 604795 <= duracao_refresh <= 604805, f'Esperado ~604800s, obtido {duracao_refresh}s'
```

---

### WR-02: GarantiaUsina nao valida meses=0 — garantia com vigencia zero aceita silenciosamente

**File:** `backend_monitoramento/usinas/models.py:181`

**Issue:** `PositiveIntegerField` no Django permite o valor `0` no nivel Python (a validacao `> 0` so e aplicada pelo banco PostgreSQL, e mesmo assim depende da versao). Com `meses=0`, `data_fim == data_inicio` e `ativa` retorna `False` imediatamente — uma garantia que nasce vencida. Isso nao e detectado pelos testes existentes e pode resultar em dados invalidos persistidos se a validacao de formulario/serializer nao for adicionada oportunamente.

**Fix:** Adicionar `MinValueValidator` no campo para garantir validacao no nivel do model, independente do banco ou serializer:

```python
from django.core.validators import MinValueValidator

class GarantiaUsina(models.Model):
    meses = models.PositiveIntegerField(
        validators=[MinValueValidator(1, message='Garantia deve ter pelo menos 1 mes.')]
    )
```

E adicionar teste cobrindo este caso:

```python
def test_garantia_meses_zero_invalido(self):
    from django.core.exceptions import ValidationError
    garantia = GarantiaUsina(
        usina=...,
        data_inicio=date(2024, 1, 1),
        meses=0,
    )
    with pytest.raises(ValidationError):
        garantia.full_clean()
```

---

### WR-03: Imports dentro de @property causam overhead desnecessario e violam convencao Django

**File:** `backend_monitoramento/usinas/models.py:192, 197, 202`

**Issue:** Os tres `@property` de `GarantiaUsina` importam `relativedelta` e `timezone` dentro do corpo da funcao a cada chamada. O padrao de import-dentro-de-funcao e usado no Django para quebrar imports circulares, mas aqui nao existe risco de circularidade: `django.utils.timezone` e `dateutil.relativedelta` sao dependencias externas sem referencia de volta ao modulo `usinas`. O custo e pequeno mas o padrao e enganoso — sugere circularidade onde nao ha.

**Fix:** Mover os imports para o topo do arquivo:

```python
# usinas/models.py — topo do arquivo
import uuid
from datetime import date
from django.db import models
from django.utils import timezone
from dateutil.relativedelta import relativedelta

# ...

class GarantiaUsina(models.Model):
    @property
    def data_fim(self):
        return self.data_inicio + relativedelta(months=self.meses)

    @property
    def ativa(self):
        return self.data_fim >= timezone.now().date()

    @property
    def dias_restantes(self):
        delta = self.data_fim - timezone.now().date()
        return max(delta.days, 0)
```

---

## Info

### IN-01: default_auto_field em ApiConfig e redundante com configuracao global

**File:** `backend_monitoramento/api/apps.py:5`

**Issue:** `default_auto_field = 'django.db.models.BigAutoField'` duplica o valor ja definido em `base.py:92`. A configuracao global em `DEFAULT_AUTO_FIELD` e suficiente. Manter o override no `AppConfig` nao causa bug, mas cria uma dependencia implicita e redundante que pode gerar confusao ao auditar a configuracao de auto field no futuro.

**Fix:** Remover a linha do `AppConfig`:

```python
class ApiConfig(AppConfig):
    name = 'api'
    verbose_name = 'API REST'
```

---

### IN-02: TestGarantiaUsina sem marcador de classe @pytest.mark.django_db — isolamento inconsistente

**File:** `backend_monitoramento/usinas/tests/test_garantia.py:23`

**Issue:** A classe `TestGarantiaUsina` nao tem `@pytest.mark.django_db`. Os testes que recebem o fixture `usina` funcionam porque a fixture declara `def usina(db)` — o `db` fixture do pytest-django propaga acesso ao banco para os testes que usam a fixture. Porem, o marcador ausente na classe torna o acesso ao banco implicito e dependente do comportamento de propagacao do pytest-django, o que e frágil: se o fixture for refatorado para nao receber `db` (por exemplo, para usar `usina_factory` sem db), os testes que nao salvam no banco passam a ter comportamento indefinido.

O teste `test_garantia_persistencia` tem `@pytest.mark.django_db` individualmente (linha 92), o que confirma que o autor estava ciente do marcador — mas nao o aplicou consistentemente.

**Fix:** Adicionar o marcador na classe para tornar o contrato explicito:

```python
@pytest.mark.django_db
class TestGarantiaUsina:
    ...
```

---

_Reviewed: 2026-04-08_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
