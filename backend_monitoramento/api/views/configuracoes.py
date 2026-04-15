from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from coleta.models import ConfiguracaoSistema
from api.serializers.configuracoes import ConfiguracaoSistemaSerializer


class ConfiguracaoSistemaView(APIView):
    """
    GET  /api/configuracoes/ — retorna a configuração atual.
    PUT  /api/configuracoes/ — atualiza todos os campos editáveis.
    PATCH /api/configuracoes/ — atualização parcial.

    Restrito a usuários staff (is_staff=True).
    Como é singleton, não há list/create nem id na URL.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        config = ConfiguracaoSistema.obter()
        return Response(ConfiguracaoSistemaSerializer(config).data)

    def put(self, request):
        return self._atualizar(request, partial=False)

    def patch(self, request):
        return self._atualizar(request, partial=True)

    def _atualizar(self, request, partial: bool):
        config = ConfiguracaoSistema.obter()
        serializer = ConfiguracaoSistemaSerializer(config, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
