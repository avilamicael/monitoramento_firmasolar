from django.db.models import Case, IntegerField, When
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
        # Ordenação: nível (crítico → importante → aviso → info) e depois por data desc.
        # Garante que usuário sempre vê os alertas mais severos primeiro.
        return Alerta.objects.select_related(
            'usina', 'usina__garantia', 'catalogo_alarme'
        ).annotate(
            nivel_ordem=Case(
                When(nivel='critico', then=0),
                When(nivel='importante', then=1),
                When(nivel='aviso', then=2),
                When(nivel='info', then=3),
                default=4,
                output_field=IntegerField(),
            ),
        ).order_by('nivel_ordem', '-inicio')

    def get_serializer_class(self):
        if self.action == 'list':
            return AlertaListSerializer
        if self.action == 'partial_update':
            return AlertaPatchSerializer
        return AlertaDetalheSerializer
