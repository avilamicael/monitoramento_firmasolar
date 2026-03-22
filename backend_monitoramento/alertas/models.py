import uuid
from django.db import models


class CatalogoAlarme(models.Model):
    """
    Catálogo de tipos de alarme conhecidos, chaveado por (provedor, id_alarme_provedor).

    Cada entrada representa um *tipo* de alarme, não uma ocorrência.

    - nivel_padrao: nível definido pela documentação do fabricante ou pela equipe
    - nivel_sobrescrito: True quando o operador ajustou o nível manualmente (protege de sobrescritas automáticas)
    - suprimido: True quando este tipo jamais deve gerar Alerta nem notificação em nenhuma usina
    - criado_auto: True quando a entrada foi criada durante a coleta ao encontrar um ID desconhecido
    """
    NIVEL_CHOICES = [
        ('info',       'Info'),
        ('aviso',      'Aviso'),
        ('importante', 'Importante'),
        ('critico',    'Crítico'),
    ]

    provedor = models.CharField(max_length=50, db_index=True)
    id_alarme_provedor = models.CharField(max_length=100, verbose_name='ID do alarme no provedor')
    nome_pt = models.CharField(max_length=200, verbose_name='Nome em português')
    nome_original = models.CharField(max_length=200, blank=True, verbose_name='Nome original (do provedor)')
    tipo = models.CharField(max_length=100, blank=True, verbose_name='Categoria/tipo')
    nivel_padrao = models.CharField(
        max_length=10,
        choices=NIVEL_CHOICES,
        default='aviso',
        verbose_name='Nível padrão',
    )
    nivel_sobrescrito = models.BooleanField(
        default=False,
        verbose_name='Nível sobrescrito pelo operador',
        help_text=(
            'Quando True, o nivel_padrao foi definido manualmente e não será '
            'alterado por atualizações automáticas da coleta.'
        ),
    )
    suprimido = models.BooleanField(
        default=False,
        verbose_name='Suprimido globalmente',
        help_text='Quando True, este tipo de alarme não gera registros nem notificações em nenhuma usina.',
    )
    sugestao = models.TextField(blank=True, verbose_name='Sugestão de resolução')
    criado_auto = models.BooleanField(
        default=False,
        verbose_name='Criado automaticamente',
        help_text='True quando a entrada foi criada durante a coleta (alarme não documentado).',
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        verbose_name = 'Catálogo de Alarme'
        verbose_name_plural = 'Catálogo de Alarmes'
        unique_together = [('provedor', 'id_alarme_provedor')]
        ordering = ['provedor', 'id_alarme_provedor']

    def __str__(self):
        return f'[{self.provedor}] {self.id_alarme_provedor} — {self.nome_pt}'

    @property
    def nivel_efetivo(self) -> str:
        """Nível a ser aplicado nos alertas (pode ter sido sobrescrito pelo operador)."""
        return self.nivel_padrao


class RegraSupressao(models.Model):
    """
    Suprime um tipo de alarme em escopo específico.

    Escopo 'usina': suprime somente na usina indicada.
    Escopo 'todas': suprime em todas as usinas (revogável com motivo e data).

    ativo_ate=None significa supressão permanente.
    Supressões expiradas são ignoradas na coleta mas preservadas no histórico.
    """
    ESCOPO_CHOICES = [
        ('usina', 'Somente esta usina'),
        ('todas', 'Todas as usinas'),
    ]

    catalogo = models.ForeignKey(
        CatalogoAlarme,
        on_delete=models.CASCADE,
        related_name='regras_supressao',
    )
    escopo = models.CharField(max_length=10, choices=ESCOPO_CHOICES)
    usina = models.ForeignKey(
        'usinas.Usina',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='regras_supressao',
        help_text='Obrigatório quando escopo=usina. Ignorado quando escopo=todas.',
    )
    motivo = models.TextField(blank=True, verbose_name='Motivo da supressão')
    ativo_ate = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Ativo até',
        help_text='Deixe em branco para supressão permanente.',
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    class Meta:
        verbose_name = 'Regra de Supressão'
        verbose_name_plural = 'Regras de Supressão'
        ordering = ['-criado_em']

    def __str__(self):
        if self.escopo == 'usina' and self.usina:
            return f'Supressão de {self.catalogo} em {self.usina.nome}'
        return f'Supressão global de {self.catalogo}'

    def esta_ativa(self) -> bool:
        """Retorna True se esta regra ainda está em vigor."""
        from django.utils import timezone
        if self.ativo_ate is None:
            return True
        return timezone.now() < self.ativo_ate


class Alerta(models.Model):
    """
    Representa uma ocorrência de alarme em uma usina, reportada pelo provedor.

    Ciclo de vida:
        ativo → em_atendimento (equipe assume) → resolvido (problema desapareceu)

    Se um alerta resolvido reaparecer no próximo ciclo de coleta, ele é reaberto (volta para 'ativo').
    Se um alerta subir de nível, uma notificação de escalonamento é disparada.
    """
    NIVEL_CHOICES = [
        ('info',       'Info'),
        ('aviso',      'Aviso'),
        ('importante', 'Importante'),
        ('critico',    'Crítico'),
    ]
    ESTADO_CHOICES = [
        ('ativo',          'Ativo'),
        ('em_atendimento', 'Em atendimento'),
        ('resolvido',      'Resolvido'),
    ]

    # Ordem para detectar escalonamento (maior índice = maior severidade)
    _NIVEL_ORDEM = {'info': 0, 'aviso': 1, 'importante': 2, 'critico': 3}

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usina = models.ForeignKey(
        'usinas.Usina',
        on_delete=models.CASCADE,
        related_name='alertas',
    )
    catalogo_alarme = models.ForeignKey(
        CatalogoAlarme,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alertas',
        verbose_name='Tipo de alarme (catálogo)',
    )
    # ID da ocorrência no provedor — usado para deduplicação (ex: "2032_SN12345")
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

    def nivel_escalou_para(self, novo_nivel: str) -> bool:
        """Retorna True se novo_nivel representa escalonamento em relação ao nível atual."""
        return self._NIVEL_ORDEM.get(novo_nivel, 0) > self._NIVEL_ORDEM.get(self.nivel, 0)
