"""
Autenticação Huawei FusionSolar (thirdData API).

Fluxo de login:
    1. POST /thirdData/login  → recebe cookie XSRF-TOKEN
    2. Injetar XSRF-TOKEN como header em todas as requisições seguintes

A sessão expira após algumas horas. O sistema detecta a expiração por:
    - HTTP 401
    - failCode=305 na resposta JSON
    - Mensagem contendo "login"

O re-login é feito automaticamente em consultas.py.

Credenciais necessárias: {"username": "...", "system_code": "..."}
"""
import logging

import requests

from provedores.excecoes import ProvedorErroAuth, ProvedorErro

logger = logging.getLogger(__name__)

BASE_URL = 'https://intl.fusionsolar.huawei.com/thirdData'


def fazer_login(usuario: str, system_code: str, sessao: requests.Session) -> str:
    """
    Executa o login FusionSolar e retorna o XSRF-TOKEN.
    Também injeta o token no header da sessão para requisições futuras.

    Raises:
        ProvedorErroAuth — se credenciais inválidas
        ProvedorErro — se erro de rede ou resposta inesperada
    """
    try:
        resp = sessao.post(
            f'{BASE_URL}/login',
            json={'userName': usuario, 'systemCode': system_code},
            timeout=20,
        )
    except requests.RequestException as exc:
        raise ProvedorErro(f'FusionSolar: erro de rede no login: {exc}') from exc

    try:
        dados = resp.json()
    except Exception as exc:
        raise ProvedorErro(f'FusionSolar: resposta inválida no login: {resp.text[:200]}') from exc

    if not dados.get('success'):
        msg = dados.get('message') or str(dados)
        raise ProvedorErroAuth(f'FusionSolar: login falhou — {msg}')

    token = resp.cookies.get('XSRF-TOKEN') or resp.headers.get('XSRF-TOKEN')
    if token:
        sessao.headers.update({'XSRF-TOKEN': token})

    logger.info('FusionSolar: login bem-sucedido')
    return token or ''
