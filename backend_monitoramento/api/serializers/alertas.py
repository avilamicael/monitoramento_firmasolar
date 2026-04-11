from rest_framework import serializers
from alertas.models import Alerta
from usinas.models import GarantiaUsina


class AlertaListSerializer(serializers.ModelSerializer):
    """Serializer de listagem de alertas — inclui com_garantia (ALT-04)."""

    com_garantia = serializers.SerializerMethodField()
    usina_nome = serializers.CharField(source='usina.nome', read_only=True)

    class Meta:
        model = Alerta
        fields = [
            'id', 'usina', 'usina_nome', 'origem', 'categoria',
            'mensagem', 'nivel', 'estado', 'inicio', 'fim',
            'com_garantia', 'criado_em', 'atualizado_em',
        ]
        # payload_bruto EXCLUIDO (T-2-07)
        # notificacao_enviada EXCLUIDO — campo interno de controle

    def get_com_garantia(self, obj) -> bool:
        """
        ALT-04: indica se a usina do alerta tem garantia ativa no momento.
        Depende de select_related('usina__garantia') no queryset para evitar N+1 (T-2-10).
        """
        try:
            garantia = obj.usina.garantia
            return garantia.ativa
        except GarantiaUsina.DoesNotExist:
            return False


class AlertaDetalheSerializer(serializers.ModelSerializer):
    """Serializer de detalhe de alerta — inclui todos os campos e com_garantia (ALT-02, ALT-04)."""

    com_garantia = serializers.SerializerMethodField()
    usina_nome = serializers.CharField(source='usina.nome', read_only=True)
    usina_provedor = serializers.CharField(source='usina.provedor', read_only=True)
    usina_id_provedor = serializers.CharField(source='usina.id_usina_provedor', read_only=True)

    class Meta:
        model = Alerta
        fields = [
            'id', 'usina', 'usina_nome', 'usina_provedor', 'usina_id_provedor',
            'origem', 'categoria',
            'catalogo_alarme', 'id_alerta_provedor', 'equipamento_sn',
            'mensagem', 'nivel', 'estado', 'inicio', 'fim',
            'sugestao', 'anotacoes', 'com_garantia',
            'criado_em', 'atualizado_em',
        ]
        # payload_bruto EXCLUIDO (T-2-07)
        # notificacao_enviada EXCLUIDO — campo interno de controle

    def get_com_garantia(self, obj) -> bool:
        """ALT-04: indica se a usina do alerta tem garantia ativa no momento."""
        try:
            garantia = obj.usina.garantia
            return garantia.ativa
        except GarantiaUsina.DoesNotExist:
            return False


class AlertaPatchSerializer(serializers.ModelSerializer):
    """
    Serializer de escrita para PATCH /api/alertas/{id}/ — apenas estado e anotacoes (ALT-03).
    Restringe mass assignment: campos extras sao ignorados pelo DRF (T-2-08).
    """

    class Meta:
        model = Alerta
        fields = ['estado', 'anotacoes']
