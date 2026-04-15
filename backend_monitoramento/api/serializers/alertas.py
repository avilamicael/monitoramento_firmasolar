from rest_framework import serializers
from alertas.models import Alerta
from usinas.models import GarantiaUsina


def _categoria_efetiva(obj) -> str:
    """
    Categoria a ser exibida na UI.

    Para alertas internos: usa Alerta.categoria (preenchida na criação).
    Para alertas do provedor: cai no CatalogoAlarme.tipo (categorização determinística
    do catálogo), pois Alerta.categoria fica vazia por design — o enriquecimento
    automático foi removido em 1d305bf para evitar categorias erradas.
    """
    if obj.categoria:
        return obj.categoria
    catalogo = getattr(obj, 'catalogo_alarme', None)
    if catalogo and catalogo.tipo:
        return catalogo.tipo
    return ''


class AlertaListSerializer(serializers.ModelSerializer):
    """Serializer de listagem de alertas — inclui com_garantia (ALT-04)."""

    com_garantia = serializers.SerializerMethodField()
    usina_nome = serializers.CharField(source='usina.nome', read_only=True)
    categoria_efetiva = serializers.SerializerMethodField()

    class Meta:
        model = Alerta
        fields = [
            'id', 'usina', 'usina_nome', 'origem', 'categoria', 'categoria_efetiva',
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

    def get_categoria_efetiva(self, obj) -> str:
        return _categoria_efetiva(obj)


class AlertaDetalheSerializer(serializers.ModelSerializer):
    """Serializer de detalhe de alerta — inclui todos os campos e com_garantia (ALT-02, ALT-04)."""

    com_garantia = serializers.SerializerMethodField()
    usina_nome = serializers.CharField(source='usina.nome', read_only=True)
    usina_provedor = serializers.CharField(source='usina.provedor', read_only=True)
    usina_id_provedor = serializers.CharField(source='usina.id_usina_provedor', read_only=True)
    categoria_efetiva = serializers.SerializerMethodField()

    class Meta:
        model = Alerta
        fields = [
            'id', 'usina', 'usina_nome', 'usina_provedor', 'usina_id_provedor',
            'origem', 'categoria', 'categoria_efetiva',
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

    def get_categoria_efetiva(self, obj) -> str:
        return _categoria_efetiva(obj)


class AlertaPatchSerializer(serializers.ModelSerializer):
    """
    Serializer de escrita para PATCH /api/alertas/{id}/ — apenas estado e anotacoes (ALT-03).
    Restringe mass assignment: campos extras sao ignorados pelo DRF (T-2-08).
    """

    class Meta:
        model = Alerta
        fields = ['estado', 'anotacoes']
