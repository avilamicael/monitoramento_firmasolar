from rest_framework import serializers

from notificacoes.models import Notificacao


class NotificacaoSerializer(serializers.ModelSerializer):
    lida = serializers.SerializerMethodField()

    class Meta:
        model = Notificacao
        fields = [
            'id', 'titulo', 'mensagem', 'tipo', 'nivel',
            'link', 'apenas_staff', 'criado_em', 'lida',
        ]
        read_only_fields = fields

    def get_lida(self, obj) -> bool:
        """True se existe registro de leitura para o usuário do request.

        Requer annotate(_lida=Exists(...)) no queryset para evitar N+1.
        Fallback: consulta direta caso o annotate não esteja presente.
        """
        if hasattr(obj, '_lida'):
            return bool(obj._lida)
        user = self.context.get('request').user if self.context.get('request') else None
        if user is None or not user.is_authenticated:
            return False
        return obj.leituras.filter(usuario=user).exists()
