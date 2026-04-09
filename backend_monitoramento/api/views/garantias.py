import datetime

from django.utils import timezone
from rest_framework import generics

from usinas.models import GarantiaUsina
from api.serializers.garantias import GarantiaUsinaSerializer


class GarantiaListView(generics.ListAPIView):
    """
    GET /api/garantias/ — lista todas as garantias com filtro de vigencia (D-05, GAR-03).

    Filtro via query param ?filtro=ativas|vencendo|vencidas.

    CRITICO: data_fim e @property no model — NAO filtrar via ORM direto.
    A filtragem e feita em Python apos carregar os IDs (volume controlado:
    no maximo uma GarantiaUsina por usina).
    """

    serializer_class = GarantiaUsinaSerializer

    def get_queryset(self):
        qs = GarantiaUsina.objects.select_related('usina').order_by('usina__nome')
        filtro = self.request.query_params.get('filtro')

        if not filtro:
            return qs

        hoje = timezone.now().date()
        todas = list(qs)

        if filtro == 'ativas':
            ids = [g.id for g in todas if g.data_fim >= hoje]
        elif filtro == 'vencidas':
            ids = [g.id for g in todas if g.data_fim < hoje]
        elif filtro == 'vencendo':
            limite = hoje + datetime.timedelta(days=30)
            ids = [g.id for g in todas if hoje <= g.data_fim <= limite]
        else:
            # Valor de filtro nao reconhecido — retorna tudo sem erro
            return qs

        return (
            GarantiaUsina.objects
            .select_related('usina')
            .filter(id__in=ids)
            .order_by('usina__nome')
        )
