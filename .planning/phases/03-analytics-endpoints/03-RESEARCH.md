# Phase 3: Analytics Endpoints — Research

**Researched:** 2026-04-09
**Domain:** Django ORM aggregation, reversible migrations, DRF APIView patterns
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01: Coordenadas de usinas — campos lat/lng no model**
O model `Usina` atualmente NAO possui campos `lat`/`lng`. Esta fase DEVE adicionar:
- `latitude = models.FloatField(null=True, blank=True)`
- `longitude = models.FloatField(null=True, blank=True)`

Migração reversível. Campos opcionais (null=True) — usinas sem coordenadas retornam `null` no endpoint de mapa (conforme Success Criteria 3: "usinas sem lat/lng aparecem com campos nulos, não omitidas").

**D-02: Fonte de dados para potência média**
Usar `SnapshotUsina.potencia_kw` do campo desnormalizado `Usina.ultimo_snapshot`. O campo `ultimo_snapshot` já é `select_related` nos ViewSets da Phase 2 — padrão estabelecido.

Para potência média por provedor: agrupar usinas ativas por `provedor`, calcular `Avg('ultimo_snapshot__potencia_kw')` via ORM `annotate`.

**D-03: Critério de "inversor ativo" para ranking**
Um inversor é considerado "ativo" quando:
- `ultimo_snapshot` não é `null` (tem pelo menos um snapshot coletado)
- `ultimo_snapshot.pac_kw > 0` (está gerando energia)

Alinhado com a definição do roadmap: "inversores ativos (com potência > 0 no último snapshot)".

**D-04: Organização dos endpoints — views dedicadas**
Seguir padrão da Phase 2 (D-01): criar `api/views/analytics.py` e `api/serializers/analytics.py`. Registrar via `path()` em `api/urls.py` (não via router — são ListAPIViews, não ViewSets).

### Claude's Discretion

- Estrutura JSON dos endpoints (campos, aninhamento, nomes)
- Otimização de queries (annotate vs subquery vs raw)
- Ordenação do ranking (descendente é o padrão natural)
- Se o endpoint de potência deve retornar contagem de usinas por provedor além da média

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.

Fora do escopo desta fase:
- Séries temporais de potência/temperatura (V2-06)
- Filtros avançados no endpoint de mapa (filtragem feita no frontend)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ANA-01 | Endpoint retorna potência média geral de todas as usinas e potência média agrupada por fabricante/provedor | `Avg` via ORM annotate sobre `ultimo_snapshot__potencia_kw`; `select_related('ultimo_snapshot')` evita N+1 |
| ANA-02 | Endpoint retorna top 5 fabricantes por quantidade de inversores ativos (ranking) | `Count` com `filter` via ORM sobre `Inversor` agrupado por `usina__provedor`; critério: `ultimo_snapshot__pac_kw__gt=0` |
| ANA-03 | Endpoint retorna todas as usinas com lat/lng, provedor e status para renderização no mapa | Migration adiciona `latitude`/`longitude` ao model `Usina`; endpoint retorna todos (inclusive `null`); sem paginação |
</phase_requirements>

---

## Summary

Esta fase entrega 3 endpoints de leitura para o dashboard analítico. Todo o trabalho é Django puro: uma migration reversível, duas views (`APIView`), dois serializers e 3 paths em `urls.py`. A stack está completamente definida — DRF + PostgreSQL + simplejwt já funcionando desde a Phase 1.

O principal risco técnico é a query de potência média: `Avg('ultimo_snapshot__potencia_kw')` com `annotate` sobre `Usina.objects` funciona porque `ultimo_snapshot` é uma FK (`OneToOneField`) — o ORM consegue fazer JOIN diretamente. Usinas sem snapshot (`ultimo_snapshot=None`) resultam em `NULL` no aggregate e devem ser excluídas do denominador. A estratégia correta é filtrar com `ultimo_snapshot__isnull=False` antes do `annotate`.

Para o ranking de fabricantes, a query parte de `Inversor.objects` (não de `Usina.objects`) porque o critério de "ativo" é em nível de inversor, não de usina. Agrupa por `usina__provedor` e conta com `Count('id', filter=Q(ultimo_snapshot__pac_kw__gt=0))`.

**Recomendação principal:** Usar `APIView` (não `ListAPIView`) para os endpoints de potência e ranking — eles retornam estruturas JSON customizadas (não querysets serializados diretamente), então o `get_queryset` + serializer padrão do `ListAPIView` não se aplica. Para mapa, `ListAPIView` com serializer funciona normalmente.

---

## Project Constraints (from CLAUDE.md)

Diretivas obrigatórias que o planner deve verificar na implementação:

| Diretiva | Impacto nesta fase |
|----------|--------------------|
| Nenhuma lógica de negócio dentro de views | Queries de aggregation podem ficar na view se forem simples (< 30 linhas); extrair para módulo `services/` apenas se crescerem |
| Nunca N+1 queries | `select_related('ultimo_snapshot')` obrigatório em todas as queries; verificar com `django-debug-toolbar` em dev |
| Toda entrada do usuário é tratada como não confiável | Endpoints são read-only sem parâmetros de filtro — risco mínimo, mas validar `request.user` via `IsAuthenticated` (já global) |
| Migrations sempre reversíveis | `FloatField(null=True, blank=True)` é reversível — `migrations.RemoveField` funciona sem perda de dados |
| Nenhuma credencial no código | Sem impacto direto nesta fase |
| Dependências externas: não adicionar biblioteca nova sem avisar | Esta fase não adiciona nenhuma dependência nova |
| Todo código novo com lógica de negócio deve ter teste unitário | Testes para valores aggregados, comportamento com usinas sem snapshot e retorno vazio |

---

## Standard Stack

### Core (já instalado — sem novos pacotes)

| Biblioteca | Versão | Propósito | Status |
|------------|--------|-----------|--------|
| djangorestframework | instalado (Phase 1) | APIView, Response, serializers | Ativo |
| djangorestframework-simplejwt | instalado (Phase 1) | JWT global — endpoints herdam automaticamente | Ativo |
| django (ORM) | instalado | `annotate`, `Avg`, `Count`, `Q`, `F` — aggregation nativa | Ativo |
| pytest-django | instalado (Phase 1) | Testes com `@pytest.mark.django_db` | Ativo |

[VERIFIED: codebase — `backend_monitoramento/config/settings/base.py`, `pytest.ini`]

**Nenhum pacote novo necessário nesta fase.** Toda funcionalidade é coberta pelo DRF + Django ORM instalados.

### Funções ORM utilizadas

| Função | Import | Uso |
|--------|--------|-----|
| `Avg` | `django.db.models` | Potência média geral e por provedor |
| `Count` | `django.db.models` | Contagem de inversores ativos por provedor |
| `Q` | `django.db.models` | Filtro condicional no `Count` (`filter=Q(...)`) |
| `annotate` | ORM queryset method | Adicionar aggregate ao queryset |
| `values` | ORM queryset method | Agrupar por provedor antes do aggregate |

[VERIFIED: Django docs — padrão de `values().annotate()` para GROUP BY]

---

## Architecture Patterns

### Estrutura de arquivos a criar

```
backend_monitoramento/
├── api/
│   ├── views/
│   │   ├── analytics.py          # NOVO — 3 classes de view
│   │   └── __init__.py           # ATUALIZAR — importar views de analytics
│   └── serializers/
│       ├── analytics.py          # NOVO — serializers para as 3 respostas
│       └── __init__.py           # ATUALIZAR — importar serializers de analytics
├── api/
│   └── urls.py                   # ATUALIZAR — 3 novos paths analytics/
└── usinas/
    └── migrations/
        └── 00XX_usina_add_lat_lng.py  # NOVO — migration reversível
```

### Pattern 1: APIView para endpoints de aggregation (ANA-01, ANA-02)

**O quê:** `APIView` com método `get()` que executa query de aggregation e retorna `Response` com estrutura JSON customizada.

**Quando usar:** Endpoint retorna dado calculado, não uma lista de objetos serializados diretamente.

**Exemplo — potência média (ANA-01):**
```python
# api/views/analytics.py
from django.db.models import Avg
from rest_framework.views import APIView
from rest_framework.response import Response
from usinas.models import Usina


class PotenciaMediaView(APIView):
    """
    GET /api/analytics/potencia/
    ANA-01: potencia media geral + por provedor.
    """

    def get(self, request):
        # Usinas com snapshot — excluir do calculo quem nao tem dados
        qs = (
            Usina.objects
            .filter(ativo=True, ultimo_snapshot__isnull=False)
            .select_related('ultimo_snapshot')
        )

        # Media geral
        resultado = qs.aggregate(media_geral=Avg('ultimo_snapshot__potencia_kw'))
        media_geral = resultado['media_geral']  # None se nao houver usinas

        # Media por provedor via values().annotate() — equivale a GROUP BY
        por_provedor = list(
            qs
            .values('provedor')
            .annotate(media_kw=Avg('ultimo_snapshot__potencia_kw'))
            .order_by('provedor')
        )

        return Response({
            'media_geral_kw': media_geral,
            'por_provedor': por_provedor,
        })
```

[ASSUMED — estrutura JSON proposta; planner pode ajustar campos]

### Pattern 2: values().annotate() para GROUP BY com Count condicional (ANA-02)

**O quê:** Query que parte de `Inversor.objects`, agrupa por provedor da usina e conta apenas os inversores que satisfazem o critério de "ativo".

**Pitfall crítico:** `Count` com `filter=Q(...)` requer Django >= 2.0. O projeto usa Django moderno — sem problema. [VERIFIED: codebase usa sintaxe moderna]

```python
# api/views/analytics.py
from django.db.models import Count, Q
from rest_framework.views import APIView
from rest_framework.response import Response
from usinas.models import Inversor


class RankingFabricantesView(APIView):
    """
    GET /api/analytics/ranking-fabricantes/
    ANA-02: top 5 provedores por inversores ativos.
    """

    def get(self, request):
        ranking = (
            Inversor.objects
            .values('usina__provedor')
            .annotate(
                inversores_ativos=Count(
                    'id',
                    filter=Q(
                        ultimo_snapshot__isnull=False,
                        ultimo_snapshot__pac_kw__gt=0,
                    )
                )
            )
            .order_by('-inversores_ativos')[:5]
        )
        return Response({'ranking': list(ranking)})
```

[ASSUMED — estrutura JSON proposta; o campo `usina__provedor` vira chave no dict]

### Pattern 3: ListAPIView para mapa (ANA-03)

**O quê:** `ListAPIView` padrão com serializer — retorna TODAS as usinas sem paginação.

**Sem paginação:** Para o mapa, o frontend precisa de todos os pontos de uma vez. Desabilitar paginação na view com `pagination_class = None`.

```python
# api/views/analytics.py
from rest_framework import generics
from usinas.models import Usina
from api.serializers.analytics import UsinaMapaSerializer


class MapaUsinasView(generics.ListAPIView):
    """
    GET /api/analytics/mapa/
    ANA-03: todas as usinas com lat/lng, provedor e status.
    """
    serializer_class = UsinaMapaSerializer
    pagination_class = None  # Frontend precisa de todos os pontos

    def get_queryset(self):
        return (
            Usina.objects
            .select_related('ultimo_snapshot')
            .only('id', 'nome', 'provedor', 'latitude', 'longitude',
                  'ativo', 'ultimo_snapshot')
            .order_by('nome')
        )
```

[VERIFIED: DRF — `pagination_class = None` desabilita paginação na view específica]
[ASSUMED — uso de `only()` para reduzir colunas lidas; planner confirma se necessário]

### Pattern 4: Migration reversível com FloatField nullable (D-01)

```python
# usinas/migrations/00XX_usina_add_lat_lng.py
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usinas', '00XX_anterior'),
    ]

    operations = [
        migrations.AddField(
            model_name='usina',
            name='latitude',
            field=models.FloatField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='usina',
            name='longitude',
            field=models.FloatField(null=True, blank=True),
        ),
    ]
```

**Reversibilidade:** `AddField` com `null=True` é reversível via `RemoveField` — sem perda de dados, sem constraint de NOT NULL que bloqueie rollback. [VERIFIED: Django docs — migrations AddField/RemoveField são reversíveis por design]

### Pattern 5: Serializer para mapa (ANA-03)

```python
# api/serializers/analytics.py
from rest_framework import serializers
from usinas.models import Usina


class UsinaMapaSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()

    class Meta:
        model = Usina
        fields = ['id', 'nome', 'provedor', 'latitude', 'longitude', 'ativo', 'status']

    def get_status(self, obj) -> str:
        """Status baseado no ultimo_snapshot.status — 'sem_dados' se ausente."""
        if obj.ultimo_snapshot is None:
            return 'sem_dados'
        return obj.ultimo_snapshot.status
```

[ASSUMED — campo `status` derivado de `ultimo_snapshot.status`; planner pode ajustar]

### Anti-Patterns a Evitar

- **N+1 em aggregation:** Não iterar usinas em Python calculando média — usar `Avg` no ORM.
- **`ListAPIView` para potência/ranking:** Esses endpoints retornam estrutura JSON customizada, não um queryset flat — usar `APIView`.
- **Paginação no endpoint de mapa:** O frontend precisa de todos os pontos; `pagination_class = None` obrigatório.
- **Filtrar `ultimo_snapshot=None` em Python:** Usar `ultimo_snapshot__isnull=False` no ORM antes do aggregate — não fazer `list(qs)` e filtrar depois.
- **`FloatField` sem `null=True` na migration:** Quebraria usinas existentes sem coordenadas; `null=True, blank=True` obrigatório conforme D-01.

---

## Don't Hand-Roll

| Problema | Não construir | Usar em vez disso | Por quê |
|----------|---------------|-------------------|---------|
| Média agrupada por provedor | Loop Python somando e dividindo | `Avg` + `values().annotate()` do Django ORM | ORM delega para SQL GROUP BY — eficiente, atômico, sem N+1 |
| Contagem condicional de inversores | Filtrar em Python depois de carregar todos | `Count('id', filter=Q(...))` | SQL conditional COUNT — executado no banco, não na aplicação |
| Autenticação JWT | Lógica custom de token | `IsAuthenticated` global já configurado — herdado automaticamente | Configurado em `DEFAULT_PERMISSION_CLASSES` desde Phase 1 |
| Serialização de estrutura customizada | Dict manual no `get()` | `Response(dict)` direto do DRF para endpoints de aggregation | `Response` já trata serialização JSON |

---

## Common Pitfalls

### Pitfall 1: `Avg` retorna `None` quando queryset vazio

**O que acontece:** `Usina.objects.aggregate(Avg('ultimo_snapshot__potencia_kw'))` retorna `{'ultimo_snapshot__potencia_kw__avg': None}` quando não há usinas com snapshot.
**Por que acontece:** SQL `AVG()` de conjunto vazio retorna NULL — comportamento correto do banco.
**Como evitar:** A view deve retornar `None` explicitamente (não `0`) para sinalizar "sem dados". O frontend deve tratar `null` diferente de `0`.
**Sinais de alerta:** Frontend exibindo "0 kW" quando não há usinas com snapshot.

### Pitfall 2: JOIN entre `Usina` e `SnapshotUsina` via `ultimo_snapshot`

**O que acontece:** `Avg('ultimo_snapshot__potencia_kw')` funciona no ORM porque `ultimo_snapshot` é `OneToOneField` — o ORM gera JOIN. Mas se a FK apontar para `null` (usina sem snapshot), o registro é excluído do JOIN (INNER JOIN por padrão).
**Por que acontece:** Django ORM usa INNER JOIN para traversal de FK por padrão. `ultimo_snapshot=None` significa que a usina não aparece no JOIN.
**Como evitar:** Filtrar com `ultimo_snapshot__isnull=False` explicitamente antes do aggregate — isso documenta a intenção e evita surpresa se o comportamento do ORM mudar.
**Sinais de alerta:** Média incorreta incluindo usinas sem dados.

### Pitfall 3: Campo `usina__provedor` no dict do ranking

**O que acontece:** `values('usina__provedor').annotate(...)` gera dicts com chave `usina__provedor` (com underscores duplos), não `provedor`.
**Por que acontece:** O ORM usa o nome do campo de traversal como chave no dict resultante.
**Como evitar:** Usar `values(provedor=F('usina__provedor'))` para renomear, ou tratar no serializer. Alternativa: renomear com `annotate(provedor=F('usina__provedor'))`.
**Sinais de alerta:** Frontend recebendo `{"usina__provedor": "solis"}` em vez de `{"provedor": "solis"}`.

### Pitfall 4: `[:5]` no queryset antes do `list()`

**O que acontece:** O slice `[:5]` em queryset não avaliado funciona corretamente (gera `LIMIT 5` no SQL). Mas se o queryset já tiver sido avaliado (ex: `list(qs)[:5]`), a limitação ocorre em Python depois de buscar todos os registros.
**Por que acontece:** Querysets são lazy — slice antes de avaliar é eficiente; slice após `list()` é ineficiente.
**Como evitar:** Manter `[:5]` no queryset antes de passar para `list()` ou iterar.

### Pitfall 5: `select_related` não aplicado no endpoint de mapa

**O que acontece:** Sem `select_related('ultimo_snapshot')`, cada usina serializada gera query adicional para buscar `ultimo_snapshot.status`.
**Por que acontece:** `SerializerMethodField` acessa `obj.ultimo_snapshot` — sem prefetch, Django faz query por objeto.
**Como evitar:** `get_queryset()` sempre com `select_related('ultimo_snapshot')`.

---

## Runtime State Inventory

> Esta fase adiciona campos ao model `Usina` — avaliação de estado em runtime.

| Categoria | Itens encontrados | Ação necessária |
|-----------|-------------------|-----------------|
| Stored data | Registros existentes de `Usina` no banco — receberão `latitude=NULL, longitude=NULL` após migration | Automático — `AddField(null=True)` preenche NULL sem intervenção |
| Live service config | Nenhum serviço externo referencia campos `lat`/`lng` da Usina | Nenhuma |
| OS-registered state | Nenhum | Nenhum |
| Secrets/env vars | Nenhum impacto — campos novos não envolvem segredos | Nenhuma |
| Build artifacts | Nenhum | Nenhum |

Nada encontrado que exija intervenção além da migration padrão.

---

## Code Examples

### Estrutura JSON proposta para ANA-01

```json
{
  "media_geral_kw": 4.75,
  "por_provedor": [
    {"provedor": "fusionsolar", "media_kw": 6.2},
    {"provedor": "hoymiles", "media_kw": 3.8},
    {"provedor": "solis", "media_kw": 4.5}
  ]
}
```

Se não há usinas com snapshot: `{"media_geral_kw": null, "por_provedor": []}`.

[ASSUMED — estrutura proposta; planner decide campos finais]

### Estrutura JSON proposta para ANA-02

```json
{
  "ranking": [
    {"provedor": "solis", "inversores_ativos": 42},
    {"provedor": "hoymiles", "inversores_ativos": 28},
    {"provedor": "fusionsolar", "inversores_ativos": 15},
    {"provedor": "growatt", "inversores_ativos": 7},
    {"provedor": "outro", "inversores_ativos": 3}
  ]
}
```

[ASSUMED — estrutura proposta]

### Estrutura JSON proposta para ANA-03

```json
{
  "usinas": [
    {
      "id": "uuid",
      "nome": "Usina Sul",
      "provedor": "solis",
      "latitude": -23.5505,
      "longitude": -46.6333,
      "ativo": true,
      "status": "normal"
    },
    {
      "id": "uuid",
      "nome": "Usina Norte (sem coords)",
      "provedor": "hoymiles",
      "latitude": null,
      "longitude": null,
      "ativo": true,
      "status": "aviso"
    }
  ]
}
```

Sem envelope `usinas` se usar `ListAPIView` diretamente — retorna array plano. Planner decide.

[ASSUMED — estrutura proposta]

---

## Validation Architecture

### Test Framework

| Propriedade | Valor |
|-------------|-------|
| Framework | pytest-django (instalado) |
| Config file | `backend_monitoramento/pytest.ini` |
| Quick run command | `cd backend_monitoramento && pytest api/tests/test_analytics.py -x` |
| Full suite command | `cd backend_monitoramento && pytest` |

### Phase Requirements → Test Map

| Req ID | Comportamento | Tipo | Comando automatizado | Arquivo existe? |
|--------|---------------|------|----------------------|-----------------|
| ANA-01 | Retorna `media_geral_kw` calculada corretamente | unit | `pytest api/tests/test_analytics.py::TestPotenciaMedia -x` | Não — Wave 0 |
| ANA-01 | Retorna `media_geral_kw: null` quando sem snapshots | unit | `pytest api/tests/test_analytics.py::TestPotenciaMedia::test_sem_snapshots -x` | Não — Wave 0 |
| ANA-01 | `por_provedor` agrupa corretamente | unit | `pytest api/tests/test_analytics.py::TestPotenciaMedia::test_por_provedor -x` | Não — Wave 0 |
| ANA-01 | Rejeita sem token com 401 | unit | `pytest api/tests/test_analytics.py::TestPotenciaMedia::test_requer_auth -x` | Não — Wave 0 |
| ANA-02 | Retorna exatamente top 5 ordenado por contagem desc | unit | `pytest api/tests/test_analytics.py::TestRankingFabricantes -x` | Não — Wave 0 |
| ANA-02 | Exclui inversores sem snapshot do count | unit | `pytest api/tests/test_analytics.py::TestRankingFabricantes::test_exclui_sem_snapshot -x` | Não — Wave 0 |
| ANA-02 | Exclui inversores com `pac_kw=0` do count | unit | `pytest api/tests/test_analytics.py::TestRankingFabricantes::test_exclui_pac_zero -x` | Não — Wave 0 |
| ANA-02 | Rejeita sem token com 401 | unit | `pytest api/tests/test_analytics.py::TestRankingFabricantes::test_requer_auth -x` | Não — Wave 0 |
| ANA-03 | Retorna todas as usinas inclusive sem lat/lng | unit | `pytest api/tests/test_analytics.py::TestMapaUsinas -x` | Não — Wave 0 |
| ANA-03 | Usinas sem coordenadas retornam `latitude: null` | unit | `pytest api/tests/test_analytics.py::TestMapaUsinas::test_sem_coords_retorna_null -x` | Não — Wave 0 |
| ANA-03 | Sem paginação — retorna array completo | unit | `pytest api/tests/test_analytics.py::TestMapaUsinas::test_sem_paginacao -x` | Não — Wave 0 |
| ANA-03 | Rejeita sem token com 401 | unit | `pytest api/tests/test_analytics.py::TestMapaUsinas::test_requer_auth -x` | Não — Wave 0 |

### Sampling Rate

- **Por task commit:** `cd backend_monitoramento && pytest api/tests/test_analytics.py -x`
- **Por wave merge:** `cd backend_monitoramento && pytest`
- **Phase gate:** Suite completa verde antes de `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `api/tests/test_analytics.py` — arquivo principal de testes desta fase; todas as classes acima
- [ ] `conftest.py` existente já tem fixtures reutilizáveis (`usina`, `inversor`, `snapshot_inversor`, `tokens`) — reusar; adicionar fixtures específicas (ex: `usina_com_coords`, `inversor_ativo`) diretamente no arquivo de teste ou no conftest

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | sim | simplejwt `IsAuthenticated` global — endpoints herdam automaticamente |
| V3 Session Management | não | Stateless JWT — sem sessão |
| V4 Access Control | sim | `IsAuthenticated` — nenhum endpoint público por acidente |
| V5 Input Validation | baixo | Endpoints são read-only sem parâmetros de usuário; nenhum filtro exposto |
| V6 Cryptography | não | Sem operações criptográficas nesta fase |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Acesso não autenticado a dados aggregados | Information Disclosure | `IsAuthenticated` global (DEFAULT_PERMISSION_CLASSES) — já configurado |
| Endpoint de mapa como OSINT de localização de instalações | Information Disclosure | Dados de lat/lng são administrativos internos; JWT obrigatório já protege |
| N+1 como vetor de DoS (polling a cada 10min × muitos inversores) | Denial of Service | `select_related` + `annotate` no ORM — uma query por endpoint; sem loop |

---

## Assumptions Log

| # | Claim | Section | Risk se errado |
|---|-------|---------|----------------|
| A1 | Estrutura JSON de ANA-01: `{media_geral_kw, por_provedor}` | Code Examples | Baixo — planner decide formato; fácil de ajustar no serializer |
| A2 | Estrutura JSON de ANA-02: `{ranking: [{provedor, inversores_ativos}]}` | Code Examples | Baixo — mesmo motivo |
| A3 | Endpoint de mapa retorna array plano (sem envelope) via `ListAPIView` | Architecture Patterns | Baixo — decisão de DX consistente com outros endpoints |
| A4 | Campo `status` no mapa derivado de `ultimo_snapshot.status` | Architecture Patterns | Baixo — única fonte de status disponível no model |
| A5 | Usar `only()` no queryset de mapa para reduzir colunas | Architecture Patterns | Muito baixo — otimização; remover se causar problema com select_related |

---

## Open Questions

1. **Contagem de usinas por provedor no endpoint de potência (ANA-01)**
   - O que sabemos: `Avg` por provedor já retorna a média; adicionar `Count('id')` no mesmo `annotate` é trivial
   - O que está indefinido: se o frontend precisa desse dado para o gráfico de pizza (tamanho das fatias)
   - Recomendação: incluir `usinas_ativas` no `por_provedor` — custo zero no banco, evita chamada adicional da Phase 6

2. **Nome do campo no ranking: `usina__provedor` vs `provedor`**
   - O que sabemos: `values('usina__provedor')` gera chave com `__` no dict
   - O que está indefinido: frontend espera qual formato?
   - Recomendação: usar `values(provedor=F('usina__provedor'))` para padronizar com o resto da API

---

## Environment Availability

| Dependência | Requerida por | Disponível | Versão | Fallback |
|-------------|---------------|------------|--------|----------|
| PostgreSQL | Todas as queries | Configurado (settings/base.py) | n/d | Nenhum — produção usa PostgreSQL |
| Django ORM (`Avg`, `Count`, `Q`) | ANA-01, ANA-02 | Sim (Django instalado) | Django moderno | Nenhum necessário |
| pytest-django | Testes | Sim (`pytest.ini` existe) | Instalado | Nenhum |

Step 2.6: SKIPPED para dependências externas além do banco — esta fase não adiciona ferramentas novas.

---

## Sources

### Primary (HIGH confidence)

- Codebase lido diretamente: `backend_monitoramento/usinas/models.py`, `backend_monitoramento/api/views/usinas.py`, `backend_monitoramento/api/views/garantias.py`, `backend_monitoramento/api/serializers/usinas.py`, `backend_monitoramento/api/urls.py`, `backend_monitoramento/config/settings/base.py`, `backend_monitoramento/api/tests/conftest.py`
- Django docs pattern verificado: `values().annotate()` para GROUP BY, `pagination_class = None` para desabilitar paginação por view, `AddField(null=True)` como migration reversível

### Secondary (MEDIUM confidence)

- Django ORM `Count` com `filter=Q(...)` — padrão documentado disponível desde Django 2.0; projeto usa Django moderno [ASSUMED — versão exata não verificada nesta sessão]

### Tertiary (LOW confidence)

- Estruturas JSON propostas (A1-A5) — baseadas em boas práticas REST, não em especificação do cliente

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — sem novos pacotes; tudo já instalado e verificado no codebase
- Architecture: HIGH — patterns estabelecidos na Phase 2 copiados diretamente; Django ORM aggregation é padrão estável
- Pitfalls: HIGH — identificados via análise do modelo de dados real (OneToOneField nullable, GROUP BY com underscores duplos)
- JSON structures: LOW — propostas; planner decide

**Research date:** 2026-04-09
**Valid until:** 2026-05-09 (stack estável; sem dependências externas voláteis)
