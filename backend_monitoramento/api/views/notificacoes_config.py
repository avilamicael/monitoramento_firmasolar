"""
Endpoints de configuração de canais de notificação — staff only.

Broadcast global: todos os destinatários recebem as notificações dos níveis marcados.
No futuro: preferências por usuário.
"""
from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser

from api.serializers.notificacoes_config import ConfiguracaoNotificacaoSerializer
from notificacoes.models import ConfiguracaoNotificacao


class ConfiguracaoNotificacaoViewSet(viewsets.ModelViewSet):
    """
    CRUD de canais de notificação.

    GET    /api/notificacoes-config/        — lista (email, whatsapp, webhook)
    GET    /api/notificacoes-config/{id}/   — detalhe
    POST   /api/notificacoes-config/        — cria canal (se ainda não existe)
    PATCH  /api/notificacoes-config/{id}/   — atualiza canal
    DELETE /api/notificacoes-config/{id}/   — remove

    O modelo já garante unicidade por canal (unique=True).
    """
    permission_classes = [IsAdminUser]
    serializer_class = ConfiguracaoNotificacaoSerializer
    queryset = ConfiguracaoNotificacao.objects.all().order_by('canal')
