from rest_framework.response import Response
from rest_framework.views import APIView


class PingView(APIView):
    """Endpoint minimo para verificar autenticacao. Retorna 200 se token valido."""

    def get(self, request):
        return Response({'status': 'ok'})
