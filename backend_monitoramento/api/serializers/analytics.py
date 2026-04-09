from rest_framework import serializers
from usinas.models import Usina


class UsinaMapaSerializer(serializers.ModelSerializer):
    """
    Serializer para o endpoint de mapa (ANA-03).
    Inclui lat/lng e status derivado do ultimo_snapshot.
    Usinas sem coordenadas retornam latitude=null, longitude=null — nao sao omitidas.
    """

    status = serializers.SerializerMethodField()

    class Meta:
        model = Usina
        fields = ['id', 'nome', 'provedor', 'latitude', 'longitude', 'ativo', 'status']

    def get_status(self, obj) -> str:
        """Status baseado no ultimo_snapshot.status — 'sem_dados' se ausente."""
        if obj.ultimo_snapshot is None:
            return 'sem_dados'
        return obj.ultimo_snapshot.status
