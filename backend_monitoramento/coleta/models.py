import uuid
from django.core.validators import MinValueValidator
from django.db import models


class ConfiguracaoSistema(models.Model):
    """
    Configurações globais do sistema (singleton).

    Acessar via ConfiguracaoSistema.obter() — sempre retorna a única linha existente,
    criando-a com valores-padrão na primeira chamada.
    """
    dias_sem_comunicacao_pausar = models.PositiveIntegerField(
        default=60,
        validators=[MinValueValidator(1)],
        verbose_name='Dias sem comunicação até pausar coleta',
        help_text=(
            'Usinas sem snapshot há mais deste número de dias são automaticamente '
            'desativadas no início do próximo ciclo de coleta. Para retomar, '
            'acesse a página da usina e reative a coleta.'
        ),
    )
    meses_garantia_padrao = models.PositiveIntegerField(
        default=12,
        validators=[MinValueValidator(1)],
        verbose_name='Meses de garantia padrão',
        help_text=(
            'Duração (em meses) da garantia criada automaticamente ao registrar uma '
            'nova usina. Só afeta garantias criadas a partir da próxima coleta.'
        ),
    )
    dias_aviso_garantia_proxima = models.PositiveIntegerField(
        default=30,
        validators=[MinValueValidator(1)],
        verbose_name='Aviso prévio de garantia (dias)',
        help_text='Gera alerta nível "aviso" quando a garantia da usina estiver a este número de dias ou menos do fim.',
    )
    dias_aviso_garantia_urgente = models.PositiveIntegerField(
        default=7,
        validators=[MinValueValidator(1)],
        verbose_name='Aviso urgente de garantia (dias)',
        help_text='Escala o alerta para nível "importante" quando a garantia estiver a este número de dias ou menos do fim.',
    )
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Configuração do Sistema'
        verbose_name_plural = 'Configuração do Sistema'

    def __str__(self):
        return 'Configuração do Sistema'

    def save(self, *args, **kwargs):
        # Singleton — sempre pk=1
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Singleton não pode ser apagado
        pass

    @classmethod
    def obter(cls) -> 'ConfiguracaoSistema':
        config, _ = cls.objects.get_or_create(pk=1)
        return config


class LogColeta(models.Model):
    """
    Registro de auditoria de cada ciclo de coleta.
    Permite saber quando ocorreu a última coleta bem-sucedida de cada provedor,
    quantos dados foram coletados e se houve erros.
    """
    STATUS_CHOICES = [
        ('sucesso',    'Sucesso'),
        ('parcial',    'Parcial'),
        ('erro',       'Erro'),
        ('auth_erro',  'Erro de autenticação'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    credencial = models.ForeignKey(
        'provedores.CredencialProvedor',
        on_delete=models.CASCADE,
        related_name='logs_coleta',
    )
    status = models.CharField(max_length=15, choices=STATUS_CHOICES)
    usinas_coletadas = models.IntegerField(default=0)
    inversores_coletados = models.IntegerField(default=0)
    alertas_sincronizados = models.IntegerField(default=0)
    detalhe_erro = models.TextField(blank=True)
    duracao_ms = models.IntegerField(default=0)
    iniciado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Log de Coleta'
        verbose_name_plural = 'Logs de Coleta'
        ordering = ['-iniciado_em']
        indexes = [
            models.Index(fields=['credencial', '-iniciado_em']),
        ]

    def __str__(self):
        return f'{self.credencial.get_provedor_display()} — {self.status} @ {self.iniciado_em:%d/%m/%Y %H:%M}'
