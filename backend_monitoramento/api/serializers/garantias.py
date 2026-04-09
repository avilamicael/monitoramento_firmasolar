from rest_framework import serializers
from usinas.models import GarantiaUsina


class GarantiaUsinaSerializer(serializers.ModelSerializer):
    """
    Serializer de leitura de GarantiaUsina.
    Inclui data_fim, dias_restantes e ativa — calculados via properties do model (GAR-04).
    Usa SerializerMethodField porque sao @property, nao colunas reais do banco.
    """

    data_fim = serializers.SerializerMethodField()
    dias_restantes = serializers.SerializerMethodField()
    ativa = serializers.SerializerMethodField()
    usina_id = serializers.UUIDField(source='usina.id', read_only=True)
    usina_nome = serializers.CharField(source='usina.nome', read_only=True)

    class Meta:
        model = GarantiaUsina
        fields = [
            'id',
            'usina_id',
            'usina_nome',
            'data_inicio',
            'meses',
            'observacoes',
            'data_fim',
            'dias_restantes',
            'ativa',
            'criado_em',
            'atualizado_em',
        ]

    def get_data_fim(self, obj) -> str:
        """Retorna data_fim em formato ISO 8601 (YYYY-MM-DD)."""
        return obj.data_fim.isoformat()

    def get_dias_restantes(self, obj) -> int:
        """Retorna dias restantes ate o vencimento (0 se ja vencida)."""
        return obj.dias_restantes

    def get_ativa(self, obj) -> bool:
        """Retorna True se garantia ainda vigente."""
        return obj.ativa


class GarantiaUsinaEscritaSerializer(serializers.Serializer):
    """
    Serializer de escrita para PUT /api/usinas/{id}/garantia/ (GAR-02).
    Aceita apenas os campos editaveis — nao usa ModelSerializer para evitar
    mass assignment de campos nao permitidos.
    """

    data_inicio = serializers.DateField()
    meses = serializers.IntegerField(min_value=1)
    observacoes = serializers.CharField(required=False, default='', allow_blank=True)
