from django.db import models


class ConfiguracaoNotificacao(models.Model):
    """
    Configura os canais de notificação disponíveis.
    Gerenciado pelo admin do Django — sem restart do servidor para alterar.

    Cada registro representa um canal (email ou whatsapp) com:
    - Se está ativo ou não
    - Quais destinatários recebem
    - Para quais níveis de alerta (crítico e/ou aviso)
    """
    CANAL_CHOICES = [
        ('email',    'E-mail'),
        ('whatsapp', 'WhatsApp'),
    ]

    canal = models.CharField(max_length=20, choices=CANAL_CHOICES, unique=True)
    ativo = models.BooleanField(default=False)
    # Lista de endereços/números separados por vírgula ou quebra de linha
    # Email: "equipe@firma.com, gestor@firma.com"
    # WhatsApp: "+5548999999999, +5511988888888"
    destinatarios = models.TextField(
        blank=True,
        help_text='Um por linha ou separados por vírgula. Email: endereços. WhatsApp: +55DDNNNNNNNNN',
    )
    # Quais níveis disparam notificação neste canal
    notificar_critico = models.BooleanField(default=True, verbose_name='Notificar alertas críticos')
    notificar_importante = models.BooleanField(default=True, verbose_name='Notificar alertas importantes')
    notificar_aviso = models.BooleanField(default=False, verbose_name='Notificar alertas de aviso')
    notificar_info = models.BooleanField(default=False, verbose_name='Notificar alertas informativos')
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Configuração de Notificação'
        verbose_name_plural = 'Configurações de Notificação'

    def __str__(self):
        status = 'ativo' if self.ativo else 'inativo'
        return f'{self.get_canal_display()} [{status}]'

    def lista_destinatarios(self) -> list[str]:
        """Retorna a lista de destinatários como lista Python."""
        import re
        raw = self.destinatarios or ''
        # Aceita separador por vírgula ou quebra de linha
        itens = re.split(r'[,\n]', raw)
        return [item.strip() for item in itens if item.strip()]
