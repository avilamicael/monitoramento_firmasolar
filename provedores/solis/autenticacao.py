"""
Autenticação Solis Cloud — HMAC-SHA1 stateless.

A Solis não usa sessão nem token. Cada requisição é assinada individualmente
com a chave de API e o segredo usando HMAC-SHA1.

Credenciais necessárias (no .env / banco):
    api_key    — chave de API fornecida pela Solis
    app_secret — segredo para assinar as requisições
"""
import base64
import hashlib
import hmac
import json
from datetime import datetime, timezone


def assinar_requisicao(body: dict, path: str, api_key: str, app_secret: str) -> dict:
    """
    Gera os headers de autenticação para uma requisição Solis.

    Retorna um dicionário com os headers prontos para usar em requests.post().
    """
    body_str = json.dumps(body, separators=(',', ':'))
    md5 = base64.b64encode(hashlib.md5(body_str.encode()).digest()).decode()
    content_type = 'application/json'
    data = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')

    string_para_assinar = f'POST\n{md5}\n{content_type}\n{data}\n{path}'
    assinatura = base64.b64encode(
        hmac.new(app_secret.encode(), string_para_assinar.encode(), hashlib.sha1).digest()
    ).decode()

    return {
        'Content-Type': content_type,
        'Content-MD5': md5,
        'Date': data,
        'Authorization': f'API {api_key}:{assinatura}',
    }, body_str
