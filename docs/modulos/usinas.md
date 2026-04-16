---
title: Módulo — Usinas
tipo: modulo
tags: [usinas, inversores, snapshots, garantia, models]
updated: 2026-04-15
---

# Módulo: Usinas

Armazena os dados de usinas, inversores e garantias, com histórico de medições em snapshots append-only.

**Arquivos:**
- `usinas/models.py` — `Usina`, `SnapshotUsina`, `Inversor`, `SnapshotInversor`, `GarantiaUsina`
- `usinas/admin.py`

---

## Models

### Usina

Dados cadastrais fixos de uma usina solar.

```python
class Usina:
    id                  : UUIDField (PK)
    id_usina_provedor   : CharField
    provedor            : CharField  # solis / hoymiles / fusionsolar / solarman / auxsol
    credencial          : FK → CredencialProvedor
    nome                : CharField
    capacidade_kwp      : FloatField
    fuso_horario        : CharField (default 'America/Sao_Paulo')
    endereco            : TextField
    cidade              : CharField
    telefone            : CharField
    latitude            : FloatField (nullable)
    longitude           : FloatField (nullable)
    ativo               : BooleanField  # False = coleta/alertas pausados
    tensao_sobretensao_v: FloatField  # default 240.0, editável na UI
    ultimo_snapshot     : OneToOneField → SnapshotUsina (null)

    unique_together: (id_usina_provedor, provedor)
```

**Campos importantes:**

- `ativo`: pode ser desativado **automaticamente** por `_pausar_usinas_inativas` (ver [[modulos/coleta]]) ou manualmente via `AtivoToggleButton` na página da usina (`PATCH /api/usinas/{id}/` com `ativo=false`). Usinas inativas não geram snapshot nem alertas no ciclo de coleta.
- `tensao_sobretensao_v`: limite para o alerta interno de sobretensão (ver [[modulos/alertas]]). Editável via dialog na página de detalhe da usina. Validação: 180–280 V.
- `ultimo_snapshot`: ponteiro desnormalizado para consultas rápidas em dashboards.

### SnapshotUsina

Medição em um instante de tempo. Append-only. `get_or_create` por `(usina, coletado_em arredondado a 10 min)`.

```python
class SnapshotUsina:
    usina               : FK → Usina
    coletado_em         : DateTimeField (arredondado para 10 min)
    data_medicao        : DateTimeField
    potencia_kw         : FloatField
    energia_hoje_kwh    : FloatField
    energia_mes_kwh     : FloatField
    energia_total_kwh   : FloatField
    status              : 'normal' | 'aviso' | 'offline' | 'construcao'
    qtd_inversores      : IntegerField
    qtd_inversores_online: IntegerField
    qtd_alertas         : IntegerField
    payload_bruto       : JSONField
```

### Inversor

```python
class Inversor:
    usina               : FK → Usina
    id_inversor_provedor: CharField
    numero_serie        : CharField
    modelo              : CharField
    ultimo_snapshot     : OneToOneField → SnapshotInversor (null)

    unique_together: (usina, id_inversor_provedor)
```

### SnapshotInversor

Inclui grandezas elétricas usadas pela análise interna de alertas:

```python
class SnapshotInversor:
    inversor        : FK → Inversor
    coletado_em     : DateTimeField
    data_medicao    : DateTimeField
    estado          : 'normal' | 'aviso' | 'offline'
    pac_kw          : FloatField
    energia_hoje_kwh, energia_total_kwh : FloatField
    soc_bateria     : FloatField (null)
    strings_mppt    : JSONField
    tensao_ac_v     : FloatField (null)   # usado em tensao_zero e sobretensao
    corrente_ac_a   : FloatField (null)   # usado em corrente_baixa
    tensao_dc_v     : FloatField (null)
    corrente_dc_a   : FloatField (null)
    frequencia_hz   : FloatField (null)
    temperatura_c   : FloatField (null)
    payload_bruto   : JSONField
```

### GarantiaUsina (novo)

Garantia comercial da usina. `data_fim`, `ativa` e `dias_restantes` são **properties calculadas** (não colunas no banco).

```python
class GarantiaUsina:
    usina        : OneToOneField → Usina
    data_inicio  : DateField
    meses        : PositiveIntegerField
    observacoes  : TextField
    criado_em, atualizado_em

    @property
    def data_fim(self): return data_inicio + relativedelta(months=meses)
    @property
    def ativa(self):    return data_fim >= hoje
    @property
    def dias_restantes(self): return max((data_fim - hoje).days, 0)
```

**Auto-criação:** `ServicoIngestao.upsert_usina` cria `GarantiaUsina(data_inicio=hoje, meses=config.meses_garantia_padrao)` na primeira inserção da usina (ver [[arquitetura/decisoes]] e [[modulos/coleta#Upsert de Usinas + auto-criação de garantia]]).

**Impacto operacional:**

- Alertas **internos** só são gerados para usinas com `garantia.ativa=True` (ver [[modulos/alertas#Regra de garantia]]).
- `GET /api/alertas/` retorna `com_garantia: bool` por alerta (baseado em `Usina.garantia.ativa`).
- `GET /api/usinas/` retorna `status_garantia: 'ativa' | 'vencida' | 'sem_garantia'`.
- Alerta interno `garantia_expirando` avisa quando dias restantes ≤ 30 (aviso) ou ≤ 7 (importante).

---

## Retenção de Dados

Snapshots com mais de **90 dias** são removidos automaticamente pela task `limpar_snapshots_antigos()` às 03:00 diariamente.

Os dados cadastrais (Usina, Inversor, GarantiaUsina) não são removidos automaticamente.

---

## Endpoints de API

| Método | Path | Permissão | Observação |
|---|---|---|---|
| GET | `/api/usinas/` | autenticado | Lista com `status_garantia` |
| GET | `/api/usinas/{id}/` | autenticado | Detalhe + inversores + `tensao_sobretensao_v` + `ultimo_snapshot` |
| PATCH | `/api/usinas/{id}/` | autenticado | `UsinaPatchSerializer` — aceita `nome`, `capacidade_kwp`, `tensao_sobretensao_v`, `ativo` |
| GET | `/api/garantias/` | autenticado | Lista de `GarantiaUsina` |

POST/DELETE não são expostos — usinas nascem exclusivamente pela coleta.

---

## Queries Úteis (PostgreSQL / Grafana)

**Estado atual de usinas ativas com garantia ativa:**
```sql
SELECT u.nome, u.provedor, s.potencia_kw, s.status, s.coletado_em
FROM usinas_usina u
JOIN usinas_snapshotusina s ON s.id = u.ultimo_snapshot_id
LEFT JOIN usinas_garantiausina g ON g.usina_id = u.id
WHERE u.ativo = true
  AND g.data_inicio + make_interval(months => g.meses) >= CURRENT_DATE
ORDER BY s.potencia_kw DESC;
```

**Usinas sem garantia (não geram alertas internos):**
```sql
SELECT u.nome, u.provedor
FROM usinas_usina u
LEFT JOIN usinas_garantiausina g ON g.usina_id = u.id
WHERE g.id IS NULL
   OR g.data_inicio + make_interval(months => g.meses) < CURRENT_DATE;
```

---

## Veja Também

- [[modulos/coleta]]
- [[modulos/alertas]]
- [[grafana/dashboards]]
- [[arquitetura/decisoes]]
