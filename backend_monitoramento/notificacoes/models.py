import uuid

from django.conf import settings
from django.db import models


class Notificacao(models.Model):
    """
    Notificação persistida, exibida no painel de cada usuário.

    Broadcast global — todos os usuários autenticados veem todas as notificações,
    exceto quando apenas_staff=True (neste caso só is_staff veem).

    O estado "lida" é individual por usuário via NotificacaoLeitura.
    """
    TIPO_CHOICES = [
        ('alerta',   'Alerta'),
        ('sistema',  'Sistema'),
        ('garantia', 'Garantia'),
        ('outro',    'Outro'),
    ]

    NIVEL_CHOICES = [
        ('info',       'Info'),
        ('aviso',      'Aviso'),
        ('importante', 'Importante'),
        ('critico',    'Crítico'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    titulo = models.CharField(max_length=200)
    mensagem = models.TextField()
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='sistema', db_index=True)
    nivel = models.CharField(max_length=15, choices=NIVEL_CHOICES, default='info', db_index=True)
    # Link relativo para onde o clique na notificação deve levar (ex: /alertas/UUID)
    link = models.CharField(max_length=500, blank=True)
    # Quando True, apenas usuários com is_staff=True veem esta notificação
    apenas_staff = models.BooleanField(default=False, db_index=True)
    criado_em = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Notificação'
        verbose_name_plural = 'Notificações'
        ordering = ['-criado_em']
        indexes = [
            models.Index(fields=['-criado_em']),
        ]

    def __str__(self):
        return f'[{self.nivel}] {self.titulo}'


class NotificacaoLeitura(models.Model):
    """
    Registro de leitura de uma notificação por um usuário específico.

    A ausência de registro = não lida. A presença = lida (com timestamp).
    Deletar um registro marca como não lida novamente.
    """
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notificacoes_lidas',
    )
    notificacao = models.ForeignKey(
        Notificacao,
        on_delete=models.CASCADE,
        related_name='leituras',
    )
    lida_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Leitura de Notificação'
        verbose_name_plural = 'Leituras de Notificações'
        unique_together = [('usuario', 'notificacao')]
        indexes = [
            models.Index(fields=['usuario', 'notificacao']),
        ]

    def __str__(self):
        return f'{self.usuario} leu {self.notificacao.titulo}'


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
        ('webhook',  'Webhook'),
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
