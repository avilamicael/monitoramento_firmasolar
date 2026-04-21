"""
Autenticação FoxESS OpenAPI — assinatura HMAC-MD5 stateless.

A FoxESS não usa sessão: cada requisição é assinada com MD5 da concatenação
do caminho, token e timestamp, separados pela string literal "\\r\\n" (4
caracteres — não CR+LF interpretado). Esse detalhe foi validado contra a
API em produção: interpretar \\r\\n como CR+LF resulta em "illegal signature".

Credenciais (no banco, criptografadas):
    api_key — gerada em https://www.foxesscloud.com/user/center → API Management
"""
import hashlib
import time


def montar_headers(path: str, api_key: str) -> dict[str, str]:
    """
    Monta os headers para uma requisição autenticada à FoxESS OpenAPI.

    A signature é MD5 hex de: path + "\\r\\n" + api_key + "\\r\\n" + timestamp_ms
    (os \\r\\n são os 4 caracteres literais, NÃO carriage return + line feed).
    """
    timestamp_ms = str(int(time.time() * 1000))
    raw = fr'{path}\r\n{api_key}\r\n{timestamp_ms}'
    signature = hashlib.md5(raw.encode('utf-8')).hexdigest()

    return {
        'token': api_key,
        'timestamp': timestamp_ms,
        'signature': signature,
        'lang': 'en',
        'Content-Type': 'application/json;charset=UTF-8',
    }
