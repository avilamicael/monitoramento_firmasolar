"""
Consultas à API Huawei FusionSolar (thirdData).

Todas as funções recebem a sessão já com XSRF-TOKEN no header.
Re-login automático em caso de sessão expirada.
"""
import logging
import time

import requests

from provedores.excecoes import ProvedorErro, ProvedorErroAuth, ProvedorErroRateLimit
from .autenticacao import fazer_login

logger = logging.getLogger(__name__)

BASE_URL = 'https://intl.fusionsolar.huawei.com/thirdData'


def _post(path: str, body: dict, sessao: requests.Session, usuario: str, system_code: str) -> dict:
    """
    Executa uma requisição POST autenticada.
    Faz re-login automático se a sessão expirar.
    """
    try:
        resp = sessao.post(f'{BASE_URL}/{path.lstrip("/")}', json=body, timeout=20)
    except requests.RequestException as exc:
        raise ProvedorErro(f'FusionSolar: erro de rede em {path}: {exc}') from exc

    if resp.status_code == 429:
        raise ProvedorErroRateLimit('FusionSolar: rate limit HTTP (429)')

    if resp.status_code == 401:
        logger.info('FusionSolar: sessão expirada (401), reconectando...')
        fazer_login(usuario, system_code, sessao)
        try:
            resp = sessao.post(f'{BASE_URL}/{path.lstrip("/")}', json=body, timeout=20)
        except requests.RequestException as exc:
            raise ProvedorErro(f'FusionSolar: erro após re-login em {path}: {exc}') from exc
        if resp.status_code == 401:
            raise ProvedorErroAuth('FusionSolar: credenciais inválidas — re-login falhou')

    try:
        dados = resp.json()
    except Exception as exc:
        raise ProvedorErro(f'FusionSolar: resposta inválida em {path}: {resp.text[:200]}') from exc

    if not dados.get('success'):
        fail_code = str(dados.get('failCode', ''))
        msg = dados.get('message') or dados.get('data') or fail_code or str(dados)

        # failCode 407 = ACCESS_FREQUENCY_IS_TOO_HIGH (rate limit da API FusionSolar)
        if fail_code == '407' or 'frequency' in str(msg).lower():
            raise ProvedorErroRateLimit(f'FusionSolar: rate limit (407) em {path}')

        # Sessão expirada: failCode 305 ou mensagem contendo "login"
        sessao_expirada = fail_code in ('305',) or 'login' in str(msg).lower()
        if sessao_expirada:
            logger.info('FusionSolar: sessão expirada (failCode=%s), reconectando...', fail_code)
            fazer_login(usuario, system_code, sessao)
            time.sleep(2)
            try:
                resp = sessao.post(f'{BASE_URL}/{path.lstrip("/")}', json=body, timeout=20)
                dados = resp.json()
            except Exception as exc:
                raise ProvedorErro(f'FusionSolar: erro após re-login em {path}: {exc}') from exc
            if not dados.get('success'):
                retry_msg = dados.get('message') or dados.get('data') or str(dados)
                raise ProvedorErroAuth(f'FusionSolar: falha após re-login — {retry_msg}')
            return dados

        raise ProvedorErro(f'FusionSolar: erro da API em {path} — {msg}')

    return dados


def listar_usinas(sessao: requests.Session, usuario: str, system_code: str) -> list[dict]:
    """
    Retorna todas as usinas com seus KPIs em tempo real.

    Fluxo:
        1. POST /getStationList → lista de usinas
        2. POST /getStationRealKpi (batch) → KPIs por código de usina
        3. Combina os dados
    """
    dados = _post('/getStationList', {}, sessao, usuario, system_code)
    usinas = dados.get('data') or []

    if not usinas:
        return []

    codigos = ','.join(u.get('stationCode', '') for u in usinas if u.get('stationCode'))
    try:
        kpi_dados = _post('/getStationRealKpi', {'stationCodes': codigos}, sessao, usuario, system_code)
        kpi_por_codigo = {
            item['stationCode']: item.get('dataItemMap', {})
            for item in (kpi_dados.get('data') or [])
            if item.get('stationCode')
        }
    except ProvedorErro:
        kpi_por_codigo = {}

    return [{**u, '_kpi': kpi_por_codigo.get(u.get('stationCode', ''), {})} for u in usinas]


def listar_inversores(id_usina: str, sessao: requests.Session, usuario: str, system_code: str) -> list[dict]:
    """
    Retorna os inversores de uma usina com seus KPIs em tempo real.
    Pode retornar lista vazia se a conta não tiver permissão (erro 407).
    """
    try:
        dados = _post('/getDevList', {'stationCodes': id_usina}, sessao, usuario, system_code)
    except ProvedorErroRateLimit:
        logger.warning('FusionSolar: sem permissão para inversores (407) em %s', id_usina)
        return []

    dispositivos = dados.get('data') or []
    inversores = [d for d in dispositivos if d.get('devTypeId') == 1]

    if not inversores:
        return []

    ids_inversores = [str(d.get('id')) for d in inversores if d.get('id')]
    kpi_por_id = {}
    if ids_inversores:
        try:
            kpi_resp = _post('/getDevRealKpi',
                             {'devIds': ','.join(ids_inversores), 'devTypeId': 1},
                             sessao, usuario, system_code)
            kpi_por_id = {
                str(item.get('devId')): item.get('dataItemMap', {})
                for item in (kpi_resp.get('data') or [])
                if item.get('devId')
            }
        except ProvedorErro:
            pass

    return [{**d, '_kpi': kpi_por_id.get(str(d.get('id', '')), {})} for d in inversores]


def listar_alertas(sessao: requests.Session, usuario: str, system_code: str) -> list[dict]:
    """
    Retorna alertas ativos de todas as usinas da conta.
    """
    try:
        dados = _post('/getAlarmList', {'language': 'pt_BR'}, sessao, usuario, system_code)
        return dados.get('data') or []
    except ProvedorErro:
        return []
