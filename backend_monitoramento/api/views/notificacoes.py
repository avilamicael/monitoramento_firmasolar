"""
Endpoints de notificações do painel.

- Visíveis para qualquer usuário autenticado.
- Notificações com apenas_staff=True só aparecem para is_staff.
- Estado "lida" é individual por usuário via NotificacaoLeitura.
"""
from django.db.models import Exists, OuterRef
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from api.serializers.notificacoes import NotificacaoSerializer
from notificacoes.models import Notificacao, NotificacaoLeitura


class NotificacaoViewSet(ReadOnlyModelViewSet):
    """
    GET /api/notificacoes/          — lista (pagina 20 por padrão)
        query params:
            apenas_nao_lidas=true   — filtra para não lidas
    GET /api/notificacoes/nao-lidas-count/ — {'count': N} para badge
    POST /api/notificacoes/{id}/marcar-lida/
    POST /api/notificacoes/marcar-todas-lidas/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = NotificacaoSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Notificacao.objects.all()
        # Filtra apenas_staff para não-staff
        if not user.is_staff:
            qs = qs.filter(apenas_staff=False)

        # Anotação "lida" = existe leitura deste user para esta notificação
        leitura_do_user = NotificacaoLeitura.objects.filter(
            usuario=user, notificacao=OuterRef('pk'),
        )
        qs = qs.annotate(_lida=Exists(leitura_do_user))

        if self.request.query_params.get('apenas_nao_lidas') == 'true':
            qs = qs.filter(_lida=False)

        return qs.order_by('-criado_em')

    @action(detail=False, methods=['get'], url_path='nao-lidas-count')
    def nao_lidas_count(self, request):
        user = request.user
        qs = Notificacao.objects.all()
        if not user.is_staff:
            qs = qs.filter(apenas_staff=False)
        leitura_do_user = NotificacaoLeitura.objects.filter(
            usuario=user, notificacao=OuterRef('pk'),
        )
        count = qs.annotate(_lida=Exists(leitura_do_user)).filter(_lida=False).count()
        return Response({'count': count})

    @action(detail=True, methods=['post'], url_path='marcar-lida')
    def marcar_lida(self, request, pk=None):
        notif = self.get_object()
        NotificacaoLeitura.objects.get_or_create(usuario=request.user, notificacao=notif)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['post'], url_path='marcar-todas-lidas')
    def marcar_todas_lidas(self, request):
        """Cria registros de leitura para TODAS as notificações visíveis ainda não lidas."""
        user = request.user
        visiveis = Notificacao.objects.all()
        if not user.is_staff:
            visiveis = visiveis.filter(apenas_staff=False)

        ja_lidas = NotificacaoLeitura.objects.filter(
            usuario=user, notificacao__in=visiveis,
        ).values_list('notificacao_id', flat=True)

        faltando = visiveis.exclude(pk__in=list(ja_lidas))
        NotificacaoLeitura.objects.bulk_create(
            [NotificacaoLeitura(usuario=user, notificacao=n) for n in faltando],
            ignore_conflicts=True,
        )
        return Response({'marcadas': faltando.count()})
