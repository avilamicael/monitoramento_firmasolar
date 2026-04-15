"""
Tasks Celery do sistema de notificações.

Desacoplam o envio de notificações do ciclo de coleta:
o alerta é persistido na transação, e a notificação é despachada
em uma task separada após o commit — erros de envio não afetam a coleta.
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60, ignore_result=True)
def enviar_notificacao_alerta(self, alerta_id: str, motivo: str) -> None:
    """
    Envia notificações para um alerta específico.

    Chamada após o commit da transação de coleta, via transaction.on_commit().
    Isso garante que o alerta já está visível no banco quando o worker executa.

    Args:
        alerta_id: UUID do Alerta (str)
        motivo:    'novo' | 'escalado'
    """
    from alertas.models import Alerta
    from notificacoes.servico import ServicoNotificacao

    try:
        alerta = Alerta.objects.select_related('usina').get(pk=alerta_id)
    except Alerta.DoesNotExist:
        logger.warning('Notificação ignorada: alerta %s não encontrado no banco', alerta_id)
        return

    # Persiste notificação no painel (independente do envio por canal externo).
    # Falha aqui não deve bloquear o envio por email/WhatsApp — só logada.
    _persistir_notificacao_painel(alerta, motivo)

    servico = ServicoNotificacao()
    try:
        if motivo == 'novo':
            servico.notificar_novo_alerta(alerta)
        elif motivo == 'escalado':
            servico.notificar_alerta_escalado(alerta)
        else:
            logger.error('Motivo de notificação desconhecido: "%s" (alerta %s)', motivo, alerta_id)
    except Exception as exc:
        logger.error('Erro ao enviar notificação para alerta %s: %s', alerta_id, exc)
        raise self.retry(exc=exc)


def _persistir_notificacao_painel(alerta, motivo: str) -> None:
    """Cria registro em Notificacao para aparecer no painel dos usuários."""
    from notificacoes.models import Notificacao

    try:
        prefixo = 'Novo alerta' if motivo == 'novo' else 'Alerta escalado'
        titulo = f'{prefixo} — {alerta.usina.nome}'
        Notificacao.objects.create(
            titulo=titulo[:200],
            mensagem=alerta.mensagem,
            tipo='alerta',
            nivel=alerta.nivel,
            link=f'/alertas/{alerta.id}',
            apenas_staff=False,
        )
    except Exception as exc:
        logger.warning('Falha ao persistir notificação no painel para %s: %s', alerta.id, exc)
