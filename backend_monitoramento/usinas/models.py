import uuid
from django.db import models


class Usina(models.Model):
    """
    Representa uma usina solar monitorada.
    Os dados fixos ficam aqui (nome, capacidade, localização).
    Os dados em tempo real ficam em SnapshotUsina.
    """
    STATUS_CHOICES = [
        ('normal',    'Normal'),
        ('aviso',     'Aviso'),
        ('offline',   'Offline'),
        ('construcao', 'Em construção'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Identificador no sistema do fabricante (ex: "123456" no Solis)
    id_usina_provedor = models.CharField(max_length=200)
    provedor = models.CharField(max_length=30)
    credencial = models.ForeignKey(
        'provedores.CredencialProvedor',
        on_delete=models.PROTECT,
        related_name='usinas',
    )
    nome = models.CharField(max_length=200)
    capacidade_kwp = models.FloatField(default=0.0)
    fuso_horario = models.CharField(max_length=50, default='America/Sao_Paulo')
    endereco = models.TextField(blank=True)
    cidade = models.CharField(max_length=100, blank=True)
    telefone = models.CharField(max_length=30, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    ativo = models.BooleanField(default=True)
    # Último snapshot salvo — desnormalizado para consultas rápidas
    ultimo_snapshot = models.OneToOneField(
        'SnapshotUsina',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='+',
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Usina'
        verbose_name_plural = 'Usinas'
        unique_together = [('id_usina_provedor', 'provedor')]
        indexes = [
            models.Index(fields=['provedor']),
        ]

    def __str__(self):
        return f'{self.nome} ({self.get_provedor_display() if hasattr(self, "get_provedor_display") else self.provedor})'

    def get_provedor_display(self):
        nomes = {'solis': 'Solis', 'hoymiles': 'Hoymiles', 'fusionsolar': 'FusionSolar'}
        return nomes.get(self.provedor, self.provedor)


class SnapshotUsina(models.Model):
    """
    Registro de dados em tempo real de uma usina em um momento específico.
    Append-only — nunca atualizado, apenas criado.
    Idempotente: get_or_create por (usina, coletado_em arredondado a 10min).
    """
    STATUS_CHOICES = [
        ('normal',    'Normal'),
        ('aviso',     'Aviso'),
        ('offline',   'Offline'),
        ('construcao', 'Em construção'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usina = models.ForeignKey(Usina, on_delete=models.CASCADE, related_name='snapshots')
    # Momento da coleta, arredondado para janelas de 10 minutos
    coletado_em = models.DateTimeField()
    # Timestamp reportado pelo provedor (pode ser diferente de coletado_em)
    data_medicao = models.DateTimeField(null=True, blank=True)
    potencia_kw = models.FloatField(default=0.0)
    energia_hoje_kwh = models.FloatField(default=0.0)
    energia_mes_kwh = models.FloatField(default=0.0)
    energia_total_kwh = models.FloatField(default=0.0)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='normal')
    qtd_inversores = models.IntegerField(default=0)
    qtd_inversores_online = models.IntegerField(default=0)
    qtd_alertas = models.IntegerField(default=0)
    payload_bruto = models.JSONField(default=dict)

    class Meta:
        verbose_name = 'Snapshot de Usina'
        verbose_name_plural = 'Snapshots de Usinas'
        indexes = [
            models.Index(fields=['usina', '-coletado_em']),
            models.Index(fields=['-coletado_em']),
        ]
        ordering = ['-coletado_em']

    def __str__(self):
        return f'{self.usina.nome} @ {self.coletado_em:%d/%m/%Y %H:%M}'


class Inversor(models.Model):
    """
    Representa um inversor solar dentro de uma usina.
    Os dados fixos ficam aqui (serial, modelo).
    Os dados em tempo real ficam em SnapshotInversor.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usina = models.ForeignKey(Usina, on_delete=models.CASCADE, related_name='inversores')
    id_inversor_provedor = models.CharField(max_length=200)
    numero_serie = models.CharField(max_length=100, blank=True)
    modelo = models.CharField(max_length=100, blank=True)
    ultimo_snapshot = models.OneToOneField(
        'SnapshotInversor',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='+',
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Inversor'
        verbose_name_plural = 'Inversores'
        unique_together = [('usina', 'id_inversor_provedor')]

    def __str__(self):
        return f'{self.numero_serie or self.id_inversor_provedor} ({self.usina.nome})'


class SnapshotInversor(models.Model):
    """
    Registro de dados em tempo real de um inversor.
    Append-only — mesma lógica de idempotência do SnapshotUsina.
    """
    ESTADO_CHOICES = [
        ('normal',  'Normal'),
        ('aviso',   'Aviso'),
        ('offline', 'Offline'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inversor = models.ForeignKey(Inversor, on_delete=models.CASCADE, related_name='snapshots')
    coletado_em = models.DateTimeField()
    data_medicao = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='normal')
    pac_kw = models.FloatField(default=0.0)
    energia_hoje_kwh = models.FloatField(default=0.0)
    energia_total_kwh = models.FloatField(default=0.0)
    soc_bateria = models.FloatField(null=True, blank=True)
    # Ex: {"string1": 120.5, "string2": 118.2}
    strings_mppt = models.JSONField(default=dict)
    tensao_ac_v = models.FloatField(null=True, blank=True, verbose_name='Tensão AC (V)')
    corrente_ac_a = models.FloatField(null=True, blank=True, verbose_name='Corrente AC (A)')
    tensao_dc_v = models.FloatField(null=True, blank=True, verbose_name='Tensão DC (V)')
    corrente_dc_a = models.FloatField(null=True, blank=True, verbose_name='Corrente DC (A)')
    frequencia_hz = models.FloatField(null=True, blank=True, verbose_name='Frequência (Hz)')
    temperatura_c = models.FloatField(null=True, blank=True, verbose_name='Temperatura (°C)')
    payload_bruto = models.JSONField(default=dict)

    class Meta:
        verbose_name = 'Snapshot de Inversor'
        verbose_name_plural = 'Snapshots de Inversores'
        indexes = [
            models.Index(fields=['inversor', '-coletado_em']),
        ]
        ordering = ['-coletado_em']

    def __str__(self):
        return f'{self.inversor.numero_serie} @ {self.coletado_em:%d/%m/%Y %H:%M}'


class GarantiaUsina(models.Model):
    """
    Garantia comercial de uma usina solar.
    data_fim e ativa sao properties calculadas — nao existem como colunas.
    """
    usina = models.OneToOneField(
        Usina,
        on_delete=models.CASCADE,
        related_name='garantia',
    )
    data_inicio = models.DateField()
    meses = models.PositiveIntegerField()
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Garantia de Usina'
        verbose_name_plural = 'Garantias de Usinas'

    @property
    def data_fim(self):
        from dateutil.relativedelta import relativedelta
        return self.data_inicio + relativedelta(months=self.meses)

    @property
    def ativa(self):
        from django.utils import timezone
        return self.data_fim >= timezone.now().date()

    @property
    def dias_restantes(self):
        from django.utils import timezone
        delta = self.data_fim - timezone.now().date()
        return max(delta.days, 0)

    def __str__(self):
        return f'Garantia — {self.usina.nome} ({self.meses} meses)'
