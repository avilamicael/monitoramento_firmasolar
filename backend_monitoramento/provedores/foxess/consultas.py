"""
Consultas à FoxESS OpenAPI.

Cada função faz uma chamada HTTP autenticada e retorna os dados brutos
(dict ou list). A normalização para os dataclasses do sistema é feita no
adaptador.

Documentação oficial: https://www.foxesscloud.com/public/i18n/en/OpenApiDocument.html

Limites documentados e observados:
  - 1 requisição por segundo (queries)
  - 1440 chamadas por inversor por dia (retorna errno=40400 ao estourar)
"""
import json
import logging
import time

import requests

from provedores.excecoes import ProvedorErro, ProvedorErroAuth, ProvedorErroRateLimit
from .autenticacao import montar_headers

logger = logging.getLogger(__name__)

BASE_URL = 'https://www.foxesscloud.com'
ITENS_POR_PAGINA = 100

# Erros de autenticação observados:
#   40256 — "illegal signature"
#   40257 — "illegal token"
#   40258 — "api key expired"
#   40260 — "permission denied"
_ERRNOS_AUTH = {40256, 40257, 40258, 40260}

# Erros de rate limit:
#   40400 — limite diário de 1440 chamadas por inversor atingido
#   40401 — chamadas concorrentes
_ERRNOS_RATE_LIMIT = {40400, 40401}


def _chamar(method: str, path: str, api_key: str, *, params=None, body=None) -> dict:
    headers = montar_headers(path, api_key)
    url = BASE_URL + path
    data = json.dumps(body) if body is not None else None

    inicio = time.time()
    try:
        resp = requests.request(
            method, url, headers=headers, params=params, data=data, timeout=20,
        )
    except requests.RequestException as exc:
        logger.warning('FoxESS: erro de rede em %s — %s', path, exc)
        raise ProvedorErro(f'FoxESS: erro de rede em {path}: {exc}') from exc

    duracao_ms = int((time.time() - inicio) * 1000)

    if resp.status_code == 429:
        logger.warning('FoxESS: rate limit HTTP 429 em %s', path)
        raise ProvedorErroRateLimit('FoxESS: rate limit atingido (HTTP 429)')
    if resp.status_code in (401, 403):
        logger.error('FoxESS: credenciais inválidas (HTTP %d) em %s', resp.status_code, path)
        raise ProvedorErroAuth(f'FoxESS: credenciais inválidas (HTTP {resp.status_code})')

    try:
        dados = resp.json()
    except ValueError as exc:
        trecho = resp.text[:200]
        logger.error('FoxESS: resposta não-JSON em %s — %s', path, trecho)
        raise ProvedorErro(f'FoxESS: resposta inválida em {path}: {trecho}') from exc

    errno = dados.get('errno')
    msg = dados.get('msg') or ''

    if errno == 0:
        logger.debug('FoxESS: %s %s → HTTP %d em %dms', method, path, resp.status_code, duracao_ms)
        return dados

    if errno in _ERRNOS_AUTH:
        raise ProvedorErroAuth(f'FoxESS: erro de autenticação em {path} — errno={errno} msg={msg}')
    if errno in _ERRNOS_RATE_LIMIT:
        raise ProvedorErroRateLimit(f'FoxESS: rate limit em {path} — errno={errno} msg={msg}')

    raise ProvedorErro(f'FoxESS: erro da API em {path} — errno={errno} msg={msg}')


def listar_usinas(api_key: str) -> list[dict]:
    """
    Retorna todas as usinas da conta (paginado).
    Endpoint: POST /op/v0/plant/list
    Campos retornados por usina: stationID, name, ianaTimezone.
    """
    resultado: list[dict] = []
    pagina = 1
    while True:
        dados = _chamar('POST', '/op/v0/plant/list', api_key,
                        body={'currentPage': pagina, 'pageSize': ITENS_POR_PAGINA})
        pagina_dados = dados.get('result') or {}
        registros = pagina_dados.get('data') or []
        resultado.extend(registros)
        total = int(pagina_dados.get('total') or 0)
        if not registros or len(resultado) >= total:
            break
        pagina += 1
    return resultado


def detalhe_usina(station_id: str, api_key: str) -> dict:
    """
    Retorna detalhes de uma usina (capacidade, endereço, timezone).
    Endpoint: GET /op/v0/plant/detail?id=<stationID>
    Não retorna lat/long — esses campos ficam None.
    """
    dados = _chamar('GET', '/op/v0/plant/detail', api_key, params={'id': station_id})
    return dados.get('result') or {}


def listar_dispositivos(api_key: str) -> list[dict]:
    """
    Retorna todos os dispositivos (inversores) da conta, em todas as usinas.
    Endpoint: POST /op/v0/device/list
    Campos: deviceSN, deviceType, stationID, stationName, moduleSN, productType,
            hasBattery, hasPV, status.

    Atenção: o campo `status` é inconsistente (foi observado 3=offline em todos
    os devices mesmo quando estavam gerando). O adaptador deriva o status real
    a partir dos dados do real/query (currentFault).
    """
    resultado: list[dict] = []
    pagina = 1
    while True:
        dados = _chamar('POST', '/op/v0/device/list', api_key,
                        body={'currentPage': pagina, 'pageSize': ITENS_POR_PAGINA})
        pagina_dados = dados.get('result') or {}
        registros = pagina_dados.get('data') or []
        resultado.extend(registros)
        total = int(pagina_dados.get('total') or 0)
        if not registros or len(resultado) >= total:
            break
        pagina += 1
    return resultado


def detalhe_dispositivo(device_sn: str, api_key: str) -> dict:
    """
    Retorna detalhes estáticos de um dispositivo (capacidade, versões, bateria).
    Endpoint: GET /op/v1/device/detail?sn=<deviceSN>
    """
    dados = _chamar('GET', '/op/v1/device/detail', api_key, params={'sn': device_sn})
    return dados.get('result') or {}


def consultar_tempo_real(sns: list[str], api_key: str) -> dict[str, dict]:
    """
    Consulta dados em tempo real de múltiplos devices em uma chamada.
    Endpoint: POST /op/v1/device/real/query

    Retorna um dict indexado por deviceSN, com estrutura:
        {
            "60Q1252054MR054": {
                "generationPower": 1.708,
                "todayYield": 1.8,
                "RVolt": 219.3,
                ...
                "currentFault": "",
                "currentFaultCount": 0,
            },
            ...
        }
    """
    if not sns:
        return {}
    # Limite empírico: evitar payloads grandes demais — 50 SNs por chamada é seguro.
    resultado: dict[str, dict] = {}
    for i in range(0, len(sns), 50):
        lote = sns[i:i + 50]
        dados = _chamar('POST', '/op/v1/device/real/query', api_key, body={'sns': lote})
        for item in dados.get('result') or []:
            sn = item.get('deviceSN')
            if not sn:
                continue
            variaveis = {v.get('variable'): v.get('value') for v in (item.get('datas') or [])}
            resultado[sn] = variaveis
    return resultado


def consultar_geracao(device_sn: str, api_key: str) -> dict:
    """
    Retorna energia acumulada do device: hoje, mês, total.
    Endpoint: GET /op/v0/device/generation?sn=<deviceSN>

    Resposta: {"today": 1.8, "month": 53.0, "cumulative": 1370.6}

    Observação: `cumulative` tem bug conhecido — às vezes é menor que `today`
    em contas novas. O adaptador prefere `PVEnergyTotal` do real/query quando
    disponível e usa `cumulative` apenas como fallback.
    """
    dados = _chamar('GET', '/op/v0/device/generation', api_key, params={'sn': device_sn})
    return dados.get('result') or {}
