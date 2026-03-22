"""
Configurações de produção.
Variáveis de ambiente injetadas pelo Docker / sistema operacional.
"""
import json
import logging

from .base import *  # noqa: F401, F403

DEBUG = False


class FormataJSON(logging.Formatter):
    """
    Formatter que produz uma linha de JSON válido por evento de log.
    Trata corretamente mensagens com aspas, newlines e exc_info.
    """
    def format(self, record: logging.LogRecord) -> str:
        entrada: dict = {
            'ts': self.formatTime(record, '%Y-%m-%dT%H:%M:%S'),
            'level': record.levelname,
            'logger': record.name,
            'msg': record.getMessage(),
        }
        if record.exc_info:
            entrada['exc'] = self.formatException(record.exc_info)
        return json.dumps(entrada, ensure_ascii=False)


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'config.settings.prod.FormataJSON',
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
        'provedores': {'level': 'INFO', 'propagate': True},
        'coleta': {'level': 'INFO', 'propagate': True},
        'alertas': {'level': 'INFO', 'propagate': True},
        'notificacoes': {'level': 'INFO', 'propagate': True},
    },
}
