from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from usinas.models import Inversor
from api.serializers.inversores import (
    InversorListSerializer,
    InversorDetalheSerializer,
    SnapshotInversorSerializer,
)
from api.filters.inversores import InversorFilterSet
from api.pagination import PaginacaoSnapshots


class InversorViewSet(viewsets.ModelViewSet):
    """
    ViewSet de Inversores — read-only + snapshots.

    POST, PUT e DELETE desabilitados — inversores sao criados exclusivamente pela coleta automatica.
    Acoes customizadas:
    - snapshots: GET /api/inversores/{id}/snapshots/ — historico paginado (INV-03)
    """

    # POST, PUT, DELETE retornam 405 — inversores sao geridos pela coleta (T-2-09)
    http_method_names = ['get', 'head', 'options']
    filterset_class = InversorFilterSet

    def get_queryset(self):
        """Select related para evitar N+1 em usina_nome e ultimo_snapshot."""
        return Inversor.objects.select_related(
            'usina', 'ultimo_snapshot'
        ).order_by('usina__nome', 'numero_serie')

    def get_serializer_class(self):
        if self.action == 'list':
            return InversorListSerializer
        return InversorDetalheSerializer

    @action(detail=True, methods=['get'], url_path='snapshots')
    def snapshots(self, request, pk=None):
        """INV-03: Historico paginado de snapshots do inversor."""
        inversor = self.get_object()
        qs = inversor.snapshots.order_by('-coletado_em')
        paginator = PaginacaoSnapshots()
        page = paginator.paginate_queryset(qs, request)
        serializer = SnapshotInversorSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
