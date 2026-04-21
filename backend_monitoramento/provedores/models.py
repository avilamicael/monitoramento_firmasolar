import uuid
from django.db import models


class CredencialProvedor(models.Model):
    """
    Armazena as credenciais de acesso a um provedor (Solis, Hoymiles, FusionSolar).
    As credenciais são criptografadas com Fernet antes de salvar no banco.
    """
    PROVEDORES = [
        ('solis',       'Solis Cloud'),
        ('hoymiles',    'Hoymiles S-Cloud'),
        ('fusionsolar', 'Huawei FusionSolar'),
        ('solarman',    'Solarman Pro'),
        ('auxsol',      'AuxSol Cloud'),
        ('foxess',      'FoxESS Cloud'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provedor = models.CharField(max_length=30, choices=PROVEDORES, unique=True)
    # JSON criptografado com Fernet: {"api_key": "...", "app_secret": "..."} (Solis)
    # ou {"username": "...", "password": "..."} (Hoymiles/FusionSolar)
    credenciais_enc = models.TextField(
        help_text='Credenciais criptografadas com Fernet. Não editar manualmente.'
    )
    ativo = models.BooleanField(default=True)
    # Marcado como True quando há falha de autenticação — requer atenção manual
    precisa_atencao = models.BooleanField(default=False)
    # Intervalo entre coletas em minutos (configurável pelo admin, mínimo 30)
    intervalo_coleta_minutos = models.PositiveIntegerField(
        default=30,
        help_text='Intervalo entre coletas em minutos. Mínimo: 30 minutos.',
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Credencial de Provedor'
        verbose_name_plural = 'Credenciais de Provedores'

    def __str__(self):
        status = '⚠️ ATENÇÃO' if self.precisa_atencao else ('✓ ativo' if self.ativo else '✗ inativo')
        return f'{self.get_provedor_display()} [{status}]'


class CacheTokenProvedor(models.Model):
    """
    Armazena o token de sessão dos provedores que usam autenticação stateful
    (Hoymiles, FusionSolar). Evita re-login a cada coleta.

    Os dados do token são criptografados com Fernet.
    """
    credencial = models.OneToOneField(
        CredencialProvedor,
        on_delete=models.CASCADE,
        related_name='cache_token',
    )
    # JSON criptografado: {"token": "3.xxx"} (Hoymiles) ou {"xsrf_token": "..."} (FusionSolar)
    dados_token_enc = models.TextField()
    expira_em = models.DateTimeField(null=True, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cache de Token'
        verbose_name_plural = 'Cache de Tokens'

    def __str__(self):
        return f'Token de {self.credencial.get_provedor_display()}'
