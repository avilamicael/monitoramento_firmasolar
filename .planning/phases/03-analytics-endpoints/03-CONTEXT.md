# Phase 3: Analytics Endpoints - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Entregar 3 endpoints de dados agregados para o dashboard analítico: potência média (geral e por provedor), ranking de fabricantes por inversores ativos, e dados de usinas para renderização no mapa. Todos protegidos por JWT.

Endpoints incluídos nesta fase:
- `GET /api/analytics/potencia/` — potência média geral + agrupada por provedor
- `GET /api/analytics/ranking-fabricantes/` — top 5 provedores por inversores ativos
- `GET /api/analytics/mapa/` — usinas com lat/lng, provedor e status

**Fora do escopo:** séries temporais de potência/temperatura (V2-06), filtros avançados no mapa (filtragem no frontend).

</domain>

<decisions>
## Implementation Decisions

### D-01: Coordenadas de usinas — campos lat/lng no model

O model `Usina` atualmente NÃO possui campos `lat`/`lng`. Esta fase DEVE adicionar:
- `latitude = models.FloatField(null=True, blank=True)`
- `longitude = models.FloatField(null=True, blank=True)`

Migração reversível. Campos opcionais (null=True) — usinas sem coordenadas retornam `null` no endpoint de mapa (conforme Success Criteria 3: "usinas sem lat/lng aparecem com campos nulos, não omitidas").

### D-02: Fonte de dados para potência média

Usar `SnapshotUsina.potencia_kw` do campo desnormalizado `Usina.ultimo_snapshot`. O campo `ultimo_snapshot` já é `select_related` nos ViewSets da Phase 2 — padrão estabelecido.

Para potência média por provedor: agrupar usinas ativas por `provedor`, calcular `Avg('ultimo_snapshot__potencia_kw')` via ORM `annotate`.

### D-03: Critério de "inversor ativo" para ranking

Um inversor é considerado "ativo" quando:
- `ultimo_snapshot` não é `null` (tem pelo menos um snapshot coletado)
- `ultimo_snapshot.pac_kw > 0` (está gerando energia)

Alinhado com a definição do roadmap: "inversores ativos (com potência > 0 no último snapshot)".

### D-04: Organização dos endpoints — views dedicadas

Seguir padrão da Phase 2 (D-01): criar `api/views/analytics.py` e `api/serializers/analytics.py`. Registrar via `path()` em `api/urls.py` (não via router — são ListAPIViews, não ViewSets).

### Claude's Discretion

- Estrutura JSON dos endpoints (campos, aninhamento, nomes) — planner decide
- Otimização de queries (annotate vs subquery vs raw) — planner decide baseado no volume esperado
- Ordenação do ranking (ascendente/descendente) — planner decide (descendente é o padrão natural)
- Se o endpoint de potência deve retornar contagem de usinas por provedor além da média — planner decide

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap e Requisitos
- `.planning/ROADMAP.md` — escopo exato da Phase 3, success criteria, out of scope
- `.planning/REQUIREMENTS.md` — ANA-01, ANA-02, ANA-03

### Models existentes (ler antes de criar queries)
- `backend_monitoramento/usinas/models.py` — Usina (sem lat/lng!), SnapshotUsina, Inversor, SnapshotInversor
- `backend_monitoramento/usinas/models.py:5` — Usina.ultimo_snapshot (OneToOne desnormalizado)
- `backend_monitoramento/usinas/models.py:107` — Inversor.ultimo_snapshot (OneToOne desnormalizado)

### Padrões estabelecidos na Phase 2
- `backend_monitoramento/api/views/usinas.py` — padrão de ViewSet com select_related
- `backend_monitoramento/api/views/garantias.py` — padrão de ListAPIView simples
- `backend_monitoramento/api/urls.py` — rotas existentes (router + paths manuais)
- `backend_monitoramento/api/serializers/usinas.py` — padrão de serializer com SerializerMethodField

### Contexto da Phase 2
- `.planning/phases/02-rest-endpoints/02-CONTEXT.md` — decisões de arquitetura que esta fase herda

### Convenções
- `CLAUDE.md` — regras de modularidade, segurança, qualidade

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `PaginacaoSnapshots` — pagination class (não necessária aqui, endpoints retornam dados agregados)
- Padrão de `select_related` e `prefetch_related` nos ViewSets existentes
- `IsAuthenticated` como permission global — endpoints herdam automaticamente

### Established Patterns
- `ListAPIView` para endpoints read-only simples (ex: GarantiaListView, LogColetaListView)
- `SerializerMethodField` para campos calculados (@property do model)
- Filtros em Python quando campo é @property não mapeável em ORM

### Integration Points
- `api/urls.py` — adicionar 3 paths novos para analytics
- `api/views/__init__.py` — registrar imports das views de analytics
- `api/serializers/__init__.py` — registrar imports dos serializers de analytics
- `usinas/models.py` — adicionar campos `latitude`/`longitude` (migração)

</code_context>

<specifics>
## Specific Ideas

- Potência média geral = média de `ultimo_snapshot.potencia_kw` de todas as usinas ativas com snapshot
- Usinas sem `ultimo_snapshot` devem ser excluídas do cálculo de potência (divisão por zero)
- Ranking: agrupar por `usina__provedor` via `Inversor.objects`, contar inversores com `pac_kw > 0`
- Mapa: retornar TODAS as usinas (inclusive sem coordenadas), com `latitude`/`longitude` null quando ausentes

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-analytics-endpoints*
*Context gathered: 2026-04-09*
