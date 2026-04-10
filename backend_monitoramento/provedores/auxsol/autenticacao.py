"""
Autenticacao AuxSol Cloud (eu.auxsolcloud.com).

Fluxo:
    1. POST /auxsol-api/auth/login com {account, password, lang}
    2. Retorna Bearer token (UUID) no campo data.access_token
    3. Token valido por 12 horas (43200 segundos)

Credenciais necessarias: {"account": "...", "password": "..."}
"""
import logging
import time

import requests

from provedores.excecoes import ProvedorErroAuth, ProvedorErro

logger = logging.getLogger(__name__)

BASE_URL = 'https://eu.auxsolcloud.com'

_HEADERS_BASE = {
    'Content-Type': 'application/json;charset=utf-8',
    'Accept': 'application/json, text/plain, */*',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0',
    'Referer': f'{BASE_URL}/',
}

# Token valido por 12h conforme observado (Admin-Expires-In: 43200)
TOKEN_VALIDADE_SEGUNDOS = 43200


def fazer_login(account: str, password: str, sessao: requests.Session) -> dict:
    """
    Executa login no AuxSol Cloud e retorna os dados do token.

    Returns:
        {"token": "uuid-here", "obtido_em": timestamp}

    Raises:
        ProvedorErroAuth: credenciais invalidas
        ProvedorErro: erro de rede ou resposta inesperada
    """
    try:
        resp = sessao.post(
            f'{BASE_URL}/auxsol-api/auth/login',
            json={'account': account, 'password': password, 'lang': 'en-US'},
            headers=_HEADERS_BASE,
            timeout=20,
        )
    except requests.RequestException as exc:
        raise ProvedorErro(f'AuxSol: erro de rede no login: {exc}') from exc

    if resp.status_code == 401:
        raise ProvedorErroAuth('AuxSol: credenciais invalidas (401)')

    try:
        dados = resp.json()
    except Exception as exc:
        raise ProvedorErro(f'AuxSol: resposta invalida no login: {resp.text[:200]}') from exc

    if dados.get('code') != 'AWX-0000':
        msg = dados.get('msg') or str(dados)
        raise ProvedorErroAuth(f'AuxSol: erro no login — {msg}')

    token = dados.get('data', {}).get('access_token') or dados.get('data')
    if not token or not isinstance(token, str):
        raise ProvedorErroAuth(f'AuxSol: login nao retornou token — {dados}')

    logger.info('AuxSol: login bem-sucedido (token: %s...)', token[:20])
    return {'token': token, 'obtido_em': int(time.time())}


def token_expirado(dados_token: dict) -> bool:
    """Verifica se o token esta proximo de expirar (margem de 10 minutos)."""
    obtido_em = dados_token.get('obtido_em', 0)
    idade = int(time.time()) - obtido_em
    return idade >= (TOKEN_VALIDADE_SEGUNDOS - 600)
