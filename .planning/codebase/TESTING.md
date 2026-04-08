# Testing Patterns

**Analysis Date:** 2026-04-07

## Test Framework

**Runner:**
- pytest 8.x
- Config: `backend_monitoramento/pytest.ini`

**Django Integration:**
- pytest-django 4.x
- `DJANGO_SETTINGS_MODULE = config.settings.dev` (set in `pytest.ini`)

**Test Data / Factories:**
- factory-boy 3.x (installed in `requirements/dev.txt`, not yet used in existing tests — fixtures via Django ORM directly)

**Run Commands:**
```bash
cd backend_monitoramento
pytest                          # Run all tests
pytest alertas/test_supressao_inteligente.py  # Run specific file
pytest -v                       # Verbose output
pytest --tb=short               # Short traceback format
```

## Test File Organization

**Location:**
- Co-located with the module being tested, inside the same Django app directory
- Pattern: `{app}/{test_module_name}.py`

**Existing test files:**
- `backend_monitoramento/alertas/test_supressao_inteligente.py` — tests for `alertas/supressao_inteligente.py`

**Naming:**
- Test files: `test_{module_name}.py` (matches `python_files = test_*.py` in `pytest.ini`)
- Test classes: `Test{ConceptBeingTested}` (matches `python_classes = Test` in `pytest.ini`)
- Test functions: `test_{scenario_description}` (matches `python_functions = test_` in `pytest.ini`)

## Test Structure

**Module docstring** at top of test file describes what is being tested and lists the main scenarios covered:
```python
"""
Testes para alertas/supressao_inteligente.py

Cobre os três cenários principais de e_desligamento_gradual():
  - Desligamento gradual: último pot abaixo do limiar → True (suprimir)
  - Desligamento abrupto: último pot acima do limiar → False (alertar)
  - Sem snapshots nas 24h: conservador → False (alertar)
"""
```

**Test class grouping** — related tests grouped in a class named after the function under test:
```python
@pytest.mark.django_db
class TestEDesligamentoGradual:

    def test_gradual_retorna_true(self, usina):
        ...

    def test_abrupto_retorna_false(self, usina):
        ...
```

**`@pytest.mark.django_db`** applied at class level (not per method) when all tests in the class require DB access.

**Test names describe behavior, not implementation** — each name states the condition and expected outcome:
- `test_gradual_retorna_true` — condition + return value
- `test_sem_snapshots_retorna_false` — missing data + conservative result
- `test_exatamente_no_limiar_considera_gradual` — boundary condition

**Inline comments** explain domain-specific values (thresholds, limits):
```python
def test_gradual_retorna_true(self, usina):
    """Último snapshot com pot abaixo do limiar → desligamento gradual."""
    # Limiar para 7.38 kWp = max(1.0, 7.38 * 0.05) = 1.0 kW (mínimo absoluto)
    _cria_snapshot(usina, horas_atras=2.5, potencia_kw=0.18)
    ...
    assert e_desligamento_gradual(usina) is True
```

## Fixtures

**pytest fixtures** defined at module level in the same test file:
```python
@pytest.fixture
def credencial(db):
    return CredencialProvedor.objects.create(
        provedor='hoymiles',
        credenciais_enc='placeholder',
        ativo=True,
    )

@pytest.fixture
def usina(db, credencial):
    return Usina.objects.create(
        id_usina_provedor='test-001',
        provedor='hoymiles',
        credencial=credencial,
        nome='Usina de Teste',
        capacidade_kwp=7.38,
        fuso_horario='America/Sao_Paulo',
    )
```

**No `conftest.py` exists** — fixtures are defined per test file, not shared globally. As the test suite grows, common fixtures should be extracted to a `conftest.py` at `backend_monitoramento/conftest.py`.

**`db` fixture** from pytest-django is used as a dependency parameter to enable DB access in fixtures.

## Helper Functions

**Private helper functions** (prefixed `_`) inside test files for repeated setup operations that are not fixtures:
```python
def _cria_snapshot(usina, horas_atras, potencia_kw):
    """Cria um SnapshotUsina com coletado_em relativo ao momento atual."""
    coletado_em = timezone.now() - timedelta(hours=horas_atras)
    return SnapshotUsina.objects.create(
        usina=usina,
        coletado_em=coletado_em,
        data_medicao=coletado_em,
        potencia_kw=potencia_kw,
        ...
    )
```

Use helper functions (not fixtures) when the function takes parameters that vary per test.

## Mocking

**No mocking framework usage observed in existing tests.** The existing test (`test_supressao_inteligente.py`) tests through the real Django ORM with a test database — no mocks.

**Policy inferred from `CLAUDE.md`:**
- Mock only external dependencies (third-party APIs, external services)
- Never mock the logic under test
- For unit tests of adapter normalization logic (`_normalizar_usina`, `_normalizar_inversor`), mock the HTTP client (`requests.Session`) or the low-level query functions (`listar_usinas`, `listar_inversores`)

**Recommended mocking for future tests:**
```python
# For adapter HTTP calls:
from unittest.mock import patch, MagicMock

@patch('provedores.solis.consultas.listar_usinas')
def test_buscar_usinas_normaliza_campos(mock_listar):
    mock_listar.return_value = [{'id': '123', 'stationName': 'Usina X', ...}]
    ...

# For Celery tasks depending on external adapters:
@patch('provedores.registro.get_adaptador')
def test_coletar_dados_provedor_auth_error(mock_get_adaptador, ...):
    mock_adaptador = MagicMock()
    mock_adaptador.buscar_usinas.side_effect = ProvedorErroAuth('credencial inválida')
    mock_get_adaptador.return_value = mock_adaptador
    ...
```

## Assertions

**Direct equality with `is`** for boolean return values (preferred over `==`):
```python
assert e_desligamento_gradual(usina) is True
assert e_desligamento_gradual(usina) is False
```

One `assert` per test when testing a single behavior. Tests that verify multiple related outcomes may group them, but each test has a single docstring-stated intent.

## Boundary and Edge Cases

The existing test suite demonstrates emphasis on **boundary conditions**:
- `test_exatamente_no_limiar_considera_gradual` — boundary at threshold value
- `test_snapshots_fora_da_janela_ignorados` — time window edge
- `test_limiar_usa_minimo_absoluto_sem_capacidade` — zero capacity edge case
- `test_sem_snapshots_retorna_false` — empty data set (conservative default)

Follow this pattern: for any function with thresholds, time windows, or comparisons, include tests for exactly-at-boundary, just-inside, and just-outside values.

## Database Tests

All tests requiring Django models use `@pytest.mark.django_db` (at class or function level).

**Django `timezone.now()`** used for time-relative test data, not `datetime.now()` — keeps timezone awareness consistent.

Test data uses realistic domain values (real `capacidade_kwp` values like `7.38 kWp`, realistic potency readings) to make threshold calculations verifiable with comments.

## Coverage

**No coverage configuration** — no minimum threshold enforced, no coverage reporting setup in `pytest.ini`.

**Current coverage state:**
- `alertas/supressao_inteligente.py` — covered by `alertas/test_supressao_inteligente.py` (comprehensive: 6 test cases covering all branches)
- All other modules — **not tested**

**High-priority untested modules** (contain business logic):
- `coleta/ingestao.py` (`ServicoIngestao`) — core upsert and alert sync logic
- `alertas/categorizacao.py` (`inferir_categoria`) — keyword-matching categorization (pure function, easy to test)
- `provedores/solis/adaptador.py` (`_normalizar_usina`, `_normalizar_inversor`, `_normalizar_alerta`) — data normalization
- `provedores/hoymiles/adaptador.py` (`_extrair_alertas`) — alert extraction from warn_data flags
- `provedores/cripto.py` (`criptografar_credenciais`, `descriptografar_credenciais`) — encryption round-trip

## Test Types

**Integration tests (DB-backed):**
- Use real Django ORM with test database
- Use `@pytest.mark.django_db`
- Cover full behavior including DB queries
- Example: `test_supressao_inteligente.py`

**Unit tests (no DB):**
- Pure functions like `inferir_categoria`, `_para_float`, `_normalizar_status`
- No `@pytest.mark.django_db` needed
- No fixtures needed
- Fast and isolated

**E2E Tests:**
- Not present. Grafana dashboards are the primary observability surface, not automated E2E tests.

## Adding New Tests

1. Create `test_{module_name}.py` in the same app directory as the module being tested.
2. Write a module docstring listing what scenarios are covered.
3. Group related test methods in a class named `Test{FunctionOrConceptName}`.
4. Define fixtures at module level using `@pytest.fixture`; use `_helper_functions()` for parametrized test data.
5. Apply `@pytest.mark.django_db` at the class level when DB is needed.
6. Write descriptive test names that state condition and expected outcome.
7. Include inline comments explaining domain-specific threshold calculations.
8. Cover: happy path, failure path, boundary values, and empty/missing data edge cases.

---

*Testing analysis: 2026-04-07*
