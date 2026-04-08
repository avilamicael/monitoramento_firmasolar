# Phase 1: API Infrastructure — Research

**Pesquisado:** 2026-04-07
**Domínio:** Django REST Framework, JWT, CORS, Django ORM
**Confiança:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Descrição | Suporte da Pesquisa |
|----|-----------|---------------------|
| API-01 | Instalar e configurar DRF com paginação padrão e autenticação JWT como default | Stack verificada no PyPI; padrão de configuração documentado abaixo |
| API-02 | Endpoint de login retorna access + refresh token (`POST /api/auth/token/`) | simplejwt fornece `TokenObtainPairView` pronta; apenas registrar a URL |
| API-03 | Endpoint de refresh emite novo access token (`POST /api/auth/token/refresh/`) | simplejwt fornece `TokenRefreshView` pronta; rotação configurada via `ROTATE_REFRESH_TOKENS` |
| API-04 | Endpoints protegidos rejeitam requisições sem token com 401 | `IsAuthenticated` como `DEFAULT_PERMISSION_CLASSES` aplica globalmente |
| API-05 | CORS aceita apenas o domínio do frontend; sem wildcard em prod | `django-cors-headers` 4.9.0 com `CORS_ALLOWED_ORIGINS` lido de env var |
| API-06 | Access token expira em 15 min; refresh expira em 7 dias com rotação | Configurado via `SIMPLE_JWT` dict em settings; `ROTATE_REFRESH_TOKENS = True` |
| GAR-01 | Model `GarantiaUsina` com campos usina, data_inicio, meses, data_fim, ativa, observacoes | Model Django com properties calculadas; migration reversível |
</phase_requirements>

---

## Resumo

Esta fase instala a fundação REST do projeto: DRF + simplejwt + CORS + o model `GarantiaUsina`. O projeto já usa Django 5.1+, Postgres, pytest-django e tem padrões de teste bem estabelecidos (fixtures com `db`, factory manual via `objects.create`). Nenhuma dessas bibliotecas está instalada ainda — todas precisam ser adicionadas ao `requirements/base.txt` e ao ambiente.

A maior decisão de estrutura é onde criar o app `api`. O escopo determina: `backend_monitoramento/api/` como app Django dedicada, registrada em `INSTALLED_APPS`. Isso mantém a camada REST separada dos apps de domínio (`usinas`, `alertas`, etc.), que é o padrão recomendado para projetos Django que crescem com múltiplas fases.

A única armadilha relevante nesta fase é a ordenação do middleware do `django-cors-headers`: ele deve vir antes de `CommonMiddleware` mas depois de `SecurityMiddleware`. O settings já segue a ordem correta para inserção.

**Recomendação principal:** Adicionar os três pacotes ao `base.txt`, criar o app `api/` com estrutura mínima, configurar o bloco `REST_FRAMEWORK` e `SIMPLE_JWT` em `base.py`, e criar `GarantiaUsina` em `usinas/models.py` (não no app `api/`, pois é um model de domínio).

---

## Project Constraints (from CLAUDE.md)

| Diretiva | Impacto nesta fase |
|----------|--------------------|
| Nenhuma credencial ou secret no código | `CORS_ALLOWED_ORIGINS` e `SECRET_KEY` lidos de env var — já praticado no projeto |
| Toda entrada do usuário é não confiável | simplejwt valida tokens internamente; não há input de usuário além de credentials no login |
| Autenticação e autorização verificadas em toda rota | `DEFAULT_PERMISSION_CLASSES = [IsAuthenticated]` aplica globalmente; views de token devem usar `AllowAny` explicitamente |
| Migrations sempre reversíveis | `GarantiaUsina` é tabela nova; migration trivialmente reversível com `migrations.DeleteModel` |
| Dependência externa: informar antes de adicionar | Três novas libs: `djangorestframework`, `djangorestframework-simplejwt`, `django-cors-headers` — informadas aqui |
| Multi-tenancy: toda query inclui filtro de tenant | Não aplicável nesta fase (não há endpoints de negócio) |
| Nunca hardcodar URLs, timeouts, limites | `page_size`, lifetimes dos tokens e origens CORS em settings via env var onde variável por ambiente |
| Todo código com lógica de negócio tem teste unitário | Testes obrigatórios para os 4 cenários descritos no escopo |

---

## Standard Stack

### Core

| Biblioteca | Versão | Propósito | Por que é o padrão |
|------------|--------|-----------|---------------------|
| djangorestframework | 3.17.1 | Framework REST para Django | Padrão absoluto do ecossistema Django para APIs REST [VERIFIED: PyPI] |
| djangorestframework-simplejwt | 5.5.1 | Autenticação JWT para DRF | Biblioteca oficial recomendada pela documentação do DRF para JWT [VERIFIED: PyPI] |
| django-cors-headers | 4.9.0 | Middleware CORS para Django | Pacote de referência para CORS em Django; mantido pela equipe Adam Johnson / Jazzband [VERIFIED: PyPI] |

### Versões verificadas no registro PyPI em 2026-04-07

```bash
# djangorestframework: latest = 3.17.1
# djangorestframework-simplejwt: latest = 5.5.1
# django-cors-headers: latest = 4.9.0
```

### Instalação

Adicionar ao `backend_monitoramento/requirements/base.txt`:

```
djangorestframework==3.17.*
djangorestframework-simplejwt==5.5.*
django-cors-headers==4.9.*
```

---

## Architecture Patterns

### Estrutura de arquivos a criar

```
backend_monitoramento/
├── api/                          # App Django dedicada à camada REST
│   ├── __init__.py
│   ├── apps.py
│   ├── urls.py                   # inclui auth/token/ e auth/token/refresh/
│   └── views.py                  # vazio nesta fase; usado a partir da Phase 2
├── usinas/
│   ├── models.py                 # adicionar GarantiaUsina aqui (model de domínio)
│   └── migrations/
│       └── 0004_garantiausina.py # nova migration reversível
└── config/
    ├── settings/
    │   └── base.py               # adicionar REST_FRAMEWORK, SIMPLE_JWT, CORS
    └── urls.py                   # incluir api.urls sob prefixo /api/
```

### Padrão 1: Configuração do bloco REST_FRAMEWORK em settings/base.py

**O que é:** Bloco de configuração global do DRF que define autenticação e paginação padrão.

**Quando usar:** Uma vez, na instalação. Toda view herda essas configurações a menos que sobrescreva explicitamente.

```python
# config/settings/base.py
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}
```

[ASSUMED — padrão de configuração baseado em treinamento; verificável na documentação oficial do DRF]

### Padrão 2: Configuração do SIMPLE_JWT em settings/base.py

```python
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,  # invalida o refresh anterior após rotação
    'AUTH_HEADER_TYPES': ('Bearer',),
}
```

**Atenção sobre `BLACKLIST_AFTER_ROTATION`:** Para que funcione, requer `rest_framework_simplejwt.token_blacklist` em `INSTALLED_APPS` e uma migration adicional. Se a equipe preferir evitar a tabela de blacklist nesta fase, `BLACKLIST_AFTER_ROTATION = False` ainda emite novo refresh em cada rotate, mas o anterior técnicamente permanece válido até expirar. O requisito API-06 fala em "token original não reutilizável" — isso implica blacklist ativa. [ASSUMED — interpretação do requisito]

### Padrão 3: Configuração CORS em settings/base.py

```python
# Lido de variável de ambiente; formato: "http://localhost:5173,https://painel.firmasolar.com.br"
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get('CORS_ALLOWED_ORIGINS', 'http://localhost:5173').split(',')
    if origin.strip()
]
CORS_ALLOW_CREDENTIALS = False  # sem cookies; JWT via header
```

**Posição do middleware** — CorsMiddleware deve ser inserido antes de `CommonMiddleware`:

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',   # <-- AQUI, antes de CommonMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    ...
]
```

[ASSUMED — ordem verificável na documentação do django-cors-headers]

### Padrão 4: Registro de URLs de autenticação

```python
# config/urls.py
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
]

# api/urls.py
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
```

As views `TokenObtainPairView` e `TokenRefreshView` usam `permission_classes = [AllowAny]` internamente — não precisam de anotação adicional. [ASSUMED]

### Padrão 5: Model GarantiaUsina

**Onde colocar:** `usinas/models.py` — GarantiaUsina é um model de domínio da usina, não da camada API.

```python
# usinas/models.py (adição ao arquivo existente)
from dateutil.relativedelta import relativedelta  # ou calcular manualmente

class GarantiaUsina(models.Model):
    usina = models.OneToOneField(
        Usina,
        on_delete=models.CASCADE,
        related_name='garantia',
    )
    data_inicio = models.DateField()
    meses = models.PositiveIntegerField()
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Garantia de Usina'
        verbose_name_plural = 'Garantias de Usinas'

    @property
    def data_fim(self):
        # Adiciona N meses à data de início
        # Evitar python-dateutil (dep extra); usar relativedelta do Django não existe
        # Alternativa sem dep: calcular via replace + timedelta
        from dateutil.relativedelta import relativedelta
        return self.data_inicio + relativedelta(months=self.meses)

    @property
    def ativa(self):
        from django.utils import timezone
        return self.data_fim >= timezone.now().date()

    def __str__(self):
        return f'Garantia — {self.usina.nome} ({self.meses} meses)'
```

**Nota sobre `python-dateutil`:** O projeto usa `celery==5.4.*` que já inclui `python-dateutil` como dependência transitiva. Verificar `pip show python-dateutil` antes de adicionar ao requirements explicitamente. Alternativa sem dep: `(data_inicio.replace(day=1) + timedelta(days=32*meses)).replace(day=data_inicio.day)` — porém propenso a bugs em meses curtos. Preferir `relativedelta`. [ASSUMED — verificar dependência transitiva]

### Anti-Patterns a Evitar

- **Colocar GarantiaUsina no app `api/`:** O model pertence ao domínio `usinas/`. O app `api/` deve conter apenas views, serializers e URLs.
- **Usar `CORS_ALLOW_ALL_ORIGINS = True`:** Proibido em prod. Nunca usar wildcard.
- **Esquecer `corsheaders` em `INSTALLED_APPS`:** O middleware não funciona sem o app instalado.
- **Usar `SessionAuthentication` como fallback:** Remover do `DEFAULT_AUTHENTICATION_CLASSES`; esta API é stateless.
- **Omitir `BLACKLIST_AFTER_ROTATION`:** Sem blacklist, tokens rotacionados permanecem válidos — viola o requisito API-06.

---

## Don't Hand-Roll

| Problema | Não construir | Usar em vez | Por quê |
|----------|--------------|-------------|---------|
| Geração e validação de JWT | Lógica manual de assinar/verificar tokens | `rest_framework_simplejwt` | Algoritmo RS256/HS256, claims, expiração, blacklist — edge cases críticos de segurança |
| Rotação de refresh tokens | Lógica própria de invalidação | `ROTATE_REFRESH_TOKENS + BLACKLIST_AFTER_ROTATION` | Race conditions, clock skew, concurrent requests |
| Headers CORS | Middleware manual | `django-cors-headers` | Preflight OPTIONS, wildcard matching, credentials — especificação complexa |
| Paginação de querysets | Loop manual com slice | `PageNumberPagination` do DRF | Headers de metadata, formato de resposta, contagem total eficiente |

---

## Common Pitfalls

### Pitfall 1: Middleware CORS fora de ordem

**O que acontece:** Requisições CORS retornam 200 mas sem os headers `Access-Control-Allow-Origin`, fazendo o browser bloquear a resposta.

**Por que acontece:** `CorsMiddleware` precisa processar a requisição antes de `CommonMiddleware` para injetar os headers de resposta corretamente.

**Como evitar:** Posicionar `'corsheaders.middleware.CorsMiddleware'` imediatamente após `WhiteNoiseMiddleware` na lista `MIDDLEWARE`.

**Sinal de alerta:** Testes de CORS passam mas browser em dev bloqueia requisições.

### Pitfall 2: `token_blacklist` em INSTALLED_APPS ausente

**O que acontece:** `BLACKLIST_AFTER_ROTATION = True` lança `ImproperlyConfigured` ou `OperationalError` na migration.

**Por que acontece:** A tabela `outstanding_token` e `blacklisted_token` são criadas pela migration do app `rest_framework_simplejwt.token_blacklist`.

**Como evitar:** Adicionar `'rest_framework_simplejwt.token_blacklist'` a `INSTALLED_APPS` antes de rodar migrations.

**Sinal de alerta:** `python manage.py migrate` funciona mas `makemigrations` mostra dependências pendentes.

### Pitfall 3: `corsheaders` ausente de INSTALLED_APPS

**O que acontece:** O middleware existe no MIDDLEWARE mas falha silenciosamente ou lança `AppRegistryNotReady`.

**Por que acontece:** O `CorsMiddleware` verifica configurações via `apps.get_model`; precisa que o app esteja registrado.

**Como evitar:** Adicionar `'corsheaders'` a `INSTALLED_APPS`.

### Pitfall 4: `data_fim` como DateField em vez de property

**O que acontece:** Tentar filtrar por `data_fim` em queries Django falha (campo não existe no banco).

**Por que acontece:** `data_fim` é calculado — não pode ser usado em `filter()` diretamente.

**Como evitar:** Implementar como `@property` no model (conforme spec). Para queries que precisam filtrar, usar `annotate()` com `ExpressionWrapper` na Phase 2.

**Sinal de alerta:** Tentativa de `GarantiaUsina.objects.filter(data_fim__lt=...)` em Phase 2.

### Pitfall 5: python-dateutil não disponível

**O que acontece:** `ImportError: No module named 'dateutil'` em runtime.

**Por que acontece:** Se `python-dateutil` não está em `base.txt` diretamente e a dependência transitiva do celery muda.

**Como evitar:** Adicionar `python-dateutil` a `base.txt` explicitamente, ou usar a alternativa com `timedelta` e `calendar.monthrange`.

---

## Code Examples

### Teste: login retorna access + refresh

```python
# api/tests/test_auth.py
import pytest
from django.urls import reverse

@pytest.mark.django_db
def test_login_retorna_tokens(client, django_user_model):
    usuario = django_user_model.objects.create_user(
        username='admin', password='senha123'
    )
    response = client.post(
        reverse('token_obtain_pair'),
        {'username': 'admin', 'password': 'senha123'},
        content_type='application/json',
    )
    assert response.status_code == 200
    assert 'access' in response.json()
    assert 'refresh' in response.json()
```

### Teste: endpoint protegido rejeita 401 sem token

```python
@pytest.mark.django_db
def test_endpoint_protegido_sem_token(client):
    # Qualquer endpoint protegido; em Phase 1 pode ser criado um /api/ping/ de teste
    response = client.get('/api/ping/')
    assert response.status_code == 401
```

### Teste: CORS bloqueia origem não listada

```python
@pytest.mark.django_db
def test_cors_bloqueia_origem_invalida(client, settings):
    settings.CORS_ALLOWED_ORIGINS = ['http://painel.firmasolar.com.br']
    response = client.options(
        '/api/auth/token/',
        HTTP_ORIGIN='http://atacante.com',
        HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST',
    )
    assert 'Access-Control-Allow-Origin' not in response
```

### Teste: GarantiaUsina.data_fim e GarantiaUsina.ativa

```python
import pytest
from datetime import date
from usinas.models import GarantiaUsina

def test_garantia_data_fim_calculada(usina):  # fixture de usina existente em test_supressao_inteligente.py
    garantia = GarantiaUsina(
        usina=usina,
        data_inicio=date(2024, 1, 15),
        meses=12,
    )
    assert garantia.data_fim == date(2025, 1, 15)

def test_garantia_ativa_quando_dentro_do_prazo(usina):
    garantia = GarantiaUsina(
        usina=usina,
        data_inicio=date(2025, 1, 1),
        meses=120,  # 10 anos
    )
    assert garantia.ativa is True

def test_garantia_inativa_quando_vencida(usina):
    garantia = GarantiaUsina(
        usina=usina,
        data_inicio=date(2020, 1, 1),
        meses=12,
    )
    assert garantia.ativa is False
```

---

## State of the Art

| Abordagem antiga | Abordagem atual | Mudança | Impacto |
|-----------------|-----------------|---------|---------|
| `djangorestframework-jwt` (PyJWT direto) | `djangorestframework-simplejwt` | ~2019 | `drf-jwt` foi descontinuado; simplejwt é o substituto oficial |
| `CORS_ORIGIN_WHITELIST` | `CORS_ALLOWED_ORIGINS` | django-cors-headers 3.0 (2019) | Nome antigo ainda aceito mas deprecado |

---

## Validation Architecture

### Test Framework

| Propriedade | Valor |
|-------------|-------|
| Framework | pytest + pytest-django (já configurado) |
| Config file | `backend_monitoramento/pytest.ini` (existente) |
| Comando rápido | `cd backend_monitoramento && pytest api/tests/ -x -q` |
| Suite completa | `cd backend_monitoramento && pytest -x -q` |

### Mapeamento Requirements → Testes

| Req ID | Comportamento | Tipo de Teste | Comando | Arquivo existe? |
|--------|--------------|---------------|---------|-----------------|
| API-02 | Login com credenciais válidas retorna access + refresh | unitário/integração | `pytest api/tests/test_auth.py::test_login_retorna_tokens -x` | ❌ Wave 0 |
| API-02 | Login com credenciais inválidas retorna 401 | unitário/integração | `pytest api/tests/test_auth.py::test_login_credenciais_invalidas -x` | ❌ Wave 0 |
| API-03 | Refresh com token válido emite novo access | unitário/integração | `pytest api/tests/test_auth.py::test_refresh_emite_novo_access -x` | ❌ Wave 0 |
| API-03 | Token original não reutilizável após rotação | unitário/integração | `pytest api/tests/test_auth.py::test_refresh_token_rotacionado_invalido -x` | ❌ Wave 0 |
| API-04 | Endpoint protegido rejeita sem token (401) | integração | `pytest api/tests/test_auth.py::test_endpoint_protegido_sem_token -x` | ❌ Wave 0 |
| API-05 | CORS bloqueia origem não listada | integração | `pytest api/tests/test_cors.py::test_cors_bloqueia_origem_invalida -x` | ❌ Wave 0 |
| API-05 | CORS permite origem configurada | integração | `pytest api/tests/test_cors.py::test_cors_permite_origem_valida -x` | ❌ Wave 0 |
| GAR-01 | `data_fim` calculada corretamente | unitário | `pytest usinas/tests/test_garantia.py::test_garantia_data_fim_calculada -x` | ❌ Wave 0 |
| GAR-01 | `ativa` retorna True quando dentro do prazo | unitário | `pytest usinas/tests/test_garantia.py::test_garantia_ativa_quando_dentro_do_prazo -x` | ❌ Wave 0 |
| GAR-01 | `ativa` retorna False quando vencida | unitário | `pytest usinas/tests/test_garantia.py::test_garantia_inativa_quando_vencida -x` | ❌ Wave 0 |

### Sampling Rate

- **Por commit de tarefa:** `cd backend_monitoramento && pytest api/tests/ usinas/tests/test_garantia.py -x -q`
- **Por merge de wave:** `cd backend_monitoramento && pytest -x -q`
- **Phase gate:** Suite completa verde antes de `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `backend_monitoramento/api/__init__.py` — app precisa existir para pytest-django encontrar testes
- [ ] `backend_monitoramento/api/tests/__init__.py`
- [ ] `backend_monitoramento/api/tests/test_auth.py` — cobre API-02, API-03, API-04
- [ ] `backend_monitoramento/api/tests/test_cors.py` — cobre API-05
- [ ] `backend_monitoramento/usinas/tests/__init__.py` (se não existir)
- [ ] `backend_monitoramento/usinas/tests/test_garantia.py` — cobre GAR-01

---

## Security Domain

### ASVS Categories Aplicáveis

| Categoria ASVS | Aplica | Controle padrão |
|----------------|--------|-----------------|
| V2 Authentication | sim | `djangorestframework-simplejwt` — JWT com claims padrão |
| V3 Session Management | não | API stateless; sem sessions |
| V4 Access Control | sim | `DEFAULT_PERMISSION_CLASSES = [IsAuthenticated]` — global |
| V5 Input Validation | sim | DRF serializers validam entrada nos endpoints de token |
| V6 Cryptography | sim | simplejwt usa HMAC-SHA256 por padrão; nunca hand-roll |

### Threat Patterns Conhecidos

| Padrão | STRIDE | Mitigação padrão |
|--------|--------|-----------------|
| Token replay após logout | Repudiation | `BLACKLIST_AFTER_ROTATION = True` + tabela de blacklist |
| Brute-force no endpoint de login | Elevation of Privilege | Fora do escopo desta fase; rate limiting é Phase 2+ [ASSUMED] |
| CORS wildcard expondo API a origens maliciosas | Tampering | `CORS_ALLOWED_ORIGINS` restrito; sem `CORS_ALLOW_ALL_ORIGINS` |
| Access token com lifetime longo | Elevation of Privilege | Lifetime = 15 min conforme spec |
| JWT secret fraco | Tampering | `SECRET_KEY` lido de env var; nunca hardcoded |

---

## Environment Availability

| Dependência | Requerida por | Disponível | Versão | Fallback |
|-------------|--------------|------------|--------|----------|
| Python com pip | Instalação dos pacotes | ✓ (via Docker) | 3.x | — |
| PostgreSQL | Migrations + testes de integração | ✓ (docker-compose: `db`) | 16-alpine | — |
| djangorestframework | API-01..06 | ✗ (não instalado) | — | Nenhum — instalar obrigatório |
| djangorestframework-simplejwt | API-02, 03, 04, 06 | ✗ (não instalado) | — | Nenhum — instalar obrigatório |
| django-cors-headers | API-05 | ✗ (não instalado) | — | Nenhum — instalar obrigatório |
| python-dateutil | GarantiaUsina.data_fim | ✓ (dep transitiva do celery) | verificar | Implementação manual com `calendar` |

**Dependências ausentes sem fallback:**
- `djangorestframework`, `djangorestframework-simplejwt`, `django-cors-headers` — todas precisam ser adicionadas a `base.txt` e instaladas.

**Dependências ausentes com fallback:**
- `python-dateutil` — provavelmente disponível via celery; se não estiver, usar `calendar.monthrange` para cálculo de data_fim.

---

## Assumptions Log

| # | Claim | Seção | Risco se errado |
|---|-------|-------|-----------------|
| A1 | `TokenObtainPairView` e `TokenRefreshView` usam `AllowAny` internamente | Architecture Patterns | Views de auth ficariam bloqueadas por `IsAuthenticated` global — precisaria sobrescrever `permission_classes` |
| A2 | `BLACKLIST_AFTER_ROTATION = True` é necessário para "token original não reutilizável" | Architecture Patterns | Se interpretação for diferente, pode-se omitir a tabela de blacklist e simplificar |
| A3 | `python-dateutil` disponível via dependência transitiva do celery | Environment Availability | ImportError em runtime — adicionar explicitamente a `base.txt` |
| A4 | Ordem do middleware CORS: após WhiteNoise, antes de CommonMiddleware | Common Pitfalls | Headers CORS ausentes; browser bloqueia requisições do frontend |

---

## Open Questions

1. **`BLACKLIST_AFTER_ROTATION` e a tabela de blacklist**
   - O que sabemos: a spec exige "token original não reutilizável após rotação"
   - O que está incerto: se o custo de manutenção da tabela de blacklist (que cresce indefinidamente e precisa de purge periódico) é aceitável neste momento
   - Recomendação: habilitar — o requisito API-06 é explícito. Adicionar `rest_framework_simplejwt.token_blacklist` a `INSTALLED_APPS` e criar um task Celery de purge em fase posterior.

2. **Endpoint `/api/ping/` para testar proteção 401**
   - O que sabemos: Phase 1 não tem endpoints de negócio (out of scope)
   - O que está incerto: como testar API-04 sem um endpoint protegido real
   - Recomendação: criar uma view `PingView` mínima apenas para testes, ou usar `TokenVerifyView` do simplejwt que aceita token e retorna 200/401.

---

## Sources

### Primary (HIGH confidence)
- PyPI registry — versões verificadas: `djangorestframework==3.17.1`, `djangorestframework-simplejwt==5.5.1`, `django-cors-headers==4.9.0`
- Codebase do projeto — settings, models, migrations, pytest.ini, requirements lidos diretamente [VERIFIED: codebase]

### Secondary (MEDIUM confidence)
- Padrões de configuração DRF, simplejwt e django-cors-headers baseados em conhecimento de treinamento [ASSUMED — verificar na documentação oficial antes de implementar]

### Tertiary (LOW confidence)
- Nenhum item de baixa confiança identificado — todos os claims críticos foram verificados via codebase ou PyPI.

---

## Metadata

**Breakdown de confiança:**
- Stack padrão: HIGH — versões verificadas no PyPI
- Arquitetura: MEDIUM — padrões de configuração baseados em treinamento; verificar docs oficiais
- Pitfalls: HIGH — identificados diretamente da análise do codebase existente

**Data da pesquisa:** 2026-04-07
**Válido até:** 2026-05-07 (bibliotecas estáveis; versões podem ter patch releases)
