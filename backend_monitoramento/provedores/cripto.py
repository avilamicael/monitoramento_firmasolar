"""
Criptografia de credenciais dos provedores.

Usa Fernet (criptografia simétrica) para armazenar as credenciais
no banco de dados de forma segura. A chave fica no .env.
"""
import json
from cryptography.fernet import Fernet
from django.conf import settings


def _fernet() -> Fernet:
    chave = getattr(settings, 'CHAVE_CRIPTOGRAFIA', '')
    if not chave:
        raise ValueError(
            'CHAVE_CRIPTOGRAFIA não definida no .env. '
            'Gere uma com: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )
    return Fernet(chave.encode())


def criptografar_credenciais(dados: dict) -> str:
    """Serializa e criptografa um dicionário de credenciais."""
    return _fernet().encrypt(json.dumps(dados).encode()).decode()


def descriptografar_credenciais(dados_enc: str) -> dict:
    """Descriptografa e desserializa as credenciais armazenadas no banco."""
    return json.loads(_fernet().decrypt(dados_enc.encode()).decode())
