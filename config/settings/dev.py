"""
Configurações de desenvolvimento.
Carrega variáveis do arquivo .env na raiz do projeto.
"""
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / '.env')

from .base import *  # noqa: F401, F403

DEBUG = True

# Em dev, permite qualquer host
ALLOWED_HOSTS = ['*']

# Logs mais detalhados em desenvolvimento
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simples': {
            'format': '{levelname} {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simples',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'provedores': {'level': 'DEBUG'},
        'coleta': {'level': 'DEBUG'},
        'alertas': {'level': 'DEBUG'},
        'notificacoes': {'level': 'DEBUG'},
    },
}
