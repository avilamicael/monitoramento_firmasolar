---
title: Provedor — Huawei FusionSolar
tipo: provedor
tags: [fusionsolar, huawei, provedor, api]
---

# Huawei FusionSolar

## Visão Geral

| Campo | Valor |
|---|---|
| Chave interna | `fusionsolar` |
| Usinas ativas | 50 |
| Usuário API | `api_firmasolar` |
| Endpoint base | `https://intl.fusionsolar.huawei.com/thirdData` |
| Intervalo de dados | 5 min (medição) |
| Intervalo de coleta | 15 min (mínimo 900s configurado) |
| Rate limit | 1 req / 5s por conta |

---

## Autenticação

A FusionSolar usa autenticação **stateful via sessão** com XSRF-TOKEN.

### Fluxo de Login

```
POST /thirdData/login
Body: {"userName": "api_firmasolar", "systemCode": "****"}

Resposta: cookie XSRF-TOKEN
→ Injetado como header em todas as requisições seguintes
```

**Atenção:** O campo `systemCode` é o que a Huawei chama de "senha" na configuração do usuário NorthBound. Não é a senha de login do portal.

### Credenciais no banco

```json
{
  "username": "api_firmasolar",
  "system_code": "****"
}
```

### Expiração de Sessão

A sessão expira após algumas horas. O sistema detecta a expiração por:
- HTTP 401 → re-login automático
- `failCode=305` na resposta JSON → re-login automático + sleep 2s
- Mensagem contendo "login" → re-login automático

O token renovado é salvo no `CacheTokenProvedor` (criptografado) para evitar re-login a cada coleta.

---

## Endpoints Utilizados

### `/getStationList`
Lista todas as usinas da conta.

```
POST /thirdData/getStationList
Body: {}
Retorna: [{stationCode, stationName, capacity, address, timeZone, ...}]
```

### `/getStationRealKpi`
KPIs em tempo real das usinas (em lote).

```
POST /thirdData/getStationRealKpi
Body: {"stationCodes": "CODE1,CODE2,..."}
Retorna: [{stationCode, dataItemMap: {total_current_power, day_power, month_power, total_power}}]
```

### `/getDevList`
Lista todos os dispositivos (inversores, dataloggers) de todas as usinas em **uma única chamada**.

```
POST /thirdData/getDevList
Body: {"stationCodes": "CODE1,CODE2,..."}
Retorna: [{id, devTypeId, devSn, esnCode, invType, stationCode, ...}]
```

**Tipos de dispositivo conhecidos:**

| devTypeId | Tipo |
|---|---|
| 1 | String Inverter (trifásico, commercial/utility) |
| 38 | SUN2000 residencial / SmartLogger integrado |
| 62 | Outros (datalogger, etc.) — sem KPI |

### `/getDevRealKpi`
KPIs em tempo real dos dispositivos, **por tipo**.

```
POST /thirdData/getDevRealKpi
Body: {"devIds": "ID1,ID2,...", "devTypeId": 38}
Retorna: [{devId, dataItemMap: {active_power, day_cap, total_cap, run_state, mppt_*_cap, ...}}]
```

Apenas `devTypeId` 1 e 38 são suportados. Outros retornam `failCode=20013`.

### `/getAlarmList`
Alertas ativos da conta.

```
POST /thirdData/getAlarmList
Body: {"language": "pt_BR"}
Retorna: [{alarmId, alarmName, alarmLevel, stationCode, devSn, repairSuggestion, ...}]
```

**Nível de alarme FusionSolar:**

| alarmLevel | Nível interno |
|---|---|
| 1 | `critico` |
| 2 | `importante` |
| 3 | `aviso` |
| 4 | `info` |

---

## Estratégia de Coleta em Lote

Para uma conta com 50 usinas, o FusionSolar poderia exigir 50+ chamadas individuais para buscar inversores. Isso causaria rate limit 407 imediatamente.

**Solução implementada:**

```python
# 1. Uma chamada para todas as usinas
dados = POST /getDevList com stationCodes = "CODE1,CODE2,...,CODE50"

# 2. Uma chamada por devTypeId encontrado
# Se há devTypeId 38 e devTypeId 1:
kpi_38 = POST /getDevRealKpi com devTypeId=38, devIds = todos os IDs do tipo 38
kpi_1  = POST /getDevRealKpi com devTypeId=1,  devIds = todos os IDs do tipo 1

# Total: 4 chamadas para 50 usinas (em vez de 50+)
```

O resultado é armazenado em `_cache_inversores` no adaptador e distribuído por usina em `buscar_inversores()`.

---

## Rate Limiting e Backoff

| Cenário | Comportamento |
|---|---|
| `failCode=407` | `ProvedorErroRateLimit` → retry com backoff exponencial |
| 3 retries esgotados | Backoff de 30 min via Redis |
| `min_intervalo_coleta_segundos=900` | Coletas ignoradas se última bem-sucedida há < 15 min |

---

## Campos Normalizados

```python
DadosUsina:
    id_usina_provedor  = stationCode
    nome               = stationName
    capacidade_kwp     = capacity (MW → kWp: × 1000 se < 100)
    potencia_atual_kw  = kpi.total_current_power
    energia_hoje_kwh   = kpi.day_power
    energia_mes_kwh    = kpi.month_power
    energia_total_kwh  = kpi.total_power
    fuso_horario       = timeZone

DadosInversor:
    id_inversor_provedor = id
    numero_serie         = esnCode ou devSn
    modelo               = invType ou devName
    estado               = 'normal' se run_state=1, senão 'offline'
    pac_kw               = kpi.active_power
    energia_hoje_kwh     = kpi.day_cap
    energia_total_kwh    = kpi.total_cap (ou mppt_total_cap)
    strings_mppt         = {mppt_N_cap: valor, ...}
```

---

## Configuração na API Huawei

Para criar o usuário NorthBound no portal FusionSolar:
`System > Company Management > System > Northbound Management`

**Recomendação Huawei:** 1 usuário API por integração. Não compartilhar o usuário entre sistemas.

---

## Veja Também

- [[modulos/coleta]]
- [[modulos/provedores]]
- [[arquitetura/fluxo-de-coleta]]
- [[operacional/credenciais]]
