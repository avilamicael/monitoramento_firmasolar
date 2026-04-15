"""
Endpoint /api/auth/me/ — retorna o perfil do usuário autenticado.

Usado pelo frontend para popular o contexto de auth com dados confiáveis
(email, nome, is_staff) a cada carga de página, já que o JWT padrão do
SimpleJWT não inclui esses campos como claims.
"""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


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
