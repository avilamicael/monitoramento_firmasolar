# Phase 3: Analytics Endpoints - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-09
**Phase:** 03-analytics-endpoints
**Areas discussed:** Coordenadas, Cálculo de potência, Inversor ativo, Formato de resposta
**Mode:** --auto (all decisions auto-selected)

---

## Coordenadas de usinas

| Option | Description | Selected |
|--------|-------------|----------|
| Adicionar campos FloatField(null=True) + migração | Simples, reversível, sem risco | ✓ |
| Extrair de campo endereco via geocoding | Complexo, dependência externa |  |
| Criar model separado UsinaCoordenada | Overengineering para 2 campos |  |

**User's choice:** [auto] Adicionar campos FloatField(null=True) + migração (recommended default)
**Notes:** Model Usina não possui lat/lng — migração necessária. Campos opcionais.

---

## Cálculo de potência média

| Option | Description | Selected |
|--------|-------------|----------|
| SnapshotUsina.potencia_kw do ultimo_snapshot | Campo desnormalizado, query simples | ✓ |
| Média de SnapshotInversor.pac_kw de todos inversores | Mais granular, query complexa |  |
| Média temporal (últimas N horas) | Mais representativo, muito mais complexo |  |

**User's choice:** [auto] SnapshotUsina.potencia_kw do ultimo_snapshot (recommended default)
**Notes:** Campo já desnormalizado e usado nos ViewSets da Phase 2.

---

## Definição de inversor ativo

| Option | Description | Selected |
|--------|-------------|----------|
| ultimo_snapshot != null AND pac_kw > 0 | Alinhado com roadmap | ✓ |
| Qualquer inversor com snapshot recente (24h) | Inclui inativos temporários |  |
| Inversor.ativo == True | Campo não existe no model |  |

**User's choice:** [auto] ultimo_snapshot != null AND pac_kw > 0 (recommended default)
**Notes:** Definição do roadmap: "inversores ativos (com potência > 0 no último snapshot)".

---

## Formato de resposta dos analytics

| Option | Description | Selected |
|--------|-------------|----------|
| Claude's Discretion | Planner decide a estrutura JSON | ✓ |
| Definir contratos agora | Lock antes do planejamento |  |

**User's choice:** [auto] Claude's Discretion (recommended default)
**Notes:** Decisão técnica sem impacto em UX nesta fase (backend only).

---

## Claude's Discretion

- Estrutura JSON dos endpoints
- Otimização de queries
- Ordenação do ranking

## Deferred Ideas

None
