from django.db.models import Avg, Count, F, Q
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from usinas.models import Inversor, Usina
from api.serializers.analytics import UsinaMapaSerializer


class PotenciaMediaView(APIView):
    """
    GET /api/analytics/potencia/
    ANA-01: potencia media geral + agrupada por provedor.
    Fonte: Usina.ultimo_snapshot.potencia_kw (D-02).
    Exclui usinas sem snapshot do calculo.
    Sem N+1: select_related('ultimo_snapshot') + Avg via ORM.
    """

    def get(self, request):
        qs = (
            Usina.objects
            .filter(ativo=True, ultimo_snapshot__isnull=False)
            .select_related('ultimo_snapshot')
        )

        resultado = qs.aggregate(media_geral=Avg('ultimo_snapshot__potencia_kw'))
        media_geral = resultado['media_geral']

        por_provedor = list(
            qs
            .values('provedor')
            .annotate(
                media_kw=Avg('ultimo_snapshot__potencia_kw'),
                usinas_ativas=Count('id'),
            )
            .order_by('provedor')
        )

        return Response({
            'media_geral_kw': media_geral,
            'por_provedor': por_provedor,
        })


class RankingFabricantesView(APIView):
    """
    GET /api/analytics/ranking-fabricantes/
    ANA-02: top 5 provedores por inversores ativos.
    Criterio de ativo: ultimo_snapshot nao null E pac_kw > 0 (D-03).
    Usa values(provedor=F('usina__provedor')) para evitar chave usina__provedor nos dicts.
    """

    def get(self, request):
        ranking = list(
            Inversor.objects
            .values(provedor=F('usina__provedor'))
            .annotate(
                inversores_ativos=Count(
                    'id',
                    filter=Q(
                        ultimo_snapshot__isnull=False,
                        ultimo_snapshot__pac_kw__gt=0,
                    )
                )
            )
            .order_by('-inversores_ativos')[:5]
        )

        return Response({'ranking': ranking})


class MapaUsinasView(generics.ListAPIView):
    """
    GET /api/analytics/mapa/
    ANA-03: todas as usinas com lat/lng, provedor e status.
    Sem paginacao — frontend precisa de todos os pontos de uma vez.
    Retorna array plano (ListAPIView padrao).
    select_related('ultimo_snapshot') evita N+1 no SerializerMethodField de status.
    """

    serializer_class = UsinaMapaSerializer
    pagination_class = None

    def get_queryset(self):
        return (
            Usina.objects
            .select_related('ultimo_snapshot')
            .order_by('nome')
        )
