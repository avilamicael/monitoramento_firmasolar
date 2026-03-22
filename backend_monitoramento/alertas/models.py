import uuid
from django.db import models


class Alerta(models.Model):
    """
    Representa um problema ou alerta reportado por um provedor em uma usina.

    Ciclo de vida:
        ativo → em_atendimento (equipe assume) → resolvido (problema desapareceu)

    Se um alerta resolvido reaparecer no próximo ciclo de coleta, ele é reaberto (volta para 'ativo').
    Se um alerta subir de 'aviso' para 'critico', uma notificação de escalonamento é disparada.
    """
    NIVEL_CHOICES = [
        ('critico', 'Crítico'),
        ('aviso',   'Aviso'),
    ]
    ESTADO_CHOICES = [
        ('ativo',         'Ativo'),
        ('em_atendimento', 'Em atendimento'),
        ('resolvido',     'Resolvido'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usina = models.ForeignKey(
        'usinas.Usina',
        on_delete=models.CASCADE,
        related_name='alertas',
    )
    # ID do alerta no sistema do fabricante — usado para deduplicação
    id_alerta_provedor = models.CharField(max_length=200, blank=True)
    equipamento_sn = models.CharField(max_length=100, blank=True, verbose_name='Serial do equipamento')
    mensagem = models.TextField(verbose_name='Descrição do problema')
    nivel = models.CharField(max_length=10, choices=NIVEL_CHOICES, default='aviso', db_index=True)
    inicio = models.DateTimeField(verbose_name='Início do problema')
    fim = models.DateTimeField(null=True, blank=True, verbose_name='Fim do problema')
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='ativo', db_index=True)
    sugestao = models.TextField(blank=True, verbose_name='Sugestão de resolução')
    # Campo livre para a equipe técnica anotar o que foi feito
    anotacoes = models.TextField(blank=True, verbose_name='Anotações da equipe')
    # Controle de notificação — evita notificar o mesmo alerta duas vezes
    notificacao_enviada = models.BooleanField(default=False)
    payload_bruto = models.JSONField(default=dict)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        verbose_name = 'Alerta'
        verbose_name_plural = 'Alertas'
        unique_together = [('usina', 'id_alerta_provedor')]
        ordering = ['-inicio']
        indexes = [
            models.Index(fields=['estado', '-inicio']),
            models.Index(fields=['nivel', 'estado']),
            models.Index(fields=['usina', 'estado']),
        ]

    def __str__(self):
        return f'[{self.nivel}] {self.mensagem[:60]} — {self.usina.nome}'

    @property
    def esta_aberto(self) -> bool:
        """True se o alerta ainda não foi resolvido."""
        return self.estado in ('ativo', 'em_atendimento')
