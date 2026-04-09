from rest_framework import serializers
from usinas.models import Inversor, SnapshotInversor


class SnapshotInversorSerializer(serializers.ModelSerializer):
    """Serializer de SnapshotInversor — EXCLUI payload_bruto (T-2-07)."""

    class Meta:
        model = SnapshotInversor
        fields = [
            'id', 'coletado_em', 'data_medicao', 'estado',
            'pac_kw', 'energia_hoje_kwh', 'energia_total_kwh',
            'soc_bateria', 'strings_mppt',
            'tensao_ac_v', 'corrente_ac_a',
            'tensao_dc_v', 'corrente_dc_a',
            'frequencia_hz', 'temperatura_c',
        ]
        # payload_bruto EXCLUIDO — dados brutos do provedor (T-2-07)


class InversorListSerializer(serializers.ModelSerializer):
    """Serializer de listagem de inversores (INV-01)."""

    usina_nome = serializers.CharField(source='usina.nome', read_only=True)

    class Meta:
        model = Inversor
        fields = [
            'id', 'usina', 'usina_nome', 'id_inversor_provedor',
            'numero_serie', 'modelo', 'criado_em',
        ]


class InversorDetalheSerializer(serializers.ModelSerializer):
    """Serializer de detalhe de inversor — inclui ultimo snapshot completo (INV-02)."""

    usina_nome = serializers.CharField(source='usina.nome', read_only=True)
    ultimo_snapshot = SnapshotInversorSerializer(read_only=True)

    class Meta:
        model = Inversor
        fields = [
            'id', 'usina', 'usina_nome', 'id_inversor_provedor',
            'numero_serie', 'modelo', 'ultimo_snapshot', 'criado_em',
        ]
