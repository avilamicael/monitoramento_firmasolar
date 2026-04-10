"""
Autenticacao Solarman Business (globalpro.solarmanpv.com).

Fluxo:
    O login web exige Cloudflare Turnstile, impossibilitando login automatico.
    O token JWT tem validade de ~60 dias, entao o login manual e raro.

    1. Usuario faz login no browser e copia o JWT (cookie tokenKey)
    2. JWT e salvo no CacheTokenProvedor via admin
    3. Quando expira, sistema marca precisa_atencao para renovacao manual

Credenciais necessarias: {"email": "...", "password": "..."}
Cache de token: {"token": "eyJ..."}
"""
import json
import logging
import time
from base64 import b64decode

from provedores.excecoes import ProvedorErroAuth

logger = logging.getLogger(__name__)

BASE_URL = 'https://globalpro.solarmanpv.com'

_HEADERS_BASE = {
    'Content-Type': 'application/json',
    'Accept': 'application/json, text/plain, */*',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0',
    'Referer': f'{BASE_URL}/',
}


def decodificar_jwt_payload(token: str) -> dict:
    """Decodifica o payload de um JWT sem validar assinatura."""
    try:
        payload_b64 = token.split('.')[1]
        # Adiciona padding se necessario
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += '=' * padding
        return json.loads(b64decode(payload_b64))
    except Exception:
        return {}


def token_expirado(token: str, margem_horas: int = 24) -> bool:
    """Verifica se o token JWT esta proximo de expirar."""
    payload = decodificar_jwt_payload(token)
    exp = payload.get('exp', 0)
    if not exp:
        return True
    agora = int(time.time())
    return agora >= (exp - margem_horas * 3600)


def validar_token(token: str) -> str:
    """Valida que o token e um JWT valido e nao expirado."""
    if not token or not token.startswith('eyJ'):
        raise ProvedorErroAuth('Solarman: token JWT invalido ou ausente')

    if token_expirado(token, margem_horas=0):
        raise ProvedorErroAuth('Solarman: token JWT expirado — renovacao manual necessaria')

    payload = decodificar_jwt_payload(token)
    logger.debug(
        'Solarman: token valido (user=%s, exp=%s)',
        payload.get('user_name', '?'),
        payload.get('exp', '?'),
    )
    return token
