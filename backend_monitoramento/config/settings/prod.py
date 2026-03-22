"""
Configurações de produção.
Variáveis de ambiente injetadas pelo Docker / sistema operacional.
"""
from .base import *  # noqa: F401, F403

DEBUG = False

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            'format': '{"level": "%(levelname)s", "logger": "%(name)s", "msg": "%(message)s"}',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'coleta': {'level': 'INFO'},
        'alertas': {'level': 'INFO'},
        'notificacoes': {'level': 'INFO'},
    },
}
