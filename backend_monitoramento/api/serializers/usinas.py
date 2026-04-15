from rest_framework import serializers
from usinas.models import Usina, SnapshotUsina, SnapshotInversor, Inversor, GarantiaUsina


class SnapshotUsinaSerializer(serializers.ModelSerializer):
    """Serializer de SnapshotUsina — EXCLUI payload_bruto (T-2-03)."""

    class Meta:
        model = SnapshotUsina
        fields = [
            'id', 'coletado_em', 'data_medicao', 'potencia_kw',
            'energia_hoje_kwh', 'energia_mes_kwh', 'energia_total_kwh',
            'status', 'qtd_inversores', 'qtd_inversores_online', 'qtd_alertas',
        ]
        # payload_bruto EXCLUIDO — dados brutos do provedor, potencialmente sensiveis (T-2-03)


class SnapshotInversorResumoSerializer(serializers.ModelSerializer):
    """Snapshot do inversor resumido para uso dentro do detalhe de usina."""

    class Meta:
        model = SnapshotInversor
        fields = [
            'coletado_em', 'estado',
            'pac_kw', 'energia_hoje_kwh', 'energia_total_kwh',
            'tensao_ac_v', 'corrente_ac_a',
            'tensao_dc_v', 'corrente_dc_a',
            'frequencia_hz', 'temperatura_c',
            'strings_mppt', 'soc_bateria',
        ]


class InversorResumoSerializer(serializers.ModelSerializer):
    """Inversor com dados elétricos do último snapshot para detalhe de usina."""

    ultimo_snapshot = SnapshotInversorResumoSerializer(read_only=True)

    class Meta:
        model = Inversor
        fields = ['id', 'numero_serie', 'modelo', 'id_inversor_provedor', 'ultimo_snapshot']


class UsinaListSerializer(serializers.ModelSerializer):
    """Serializer de listagem de usinas — inclui status_garantia (USN-01, USN-04)."""

    status_garantia = serializers.SerializerMethodField()

    class Meta:
        model = Usina
        fields = [
            'id', 'nome', 'provedor', 'capacidade_kwp', 'ativo',
            'endereco', 'cidade', 'telefone',
            'status_garantia', 'criado_em', 'atualizado_em',
        ]

    def get_status_garantia(self, obj) -> str:
        """USN-04: 3 valores — 'ativa', 'vencida', 'sem_garantia'."""
        try:
            garantia = obj.garantia
        except GarantiaUsina.DoesNotExist:
            return 'sem_garantia'
        return 'ativa' if garantia.ativa else 'vencida'


class UsinaDetalheSerializer(serializers.ModelSerializer):
    """Serializer de detalhe de usina — inclui inversores e ultimo_snapshot (USN-02)."""

    status_garantia = serializers.SerializerMethodField()
    ultimo_snapshot = SnapshotUsinaSerializer(read_only=True)
    inversores = InversorResumoSerializer(many=True, read_only=True)

    class Meta:
        model = Usina
        fields = [
            'id', 'nome', 'provedor', 'capacidade_kwp', 'ativo',
            'fuso_horario', 'endereco', 'cidade', 'telefone',
            'latitude', 'longitude', 'status_garantia',
            'tensao_sobretensao_v',
            'ultimo_snapshot', 'inversores', 'criado_em', 'atualizado_em',
        ]

    def get_status_garantia(self, obj) -> str:
        try:
            garantia = obj.garantia
        except GarantiaUsina.DoesNotExist:
            return 'sem_garantia'
        return 'ativa' if garantia.ativa else 'vencida'


class UsinaPatchSerializer(serializers.ModelSerializer):
    """Serializer de escrita para PATCH /api/usinas/{id}/ — apenas campos editáveis pelo operador (USN-03, T-2-04).

    Campo `ativo`: permite reativar usina pausada por inatividade sem precisar do Django admin.
    """

    class Meta:
        model = Usina
        fields = ['nome', 'capacidade_kwp', 'tensao_sobretensao_v', 'ativo']

    def validate_tensao_sobretensao_v(self, valor):
        if valor is None:
            return 240.0
        if valor < 180 or valor > 280:
            raise serializers.ValidationError(
                'Limite fora da faixa razoável (180V a 280V).'
            )
        return valor
