from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from usinas.models import Usina, GarantiaUsina
from api.serializers.usinas import (
    UsinaListSerializer,
    UsinaDetalheSerializer,
    UsinaPatchSerializer,
    SnapshotUsinaSerializer,
)
from api.serializers.garantias import GarantiaUsinaSerializer, GarantiaUsinaEscritaSerializer
from api.filters.usinas import UsinaFilterSet
from api.pagination import PaginacaoSnapshots


class UsinaViewSet(viewsets.ModelViewSet):
    """
    ViewSet de Usinas.

    Metodos permitidos: GET (list/detail), PATCH (nome e capacidade).
    POST e DELETE desabilitados — usinas sao criadas exclusivamente pela coleta automatica (T-2-05).

    Acoes customizadas:
    - snapshots: GET /api/usinas/{id}/snapshots/ — historico paginado (USN-05)
    - garantia:  PUT /api/usinas/{id}/garantia/  — upsert de garantia (GAR-02)
    """

    # POST e DELETE retornam 405 (T-2-05)
    # PUT e permitido apenas para a action 'garantia' — nao para o recurso principal
    http_method_names = ['get', 'patch', 'put', 'head', 'options']
    filterset_class = UsinaFilterSet

    def get_queryset(self):
        """
        Otimizacao de queries via select_related e prefetch_related.
        Evita N+1 para garantia (select_related) e inversores (prefetch_related).
        """
        return (
            Usina.objects
            .select_related('ultimo_snapshot', 'garantia')
            .prefetch_related('inversores')
            .order_by('nome')
        )

    def update(self, request, *args, **kwargs):
        """
        Bloqueia PUT /api/usinas/{id}/ — usinas nao sao substituidas via API.
        PATCH (partial=True) e permitido e delegado ao comportamento padrao do DRF.
        PUT e permitido apenas na action 'garantia' (url_path='garantia').
        """
        if not kwargs.get('partial', False):
            return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
        return super().update(request, *args, **kwargs)

    def get_serializer_class(self):
        if self.action == 'list':
            return UsinaListSerializer
        if self.action == 'partial_update':
            return UsinaPatchSerializer
        return UsinaDetalheSerializer

    @action(detail=True, methods=['get'], url_path='snapshots')
    def snapshots(self, request, pk=None):
        """USN-05: Historico paginado de snapshots da usina, ordenado do mais recente."""
        usina = self.get_object()
        qs = usina.snapshots.order_by('-coletado_em')
        paginator = PaginacaoSnapshots()
        page = paginator.paginate_queryset(qs, request)
        serializer = SnapshotUsinaSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @action(detail=True, methods=['put'], url_path='garantia')
    def garantia(self, request, pk=None):
        """
        GAR-02: Upsert de garantia da usina via PUT.
        Cria ou substitui a garantia existente (OneToOne garante unicidade).
        Retorna imediatamente data_fim e dias_restantes calculados (GAR-04).
        """
        usina = self.get_object()
        serializer = GarantiaUsinaEscritaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        garantia, _ = GarantiaUsina.objects.update_or_create(
            usina=usina,
            defaults=serializer.validated_data,
        )
        return Response(GarantiaUsinaSerializer(garantia).data)
