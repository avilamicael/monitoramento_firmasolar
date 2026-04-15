"""
Views para gestão de CredencialProvedor via API REST.

Todos os endpoints exigem is_staff=True.
"""
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers.provedores import (
    CredencialProvedorReadSerializer,
    CredencialProvedorWriteSerializer,
)
from provedores.campos import (
    CAMPOS_POR_PROVEDOR,
    INTERVALO_MINIMO_MINUTOS,
    PROVEDORES_TOKEN_MANUAL,
)
from provedores.models import CredencialProvedor


class ProvedoresMetaView(APIView):
    """
    GET /api/provedores/meta/ — metadados para o frontend montar forms dinâmicos.

    Estrutura:
        {
            "provedores": [
                {
                    "valor": "solis",
                    "label": "Solis Cloud",
                    "campos": [{"chave": "api_key", "label": "API Key", "tipo": "texto"}, ...],
                    "usa_token_manual": false
                },
                ...
            ],
            "intervalo_minimo_minutos": 30
        }
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        provedores = []
        for valor, label in CredencialProvedor.PROVEDORES:
            campos = [
                {'chave': chave, 'label': label_campo, 'tipo': tipo}
                for chave, label_campo, tipo in CAMPOS_POR_PROVEDOR.get(valor, [])
            ]
            provedores.append({
                'valor': valor,
                'label': label,
                'campos': campos,
                'usa_token_manual': valor in PROVEDORES_TOKEN_MANUAL,
            })
        return Response({
            'provedores': provedores,
            'intervalo_minimo_minutos': INTERVALO_MINIMO_MINUTOS,
        })


class CredencialProvedorViewSet(viewsets.ModelViewSet):
    """
    CRUD de CredencialProvedor — restrito a staff.

    Lista → GET /api/provedores/
    Detalhe → GET /api/provedores/{id}/
    Criar → POST /api/provedores/
    Atualizar → PATCH /api/provedores/{id}/
    Remover → DELETE /api/provedores/{id}/

    Action extra:
        POST /api/provedores/{id}/forcar-coleta/ — dispara coleta imediata.
    """
    permission_classes = [IsAdminUser]
    queryset = CredencialProvedor.objects.all().order_by('provedor')

    def get_serializer_class(self):
        if self.action in {'create', 'update', 'partial_update'}:
            return CredencialProvedorWriteSerializer
        return CredencialProvedorReadSerializer

    def create(self, request, *args, **kwargs):
        write = CredencialProvedorWriteSerializer(data=request.data)
        write.is_valid(raise_exception=True)
        instance = write.save()
        read = CredencialProvedorReadSerializer(instance)
        return Response(read.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        write = CredencialProvedorWriteSerializer(instance, data=request.data, partial=partial)
        write.is_valid(raise_exception=True)
        instance = write.save()
        read = CredencialProvedorReadSerializer(instance)
        return Response(read.data)

    @action(detail=True, methods=['post'], url_path='forcar-coleta')
    def forcar_coleta(self, request, pk=None):
        """Dispara coleta imediata para este provedor (só se estiver ativo)."""
        credencial = self.get_object()
        if not credencial.ativo:
            return Response(
                {'detail': 'Provedor está inativo. Ative antes de forçar coleta.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from coleta.tasks import coletar_dados_provedor
        task = coletar_dados_provedor.delay(str(credencial.id))
        return Response({'task_id': task.id, 'detail': 'Coleta disparada.'})
