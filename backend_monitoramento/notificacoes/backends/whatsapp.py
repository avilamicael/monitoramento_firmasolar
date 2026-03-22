import logging
import requests
from django.conf import settings
from notificacoes.base import BackendNotificacao, DadosNotificacao

logger = logging.getLogger(__name__)

_EMOJI_NIVEL = {'critico': '🔴', 'aviso': '⚠️'}


class WhatsAppBackend(BackendNotificacao):
    """
    Envia notificações via WhatsApp.
    Suporta dois provedores (configurado via WHATSAPP_PROVEDOR no .env):

    1. Meta Cloud API (padrão):
        WHATSAPP_PROVEDOR=meta
        WHATSAPP_API_TOKEN=EAAxxxxxxx
        WHATSAPP_PHONE_ID=123456789

    2. Evolution API (self-hosted):
        WHATSAPP_PROVEDOR=evolution
        WHATSAPP_EVOLUTION_URL=http://localhost:8080
        WHATSAPP_EVOLUTION_TOKEN=seu-token
        WHATSAPP_EVOLUTION_INSTANCIA=firma-solar

    Destinatários gerenciados pelo Django admin (sem restart).
    """

    def is_disponivel(self) -> bool:
        return bool(
            getattr(settings, 'WHATSAPP_API_TOKEN', '')
            or getattr(settings, 'WHATSAPP_EVOLUTION_TOKEN', '')
        )

    def enviar(self, dados: DadosNotificacao, destinatarios: list[str]) -> None:
        provedor = getattr(settings, 'WHATSAPP_PROVEDOR', 'meta')
        mensagem = self._formatar_mensagem(dados)

        for destinatario in destinatarios:
            if provedor == 'evolution':
                self._enviar_evolution(mensagem, destinatario, dados.id_alerta)
            else:
                self._enviar_meta(mensagem, destinatario, dados.id_alerta)

    def _formatar_mensagem(self, dados: DadosNotificacao) -> str:
        emoji = _EMOJI_NIVEL.get(dados.nivel, '⚠️')
        nivel_label = 'CRÍTICO' if dados.nivel == 'critico' else 'AVISO'
        prefixo = '🆕 NOVO ALERTA' if dados.novo else '📈 ALERTA ESCALADO'

        linhas = [
            f'{prefixo} {emoji}',
            f'*Usina:* {dados.nome_usina}',
            f'*Nível:* {nivel_label}',
            f'*Problema:* {dados.mensagem}',
        ]
        if dados.equipamento_sn:
            linhas.append(f'*Equipamento:* {dados.equipamento_sn}')
        if dados.sugestao:
            linhas.append(f'*Sugestão:* {dados.sugestao}')
        linhas.append(f'*Início:* {dados.inicio:%d/%m/%Y %H:%M}')
        return '\n'.join(linhas)

    def _enviar_meta(self, mensagem: str, destinatario: str, id_alerta: str) -> None:
        token = getattr(settings, 'WHATSAPP_API_TOKEN', '')
        phone_id = getattr(settings, 'WHATSAPP_PHONE_ID', '')
        numero = destinatario.replace('+', '').replace(' ', '')
        try:
            resp = requests.post(
                f'https://graph.facebook.com/v19.0/{phone_id}/messages',
                headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
                json={
                    'messaging_product': 'whatsapp',
                    'to': numero,
                    'type': 'text',
                    'text': {'body': mensagem},
                },
                timeout=10,
            )
            resp.raise_for_status()
            logger.info('WhatsApp (Meta) enviado para %s — alerta %s', destinatario, id_alerta)
        except Exception as exc:
            logger.error('Falha WhatsApp (Meta) para %s: %s', destinatario, exc)

    def _enviar_evolution(self, mensagem: str, destinatario: str, id_alerta: str) -> None:
        base_url = getattr(settings, 'WHATSAPP_EVOLUTION_URL', '')
        token = getattr(settings, 'WHATSAPP_EVOLUTION_TOKEN', '')
        instancia = getattr(settings, 'WHATSAPP_EVOLUTION_INSTANCIA', '')
        try:
            resp = requests.post(
                f'{base_url}/message/sendText/{instancia}',
                headers={'apikey': token, 'Content-Type': 'application/json'},
                json={'number': destinatario, 'text': mensagem},
                timeout=10,
            )
            resp.raise_for_status()
            logger.info('WhatsApp (Evolution) enviado para %s — alerta %s', destinatario, id_alerta)
        except Exception as exc:
            logger.error('Falha WhatsApp (Evolution) para %s: %s', destinatario, exc)
