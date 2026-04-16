"""
Endpoints de autenticação complementares ao SimpleJWT.

MeView             — /api/auth/me/              — perfil do usuário logado
GrafanaVerifyView   — /api/auth/grafana-verify/  — validação de cookie para nginx auth_request
"""
import logging

from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)
User = get_user_model()


class MeView(APIView):
    """GET /api/auth/me/ — dados do usuário do token."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        u = request.user
        return Response({
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'first_name': u.first_name,
            'last_name': u.last_name,
            'name': u.get_full_name() or u.username,
            'is_staff': u.is_staff,
            'is_superuser': u.is_superuser,
        })


class GrafanaVerifyView(APIView):
    """
    GET /api/auth/grafana-verify/ — chamado internamente pelo nginx via auth_request.

    Lê o cookie `fs_access_token` (setado pelo frontend no login),
    valida o JWT e retorna 200 com header X-Auth-User ou 401.

    Nginx usa o header X-Auth-User para autenticar no Grafana via auth proxy.
    Sem permission_classes do DRF — validação manual do cookie.
    """
    permission_classes = []
    authentication_classes = []

    def get(self, request):
        token = request.COOKIES.get('fs_access_token')
        if not token:
            return Response(status=401)
        try:
            from rest_framework_simplejwt.tokens import AccessToken
            validated = AccessToken(token)
            user = User.objects.get(pk=validated['user_id'])
            if not user.is_active:
                return Response(status=401)
            response = Response(status=200)
            response['X-Auth-User'] = user.username
            return response
        except Exception:
            return Response(status=401)
