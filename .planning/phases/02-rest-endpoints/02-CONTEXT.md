# Phase 2: REST Endpoints - Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Expor via API REST autenticada todos os dados operacionais do sistema: usinas (com status de garantia), inversores, alertas (com indicação de garantia), garantias e logs de coleta.

Endpoints incluídos nesta fase:
- `GET /api/usinas/` — listagem com filtros
- `GET /api/usinas/{id}/` — detalhe com inversores e último snapshot
- `PATCH /api/usinas/{id}/` — atualizar nome e capacidade
- `GET /api/usinas/{id}/snapshots/` — histórico paginado
- `PUT /api/usinas/{id}/garantia/` — criar ou substituir garantia
- `GET /api/garantias/` — listagem com filtro de vigência
- `GET /api/inversores/` — listagem com filtros
- `GET /api/inversores/{id}/` — detalhe com último snapshot completo
- `GET /api/inversores/{id}/snapshots/` — histórico paginado
- `GET /api/alertas/` — listagem com filtros
- `GET /api/alertas/{id}/` — detalhe
- `PATCH /api/alertas/{id}/` — atualizar estado e anotações
- `GET /api/coleta/logs/` — últimos ciclos de coleta

**Fora do escopo desta fase:** endpoints de analytics (potência média, ranking, mapa) → Phase 3.

</domain>

<decisions>
## Implementation Decisions

### D-01: Organização da app `api` — pacote por domínio

Views e serializers organizados como pacotes com módulos por domínio:

```
api/
  views/
    __init__.py
    usinas.py      # UsinaViewSet, SnapshotUsinaListView
    garantias.py   # GarantiaUsinaView, GarantiaListView
    inversores.py  # InversorViewSet, SnapshotInversorListView
    alertas.py     # AlertaViewSet
    logs.py        # LogColetaListView
  serializers/
    __init__.py
    usinas.py
    garantias.py
    inversores.py
    alertas.py
    logs.py
  views.py         # (arquivo existente da Phase 1 — manter PingView aqui ou mover para views/__init__.py)
```

Razão: a Phase 2 adiciona ~15 views/serializers; um arquivo único violaria a regra do projeto ("se precisar de 'e' para descrever o que um arquivo faz, divide").

### D-02: Roteamento — router central único

Um único `api/urls.py` com `DefaultRouter` registrando todos os ViewSets. Rotas de ação customizada (ex: `/api/usinas/{id}/garantia/`, `/api/usinas/{id}/snapshots/`) registradas via `@action` no próprio ViewSet ou como `path()` explícito no mesmo arquivo.

### D-03: Estratégia de filtros — django-filter

Instalar `django-filter` e ativar `DjangoFilterBackend` no `REST_FRAMEWORK['DEFAULT_FILTER_BACKENDS']`. Filtros declarativos via `FilterSet` por domínio. Validação de tipos automática pelo framework.

Nova dependência aprovada: `django-filter==X.Y` (planner verifica versão compatível com Django 5.1).

### D-04: Campo `status_garantia` — 3 valores

O campo calculado `status_garantia` nas respostas de usina (listagem e detalhe) deve usar exatamente 3 valores:
- `"ativa"` — garantia cadastrada e `data_fim >= hoje`
- `"vencida"` — garantia cadastrada e `data_fim < hoje`
- `"sem_garantia"` — nenhuma `GarantiaUsina` associada

O mesmo conjunto de valores é usado como filtro: `?status_garantia=ativa`, `?status_garantia=vencida`, `?status_garantia=sem_garantia`.

Valor calculado no serializer a partir da property `ativa` e da existência de `GarantiaUsina` — não persistido no banco.

### D-05: Parâmetro de filtro em /api/garantias/

Conforme roadmap e GAR-03, o parâmetro de filtro é `filtro` com valores:
- `ativas` — garantias com `data_fim >= hoje`
- `vencendo` — garantias com `data_fim` nos próximos 30 dias (inclui ativas)
- `vencidas` — garantias com `data_fim < hoje`

Sem valor: retorna todas as garantias.

### D-06: Paginação de snapshots históricos

Endpoints `/api/usinas/{id}/snapshots/` e `/api/inversores/{id}/snapshots/` usam `PageNumberPagination` com `page_size = 100`. Navegação via `?page=N`. Configurar como classe de paginação específica para essas views (não alterar o padrão global).

### D-07: Paginação global dos endpoints de listagem

Verificar o valor atual de `PAGE_SIZE` no `base.py` e ajustar se necessário para os endpoints de listagem desta fase. O planner avalia o valor existente e propõe ajuste justificado se for inadequado para o contexto de uso.

### Claude's Discretion

- Estrutura interna dos serializers (aninhados vs. separados por operação lista/detalhe) — planner decide a melhor abordagem para cada endpoint
- Cálculo do campo `com_garantia` em alertas — anotação SQL via `annotate()` ou property no serializer; planner decide baseado em performance com o volume esperado
- Ordenação padrão de cada endpoint (usinas por nome, alertas por data, etc.) — planner decide
- Formato dos campos `data_fim` e `dias_restantes` na resposta (ISO 8601 para datas, inteiro para dias)
- Campos incluídos no serializer de lista vs. detalhe (planner define o contrato de campos)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap e Requisitos
- `.planning/ROADMAP.md` — escopo exato da Phase 2, dependências, success criteria
- `.planning/REQUIREMENTS.md` — USN-01..05, GAR-02..06, INV-01..03, ALT-01..04, LOG-01

### Models existentes (ler antes de criar serializers)
- `backend_monitoramento/usinas/models.py` — Usina, SnapshotUsina, Inversor, SnapshotInversor, GarantiaUsina (com properties `data_fim`, `ativa`, `dias_restantes`)
- `backend_monitoramento/alertas/models.py` — Alerta, CatalogoAlarme
- `backend_monitoramento/coleta/models.py` — LogColeta

### Configuração DRF existente (Phase 1)
- `backend_monitoramento/config/settings/base.py` — `REST_FRAMEWORK` config atual (auth, paginação, permissões)
- `backend_monitoramento/config/urls.py` — como a app `api` está incluída no URL root
- `backend_monitoramento/api/urls.py` — rotas existentes (auth/token, ping)

### O que foi entregue na Phase 1
- `.planning/phases/01-api-infrastructure/01-01-SUMMARY.md` — dependências instaladas, padrões estabelecidos, arquivos criados

### Convenções do projeto
- `.planning/codebase/CONVENTIONS.md` — nomenclatura em português, estrutura de módulos
- `CLAUDE.md` — regras de modularidade, segurança, qualidade

</canonical_refs>

<specifics>
## Specific Ideas

- O campo `com_garantia` em respostas de alerta deve refletir a situação **no momento da requisição**, não em cache
- `PUT /api/usinas/{id}/garantia/` é upsert: cria se não existe, substitui se já existe (OneToOne garantido pelo model)
- A resposta do PUT de garantia deve incluir imediatamente `data_fim` e `dias_restantes` (GAR-04, success criteria 3)
- Todos os endpoints retornam 401 sem token — garantido pelo `IsAuthenticated` global da Phase 1

</specifics>

<deferred>
## Deferred Ideas

Nenhuma ideia fora do escopo foi levantada durante a discussão.

</deferred>

---

*Phase: 02-rest-endpoints*
*Context gathered: 2026-04-08*
