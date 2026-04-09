# Pacote de views por dominio (D-01)
from rest_framework.response import Response
from rest_framework.views import APIView

from .logs import LogColetaListView
from .analytics import PotenciaMediaView, RankingFabricantesView, MapaUsinasView


class PingView(APIView):
    """Endpoint minimo para verificar autenticacao. Retorna 200 se token valido."""

    def get(self, request):
        return Response({'status': 'ok'})
