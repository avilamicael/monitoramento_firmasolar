"""
Consultas a API AuxSol Cloud.

Cada funcao faz uma chamada especifica e retorna os dados brutos (dict/list).
A normalizacao para os dataclasses do sistema e feita no adaptador.

Base URL: https://eu.auxsolcloud.com
Auth: Bearer token no header Authorization
"""
import logging
import time

import requests

from provedores.excecoes import ProvedorErro, ProvedorErroAuth, ProvedorErroRateLimit
from .autenticacao import BASE_URL

logger = logging.getLogger(__name__)

ITENS_POR_PAGINA = 100


def _get(path: str, sessao: requests.Session, token: str, params: dict | None = None) -> dict:
    """Executa uma requisicao GET autenticada a API AuxSol."""
    headers = {'Authorization': f'Bearer {token}'}

    inicio = time.time()
    try:
        resp = sessao.get(
            f'{BASE_URL}{path}',
            params=params,
            headers=headers,
            timeout=20,
        )
    except requests.RequestException as exc:
        logger.warning('AuxSol: erro de rede em %s — %s', path, exc)
        raise ProvedorErro(f'AuxSol: erro de rede em {path}: {exc}') from exc

    duracao_ms = int((time.time() - inicio) * 1000)

    if resp.status_code == 429:
        logger.warning('AuxSol: rate limit (429) em %s', path)
        raise ProvedorErroRateLimit('AuxSol: rate limit atingido (429)')
    if resp.status_code == 401:
        logger.error('AuxSol: token invalido (401) em %s', path)
        raise ProvedorErroAuth('AuxSol: token invalido (401)')

    try:
        dados = resp.json()
    except Exception as exc:
        logger.error('AuxSol: resposta invalida de %s — %s', path, resp.text[:200])
        raise ProvedorErro(f'AuxSol: resposta invalida de {path}: {resp.text[:200]}') from exc

    code = dados.get('code', '')
    if code != 'AWX-0000':
        msg = dados.get('msg') or str(dados)
        if 'auth' in msg.lower() or 'token' in msg.lower() or '401' in str(code) or '登录' in msg or '过期' in msg or 'login' in msg.lower() or 'expir' in msg.lower():
            raise ProvedorErroAuth(f'AuxSol: erro de autenticacao — {msg}')
        raise ProvedorErro(f'AuxSol: erro da API em {path} — {msg}')

    logger.debug('AuxSol: GET %s → HTTP %d em %dms', path, resp.status_code, duracao_ms)
    return dados


def listar_usinas(sessao: requests.Session, token: str) -> list[dict]:
    """
    Retorna todas as usinas da conta.
    Endpoint: GET /auxsol-api/archive/plant/list (paginado)

    Campos retornados por usina:
        plantId, plantName, capacity (kWp), currentPower (kW),
        todayYield (kWh), monthlyYield (kWh), totalYield (kWh),
        status ("01"=normal), address, timeZone, dt (last update)
    """
    resultado = []
    pagina = 1

    while True:
        dados = _get('/auxsol-api/archive/plant/list', sessao, token, {
            'status': '',
            'plantType': '',
            'pageSize': ITENS_POR_PAGINA,
            'pageNum': pagina,
        })
        inner = dados.get('data', {})
        registros = inner.get('rows') or []
        resultado.extend(registros)

        total = int(inner.get('total') or 0)
        if not registros or len(resultado) >= total:
            break
        pagina += 1

    return resultado


def listar_inversores(plant_id: str, sessao: requests.Session, token: str) -> list[dict]:
    """
    Retorna os inversores de uma usina.
    Endpoint: GET /auxsol-api/archive/inverter/getInverterByPlant/{plantId}

    Campos retornados por inversor:
        inverterId, sn, model, status ("01"=normal), ratePower (kW),
        currentPower (kW), dayEnergy (kWh), totalEnergy (kWh),
        monthEnergy (kWh), lastDt, plantId, plantName
    """
    dados = _get(f'/auxsol-api/archive/inverter/getInverterByPlant/{plant_id}', sessao, token)
    return dados.get('data') or []


def buscar_inversor_realtime(sn: str, sessao: requests.Session, token: str) -> dict:
    """
    Retorna dados em tempo real de um inversor (MPPT, grid, temperaturas).
    Endpoint: GET /auxsol-api/analysis/inverterReport/findInverterRealTimeInfoBySnV1

    Campos retornados:
        energyData.pvList[]: {index, u (V), i (A), p (W)} — strings MPPT
        gridData.acList[]: {phase, u (V), i (A), f (Hz)} — dados da rede
        otherData: {temperature1, insideTemperature} — temperaturas
        energyData: {power (kW), y (kWh dia), ym (kWh mes), yt (kWh total)}
        batteryData: dados de bateria (quando disponivel)
    """
    dados = _get(
        '/auxsol-api/analysis/inverterReport/findInverterRealTimeInfoBySnV1',
        sessao, token, {'sn': sn},
    )
    return dados.get('data') or {}


def listar_alertas(sessao: requests.Session, token: str, plant_id: str | None = None) -> list[dict]:
    """
    Retorna alertas ativos (nao tratados).
    Endpoint: GET /auxsol-api/analysis/alarm/list

    Parametros:
        type: "01" = geral, "02" = por planta, "03" = por inversor
        status: "01" = nao tratado
        startTime / endTime: formato YYYY-MM-DD

    Campos retornados por alarme:
        id, alarmLevel, alarmName, alarmCode, alarmTime, restoredTime,
        duration, plantName, plantId, sn, status
    """
    from datetime import date, timedelta

    hoje = date.today()
    inicio = hoje - timedelta(days=30)

    params = {
        'type': '01',
        'startTime': inicio.strftime('%Y-%m-%d'),
        'endTime': hoje.strftime('%Y-%m-%d'),
        'status': '01',
        'pageSize': ITENS_POR_PAGINA,
        'pageNum': 1,
    }
    if plant_id:
        params['plantIds'] = plant_id
        params['type'] = '02'

    dados = _get('/auxsol-api/analysis/alarm/list', sessao, token, params)
    return (dados.get('data') or {}).get('rows') or []


def buscar_status_equipamentos(sessao: requests.Session, token: str) -> dict:
    """
    Retorna contadores de equipamentos online/offline/alarme.
    Endpoint: GET /auxsol-api/archive/plant/queryEquipmentOnlineV1
    """
    dados = _get('/auxsol-api/archive/plant/queryEquipmentOnlineV1', sessao, token)
    return dados.get('data') or {}
