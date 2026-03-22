---
title: Provedor — Hoymiles S-Cloud
tipo: provedor
tags: [hoymiles, provedor, api]
---

# Hoymiles S-Cloud

## Visão Geral

| Campo | Valor |
|---|---|
| Chave interna | `hoymiles` |
| Usinas ativas | 69 |
| Usuário | `firmasolar` |
| Endpoint base | `https://global.hoymiles.com` |
| Rate limit | 5 req / 10s |
| Autenticação | Token de sessão (válido por semanas) |

---

## Autenticação

A Hoymiles usa autenticação em **dois passos** com nonce e hash de senha.

### Fluxo de Login

**Passo 1 — Pre-insp (obter nonce):**
```
POST /pvm/api/0/getLoginInfo
Body: {"user_name": "firmasolar"}
Retorna: {"nonce": "abc123..."}
```

**Passo 2 — Login com hash:**
```
POST /pvm/api/0/login
Body: {
    "user_name": "firmasolar",
    "password": hash(nonce + hash(senha))
}
Retorna: {"token": "3.xxxxxx..."}
```

O sistema suporta os algoritmos de hash das versões v1/v2 (MD5 + SHA256) e v3 (Argon2), detectando automaticamente qual usar com base na resposta do servidor.

### Credenciais no banco

```json
{
  "username": "firmasolar",
  "password": "****"
}
```

### Cache do Token

O token retornado começa com `"3."` e é válido por **semanas**. É armazenado criptografado no `CacheTokenProvedor` e renovado proativamente pela task `renovar_tokens_provedores()` a cada 6 horas.

---

## Endpoints Utilizados

### `/pvm/api/0/station/select_by_page`
Lista todas as usinas da conta (paginado).

```
POST com paginação automática até buscar todas
Retorna: [{id, name, capacity, ...}]
```

### `/pvm-data/api/0/station/data/count_station_real_data`
Dados em tempo real de uma usina (potência, energia, status).

```
POST com station_id
Retorna: {today_eq, real_power, alarm_count, connect_status, ...}
```

Este endpoint é chamado **em paralelo** com `ThreadPoolExecutor` (5 workers) para as 69 usinas simultaneamente, reduzindo o tempo total de coleta.

### `/pvm-data/api/0/inverter/data/`
Inversores de uma usina e seus dados em tempo real.

```
POST com station_id
Retorna: [{sn, model, real_power, today_e, total_e, state, ...}]
```

### `/pvm-data/api/0/alarmData/select_realtime_alarm`
Alarmes ativos de todas as usinas.

```
POST
Retorna: [{alarm_id, alarm_name, alarm_level, station_id, sn, ...}]
```

---

## Estratégia de Coleta em Paralelo

Com 69 usinas, a Hoymiles permite até 5 requisições simultâneas. O adaptador usa `ThreadPoolExecutor` para buscar os dados realtime das usinas em paralelo:

```python
with ThreadPoolExecutor(max_workers=5) as executor:
    futuras = {executor.submit(buscar_realtime, usina.id): usina.id
               for usina in todas_as_usinas}
```

Isso reduz o tempo de coleta de ~14 chamadas sequenciais para ~3 chamadas paralelas de 5.

---

## Campos Normalizados

```python
DadosUsina:
    id_usina_provedor  = id (string)
    nome               = name
    capacidade_kwp     = capacity
    potencia_atual_kw  = real_power
    energia_hoje_kwh   = today_eq
    status             = 'normal' se connect_status ok, senão 'offline'
    qtd_alertas        = alarm_count

DadosInversor:
    id_inversor_provedor = sn
    numero_serie         = sn
    modelo               = model
    estado               = baseado em state
    pac_kw               = real_power
    energia_hoje_kwh     = today_e
    energia_total_kwh    = total_e
```

---

## Veja Também

- [[modulos/coleta]]
- [[modulos/provedores]]
- [[operacional/credenciais]]
