from rest_framework import serializers

from coleta.models import ConfiguracaoSistema


class ConfiguracaoSistemaSerializer(serializers.ModelSerializer):
    """Serializer para leitura e atualização da configuração global (singleton)."""

    class Meta:
        model = ConfiguracaoSistema
        fields = [
            'dias_sem_comunicacao_pausar',
            'meses_garantia_padrao',
            'dias_aviso_garantia_proxima',
            'dias_aviso_garantia_urgente',
            'atualizado_em',
        ]
        read_only_fields = ['atualizado_em']

    def validate(self, attrs):
        proxima = attrs.get(
            'dias_aviso_garantia_proxima',
            self.instance.dias_aviso_garantia_proxima if self.instance else 30,
        )
        urgente = attrs.get(
            'dias_aviso_garantia_urgente',
            self.instance.dias_aviso_garantia_urgente if self.instance else 7,
        )
        if urgente >= proxima:
            raise serializers.ValidationError({
                'dias_aviso_garantia_urgente':
                    'O aviso urgente deve ser menor que o aviso prévio (ex: urgente=7, prévio=30).',
            })
        return attrs
