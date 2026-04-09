---
phase: 02-rest-endpoints
verified: 2026-04-09T00:00:00Z
status: passed
score: 18/18 must-haves verified
overrides_applied: 0
---

# Phase 02: REST Endpoints — Relatório de Verificação

**Meta do Fase:** Todo dado operacional do sistema — usinas, inversores, alertas, garantias e logs — é acessível via API REST autenticada.
**Verificado:** 2026-04-09
**Status:** PASSOU
**Re-verificação:** Não — verificação inicial

---

## Atingimento do Objetivo

### Verdades Observáveis (Success Criteria do Roadmap)

| # | Verdade | Status | Evidência |
|---|---------|--------|-----------|
| 1 | Administrador obtém lista de usinas filtrada por provedor e/ou status de garantia em uma única requisição autenticada | VERIFICADO | `UsinaViewSet` com `UsinaFilterSet` (filtros `provedor`, `ativo`, `status_garantia`). 5 testes passando em `TestUsinaList`. |
| 2 | Detalhe de usina retorna inversores associados e os dados do último snapshot coletado | VERIFICADO | `UsinaDetalheSerializer` inclui `inversores = InversorResumoSerializer(many=True)` e `ultimo_snapshot = SnapshotUsinaSerializer(read_only=True)`. Testado em `TestUsinaDetalhe`. |
| 3 | `PUT /api/usinas/{id}/garantia/` cria ou substitui garantia; resposta imediata inclui `data_fim` e `dias_restantes` | VERIFICADO | `@action garantia` em `UsinaViewSet` usa `update_or_create`. `GarantiaUsinaSerializer` com `SerializerMethodField` para `data_fim` e `dias_restantes`. `test_resposta_inclui_data_fim` verifica os campos. |
| 4 | `GET /api/garantias/?filtro=vencendo` retorna apenas garantias vencendo nos próximos 30 dias, com `dias_restantes` correto | VERIFICADO | `GarantiaListView.get_queryset()` filtra em Python com `hoje <= g.data_fim <= limite` onde `limite = hoje + timedelta(days=30)`. Testado em `TestGarantiaFiltros`. |
| 5 | `PATCH /api/alertas/{id}/` atualiza estado e anotações; campo `com_garantia` reflete situação real da usina no momento | VERIFICADO | `AlertaViewSet` com `AlertaPatchSerializer(fields=['estado','anotacoes'])`. `select_related('usina__garantia')` garante dado atual. Testado em `TestAlertaPatch` e `TestAlertaCampoComGarantia`. |
| 6 | Todos os endpoints retornam 401 sem token válido — sem exceções | VERIFICADO | `IsAuthenticated` como default global (Phase 1). Testes de 401 presentes em todos os 5 grupos de endpoints. |

**Pontuação:** 6/6 success criteria verificados

---

### Must-Haves por Plano

#### Plan 01 — Infraestrutura

| Must-Have | Status | Evidência |
|-----------|--------|-----------|
| django-filter 25.2 instalado e configurado | VERIFICADO | `requirements/base.txt:14: django-filter==25.2`; `settings/base.py:114: DjangoFilterBackend` |
| Pacotes views/, serializers/, filters/ com `__init__.py` | VERIFICADO | Todos os diretórios existem com `__init__.py`. Confirmado com `ls`. |
| `conftest.py` com 12 fixtures compartilhadas | VERIFICADO | `conftest.py` com 173 linhas, contém credencial, usina, usina_hoymiles, garantia_ativa, garantia_vencida, snapshot_usina, inversor, snapshot_inversor, catalogo_alarme, alerta, log_coleta, tokens. |
| Test stubs coletáveis por pytest para todos os 5 grupos | VERIFICADO | 72 testes passando (todos implementados, nenhum em skip). |
| `PaginacaoSnapshots` com `page_size=100` definida | VERIFICADO | `api/pagination.py` com `page_size = 100`, `max_page_size = 500`. |

#### Plan 02 — Usinas e Garantias

| Must-Have | Status | Evidência |
|-----------|--------|-----------|
| Administrador lista usinas filtradas por provedor, ativo e status_garantia | VERIFICADO | `UsinaFilterSet` com os 3 filtros. Testes passando. |
| Detalhe de usina retorna inversores e último snapshot | VERIFICADO | `UsinaDetalheSerializer` inclui ambos os campos aninhados. |
| PATCH atualiza nome e capacidade; POST e DELETE retornam 405 | VERIFICADO | `UsinaPatchSerializer(fields=['nome','capacidade_kwp'])`. `http_method_names` não inclui `post`/`delete`. `update()` bloqueia PUT direto. |
| Histórico de snapshots de usina paginado com page_size=100 | VERIFICADO | `@action snapshots` usa `PaginacaoSnapshots`. |
| PUT /api/usinas/{id}/garantia/ cria ou substitui garantia com data_fim e dias_restantes | VERIFICADO | `update_or_create` + `GarantiaUsinaSerializer`. |
| GET /api/garantias/ filtra por ativas, vencendo, vencidas via parâmetro filtro | VERIFICADO | `GarantiaListView.get_queryset()` com filtro Python. |
| status_garantia retorna exatamente 'ativa', 'vencida' ou 'sem_garantia' | VERIFICADO | `get_status_garantia()` em ambos `UsinaListSerializer` e `UsinaDetalheSerializer`. |
| Todos os endpoints retornam 401 sem token | VERIFICADO | Testes explícitos de 401 em cada grupo. |

#### Plan 03 — Inversores e Alertas

| Must-Have | Status | Evidência |
|-----------|--------|-----------|
| Administrador lista inversores filtrados por usina, provedor e modelo | VERIFICADO | `InversorFilterSet` com os 3 filtros. Testes passando. |
| Detalhe de inversor retorna último snapshot completo | VERIFICADO | `InversorDetalheSerializer` com `ultimo_snapshot = SnapshotInversorSerializer(read_only=True)` incluindo pac_kw, tensao_ac_v, corrente_ac_a, frequencia_hz, temperatura_c. |
| Histórico de snapshots de inversor paginado com page_size=100 | VERIFICADO | `@action snapshots` em `InversorViewSet` usa `PaginacaoSnapshots`. |
| Administrador lista alertas filtrados por estado, nível e usina | VERIFICADO | `AlertaFilterSet` com os 3 filtros. |
| Detalhe de alerta retorna dados completos incluindo com_garantia | VERIFICADO | `AlertaDetalheSerializer` com todos os campos + `com_garantia`. |
| PATCH em alerta atualiza estado e anotações; POST e DELETE retornam 405 | VERIFICADO | `AlertaPatchSerializer(fields=['estado','anotacoes'])`. `http_method_names=['get','patch','head','options']`. |
| Campo com_garantia presente em todas as respostas de alerta | VERIFICADO | Presente em `AlertaListSerializer` e `AlertaDetalheSerializer`. |
| Todos os endpoints retornam 401 sem token | VERIFICADO | Testes explícitos presentes. |

#### Plan 04 — Logs de Coleta

| Must-Have | Status | Evidência |
|-----------|--------|-----------|
| GET /api/coleta/logs/ retorna lista com status e iniciado_em | VERIFICADO | `LogColetaListView` em `api/views/logs.py`. Rota registrada em `urls.py`. |
| Endpoint retorna 401 sem token JWT válido | VERIFICADO | `permission_classes = [IsAuthenticated]` explícito. `test_lista_logs_sem_token_retorna_401` passando. |
| Suite completa verde: pytest api/tests/ exits 0 | VERIFICADO | 72 passed, 0 failed/skipped — saída confirmada. |

**Pontuação:** 18/18 must-haves verificados

---

### Artefatos Obrigatórios

| Artefato | Status | Detalhes |
|----------|--------|---------|
| `api/serializers/usinas.py` | VERIFICADO | 76 linhas. Contém `UsinaListSerializer`, `UsinaDetalheSerializer`, `UsinaPatchSerializer`, `SnapshotUsinaSerializer`. |
| `api/serializers/garantias.py` | VERIFICADO | Contém `GarantiaUsinaSerializer` (com `data_fim`, `dias_restantes`, `ativa` via `SerializerMethodField`) e `GarantiaUsinaEscritaSerializer`. |
| `api/serializers/inversores.py` | VERIFICADO | Contém `SnapshotInversorSerializer`, `InversorListSerializer`, `InversorDetalheSerializer`. |
| `api/serializers/alertas.py` | VERIFICADO | Contém `AlertaListSerializer`, `AlertaDetalheSerializer`, `AlertaPatchSerializer`. |
| `api/serializers/logs.py` | VERIFICADO | Contém `LogColetaSerializer` com `provedor_nome` via `SerializerMethodField`. |
| `api/filters/usinas.py` | VERIFICADO | Contém `UsinaFilterSet` com método `filtrar_status_garantia`. |
| `api/filters/inversores.py` | VERIFICADO | Contém `InversorFilterSet` com filtros `usina`, `provedor`, `modelo`. |
| `api/filters/alertas.py` | VERIFICADO | Contém `AlertaFilterSet` com filtros `estado`, `nivel`, `usina`. |
| `api/views/usinas.py` | VERIFICADO | Contém `UsinaViewSet` com `@action` para `snapshots` e `garantia`. |
| `api/views/garantias.py` | VERIFICADO | Contém `GarantiaListView` com filtro via parâmetro `filtro`. |
| `api/views/inversores.py` | VERIFICADO | Contém `InversorViewSet` com `@action snapshots`. |
| `api/views/alertas.py` | VERIFICADO | Contém `AlertaViewSet` com `select_related('usina__garantia')`. |
| `api/views/logs.py` | VERIFICADO | Contém `LogColetaListView` com `permission_classes = [IsAuthenticated]` e `select_related('credencial')`. |
| `api/urls.py` | VERIFICADO | Router registra `usinas`, `inversores`, `alertas`. Rotas diretas para `garantias/` e `coleta/logs/`. |
| `api/tests/conftest.py` | VERIFICADO | 173 linhas, 12 fixtures cobrindo todos os domínios. |
| `api/pagination.py` | VERIFICADO | `PaginacaoSnapshots(page_size=100, max_page_size=500)`. |

---

### Verificação de Links Chave (Wiring)

| De | Para | Via | Status |
|----|------|-----|--------|
| `views/usinas.py` | `serializers/usinas.py` | `serializer_class` / `get_serializer_class()` | CONECTADO |
| `views/usinas.py` | `filters/usinas.py` | `filterset_class = UsinaFilterSet` | CONECTADO |
| `views/alertas.py` | `usinas/models.py` | `select_related('usina__garantia')` para `com_garantia` | CONECTADO |
| `urls.py` | `views/usinas.py` | `router.register('usinas', UsinaViewSet, basename='usina')` | CONECTADO |
| `urls.py` | `views/inversores.py` | `router.register('inversores', InversorViewSet, basename='inversor')` | CONECTADO |
| `urls.py` | `views/alertas.py` | `router.register('alertas', AlertaViewSet, basename='alerta')` | CONECTADO |
| `urls.py` | `views/garantias.py` | `path('garantias/', GarantiaListView.as_view())` | CONECTADO |
| `urls.py` | `views/logs.py` | `path('coleta/logs/', LogColetaListView.as_view())` | CONECTADO |
| `serializers/__init__.py` | `serializers/logs.py` | `from .logs import LogColetaSerializer` | CONECTADO |
| `views/__init__.py` | `views/logs.py` | `from .logs import LogColetaListView` | CONECTADO |

---

### Rastreio de Dados (Nível 4)

| Artefato | Variável de dados | Fonte | Produz dados reais | Status |
|----------|------------------|-------|--------------------|--------|
| `views/usinas.py` | queryset Usina | `Usina.objects.select_related(...)` | Sim — query real ao banco | FLUINDO |
| `views/garantias.py` | queryset GarantiaUsina | `GarantiaUsina.objects.select_related('usina')` | Sim — query real + filtro Python | FLUINDO |
| `views/inversores.py` | queryset Inversor | `Inversor.objects.select_related('usina', 'ultimo_snapshot')` | Sim — query real ao banco | FLUINDO |
| `views/alertas.py` | queryset Alerta | `Alerta.objects.select_related('usina', 'usina__garantia', 'catalogo_alarme')` | Sim — query real com JOIN | FLUINDO |
| `views/logs.py` | queryset LogColeta | `LogColeta.objects.select_related('credencial').all()` | Sim — query real ao banco | FLUINDO |
| `serializers/garantias.py` | `data_fim`, `dias_restantes` | `@property` nos models `GarantiaUsina` | Sim — calculados do banco | FLUINDO |
| `serializers/alertas.py` | `com_garantia` | `obj.usina.garantia` via `select_related` | Sim — propriedade real do banco | FLUINDO |

---

### Spot-Checks Comportamentais

| Comportamento | Comando | Resultado | Status |
|---------------|---------|-----------|--------|
| Suite completa de testes | `pytest api/tests/ -q` | 72 passed, 0 failed em 1.68s | PASSOU |
| payload_bruto não em serializers | `grep payload_bruto api/serializers/*.py` (excluindo comentários) | Nenhum campo com o nome nos `fields` | PASSOU |
| POST/DELETE bloqueados em usinas | `http_method_names` em `UsinaViewSet` | `['get', 'patch', 'put', 'head', 'options']` — sem `post`/`delete` | PASSOU |
| POST/DELETE bloqueados em alertas | `http_method_names` em `AlertaViewSet` | `['get', 'patch', 'head', 'options']` | PASSOU |
| Filtro status_garantia implementado em Python | `filtrar_status_garantia` em `UsinaFilterSet` | Usa propriedade `data_fim` (não ORM), conforme D-04 | PASSOU |

---

### Cobertura de Requisitos

| Requisito | Plano | Descrição | Status | Evidência |
|-----------|-------|-----------|--------|-----------|
| USN-01 | 02-02 | Lista usinas com filtros por provedor, ativo, status_garantia | SATISFEITO | `UsinaViewSet` + `UsinaFilterSet`. 5 testes em `TestUsinaList`. |
| USN-02 | 02-02 | Detalhe de usina com inversores e última coleta | SATISFEITO | `UsinaDetalheSerializer` com aninhamento. Teste `TestUsinaDetalhe`. |
| USN-03 | 02-02 | PATCH atualiza nome e capacidade | SATISFEITO | `UsinaPatchSerializer(fields=['nome','capacidade_kwp'])`. |
| USN-04 | 02-02 | status_garantia visível na listagem | SATISFEITO | `get_status_garantia()` em `UsinaListSerializer` com valores ativa/vencida/sem_garantia. |
| USN-05 | 02-02 | Histórico de snapshots de usina | SATISFEITO | `@action snapshots` com `PaginacaoSnapshots`. |
| GAR-02 | 02-02 | PUT cria ou atualiza garantia por usina | SATISFEITO | `@action garantia` com `update_or_create`. |
| GAR-03 | 02-02 | Lista garantias com filtros ativas/vencendo/vencidas | SATISFEITO | `GarantiaListView` com filtro Python. |
| GAR-04 | 02-02 | Resposta de garantia inclui dias_restantes calculado | SATISFEITO | `SerializerMethodField` em `GarantiaUsinaSerializer`. |
| GAR-05 | 02-02 | Usina sem garantia não aparece em filtro ativas | SATISFEITO | `test_usina_sem_garantia_nao_aparece_com_filtro_ativas` passando. |
| GAR-06 | 02-02 | Usina com garantia ativa aparece em filtro ativas | SATISFEITO | `test_usina_com_garantia_ativa_aparece_com_filtro_ativas` passando. |
| INV-01 | 02-03 | Lista inversores com filtros por usina, provedor, modelo | SATISFEITO | `InversorViewSet` + `InversorFilterSet`. |
| INV-02 | 02-03 | Detalhe de inversor com último snapshot completo | SATISFEITO | `InversorDetalheSerializer` com todos os campos solicitados. |
| INV-03 | 02-03 | Histórico de snapshots de inversor | SATISFEITO | `@action snapshots` em `InversorViewSet`. |
| ALT-01 | 02-03 | Lista alertas com filtros por estado, nível, usina | SATISFEITO | `AlertaViewSet` + `AlertaFilterSet`. |
| ALT-02 | 02-03 | Detalhe de alerta com dados completos | SATISFEITO | `AlertaDetalheSerializer` com todos os campos. |
| ALT-03 | 02-03 | PATCH atualiza estado e anotações | SATISFEITO | `AlertaPatchSerializer(fields=['estado','anotacoes'])`. |
| ALT-04 | 02-03 | Campo com_garantia em respostas de alerta | SATISFEITO | Presente em `AlertaListSerializer` e `AlertaDetalheSerializer`. |
| LOG-01 | 02-04 | Lista últimos ciclos de coleta com status e timestamp | SATISFEITO | `LogColetaListView` com `LogColetaSerializer`. 4 testes passando. |

**Cobertura:** 18/18 requisitos satisfeitos. Nenhum requisito órfão.

---

### Anti-Padrões Encontrados

Nenhum anti-padrão bloqueante encontrado.

| Arquivo | Padrão | Severidade | Impacto |
|---------|--------|------------|---------|
| — | — | — | — |

Verificações negativas confirmadas:
- `payload_bruto` não aparece em nenhum `fields` de serializer (apenas em comentários documentando a exclusão)
- Nenhum serializer usa `fields = '__all__'`
- Nenhum stub com `return []` ou `return {}` como dado final
- Nenhum `TODO`/`FIXME`/`placeholder` em arquivos de produção (exceto `credenciais_enc='placeholder-nao-usado-em-testes'` no conftest, que é intencional)

---

### Verificação Humana Necessária

Nenhum item requer verificação humana. Todos os comportamentos foram verificáveis via testes automatizados passando.

---

## Resumo do Atingimento do Objetivo

A fase 02 atingiu plenamente seu objetivo. Os 13 endpoints especificados no CONTEXT.md estão todos implementados, registrados no router/urls.py e cobertos por testes. Os 72 testes passam em 1.68s sem nenhuma falha ou skip.

Pontos críticos verificados com sucesso:
- `payload_bruto` excluído de todos os serializers de snapshot (T-2-03, T-2-07)
- Filtro `status_garantia` implementado corretamente em Python (não via ORM), pois `data_fim` é `@property` no model
- `com_garantia` em alertas resolvido via `select_related('usina__garantia')` — zero N+1
- `UsinaPatchSerializer` restrito a `nome` e `capacidade_kwp` — previne mass assignment (T-2-04)
- POST/DELETE bloqueados nos ViewSets onde usinas/inversores são geridos pela coleta automática
- GAR-05 e GAR-06 cobertos via testes de visibilidade por filtro de garantia

---

_Verificado: 2026-04-09_
_Verificador: Claude (gsd-verifier)_
