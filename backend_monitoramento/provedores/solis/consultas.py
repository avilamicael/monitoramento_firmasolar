"""
Consultas à API Solis Cloud.

Cada função faz uma chamada específica e retorna os dados brutos (dict).
A normalização para os dataclasses do sistema é feita no adaptador.

Documentação Solis: https://www.soliscloud.com/doc/en/solis-cloud-api/
"""
import logging
import time

import requests

from provedores.excecoes import ProvedorErro, ProvedorErroAuth, ProvedorErroRateLimit
from .autenticacao import assinar_requisicao

logger = logging.getLogger(__name__)

BASE_URL = 'https://www.soliscloud.com:13333'
ITENS_POR_PAGINA = 100


def _post(path: str, body: dict, api_key: str, app_secret: str) -> dict:
    """Executa uma requisição POST autenticada à API Solis."""
    headers, body_str = assinar_requisicao(body, path, api_key, app_secret)

    inicio = time.time()
    try:
        resp = requests.post(BASE_URL + path, data=body_str, headers=headers, timeout=20)
    except requests.RequestException as exc:
        logger.warning('Solis: erro de rede em %s — %s', path, exc)
        raise ProvedorErro(f'Solis: erro de rede em {path}: {exc}') from exc

    duracao_ms = int((time.time() - inicio) * 1000)

    if resp.status_code == 429:
        logger.warning('Solis: rate limit (429) em %s', path)
        raise ProvedorErroRateLimit('Solis: rate limit atingido (429)')
    if resp.status_code == 401:
        logger.error('Solis: credenciais inválidas (401) em %s', path)
        raise ProvedorErroAuth('Solis: credenciais inválidas (401)')

    try:
        dados = resp.json()
    except Exception as exc:
        logger.error('Solis: resposta inválida em %s — %s', path, resp.text[:200])
        raise ProvedorErro(f'Solis: resposta inválida em {path}: {resp.text[:200]}') from exc

    if not dados.get('success') and dados.get('code') not in ('0', 0):
        msg = dados.get('msg') or dados.get('message') or str(dados)
        if 'auth' in msg.lower() or 'sign' in msg.lower():
            logger.error('Solis: erro de autenticação em %s — %s', path, msg)
            raise ProvedorErroAuth(f'Solis: erro de autenticação — {msg}')
        logger.warning('Solis: erro da API em %s — %s', path, msg)
        raise ProvedorErro(f'Solis: erro da API em {path} — {msg}')

    logger.debug('Solis: POST %s → HTTP %d em %dms', path, resp.status_code, duracao_ms)
    return dados


def listar_usinas(api_key: str, app_secret: str) -> list[dict]:
    """
    Retorna todas as usinas da conta.
    Endpoint: POST /v1/api/userStationList (paginado)
    """
    resultado = []
    pagina = 1

    while True:
        dados = _post('/v1/api/userStationList', {'pageNo': pagina, 'pageSize': ITENS_POR_PAGINA}, api_key, app_secret)
        pagina_dados = dados.get('data', {}).get('page', {})
        registros = pagina_dados.get('records') or []
        resultado.extend(registros)

        total = int(pagina_dados.get('total') or 0)
        if not registros or len(resultado) >= total:
            break
        pagina += 1

    return resultado


def listar_inversores(id_usina: str, api_key: str, app_secret: str) -> list[dict]:
    """
    Retorna os inversores de uma usina.
    Endpoint: POST /v1/api/inverterList (paginado)
    """
    resultado = []
    pagina = 1

    while True:
        dados = _post('/v1/api/inverterList', {
            'stationId': id_usina,
            'pageNo': pagina,
            'pageSize': ITENS_POR_PAGINA,
        }, api_key, app_secret)

        inner = dados.get('data') or dados
        pagina_dados = inner.get('page', {})
        registros = pagina_dados.get('records') or []
        resultado.extend(registros)

        total = int(pagina_dados.get('total') or 0)
        if not registros or len(resultado) >= total:
            break
        pagina += 1

    return resultado


def listar_alertas(api_key: str, app_secret: str, id_usina: str | None = None) -> list[dict]:
    """
    Retorna alertas ativos da conta (ou de uma usina específica).
    Endpoint: POST /v1/api/alarmList
    """
    body = {'pageNo': 1, 'pageSize': 100}
    if id_usina:
        body['stationId'] = id_usina

    dados = _post('/v1/api/alarmList', body, api_key, app_secret)
    return (dados.get('data') or {}).get('records') or []
