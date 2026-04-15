"""
Backend de notificação por webhook.

Para cada destinatário (URL) faz POST JSON com o payload do alerta.
Implementação stateless — não depende de .env, basta haver a URL cadastrada.
"""
import logging
from typing import List

import requests

from ..base import BackendNotificacao, DadosNotificacao

logger = logging.getLogger(__name__)

TIMEOUT_SEGUNDOS = 10


class WebhookBackend(BackendNotificacao):
    def is_disponivel(self) -> bool:
        # Webhook não exige credenciais — só precisa das URLs em destinatários.
        return True

    def enviar(self, dados: DadosNotificacao, destinatarios: List[str]) -> None:
        payload = {
            'id_alerta': dados.id_alerta,
            'nome_usina': dados.nome_usina,
            'provedor': dados.provedor,
            'mensagem': dados.mensagem,
            'nivel': dados.nivel,
            'sugestao': dados.sugestao,
            'equipamento_sn': dados.equipamento_sn,
            'inicio': dados.inicio.isoformat() if dados.inicio else None,
            'motivo': 'novo' if dados.novo else 'escalado',
        }
        for url in destinatarios:
            url = url.strip()
            if not url.lower().startswith(('http://', 'https://')):
                logger.warning('Webhook ignorado: URL inválida "%s"', url)
                continue
            try:
                resp = requests.post(url, json=payload, timeout=TIMEOUT_SEGUNDOS)
                if resp.status_code >= 400:
                    logger.warning(
                        'Webhook %s retornou HTTP %d: %s',
                        url, resp.status_code, resp.text[:200],
                    )
            except requests.RequestException as exc:
                logger.warning('Webhook %s falhou: %s', url, exc)
