"""
CRUD de usuários — restrito a staff.

Superusuários não podem ser editados/removidos por staff não-superusuário.
Um usuário não pode se remover.
"""
from django.contrib.auth import get_user_model
from rest_framework import status, viewsets
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from api.serializers.usuarios import UsuarioReadSerializer, UsuarioWriteSerializer

User = get_user_model()


class UsuarioViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    queryset = User.objects.all().order_by('username')

    def get_serializer_class(self):
        if self.action in {'create', 'update', 'partial_update'}:
            return UsuarioWriteSerializer
        return UsuarioReadSerializer

    def create(self, request, *args, **kwargs):
        write = UsuarioWriteSerializer(data=request.data)
        write.is_valid(raise_exception=True)
        user = write.save()
        return Response(UsuarioReadSerializer(user).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        if instance.is_superuser and not request.user.is_superuser:
            return Response(
                {'detail': 'Apenas superusuários podem editar outros superusuários.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        write = UsuarioWriteSerializer(instance, data=request.data, partial=partial)
        write.is_valid(raise_exception=True)
        user = write.save()
        return Response(UsuarioReadSerializer(user).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.pk == request.user.pk:
            return Response(
                {'detail': 'Você não pode remover sua própria conta.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if instance.is_superuser and not request.user.is_superuser:
            return Response(
                {'detail': 'Apenas superusuários podem remover outros superusuários.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
