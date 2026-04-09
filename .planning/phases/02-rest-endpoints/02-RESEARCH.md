# Phase 2: REST Endpoints - Research

**Researched:** 2026-04-09
**Domain:** Django REST Framework — ViewSets, Serializers, Filters, Paginação, Testes de API
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01: Organização da app `api` — pacote por domínio**

Views e serializers organizados como pacotes com módulos por domínio:

```
api/
  views/
    __init__.py
    usinas.py
    garantias.py
    inversores.py
    alertas.py
    logs.py
  serializers/
    __init__.py
    usinas.py
    garantias.py
    inversores.py
    alertas.py
    logs.py
  views.py         # (arquivo existente da Phase 1 — manter PingView aqui ou mover para views/__init__.py)
```

**D-02: Roteamento — router central único**

Um único `api/urls.py` com `DefaultRouter` registrando todos os ViewSets. Rotas de ação customizada registradas via `@action` no próprio ViewSet ou como `path()` explícito no mesmo arquivo.

**D-03: Estratégia de filtros — django-filter**

Instalar `django-filter` e ativar `DjangoFilterBackend` no `REST_FRAMEWORK['DEFAULT_FILTER_BACKENDS']`. Filtros declarativos via `FilterSet` por domínio. Validação de tipos automática pelo framework.

Nova dependência aprovada: `django-filter==25.2` (versão atual compatível com Django 5.1).

**D-04: Campo `status_garantia` — 3 valores**

O campo calculado `status_garantia` nas respostas de usina usa exatamente 3 valores:
- `"ativa"` — garantia cadastrada e `data_fim >= hoje`
- `"vencida"` — garantia cadastrada e `data_fim < hoje`
- `"sem_garantia"` — nenhuma `GarantiaUsina` associada

Valor calculado no serializer a partir da property `ativa` e da existência de `GarantiaUsina` — não persistido no banco.

**D-05: Parâmetro de filtro em /api/garantias/**

Parâmetro `filtro` com valores:
- `ativas` — garantias com `data_fim >= hoje`
- `vencendo` — garantias com `data_fim` nos próximos 30 dias (inclui ativas)
- `vencidas` — garantias com `data_fim < hoje`

Sem valor: retorna todas as garantias.

**D-06: Paginação de snapshots históricos**

`PageNumberPagination` com `page_size = 100`. Navegação via `?page=N`. Classe de paginação específica para essas views (não alterar o padrão global de 20).

**D-07: Paginação global dos endpoints de listagem**

Verificar o valor atual de `PAGE_SIZE` no `base.py` (atualmente: 20) e ajustar se necessário para os endpoints de listagem desta fase. Planner propõe ajuste justificado.

### Claude's Discretion

- Estrutura interna dos serializers (aninhados vs. separados por operação lista/detalhe)
- Cálculo do campo `com_garantia` em alertas — anotação SQL via `annotate()` ou property no serializer
- Ordenação padrão de cada endpoint
- Formato dos campos `data_fim` e `dias_restantes` na resposta
- Campos incluídos no serializer de lista vs. detalhe

### Deferred Ideas (OUT OF SCOPE)

Nenhuma ideia fora do escopo foi levantada durante a discussão.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Descrição | Suporte na Research |
|----|-----------|---------------------|
| USN-01 | Lista usinas com filtros por provedor, ativo e status de garantia | D-03 (django-filter), D-04 (status_garantia) |
| USN-02 | Detalhe de usina com inversores e último snapshot | Serializer aninhado, `select_related`/`prefetch_related` |
| USN-03 | PATCH para atualizar nome e capacidade da usina | ViewSet com `partial_update`, campos restritos via serializer |
| USN-04 | Listagem exibe status de garantia (ativa/vencida/sem_garantia) | `SerializerMethodField`, D-04 |
| USN-05 | Histórico temporal de snapshots de uma usina | `@action` no ViewSet + paginação D-06 |
| GAR-02 | PUT para criar ou substituir garantia de uma usina | Upsert via `get_or_create` / `update_or_create`, `@action` |
| GAR-03 | Lista garantias com filtros: ativas, vencendo, vencidas | Filtro manual via `get_queryset()` com parâmetro `filtro` |
| GAR-04 | Resposta inclui `dias_restantes` calculado no momento | `SerializerMethodField` lendo property do model |
| GAR-05 | Usina sem garantia não aparece no dashboard de garantia | Filtros de queryset — sem interferência na coleta |
| GAR-06 | Usina com garantia ativa aparece no dashboard de garantia | Filtros de queryset |
| INV-01 | Lista inversores com filtros por usina, provedor e modelo | D-03 (django-filter), FK traversal |
| INV-02 | Detalhe de inversor com último snapshot completo | `select_related('ultimo_snapshot')`, serializer |
| INV-03 | Histórico de snapshots de um inversor | `@action` no ViewSet + paginação D-06 |
| ALT-01 | Lista alertas com filtros por estado, nível e usina | D-03 (django-filter) |
| ALT-02 | Detalhe de alerta | Serializer de detalhe com todos os campos |
| ALT-03 | PATCH para estado e anotações do alerta | `partial_update`, validação de transição de estado |
| ALT-04 | Campo `com_garantia` em todas as respostas de alerta | `annotate()` via `Exists()` ou `SerializerMethodField` |
| LOG-01 | Lista últimos ciclos de coleta com status e timestamp | `ListAPIView` com `LogColeta`, sem filtros complexos |
</phase_requirements>

---

## Summary

A Phase 2 constrói a camada REST operacional completa sobre a infraestrutura estabelecida na Phase 1. O projeto já tem DRF 3.17, simplejwt 5.5 e autenticação JWT global configurados — esta fase apenas adiciona ViewSets, serializers e filtros. A decisão mais crítica já está resolvida (D-01 a D-07 do CONTEXT.md); o trabalho é implementação direta sem escolhas arquiteturais abertas.

O padrão dominante é `ModelViewSet` com `@action` para sub-recursos (snapshots e garantia por usina). O campo `status_garantia` em usinas e `com_garantia` em alertas exigem atenção especial: são campos calculados que dependem de `GarantiaUsina` — potencial N+1 se não houver `select_related`/`prefetch_related` correto.

`django-filter 25.2` não está instalado — é a única nova dependência desta fase. Todos os outros elementos (models, DRF, JWT, paginação global) já estão prontos. O test settings usa SQLite em memória, que é suficiente para todos os testes desta fase.

**Recomendação principal:** Usar `prefetch_related('garantia')` na queryset de usinas e `annotate(com_garantia=Exists(...))` na queryset de alertas para evitar N+1, dada a frequência de acesso esperada.

---

## Standard Stack

### Core

| Biblioteca | Versão | Propósito | Status |
|------------|--------|-----------|--------|
| djangorestframework | 3.17.x | ViewSets, Serializers, Router, Paginação | Instalado (Phase 1) |
| django-filter | 25.2 | Filtros declarativos via FilterSet | **A instalar** |
| djangorestframework-simplejwt | 5.5.x | JWT authentication (global) | Instalado (Phase 1) |

[VERIFIED: pip index] — `django-filter 25.2` é a versão atual (2025). Compatível com Django 5.1 e DRF 3.17.

### Dependências já presentes relevantes

| Biblioteca | Versão | Relevância para Phase 2 |
|------------|--------|-------------------------|
| python-dateutil | 2.9.x | `relativedelta` usado em `GarantiaUsina.data_fim` |
| django | 5.1.x | `Exists`, `OuterRef`, `annotate` para `com_garantia` |

### Não instalar

| Alternativa | Razão para não usar |
|-------------|---------------------|
| `dj-rest-auth` | Desnecessário — auth já implementada com simplejwt puro |
| `drf-spectacular` | Geração de schema/OpenAPI fora do escopo |
| `django-rest-multiple-models` | Não há endpoints multi-model nesta fase |

**Instalação da nova dependência:**
```bash
pip install django-filter==25.2
```

Adicionar em `backend_monitoramento/requirements/base.txt`:
```
django-filter==25.*
```

---

## Architecture Patterns

### Estrutura de arquivos (Decisão D-01)

```
backend_monitoramento/api/
├── views.py                  # PingView existente (Phase 1) — manter aqui
├── views/
│   ├── __init__.py
│   ├── usinas.py             # UsinaViewSet, SnapshotUsinaListView
│   ├── garantias.py          # GarantiaUsinaView, GarantiaListView
│   ├── inversores.py         # InversorViewSet, SnapshotInversorListView
│   ├── alertas.py            # AlertaViewSet
│   └── logs.py               # LogColetaListView
├── serializers/
│   ├── __init__.py
│   ├── usinas.py             # UsinaListSerializer, UsinaDetalheSerializer, SnapshotUsinaSerializer
│   ├── garantias.py          # GarantiaUsinaSerializer
│   ├── inversores.py         # InversorListSerializer, InversorDetalheSerializer, SnapshotInversorSerializer
│   ├── alertas.py            # AlertaListSerializer, AlertaDetalheSerializer, AlertaAtualizarSerializer
│   └── logs.py               # LogColetaSerializer
├── filters/
│   ├── __init__.py
│   ├── usinas.py             # UsinaFilterSet
│   ├── inversores.py         # InversorFilterSet
│   └── alertas.py            # AlertaFilterSet
├── urls.py                   # DefaultRouter + paths explícitos
├── apps.py
└── tests/
    ├── __init__.py
    ├── test_auth.py           # Existente (Phase 1)
    ├── test_cors.py           # Existente (Phase 1)
    ├── conftest.py            # Fixtures compartilhadas (credencial, usina, inversor, alerta, garantia)
    ├── test_usinas.py
    ├── test_garantias.py
    ├── test_inversores.py
    ├── test_alertas.py
    └── test_logs.py
```

### Pattern 1: ViewSet com @action para sub-recursos

**O que é:** `ModelViewSet` cobre list/retrieve/partial_update. Ações adicionais (snapshots, garantia) são `@action` decoradas no mesmo ViewSet — evita classes separadas.

**Quando usar:** Sub-recursos acessados via URL aninhada (`/usinas/{id}/snapshots/`, `/usinas/{id}/garantia/`).

```python
# Source: DRF docs — https://www.django-rest-framework.org/api-guide/viewsets/#marking-extra-actions-for-routing
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

class UsinaViewSet(viewsets.ModelViewSet):
    queryset = Usina.objects.select_related('ultimo_snapshot', 'garantia').prefetch_related('inversores')
    http_method_names = ['get', 'patch', 'head', 'options']  # sem POST/DELETE

    @action(detail=True, methods=['get'], url_path='snapshots')
    def snapshots(self, request, pk=None):
        usina = self.get_object()
        qs = usina.snapshots.order_by('-coletado_em')
        page = self.paginate_queryset(qs)
        serializer = SnapshotUsinaSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['put'], url_path='garantia')
    def garantia(self, request, pk=None):
        usina = self.get_object()
        garantia, _ = GarantiaUsina.objects.update_or_create(
            usina=usina,
            defaults={
                'data_inicio': request.data['data_inicio'],
                'meses': request.data['meses'],
                'observacoes': request.data.get('observacoes', ''),
            },
        )
        serializer = GarantiaUsinaSerializer(garantia)
        return Response(serializer.data)
```

[ASSUMED] — padrão de `update_or_create` para upsert de OneToOne; verificado como correto contra o model, mas exemplo de código não extraído de documentação oficial nesta sessão.

### Pattern 2: Serializer separado para lista vs. detalhe

**O que é:** Dois serializers por recurso — um leve para listagem (campos essenciais), um completo para detalhe.

**Por que:** `GET /api/usinas/` pode retornar centenas de registros; incluir inversores + snapshots em cada item seria um payload enorme. `GET /api/usinas/{id}/` retorna tudo.

```python
# Serializer de lista — campos mínimos + status_garantia
class UsinaListSerializer(serializers.ModelSerializer):
    status_garantia = serializers.SerializerMethodField()

    class Meta:
        model = Usina
        fields = ['id', 'nome', 'provedor', 'capacidade_kwp', 'ativo', 'status_garantia']

    def get_status_garantia(self, obj) -> str:
        try:
            garantia = obj.garantia  # acesso via related_name — prefetch necessário
        except GarantiaUsina.DoesNotExist:
            return 'sem_garantia'
        return 'ativa' if garantia.ativa else 'vencida'

# Serializer de detalhe — inclui inversores e último snapshot
class UsinaDetalheSerializer(serializers.ModelSerializer):
    status_garantia = serializers.SerializerMethodField()
    inversores = InversorListSerializer(many=True, read_only=True)
    ultimo_snapshot = SnapshotUsinaSerializer(read_only=True)
    # ...
```

### Pattern 3: Filtros declarativos com django-filter

**O que é:** `FilterSet` por domínio, ativado globalmente via `DEFAULT_FILTER_BACKENDS`.

**Configuração em settings:**
```python
REST_FRAMEWORK = {
    # ... existente ...
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
}
```

**FilterSet de usinas:**
```python
import django_filters
from usinas.models import Usina

class UsinaFilterSet(django_filters.FilterSet):
    provedor = django_filters.CharFilter(field_name='provedor', lookup_expr='exact')
    ativo = django_filters.BooleanFilter(field_name='ativo')
    status_garantia = django_filters.CharFilter(method='filtrar_por_status_garantia')

    def filtrar_por_status_garantia(self, queryset, name, value):
        hoje = timezone.now().date()
        if value == 'sem_garantia':
            return queryset.filter(garantia__isnull=True)
        elif value == 'ativa':
            return queryset.filter(garantia__isnull=False, garantia__data_inicio__lte=hoje)
            # Nota: data_fim é property — não pode ser filtrada pelo ORM diretamente
            # Precisa de anotação ou cálculo alternativo — ver Pitfall 2
        elif value == 'vencida':
            return queryset.filter(garantia__isnull=False)  # + exclusão das ativas
        return queryset

    class Meta:
        model = Usina
        fields = ['provedor', 'ativo']
```

### Pattern 4: Campo `com_garantia` em alertas via annotate

**O que é:** `Exists()` subquery para marcar alertas cujas usinas têm garantia ativa.

**Por que annotate em vez de SerializerMethodField:** Evita N+1 — com `annotate`, uma única query resolve o campo para toda a listagem. SerializerMethodField causaria 1 query extra por alerta.

```python
from django.db.models import Exists, OuterRef
from django.utils import timezone
from usinas.models import GarantiaUsina

class AlertaViewSet(viewsets.ModelViewSet):
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_queryset(self):
        hoje = timezone.now().date()
        # Subquery: existe GarantiaUsina para a usina do alerta?
        # data_fim é property — não coluna, então filtro é por data calculada
        garantia_ativa = GarantiaUsina.objects.filter(
            usina=OuterRef('usina'),
        )
        return Alerta.objects.select_related('usina', 'catalogo_alarme').annotate(
            com_garantia=Exists(garantia_ativa)
        )
```

**Limitação conhecida:** `data_fim` é property calculada (não coluna). O filtro de "ativa" em `com_garantia` precisará de uma das abordagens a seguir — ver Pitfall 2.

### Pattern 5: Filtro `?filtro=` em /api/garantias/ via get_queryset manual

O endpoint de garantias não usa FilterSet pois o parâmetro `filtro` não mapeia diretamente para campos ORM (porque `data_fim` é property). O filtro é aplicado em `get_queryset()`:

```python
class GarantiaListView(generics.ListAPIView):
    serializer_class = GarantiaUsinaSerializer

    def get_queryset(self):
        from django.utils import timezone
        from dateutil.relativedelta import relativedelta

        qs = GarantiaUsina.objects.select_related('usina')
        filtro = self.request.query_params.get('filtro')
        hoje = timezone.now().date()

        if filtro == 'ativas':
            # data_fim = data_inicio + relativedelta(months=meses)
            # Não é coluna — precisamos filtrar via anotação ou expression
            # Abordagem: anotar data_fim como ExpressionWrapper
            pass
        elif filtro == 'vencendo':
            # data_fim entre hoje e hoje+30d
            pass
        elif filtro == 'vencidas':
            # data_fim < hoje
            pass
        return qs
```

**Solução para `data_fim` como expression ORM — ver Pitfall 2 e Code Examples.**

### Pattern 6: Paginação específica para snapshots

```python
from rest_framework.pagination import PageNumberPagination

class PaginacaoSnapshots(PageNumberPagination):
    """Paginação para endpoints de histórico de snapshots."""
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 500
```

### Anti-Patterns a Evitar

- **N+1 em status_garantia:** Acessar `obj.garantia` no serializer sem `prefetch_related('garantia')` no queryset causa 1 query por usina na listagem.
- **N+1 em com_garantia:** Usar `SerializerMethodField` para `com_garantia` em alertas sem annotate causa 1 query por alerta.
- **Filtrar data_fim sem anotação:** `data_fim` é property Python, não coluna SQL. Filtros ORM diretos falham silenciosamente.
- **ViewSet sem restrição de métodos HTTP:** `ModelViewSet` expõe create/destroy por padrão — desativar com `http_method_names`.
- **Serializer único para lista e detalhe:** Payload excessivo em listagens de centenas de registros.

---

## Don't Hand-Roll

| Problema | Não construir | Usar em vez disso | Por que |
|----------|--------------|-------------------|---------|
| Filtros por campo com validação de tipo | Parser manual de query params | `django-filter` + `FilterSet` | Validação automática, integração com DRF, documentação automática |
| Paginação | Slicing manual com offset | `PageNumberPagination` do DRF | Headers `Link`, meta `count`, integração com `get_paginated_response` |
| Roteamento de ViewSets | `path()` manual para cada ação | `DefaultRouter` | Gera automaticamente list/detail/actions |
| Serialização de UUIDs | `str(obj.id)` no response | `UUIDField` do DRF | Formato correto, consistência |
| Upsert OneToOne | `try/except` create/update | `update_or_create()` | Atômico, menos código, sem race condition |

---

## Pitfall 1: `data_fim` como property — não é coluna SQL

**O que dá errado:** Tentar filtrar garantias por `data_fim` com `filter(data_fim__gte=hoje)` resulta em `FieldError: Cannot resolve keyword 'data_fim' into field`.

**Por que acontece:** `data_fim` é `@property` em `GarantiaUsina`, calculada como `data_inicio + relativedelta(months=meses)`. Não existe como coluna no banco.

**Como evitar:** Para filtragem ORM, calcular a data equivalente no Python e filtrar pelos campos reais (`data_inicio`, `meses`), ou usar `ExpressionWrapper` com `F` expressions para a anotação.

**Solução recomendada para filtros de garantia:**

```python
from django.db.models import ExpressionWrapper, DateField, F
from django.db.models.functions import TruncDate
from dateutil.relativedelta import relativedelta
from django.utils import timezone

# Não é possível usar relativedelta em ORM puro no PostgreSQL.
# Solução alternativa: calcular as datas limites em Python e filtrar por data_inicio+meses.

def _qs_garantias_ativas(qs, hoje):
    """Retorna apenas garantias onde data_inicio + meses >= hoje."""
    # Como data_fim = data_inicio + N meses, e meses é inteiro,
    # usar PostgreSQL interval com Cast ou filtrar via Python em memória
    # Para volumes pequenos (<1000 garantias), filtrar em Python é aceitável.
    # Para escala, usar anotação com RawSQL ou migrar data_fim para coluna.
    return [g for g in qs if g.data_fim >= hoje]
```

**Nota para o planner:** Para esta fase (volume operacional pequeno — dezenas a centenas de usinas), filtrar em Python após `qs.all()` é aceitável e mais simples. Se houver crescimento significativo, migrar `data_fim` para coluna calculada é a solução adequada — registrar em DECISIONS.md.

[VERIFIED: codebase] — confirmado que `data_fim` é `@property` em `usinas/models.py` linha 191.

---

## Pitfall 2: N+1 em `com_garantia` com SerializerMethodField

**O que dá errado:** `SerializerMethodField` acessa `alerta.usina.garantia` para cada alerta — 1 query extra por item na listagem.

**Por que acontece:** Django não carrega relacionamentos automaticamente; cada acesso `alerta.usina.garantia` dispara uma nova query.

**Como evitar:** Usar `annotate(com_garantia=Exists(...))` no queryset da view, não no serializer.

**Limitação:** Como `GarantiaUsina.ativa` é property (não coluna), a subquery `Exists()` detecta apenas a *existência* de uma garantia, não se está ativa. Para verificar vigência em SQL puro, é necessário incluir filtro por data no `OuterRef`. A solução viável:

```python
# Anotação que verifica existência de garantia (sem filtro de ativa — simplificação aceitável)
# O campo com_garantia refletirá "tem garantia cadastrada", não "garantia ativa"
# Para "garantia ativa", filtrar pela data calculada em Python no serializer para o detalhe

# Alternativa para listagem com volume controlado:
# SELECT_RELATED + check em serializer (aceitável se qs tem <500 alertas)
```

**Recomendação para o planner:** Para ALT-04 (`com_garantia`), usar `select_related('usina__garantia')` no queryset + `SerializerMethodField` que acessa `obj.usina.garantia` — isso evita N+1 via join único. `Exists()` puro detecta apenas existência sem `ativa`. O contexto indica volume operacional pequeno.

---

## Pitfall 3: `UsinaViewSet` expõe create/delete por acidente

**O que dá errado:** `ModelViewSet` herda `create` (POST) e `destroy` (DELETE). Usinas são criadas via coleta automática, não via API. Expor esses endpoints é risco de segurança.

**Como evitar:**
```python
class UsinaViewSet(viewsets.ModelViewSet):
    http_method_names = ['get', 'patch', 'head', 'options']
```

O mesmo se aplica a `InversorViewSet` (read-only) e `AlertaViewSet` (sem delete).

---

## Pitfall 4: Filtro por `status_garantia` requer annotate ou queryset customizado

**O que dá errado:** `UsinaFilterSet` tenta `filter(status_garantia='ativa')` mas `status_garantia` não é campo do model.

**Como evitar:** Usar `method=` no filtro do FilterSet para implementar lógica custom:

```python
class UsinaFilterSet(django_filters.FilterSet):
    status_garantia = django_filters.CharFilter(method='filtrar_status_garantia')

    def filtrar_status_garantia(self, queryset, name, value):
        if value == 'sem_garantia':
            return queryset.filter(garantia__isnull=True)
        # Para 'ativa' e 'vencida': sem coluna data_fim, filtrar IDs em Python
        # (volume controlado) ou usar anotação PostgreSQL
        ...
```

---

## Pitfall 5: `PAGE_SIZE=20` inadequado para snapshots

**O que dá errado:** Usar paginação global (20) para histórico de snapshots retorna apenas 20 pontos — insuficiente para visualização temporal.

**Como evitar:** D-06 já define `PageNumberPagination` com `page_size=100` como classe separada para snapshots. Não alterar o `PAGE_SIZE` global.

---

## Code Examples

### Configuração de django-filter em settings

```python
# backend_monitoramento/config/settings/base.py
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}
```

[ASSUMED] — padrão de configuração; verificável contra docs do django-filter em https://django-filter.readthedocs.io/en/stable/guide/rest_framework.html

### DefaultRouter com paths explícitos (D-02)

```python
# backend_monitoramento/api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import PingView
from .views.usinas import UsinaViewSet
from .views.inversores import InversorViewSet
from .views.alertas import AlertaViewSet
from .views.garantias import GarantiaListView
from .views.logs import LogColetaListView

router = DefaultRouter()
router.register('usinas', UsinaViewSet, basename='usina')
router.register('inversores', InversorViewSet, basename='inversor')
router.register('alertas', AlertaViewSet, basename='alerta')

urlpatterns = [
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('ping/', PingView.as_view(), name='api_ping'),
    path('garantias/', GarantiaListView.as_view(), name='garantia-list'),
    path('coleta/logs/', LogColetaListView.as_view(), name='log-coleta-list'),
    path('', include(router.urls)),
]
```

### Serializer de detalhe de Usina

```python
# api/serializers/usinas.py
from rest_framework import serializers
from usinas.models import Usina, SnapshotUsina, GarantiaUsina

class SnapshotUsinaSerializer(serializers.ModelSerializer):
    class Meta:
        model = SnapshotUsina
        fields = [
            'id', 'coletado_em', 'potencia_kw', 'energia_hoje_kwh',
            'energia_mes_kwh', 'energia_total_kwh', 'status',
            'qtd_inversores', 'qtd_inversores_online', 'qtd_alertas',
        ]

class UsinaDetalheSerializer(serializers.ModelSerializer):
    status_garantia = serializers.SerializerMethodField()
    ultimo_snapshot = SnapshotUsinaSerializer(read_only=True)
    inversores = serializers.SerializerMethodField()

    class Meta:
        model = Usina
        fields = [
            'id', 'nome', 'provedor', 'capacidade_kwp', 'ativo',
            'fuso_horario', 'endereco', 'status_garantia',
            'ultimo_snapshot', 'inversores', 'criado_em', 'atualizado_em',
        ]

    def get_status_garantia(self, obj) -> str:
        try:
            garantia = obj.garantia
        except GarantiaUsina.DoesNotExist:
            return 'sem_garantia'
        return 'ativa' if garantia.ativa else 'vencida'

    def get_inversores(self, obj):
        from .inversores import InversorListSerializer
        return InversorListSerializer(
            obj.inversores.select_related('ultimo_snapshot').all(),
            many=True,
        ).data
```

### Teste padrão de endpoint autenticado

```python
# api/tests/test_usinas.py
import pytest
from django.urls import reverse

@pytest.mark.django_db
class TestUsinaList:
    """Testes para GET /api/usinas/ — USN-01, USN-04."""

    def test_lista_usinas_requer_autenticacao(self, client):
        """USN-01: sem token retorna 401."""
        response = client.get(reverse('usina-list'))
        assert response.status_code == 401

    def test_lista_usinas_autenticado(self, client, tokens, usina):
        """USN-01: com token retorna lista com campo status_garantia."""
        response = client.get(
            reverse('usina-list'),
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        data = response.json()
        assert data['count'] >= 1
        assert 'status_garantia' in data['results'][0]

    def test_filtro_por_provedor(self, client, tokens, usina):
        """USN-01: filtro por provedor retorna apenas usinas do provedor."""
        response = client.get(
            reverse('usina-list'),
            {'provedor': usina.provedor},
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        for item in response.json()['results']:
            assert item['provedor'] == usina.provedor

    def test_status_garantia_sem_garantia(self, client, tokens, usina):
        """USN-04: usina sem GarantiaUsina retorna status_garantia='sem_garantia'."""
        response = client.get(
            f"/api/usinas/{usina.id}/",
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        assert response.json()['status_garantia'] == 'sem_garantia'
```

### conftest.py compartilhado (Wave 0)

```python
# api/tests/conftest.py
import pytest
from provedores.models import CredencialProvedor
from usinas.models import Usina, Inversor, GarantiaUsina
from alertas.models import Alerta, CatalogoAlarme
from coleta.models import LogColeta
from django.utils import timezone
import datetime

@pytest.fixture
def credencial(db):
    return CredencialProvedor.objects.create(
        provedor='solis',
        credenciais_enc='placeholder',
        ativo=True,
    )

@pytest.fixture
def usina(db, credencial):
    return Usina.objects.create(
        id_usina_provedor='test-001',
        provedor='solis',
        credencial=credencial,
        nome='Usina Teste',
        capacidade_kwp=10.0,
        fuso_horario='America/Sao_Paulo',
        ativo=True,
    )

@pytest.fixture
def garantia(db, usina):
    return GarantiaUsina.objects.create(
        usina=usina,
        data_inicio=datetime.date.today() - datetime.timedelta(days=30),
        meses=24,
    )

@pytest.fixture
def tokens(client, django_user_model):
    django_user_model.objects.create_user(username='admin', password='senha123')
    response = client.post(
        '/api/auth/token/',
        {'username': 'admin', 'password': 'senha123'},
        content_type='application/json',
    )
    return response.json()
```

---

## Estado Atual da Infraestrutura (Phase 1 entregue)

| Item | Estado | Referência |
|------|--------|-----------|
| DRF 3.17.x | Instalado e configurado | `requirements/base.txt`, `settings/base.py` |
| simplejwt 5.5.x | Configurado com blacklist | `settings/base.py` |
| django-cors-headers 4.9.x | Configurado sem wildcard | `settings/base.py` |
| App `api` | Criada com `PingView`, auth URLs | `api/urls.py`, `api/views.py` |
| `GarantiaUsina` | Model criado com properties | `usinas/models.py` |
| Migration 0002_garantiausina | Gerada (aplicar no deploy) | `usinas/migrations/` |
| `IsAuthenticated` global | Ativo para todos os endpoints | `settings/base.py` |
| `PAGE_SIZE=20` | Configurado globalmente | `settings/base.py` |
| SQLite in-memory para testes | Configurado | `settings/test.py` |

[VERIFIED: codebase] — leitura direta dos arquivos.

---

## Paginação — Decisão sobre PAGE_SIZE global

O `PAGE_SIZE=20` global é razoável para:
- Listagem de usinas (dezenas a centenas)
- Listagem de alertas (pode ter muitos)
- Listagem de inversores (dezenas por usina)
- Listagem de garantias (igual ao número de usinas)
- Logs de coleta (últimos ciclos — 20 é adequado)

**Recomendação para o planner:** Manter `PAGE_SIZE=20` como padrão global. Para snapshots, usar `PaginacaoSnapshots` com `page_size=100` (D-06). Considerar adicionar `page_size_query_param='page_size'` no padrão global para flexibilidade do cliente.

---

## Ambiente de Execução

| Dependência | Requerida por | Disponível | Versão | Fallback |
|-------------|--------------|-----------|--------|----------|
| PostgreSQL | Produção | Não (VPS) | — | SQLite :memory: para testes |
| Python 3.10 | Runtime | Sim (verificado via pytest) | 3.10.x | — |
| django-filter | D-03 | Não instalada | — | Instalar como Wave 0 |
| pytest / pytest-django | Testes | Sim (Phase 1 usou) | 8.x / 4.x | — |

[VERIFIED: codebase] — `pytest.ini` usa `config.settings.test` que configura SQLite in-memory. Testes da Phase 1 passaram sem PostgreSQL local.

---

## Validation Architecture

### Test Framework

| Propriedade | Valor |
|-------------|-------|
| Framework | pytest 8.x + pytest-django 4.x |
| Config | `backend_monitoramento/pytest.ini` |
| Settings de teste | `config.settings.test` (SQLite :memory:) |
| Comando rápido | `cd backend_monitoramento && pytest api/tests/ -x --tb=short` |
| Suite completa | `cd backend_monitoramento && pytest --tb=short` |

### Mapeamento Requisito → Teste

| Req ID | Comportamento | Tipo | Comando | Arquivo |
|--------|--------------|------|---------|---------|
| USN-01 | Lista com filtros por provedor, ativo, status_garantia | integration | `pytest api/tests/test_usinas.py -x` | Wave 0 |
| USN-02 | Detalhe retorna inversores e último snapshot | integration | `pytest api/tests/test_usinas.py::TestUsinaDetalhe -x` | Wave 0 |
| USN-03 | PATCH atualiza nome e capacidade | integration | `pytest api/tests/test_usinas.py::TestUsinaPatch -x` | Wave 0 |
| USN-04 | Campo status_garantia com 3 valores | integration | `pytest api/tests/test_usinas.py -x -k status_garantia` | Wave 0 |
| USN-05 | Histórico de snapshots paginado | integration | `pytest api/tests/test_usinas.py::TestUsinaSnapshots -x` | Wave 0 |
| GAR-02 | PUT cria ou substitui garantia | integration | `pytest api/tests/test_garantias.py::TestGarantiaUpsert -x` | Wave 0 |
| GAR-03 | Lista com filtro ativas/vencendo/vencidas | integration | `pytest api/tests/test_garantias.py::TestGarantiaFiltros -x` | Wave 0 |
| GAR-04 | Resposta inclui dias_restantes correto | integration | `pytest api/tests/test_garantias.py -x -k dias_restantes` | Wave 0 |
| GAR-05/06 | Garantia não interfere na visibilidade | integration | `pytest api/tests/test_garantias.py::TestGarantiaVisibilidade -x` | Wave 0 |
| INV-01 | Lista inversores com filtros | integration | `pytest api/tests/test_inversores.py -x` | Wave 0 |
| INV-02 | Detalhe com último snapshot completo | integration | `pytest api/tests/test_inversores.py::TestInversorDetalhe -x` | Wave 0 |
| INV-03 | Histórico de snapshots paginado | integration | `pytest api/tests/test_inversores.py::TestInversorSnapshots -x` | Wave 0 |
| ALT-01 | Lista alertas com filtros | integration | `pytest api/tests/test_alertas.py -x` | Wave 0 |
| ALT-02 | Detalhe de alerta | integration | `pytest api/tests/test_alertas.py::TestAlertaDetalhe -x` | Wave 0 |
| ALT-03 | PATCH estado e anotações | integration | `pytest api/tests/test_alertas.py::TestAlertaPatch -x` | Wave 0 |
| ALT-04 | Campo com_garantia em todas as respostas | integration | `pytest api/tests/test_alertas.py -x -k com_garantia` | Wave 0 |
| LOG-01 | Lista logs de coleta com status e timestamp | integration | `pytest api/tests/test_logs.py -x` | Wave 0 |

### Taxa de Amostragem

- **Por commit de task:** `cd backend_monitoramento && pytest api/tests/ -x --tb=short`
- **Por merge de wave:** `cd backend_monitoramento && pytest --tb=short`
- **Gate da fase:** Suite completa verde antes do `/gsd-verify-work`

### Gaps do Wave 0

- [ ] `api/tests/conftest.py` — fixtures compartilhadas (credencial, usina, inversor, garantia, alerta, tokens)
- [ ] `api/tests/test_usinas.py` — cobre USN-01..05
- [ ] `api/tests/test_garantias.py` — cobre GAR-02..06
- [ ] `api/tests/test_inversores.py` — cobre INV-01..03
- [ ] `api/tests/test_alertas.py` — cobre ALT-01..04
- [ ] `api/tests/test_logs.py` — cobre LOG-01
- [ ] `api/filters/__init__.py`, `api/filters/usinas.py`, etc. — módulos de filtros
- [ ] Instalar `django-filter==25.*` em `requirements/base.txt`

---

## Security Domain

### Categorias ASVS Aplicáveis

| Categoria ASVS | Aplica | Controle padrão |
|----------------|--------|----------------|
| V2 Authentication | sim | simplejwt global (Phase 1) |
| V3 Session Management | não | sem sessão — JWT stateless |
| V4 Access Control | sim | `IsAuthenticated` global — todos os endpoints protegidos |
| V5 Input Validation | sim | DRF serializers com validação de tipo; django-filter com coerção automática |
| V6 Cryptography | não | sem operações criptográficas nesta fase |

### Padrões de Ameaça Relevantes

| Padrão | STRIDE | Mitigação padrão |
|--------|--------|-----------------|
| Acesso não autenticado | Elevation of Privilege | `IsAuthenticated` global já configurado |
| PATCH de campos não permitidos | Tampering | Serializer de escrita com `fields` explícitos (não `__all__`) |
| Filtros com injection | Tampering | django-filter com tipos declarados — sem SQL manual |
| Resposta com dados internos | Information Disclosure | Serializer lista/detalhe separados; `payload_bruto` excluído explicitamente |
| Endpoint fora do escopo exposto | Elevation of Privilege | `http_method_names` restrito por ViewSet |

**Campo `payload_bruto`** presente em `SnapshotUsina`, `SnapshotInversor` e `Alerta` — jamais incluir em serializers. É JSON bruto do provedor com dados potencialmente sensíveis.

[VERIFIED: codebase] — campo `payload_bruto = models.JSONField(default=dict)` confirmado nos três models.

---

## Project Constraints (from CLAUDE.md)

| Diretriz | Impacto nesta fase |
|----------|-------------------|
| Nenhuma lógica de negócio em views — extrair para serviços ou use cases | Cálculos de `status_garantia` e `com_garantia` ficam no serializer ou em métodos de queryset, não em views |
| Dependências externas: informar e justificar antes de adicionar | `django-filter` já aprovado no CONTEXT.md D-03 |
| Toda entrada do usuário é tratada como não confiável — validar e sanitizar | Serializers de escrita com campos explícitos; django-filter com tipos declarados |
| Autenticação verificada em toda rota, sem exceção | Garantido pelo `IsAuthenticated` global; nenhum endpoint com `AllowAny` |
| Nunca expor detalhes internos em erros ao cliente | DRF retorna erros genéricos por padrão; não sobrescrever exception handler |
| Código sem N+1 queries — verificar plano de execução | `select_related`/`prefetch_related` em todos os querysets; `annotate` para campos derivados |
| Nomes em português (pt-BR) | Todos os módulos, classes, variáveis e comentários em português |
| Funções >30 linhas provavelmente fazem mais de uma coisa | Serializers e views devem ser compactos; lógica de filtro extraída para `FilterSet` |
| Nunca hardcodar valores que possam mudar por ambiente | `page_size` pode ser externalizado se necessário; sem URLs hardcodadas |
| Cada decisão arquitetural não trivial em DECISIONS.md | Decisão sobre filtro de `data_fim` em Python vs. coluna deve ser registrada |

---

## Assumptions Log

| # | Claim | Seção | Risco se Errado |
|---|-------|-------|-----------------|
| A1 | Filtrar garantias por `data_fim` em Python (não ORM) é aceitável para o volume atual | Pitfall 1, Pattern 5 | Performance degradada em produção com muitas garantias (improvável neste contexto) |
| A2 | `select_related('usina__garantia')` + check em serializer é suficiente para `com_garantia` sem N+1 | Pitfall 2 | N+1 em alertas se volume for >500 alertas por página (improvável com PAGE_SIZE=20) |
| A3 | `PingView` deve permanecer em `api/views.py` (não mover para `views/__init__.py`) | Arquitetura | Sem risco funcional; apenas convenção |
| A4 | `page_size_query_param` não precisa ser configurado globalmente | Paginação | Clientes não podem ajustar tamanho de página sem isso |

---

## Open Questions

1. **`status_garantia` como filtro ORM — solução definitiva para `data_fim`**
   - O que sabemos: `data_fim` é property calculada via `relativedelta`; não há coluna no banco
   - O que não está claro: se o planner quer anotação SQL (mais complexa, escalável) ou filtro Python (simples, aceitável para volume atual)
   - Recomendação: filtro Python para esta fase; registrar em DECISIONS.md com nota de quando migrar

2. **`http_method_names` vs. mixins para restringir verbos HTTP**
   - O que sabemos: duas abordagens válidas no DRF — `http_method_names` ou herdar apenas os mixins necessários
   - O que não está claro: qual o planner prefere
   - Recomendação: `http_method_names` por ser mais explícito e menos código

---

## Sources

### Primary (HIGH confidence)

- Leitura direta do codebase — `usinas/models.py`, `alertas/models.py`, `coleta/models.py`, `provedores/models.py`, `config/settings/base.py`, `api/urls.py`, `api/views.py`, `api/tests/test_auth.py`
- `.planning/phases/01-api-infrastructure/01-01-SUMMARY.md` — o que foi entregue
- `.planning/codebase/CONVENTIONS.md` — padrões de nomenclatura
- `.planning/codebase/TESTING.md` — framework de testes
- `pip index versions django-filter` — versão 25.2 confirmada [VERIFIED: pip registry]

### Secondary (MEDIUM confidence)

- Padrões DRF de `@action`, `DefaultRouter`, `FilterSet` — baseados em conhecimento de treinamento, alinhados com DRF 3.17 [ASSUMED - compatível com versão instalada]

### Tertiary (LOW confidence)

- Nenhum item de baixa confiança não resolvido

---

## Metadata

**Confidence breakdown:**
- Stack: HIGH — Phase 1 já entregue e verificado no codebase
- Arquitetura: HIGH — decisions D-01 a D-07 já tomadas pelo usuário; pesquisa confirmou viabilidade
- Pitfalls: HIGH — identificados via leitura direta dos models
- Testes: HIGH — pytest.ini, settings/test.py e padrão existente verificados

**Research date:** 2026-04-09
**Valid until:** 2026-05-09 (stack estável — DRF, django-filter, simplejwt não mudam breaking em 30 dias)
