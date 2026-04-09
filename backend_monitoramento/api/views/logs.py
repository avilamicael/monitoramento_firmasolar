from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from coleta.models import LogColeta
from api.serializers import LogColetaSerializer
from api.pagination import PaginacaoSnapshots


class LogColetaListView(ListAPIView):
    """
    GET /api/coleta/logs/
    Retorna ultimos ciclos de coleta com status e timestamp.
    Ordenacao: mais recente primeiro (definida pelo Meta.ordering do model).
    """
    serializer_class = LogColetaSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PaginacaoSnapshots  # criada no Plan 01; page_size=100

    def get_queryset(self):
        # select_related('credencial') evita N+1 em get_provedor_display()
        # credencial.provedor é CharField — sem join extra necessario
        return LogColeta.objects.select_related('credencial').all()
