---
title: Provedor — Solis Cloud
tipo: provedor
tags: [solis, provedor, api]
---

# Solis Cloud

## Visão Geral

| Campo | Valor |
|---|---|
| Chave interna | `solis` |
| Usinas ativas | 12 |
| Email da conta | `engenharia@firmasolar.com.br` |
| Endpoint base | `https://www.soliscloud.com:13333` |
| Rate limit | 3 req / 5s |
| Autenticação | HMAC-SHA1 stateless (sem sessão) |

---

## Autenticação

A Solis usa autenticação **stateless por assinatura HMAC-SHA1** em cada requisição. Não há sessão ou token para gerenciar.

### Mecanismo de Assinatura

Cada requisição é assinada com:
```
HMAC-SHA1(
    key = app_secret,
    msg = "POST\n" + md5(body) + "\napplication/json\n" + data + "\n" + path
)
```

O resultado vai no header `Authorization`:
```
Authorization: API {api_key}:{assinatura_base64}
```

### Credenciais no banco

```json
{
  "api_key": "1300386381677237960",
  "app_secret": "44b0ec1056ba46dfab4fd3051bc7b609"
}
```

**Nota:** A senha da conta (`edyengenharia`) e o email são credenciais do portal web. A API usa apenas `api_key` + `app_secret`, que são gerados no painel da Solis Cloud e são independentes da senha de login.

---

## Endpoints Utilizados

### `/v1/api/userStationList`
Lista todas as usinas com paginação.

```
POST com paginação (pageNo=1, pageSize=100)
Retorna: {data: {page: {records: [...]}}}
```

### `/v1/api/inverterList`
Inversores de uma usina específica.

```
POST com stationId
Retorna: lista de inversores com dados realtime
```

### `/v1/api/alarmList`
Alertas ativos da conta.

```
POST
Retorna: lista de alarmes com tipo, nível, data
```

---

## Características

- **Stateless:** Nenhum token para gerenciar. Cada requisição é auto-assinada.
- **Mais simples operacionalmente:** Sem risco de expiração de sessão ou re-login.
- **Rate limit moderado:** 3 req / 5s é suficiente para 12 usinas.

---

## Campos Normalizados

```python
DadosUsina:
    id_usina_provedor  = id
    nome               = stationName
    capacidade_kwp     = capacity (kWp)
    potencia_atual_kw  = power
    energia_hoje_kwh   = dayEnergy
    energia_mes_kwh    = monthEnergy
    energia_total_kwh  = allEnergy

DadosInversor:
    id_inversor_provedor = id
    numero_serie         = sn
    modelo               = model
    estado               = baseado em state
    pac_kw               = power (AC)
    energia_hoje_kwh     = eToday
    energia_total_kwh    = eTotal
```

---

## Veja Também

- [[modulos/coleta]]
- [[modulos/provedores]]
- [[operacional/credenciais]]
