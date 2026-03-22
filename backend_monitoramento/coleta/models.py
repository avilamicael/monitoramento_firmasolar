import uuid
from django.db import models


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
