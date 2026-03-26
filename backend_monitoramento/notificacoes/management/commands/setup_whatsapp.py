"""
Comando de setup inicial do canal WhatsApp.

Lê WHATSAPP_DESTINATARIO_TESTE do .env e cria (ou atualiza) o registro
ConfiguracaoNotificacao para o canal WhatsApp, já marcado como ativo.

Uso:
    python manage.py setup_whatsapp

Após rodar, o destinatário fica salvo no banco e pode ser ajustado pelo
Django admin sem precisar rodar o comando novamente.
"""
import os

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Configura o canal WhatsApp com o número de teste definido em WHATSAPP_DESTINATARIO_TESTE'

    def handle(self, *args, **options):
        from notificacoes.models import ConfiguracaoNotificacao

        telefone = os.environ.get('WHATSAPP_DESTINATARIO_TESTE', '').strip()
        if not telefone or telefone == '+55':
            self.stderr.write(self.style.ERROR(
                'WHATSAPP_DESTINATARIO_TESTE não está definido no .env. '
                'Preencha com o número no formato +55DDNNNNNNNNN e rode novamente.'
            ))
            return

        config, criado = ConfiguracaoNotificacao.objects.update_or_create(
            canal='whatsapp',
            defaults={
                'ativo': True,
                'destinatarios': telefone,
                'notificar_critico': True,
                'notificar_importante': True,
                'notificar_aviso': False,
                'notificar_info': False,
            },
        )

        acao = 'criado' if criado else 'atualizado'
        self.stdout.write(self.style.SUCCESS(
            f'Canal WhatsApp {acao} com sucesso.\n'
            f'  Destinatário: {telefone}\n'
            f'  Notifica: crítico + importante\n'
            f'  Para alterar: Django admin → Configurações de Notificação'
        ))
