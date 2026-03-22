import logging
from django.conf import settings
from notificacoes.base import BackendNotificacao, DadosNotificacao

logger = logging.getLogger(__name__)

_EMOJI_NIVEL = {'critico': '🔴', 'aviso': '⚠️'}


class EmailBackend(BackendNotificacao):
    """
    Envia notificações por e-mail usando o servidor SMTP configurado no .env.

    Configurar no .env:
        EMAIL_HOST=smtp.exemplo.com
        EMAIL_PORTA=587
        EMAIL_USUARIO=noreply@firmasolar.com.br
        EMAIL_SENHA=sua_senha
        NOTIFICACAO_EMAIL_DE=noreply@firmasolar.com.br

    Destinatários gerenciados pelo Django admin (sem restart).
    """

    def is_disponivel(self) -> bool:
        return bool(getattr(settings, 'EMAIL_HOST', ''))

    def enviar(self, dados: DadosNotificacao, destinatarios: list[str]) -> None:
        from django.core.mail import send_mail

        emoji = _EMOJI_NIVEL.get(dados.nivel, '⚠️')
        nivel_label = 'CRÍTICO' if dados.nivel == 'critico' else 'AVISO'
        prefixo = '[NOVO]' if dados.novo else '[ESCALADO]'

        assunto = f'{prefixo} {emoji} {nivel_label} — {dados.nome_usina} ({dados.provedor.upper()})'

        linhas = [
            f'Usina: {dados.nome_usina}',
            f'Provedor: {dados.provedor.upper()}',
            f'Nível: {nivel_label}',
            f'Problema: {dados.mensagem}',
        ]
        if dados.equipamento_sn:
            linhas.append(f'Equipamento: {dados.equipamento_sn}')
        if dados.sugestao:
            linhas.append(f'Sugestão: {dados.sugestao}')
        linhas.append(f'Início: {dados.inicio:%d/%m/%Y %H:%M}')
        linhas.append('\nAcesse o painel para mais detalhes.')

        corpo = '\n'.join(linhas)
        remetente = getattr(settings, 'NOTIFICACAO_EMAIL_DE', None)

        try:
            send_mail(
                subject=assunto,
                message=corpo,
                from_email=remetente,
                recipient_list=destinatarios,
                fail_silently=False,
            )
            logger.info('Email enviado para %s — alerta %s', destinatarios, dados.id_alerta)
        except Exception as exc:
            logger.error('Falha ao enviar email para alerta %s: %s', dados.id_alerta, exc)
