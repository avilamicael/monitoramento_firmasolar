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

# devTypeIds confirmados como suportados por /getDevRealKpi
# Tipos não listados aqui retornam erro 20013 ("device type not supported")
# e são incluídos na lista com _kpi={} sem tentativa de busca.
# Referência: FusionSolar thirdData API — getDevRealKpi
TIPOS_COM_KPI: frozenset[int] = frozenset({
    1,   # String Inverter (trifásico, instalações comerciais/utility)
    38,  # SUN2000 residencial / SmartLogger com inversor integrado
})


def _post(path: str, body: dict, sessao: requests.Session, usuario: str, system_code: str) -> dict:
    """
    Executa uma requisição POST autenticada.
    Faz re-login automático se a sessão expirar.
    """
    inicio = time.time()
    try:
        resp = sessao.post(f'{BASE_URL}/{path.lstrip("/")}', json=body, timeout=20)
    except requests.RequestException as exc:
        logger.warning('FusionSolar: erro de rede em %s — %s', path, exc)
        raise ProvedorErro(f'FusionSolar: erro de rede em {path}: {exc}') from exc

    if resp.status_code == 429:
        logger.warning('FusionSolar: rate limit HTTP (429) em %s', path)
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
                retry_fail_code = str(dados.get('failCode', ''))
                retry_msg = dados.get('message') or dados.get('data') or retry_fail_code or str(dados)
                # Rate limit após re-login — não é erro de autenticação
                if retry_fail_code == '407' or 'frequency' in str(retry_msg).lower():
                    raise ProvedorErroRateLimit(f'FusionSolar: rate limit após re-login em {path}')
                raise ProvedorErroAuth(f'FusionSolar: falha após re-login — {retry_msg}')
            return dados

        raise ProvedorErro(f'FusionSolar: erro da API em {path} — {msg}')

    duracao_ms = int((time.time() - inicio) * 1000)
    logger.debug('FusionSolar: POST %s → HTTP %d em %dms', path, resp.status_code, duracao_ms)
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


def listar_todos_inversores(
    codigos_usinas: list[str],
    sessao: requests.Session,
    usuario: str,
    system_code: str,
) -> dict[str, list[dict]]:
    """
    Busca inversores de todas as usinas em lote, minimizando chamadas à API.

    Fluxo:
        1. POST /getDevList com todos os station codes de uma vez
        2. POST /getDevRealKpi por devTypeId (1 chamada por tipo encontrado)
        3. Retorna dict {stationCode: [dispositivos com _kpi]}

    Tipos de inversor reconhecidos na API FusionSolar thirdData:
      devTypeId=1  — String Inverter (trifásico, instalações comerciais/utility)
      devTypeId=38 — SUN2000 residencial / SmartLogger com inversor integrado
    """
    resultado: dict[str, list[dict]] = {c: [] for c in codigos_usinas}

    logger.info('FusionSolar: listar_todos_inversores chamado com %d códigos', len(codigos_usinas))

    if not codigos_usinas:
        return resultado

    # 1. Busca todos os dispositivos em lote (uma única chamada)
    batch_code = ','.join(codigos_usinas)
    logger.info('FusionSolar: chamando /getDevList com %d stations...', len(codigos_usinas))
    try:
        dados = _post('/getDevList', {'stationCodes': batch_code}, sessao, usuario, system_code)
    except ProvedorErroRateLimit:
        logger.warning('FusionSolar: rate limit em /getDevList — inversores não coletados neste ciclo')
        return resultado
    except ProvedorErro as exc:
        logger.warning('FusionSolar: erro em /getDevList — %s', exc)
        return resultado

    # A API thirdData pode retornar dispositivos de tipos variados (inversores, dataloggers, etc.)
    # Apenas os tipos em TIPOS_COM_KPI suportam /getDevRealKpi — os demais ficam com _kpi vazio.
    inversores = dados.get('data') or []

    # Loga os tipos encontrados para auditoria (ajuda identificar novos modelos)
    tipos_encontrados: dict[int, int] = {}
    for d in inversores:
        t = d.get('devTypeId')
        tipos_encontrados[t] = tipos_encontrados.get(t, 0) + 1
    if tipos_encontrados:
        logger.info('FusionSolar: devTypeIds encontrados em /getDevList — %s', tipos_encontrados)

    if not inversores:
        return resultado

    # 2. Busca KPIs em lote, agrupado por devTypeId (tipos diferentes precisam de chamadas separadas)
    por_tipo: dict[int, list[dict]] = {}
    for d in inversores:
        por_tipo.setdefault(d.get('devTypeId'), []).append(d)

    kpi_por_id: dict[str, dict] = {}
    for dev_type, devs in por_tipo.items():
        if dev_type not in TIPOS_COM_KPI:
            # Tipo não suportado pelo /getDevRealKpi — dispositivo incluído com _kpi vazio
            logger.debug('FusionSolar: devTypeId=%s não suportado por /getDevRealKpi — ignorando KPI', dev_type)
            continue
        ids = [str(d.get('id')) for d in devs if d.get('id')]
        if not ids:
            continue
        try:
            kpi_resp = _post(
                '/getDevRealKpi',
                {'devIds': ','.join(ids), 'devTypeId': dev_type},
                sessao, usuario, system_code,
            )
            for item in (kpi_resp.get('data') or []):
                if item.get('devId'):
                    kpi_por_id[str(item['devId'])] = item.get('dataItemMap', {})
        except ProvedorErro as exc:
            logger.warning('FusionSolar: erro ao buscar KPI de inversores (devTypeId=%s) — %s', dev_type, exc)

    # 3. Distribui os inversores com KPI de volta por stationCode
    for d in inversores:
        codigo = d.get('stationCode', '')
        if codigo in resultado:
            resultado[codigo].append({**d, '_kpi': kpi_por_id.get(str(d.get('id', '')), {})})

    total = sum(len(v) for v in resultado.values())
    usinas_com_inv = sum(1 for v in resultado.values() if v)
    logger.info('FusionSolar: %d inversores em %d/%d usinas', total, usinas_com_inv, len(codigos_usinas))
    return resultado


def listar_alertas(sessao: requests.Session, usuario: str, system_code: str) -> list[dict]:
    """
    Retorna alertas ativos de todas as usinas da conta.
    """
    try:
        dados = _post('/getAlarmList', {'language': 'pt_BR'}, sessao, usuario, system_code)
        return dados.get('data') or []
    except ProvedorErro:
        return []
