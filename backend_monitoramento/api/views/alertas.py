from rest_framework import viewsets

from alertas.models import Alerta
from api.serializers.alertas import (
    AlertaListSerializer,
    AlertaDetalheSerializer,
    AlertaPatchSerializer,
)
from api.filters.alertas import AlertaFilterSet


class AlertaViewSet(viewsets.ModelViewSet):
    """
    ViewSet de Alertas.

    Metodos permitidos: GET (list/detail), PATCH (estado e anotacoes).
    POST e DELETE desabilitados — alertas sao criados exclusivamente pela coleta automatica (T-2-09).
    """

    # POST e DELETE retornam 405 — alertas sao geridos pela coleta (T-2-09)
    http_method_names = ['get', 'patch', 'head', 'options']
    filterset_class = AlertaFilterSet

    def get_queryset(self):
        """
        select_related('usina__garantia') evita N+1 no calculo de com_garantia (T-2-10).
        select_related('catalogo_alarme') evita N+1 no detalhe.
        """
        return Alerta.objects.select_related(
            'usina', 'usina__garantia', 'catalogo_alarme'
        ).order_by('-inicio')

    def get_serializer_class(self):
        if self.action == 'list':
            return AlertaListSerializer
        if self.action == 'partial_update':
            return AlertaPatchSerializer
        return AlertaDetalheSerializer
