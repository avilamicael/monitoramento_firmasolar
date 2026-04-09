from rest_framework import serializers
from coleta.models import LogColeta


class LogColetaSerializer(serializers.ModelSerializer):
    # credencial.provedor é CharField com choices (ex: 'solis'), nao FK.
    # get_provedor_display() retorna o label legivel ('Solis Cloud', etc.)
    provedor_nome = serializers.SerializerMethodField()

    def get_provedor_nome(self, obj) -> str:
        return obj.credencial.get_provedor_display()

    class Meta:
        model = LogColeta
        fields = [
            'id',
            'provedor_nome',
            'status',
            'usinas_coletadas',
            'inversores_coletados',
            'alertas_sincronizados',
            'detalhe_erro',
            'duracao_ms',
            'iniciado_em',
        ]
        read_only_fields = fields
