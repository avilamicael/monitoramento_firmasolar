"""
Consultas a API Solarman Business (globalpro.solarmanpv.com).

Cada funcao faz uma chamada especifica e retorna os dados brutos.
A normalizacao para os dataclasses do sistema e feita no adaptador.

Base URL: https://globalpro.solarmanpv.com
Auth: Bearer JWT token no header Authorization
"""
import logging
import time

import requests

from provedores.excecoes import ProvedorErro, ProvedorErroAuth, ProvedorErroRateLimit
from .autenticacao import BASE_URL

logger = logging.getLogger(__name__)

ITENS_POR_PAGINA = 100


def _request(method: str, path: str, sessao: requests.Session, token: str,
             json_body: dict | None = None, params: dict | None = None) -> dict | list:
    """Executa uma requisicao autenticada a API Solarman."""
    headers = {'Authorization': f'Bearer {token}'}

    inicio = time.time()
    try:
        resp = sessao.request(
            method,
            f'{BASE_URL}{path}',
            json=json_body,
            params=params,
            headers=headers,
            timeout=30,
        )
    except requests.RequestException as exc:
        logger.warning('Solarman: erro de rede em %s — %s', path, exc)
        raise ProvedorErro(f'Solarman: erro de rede em {path}: {exc}') from exc

    duracao_ms = int((time.time() - inicio) * 1000)

    if resp.status_code == 429:
        raise ProvedorErroRateLimit('Solarman: rate limit atingido (429)')
    if resp.status_code == 401:
        raise ProvedorErroAuth('Solarman: token invalido ou expirado (401)')
    if resp.status_code == 403:
        raise ProvedorErroAuth('Solarman: acesso negado (403)')

    try:
        dados = resp.json()
    except Exception as exc:
        raise ProvedorErro(f'Solarman: resposta invalida de {path}: {resp.text[:200]}') from exc

    # Solarman retorna erros com campo "code"
    if isinstance(dados, dict) and dados.get('code'):
        msg = dados.get('msg') or dados.get('code') or str(dados)
        if 'token' in str(msg).lower() or 'auth' in str(msg).lower():
            raise ProvedorErroAuth(f'Solarman: erro de autenticacao — {msg}')
        raise ProvedorErro(f'Solarman: erro da API em {path} — {msg}')

    logger.debug('Solarman: %s %s → HTTP %d em %dms', method, path, resp.status_code, duracao_ms)
    return dados


def _get(path: str, sessao: requests.Session, token: str, params: dict | None = None):
    return _request('GET', path, sessao, token, params=params)


def _post(path: str, sessao: requests.Session, token: str, body: dict | None = None):
    return _request('POST', path, sessao, token, json_body=body or {})


def listar_usinas(sessao: requests.Session, token: str) -> list[dict]:
    """
    Retorna todas as usinas da conta.
    Endpoint: POST /maintain-s/operating/station/v2/search (paginado)

    Campos retornados por usina (dentro de station):
        id, name, locationAddress, installedCapacity (kWp),
        networkStatus ("NORMAL"/"OFFLINE"), generationPower (W),
        generationValue (kWh dia), generationMonth (kWh), generationYear (kWh),
        generationTotal (kWh), lastUpdateTime (unix), regionTimezone
    """
    resultado = []
    pagina = 1

    while True:
        dados = _post(
            f'/maintain-s/operating/station/v2/search?page={pagina}&size={ITENS_POR_PAGINA}'
            f'&order.direction=ASC&order.property=name',
            sessao, token,
            {'station': {'powerTypeList': ['PV']}},
        )
        registros = dados.get('data') or []
        resultado.extend(registros)

        total = int(dados.get('total') or 0)
        if not registros or len(resultado) >= total:
            break
        pagina += 1

    return resultado


def listar_inversores(station_id: str, sessao: requests.Session, token: str) -> list[dict]:
    """
    Retorna os inversores/microinversores de uma usina.
    Endpoint: GET /maintain-s/operating/station/{id}/microInverter (paginado)

    Campos retornados por inversor:
        id, deviceSn, type ("MICRO_INVERTER"), netState (1=online),
        deviceState, serialNumber, collectionTime (unix), productId,
        systemName, parentDeviceSn (logger SN)
    """
    resultado = []
    pagina = 1

    while True:
        dados = _get(
            f'/maintain-s/operating/station/{station_id}/microInverter'
            f'?page={pagina}&size={ITENS_POR_PAGINA}'
            f'&order.direction=ASC&order.property=device_sn',
            sessao, token,
        )
        registros = dados.get('data') or []
        resultado.extend(registros)

        total = int(dados.get('total') or 0)
        if not registros or len(resultado) >= total:
            break
        pagina += 1

    return resultado


def buscar_dados_inversor(device_id: str, sessao: requests.Session, token: str) -> dict:
    """
    Retorna dados eletricos do dia de um inversor (ultimo ponto = valor atual).
    Endpoint: GET /device-s/device/{id}/stats/day

    Retorna lista de parametros, cada um com detailList (serie temporal).
    Extraimos o ultimo valor de cada parametro relevante.

    Parametros conhecidos (storageName):
        DV1-DV4: DC Voltage PV1-4 (V)
        DC1-DC4: DC Current PV1-4 (A)
        DP1-DP4: DC Power PV1-4 (W)
        AV1: AC Voltage (V)
        AC1: AC Current (A)
        AF1: AC Frequency (Hz)
        APo_t1: Total AC Output Power Active (W)
        Et_ge0: Total Production Active (kWh)
        Etdy_ge0: Daily Production Active (kWh)
        AC_RDT_T1: AC Radiator Temp (C)
    """
    from datetime import date
    hoje = date.today().strftime('%Y/%m/%d')

    dados = _get(
        f'/device-s/device/{device_id}/stats/day',
        sessao, token,
        {'day': hoje, 'lan': 'en'},
    )

    if not isinstance(dados, list):
        return {}

    resultado = {}
    for param in dados:
        nome = param.get('storageName', '')
        detail_list = param.get('detailList') or []
        if not detail_list:
            continue
        # Ultimo valor da serie temporal
        ultimo = detail_list[-1].get('value')
        if ultimo is not None:
            try:
                resultado[nome] = float(ultimo)
            except (TypeError, ValueError):
                resultado[nome] = ultimo

    return resultado


def listar_alertas(station_ids: list[int], sessao: requests.Session, token: str) -> list[dict]:
    """
    Retorna alertas mais recentes das usinas.
    Endpoint: POST /maintain-s/operating/station/alert/lastest/list

    Envia em lotes de 50 station IDs por chamada.
    """
    resultado = []
    for i in range(0, len(station_ids), 50):
        lote = station_ids[i:i + 50]
        dados = _post(
            '/maintain-s/operating/station/alert/lastest/list',
            sessao, token,
            {'stationIds': lote, 'lan': 'en'},
        )
        if isinstance(dados, list):
            resultado.extend(dados)

    return resultado


def buscar_contagem_status(sessao: requests.Session, token: str) -> dict:
    """
    Retorna contadores de status das usinas (online, offline, alertas).
    Endpoint: POST /maintain-s/operating/station/v2/status/counting
    """
    return _post(
        '/maintain-s/operating/station/v2/status/counting',
        sessao, token,
        {'station': {'powerTypeList': ['PV']}},
    )
