"""
Autenticação Hoymiles S-Cloud.

Fluxo de login:
    1. POST /iam/pub/3/auth/pre-insp  → recebe nonce (n), salt (a), versão (v)
    2. Gera hash da senha conforme a versão (v1/v2: MD5+SHA256, v3: Argon2)
    3. POST /iam/pub/3/auth/login     → recebe token "3.xxx..."

O token é válido por um tempo indeterminado (semanas a meses).
Deve ser armazenado no cache de tokens para evitar re-login a cada coleta.

Credenciais necessárias: {"username": "...", "password": "..."}
"""
import base64
import hashlib
import json
import logging

import requests

from provedores.excecoes import ProvedorErroAuth, ProvedorErro

logger = logging.getLogger(__name__)

BASE_URL = 'https://neapi.hoymiles.com'

_HEADERS_BASE = {
    'Content-Type': 'application/json; charset=UTF-8',
    'Accept': 'application/json',
    'Origin': 'https://global.hoymiles.com',
    'Referer': 'https://global.hoymiles.com/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0',
    'language': 'pt-pt',
}


def _md5(texto: str) -> str:
    return hashlib.md5(texto.encode()).hexdigest()


def _sha256_b64(texto: str) -> str:
    return base64.b64encode(hashlib.sha256(texto.encode()).digest()).decode()


def _hash_senha_v1v2(senha: str) -> str:
    return f'{_md5(senha)}.{_sha256_b64(senha)}'


def _hash_senha_v3(senha: str, salt_hex: str) -> str:
    try:
        from argon2.low_level import hash_secret_raw, Type
    except ImportError as exc:
        raise ProvedorErro('Hoymiles v3 auth requer argon2-cffi: pip install argon2-cffi') from exc
    h = hash_secret_raw(
        secret=senha.encode(),
        salt=bytes.fromhex(salt_hex),
        time_cost=3, memory_cost=32768, parallelism=1,
        hash_len=32, type=Type.ID,
    )
    return h.hex()


def _post_sem_auth(path: str, body: dict, sessao: requests.Session) -> dict:
    try:
        resp = sessao.post(
            f'{BASE_URL}/{path.lstrip("/")}',
            data=json.dumps(body, ensure_ascii=False),
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        raise ProvedorErro(f'Hoymiles: erro de rede em {path}: {exc}') from exc


def fazer_login(usuario: str, senha: str, sessao: requests.Session) -> str:
    """
    Executa o fluxo de login Hoymiles e retorna o token de autenticação.

    Raises:
        ProvedorErroAuth — se credenciais inválidas ou token não retornado
        ProvedorErro — se erro de rede ou resposta inesperada
    """
    # Etapa 1: obter nonce, salt e versão do algoritmo
    pre = _post_sem_auth('/iam/pub/3/auth/pre-insp', {'u': usuario}, sessao)
    inner = pre.get('data') or {}
    salt = inner.get('a')
    nonce = inner.get('n')
    versao = inner.get('v', 1)

    # Etapa 2: gerar hash da senha conforme a versão
    if versao == 3:
        if not salt:
            raise ProvedorErroAuth('Hoymiles v3: salt ausente na resposta de pre-insp')
        ch = _hash_senha_v3(senha, salt)
    else:
        ch = _hash_senha_v1v2(senha)

    # Etapa 3: enviar login
    resp = _post_sem_auth('/iam/pub/3/auth/login', {'u': usuario, 'ch': ch, 'n': nonce}, sessao)
    inner_data = resp.get('data') or {}
    token = inner_data.get('token') if isinstance(inner_data, dict) else inner_data

    if not token:
        raise ProvedorErroAuth(f'Hoymiles: login não retornou token — {resp}')

    logger.info('Hoymiles: login bem-sucedido (token: %s...)', str(token)[:20])
    return token
