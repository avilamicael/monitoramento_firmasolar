"""
Serviço central de notificações.

Quando um alerta novo é criado ou escalado, o ServicoNotificacao:
1. Lê as ConfiguracaoNotificacao do banco (sem restart)
2. Para cada canal ativo, verifica se o nível do alerta está configurado
3. Carrega o backend correspondente e envia
4. Falha em um canal não impede os demais
"""
import logging

from .base import BackendNotificacao, DadosNotificacao
from .models import ConfiguracaoNotificacao

logger = logging.getLogger(__name__)

_BACKENDS_MAP: dict[str, type[BackendNotificacao]] = {}


def _carregar_backends():
    if not _BACKENDS_MAP:
        from .backends.email import EmailBackend
        from .backends.whatsapp import WhatsAppBackend
        _BACKENDS_MAP['email'] = EmailBackend
        _BACKENDS_MAP['whatsapp'] = WhatsAppBackend


class ServicoNotificacao:
    """
    Despacha notificações de alertas para todos os canais configurados no banco.
    """

    def notificar_novo_alerta(self, alerta) -> None:
        """Chamado quando um novo alerta é criado (estado=ativo)."""
        self._despachar(alerta, novo=True)

    def notificar_alerta_escalado(self, alerta) -> None:
        """Chamado quando um alerta sobe de 'aviso' para 'critico'."""
        self._despachar(alerta, novo=False)

    def _despachar(self, alerta, novo: bool) -> None:
        _carregar_backends()

        dados = DadosNotificacao(
            id_alerta=str(alerta.id),
            nome_usina=alerta.usina.nome,
            provedor=alerta.usina.provedor,
            mensagem=alerta.mensagem,
            nivel=alerta.nivel,
            sugestao=alerta.sugestao or '',
            equipamento_sn=alerta.equipamento_sn or '',
            inicio=alerta.inicio,
            novo=novo,
        )

        configuracoes = ConfiguracaoNotificacao.objects.filter(ativo=True)
        if not configuracoes.exists():
            logger.debug('Nenhum canal de notificação ativo — ignorando alerta %s', alerta.id)
            return

        for config in configuracoes:
            # Verificar se este canal notifica este nível de alerta
            if alerta.nivel == 'critico' and not config.notificar_critico:
                continue
            if alerta.nivel == 'aviso' and not config.notificar_aviso:
                continue

            destinatarios = config.lista_destinatarios()
            if not destinatarios:
                logger.debug('Canal %s ativo mas sem destinatários', config.canal)
                continue

            classe_backend = _BACKENDS_MAP.get(config.canal)
            if not classe_backend:
                logger.warning('Backend "%s" não encontrado', config.canal)
                continue

            backend = classe_backend()
            if not backend.is_disponivel():
                logger.debug('Backend %s não disponível (falta credencial no .env)', config.canal)
                continue

            try:
                backend.enviar(dados, destinatarios)
            except Exception as exc:
                logger.error('Backend %s falhou para alerta %s: %s', config.canal, alerta.id, exc)
