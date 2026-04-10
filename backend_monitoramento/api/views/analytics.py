import datetime

from django.db.models import Avg, Count, F, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from alertas.models import Alerta
from usinas.models import Inversor, SnapshotUsina, Usina
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
    ANA-02: top 5 provedores por inversores monitorados.
    Criterio: inversor com ultimo_snapshot nao null (esta sendo coletado).
    Nota: pac_kw > 0 nao funciona para microinversores Hoymiles cujos dados
    eletricos individuais nao sao populados pela API (dados vem agregados na usina).
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


class AlertasResumoView(APIView):
    """
    GET /api/analytics/alertas-resumo/
    Contagem de alertas ativos por nível e estado.
    Retorna também total de alertas em atendimento.
    """

    def get(self, request):
        ativos = Alerta.objects.filter(estado='ativo')

        por_nivel = dict(
            ativos.values('nivel')
            .annotate(total=Count('id'))
            .values_list('nivel', 'total')
        )

        por_estado = dict(
            Alerta.objects.exclude(estado='resolvido')
            .values('estado')
            .annotate(total=Count('id'))
            .values_list('estado', 'total')
        )

        return Response({
            'critico': por_nivel.get('critico', 0),
            'importante': por_nivel.get('importante', 0),
            'aviso': por_nivel.get('aviso', 0),
            'info': por_nivel.get('info', 0),
            'total_ativos': sum(por_nivel.values()),
            'em_atendimento': por_estado.get('em_atendimento', 0),
        })


class GeracaoDiariaView(APIView):
    """
    GET /api/analytics/geracao-diaria/?dias=30
    Energia gerada por dia (soma de energia_hoje_kwh de todos os snapshots do dia).
    Retorna últimos N dias (default 30).
    """

    def get(self, request):
        dias = min(int(request.query_params.get('dias', 30)), 90)
        data_inicio = timezone.now() - datetime.timedelta(days=dias)

        por_dia = list(
            SnapshotUsina.objects
            .filter(coletado_em__gte=data_inicio)
            .annotate(dia=TruncDate('coletado_em'))
            .values('dia')
            .annotate(
                energia_kwh=Sum('energia_hoje_kwh'),
                usinas_coletadas=Count('usina', distinct=True),
            )
            .order_by('dia')
        )

        # Converter date para string ISO
        resultado = [
            {
                'dia': item['dia'].isoformat(),
                'energia_kwh': round(item['energia_kwh'] or 0, 2),
                'usinas_coletadas': item['usinas_coletadas'],
            }
            for item in por_dia
        ]

        return Response({
            'dias': dias,
            'geracao': resultado,
        })


class EnergiaResumoView(APIView):
    """
    GET /api/analytics/energia-resumo/
    Soma total de energia de todas as usinas (via ultimo_snapshot).
    Inclui energia_hoje, energia_mes e energia_total.
    """

    def get(self, request):
        qs = (
            Usina.objects
            .filter(ativo=True, ultimo_snapshot__isnull=False)
            .select_related('ultimo_snapshot')
        )

        totais = qs.aggregate(
            energia_hoje_kwh=Sum('ultimo_snapshot__energia_hoje_kwh'),
            energia_mes_kwh=Sum('ultimo_snapshot__energia_mes_kwh'),
            energia_total_kwh=Sum('ultimo_snapshot__energia_total_kwh'),
            usinas_ativas=Count('id'),
        )

        return Response({
            'energia_hoje_kwh': round(totais['energia_hoje_kwh'] or 0, 2),
            'energia_mes_kwh': round(totais['energia_mes_kwh'] or 0, 2),
            'energia_total_kwh': round(totais['energia_total_kwh'] or 0, 2),
            'usinas_ativas': totais['usinas_ativas'],
        })
