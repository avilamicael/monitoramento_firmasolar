---
title: Módulo — Usinas
tipo: modulo
tags: [usinas, inversores, snapshots, models]
---

# Módulo: Usinas

Armazena os dados de usinas e inversores, com histórico de medições em snapshots append-only.

**Arquivos:**
- `usinas/models.py`
- `usinas/admin.py`

---

## Models

### Usina

Dados cadastrais fixos de uma usina solar. Um registro por usina.

```python
class Usina:
    id                  : UUIDField (PK)
    id_usina_provedor   : CharField (ID no sistema do fabricante)
    provedor            : CharField (solis / hoymiles / fusionsolar)
    credencial          : FK → CredencialProvedor
    nome                : CharField
    capacidade_kwp      : FloatField
    fuso_horario        : CharField (ex: 'America/Sao_Paulo')
    endereco            : TextField
    ativo               : BooleanField
    ultimo_snapshot     : OneToOneField → SnapshotUsina (null)

    unique_together: (id_usina_provedor, provedor)
```

O campo `ultimo_snapshot` é desnormalizado — aponta para o snapshot mais recente da usina. Isso permite que o Grafana faça queries rápidas de "estado atual" sem precisar de subqueries ou joins complexos.

### SnapshotUsina

Medição em um instante de tempo. Append-only.

```python
class SnapshotUsina:
    id                  : UUIDField (PK)
    usina               : FK → Usina
    coletado_em         : DateTimeField (arredondado para 10 min)
    data_medicao        : DateTimeField (timestamp do provedor)
    potencia_kw         : FloatField (potência AC atual)
    energia_hoje_kwh    : FloatField
    energia_mes_kwh     : FloatField
    energia_total_kwh   : FloatField
    status              : 'normal' | 'aviso' | 'offline' | 'construcao'
    qtd_inversores      : IntegerField
    qtd_inversores_online: IntegerField
    qtd_alertas         : IntegerField
    payload_bruto       : JSONField (resposta completa do provedor)

    unique_together: (usina, coletado_em)
    indexes: (usina, -coletado_em), (-coletado_em)
```

### Inversor

Dados cadastrais de um inversor. Um registro por inversor.

```python
class Inversor:
    id                  : UUIDField (PK)
    usina               : FK → Usina
    id_inversor_provedor: CharField
    numero_serie        : CharField
    modelo              : CharField
    ativo               : BooleanField
    ultimo_snapshot     : OneToOneField → SnapshotInversor (null)

    unique_together: (usina, id_inversor_provedor)
```

### SnapshotInversor

Medição do inversor em um instante de tempo. Append-only.

```python
class SnapshotInversor:
    id                  : UUIDField (PK)
    inversor            : FK → Inversor
    coletado_em         : DateTimeField (arredondado para 10 min)
    data_medicao        : DateTimeField
    estado              : 'normal' | 'aviso' | 'offline'
    pac_kw              : FloatField (potência AC atual)
    energia_hoje_kwh    : FloatField
    energia_total_kwh   : FloatField
    soc_bateria         : FloatField (null se sem armazenamento)
    strings_mppt        : JSONField (ex: {"mppt_1_cap": 120.5, "mppt_2_cap": 118.2})
    payload_bruto       : JSONField

    unique_together: (inversor, coletado_em)
    indexes: (inversor, -coletado_em)
```

---

## Retenção de Dados

Snapshots com mais de **90 dias** são removidos automaticamente pela task `limpar_snapshots_antigos()` às 03:00 diariamente.

Os dados cadastrais (Usina, Inversor) não são removidos automaticamente.

---

## Queries Úteis (PostgreSQL / Grafana)

**Estado atual de todas as usinas ativas:**
```sql
SELECT u.nome, u.provedor, s.potencia_kw, s.status, s.coletado_em
FROM usinas_usina u
JOIN usinas_snapshotusina s ON s.id = u.ultimo_snapshot_id
WHERE u.ativo = true
ORDER BY s.potencia_kw DESC;
```

**Histórico de potência de uma usina (últimas 24h):**
```sql
SELECT coletado_em, potencia_kw
FROM usinas_snapshotusina
WHERE usina_id = 'uuid-aqui'
  AND coletado_em > NOW() - INTERVAL '24 hours'
ORDER BY coletado_em;
```

**Inversores offline agora:**
```sql
SELECT u.nome AS usina, i.modelo, i.numero_serie, s.estado, s.coletado_em
FROM usinas_inversor i
JOIN usinas_usina u ON u.id = i.usina_id
JOIN usinas_snapshotinversor s ON s.id = i.ultimo_snapshot_id
WHERE s.estado = 'offline'
ORDER BY u.nome;
```

---

## Veja Também

- [[modulos/coleta]]
- [[grafana/dashboards]]
