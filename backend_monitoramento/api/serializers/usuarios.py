from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UsuarioReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'is_staff', 'is_active', 'is_superuser', 'last_login', 'date_joined',
        ]
        read_only_fields = fields


class UsuarioWriteSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=False, allow_blank=True,
        min_length=6,
        help_text='Obrigatório na criação. Em edição, deixe em branco para manter a senha atual.',
    )

    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'is_staff', 'is_active', 'password',
        ]

    def validate_username(self, valor):
        qs = User.objects.filter(username=valor)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Este nome de usuário já está em uso.')
        return valor

    def validate_email(self, valor):
        if not valor:
            return valor
        qs = User.objects.filter(email=valor)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Este e-mail já está em uso.')
        return valor

    def validate(self, attrs):
        if not self.instance and not attrs.get('password'):
            raise serializers.ValidationError({
                'password': 'Senha é obrigatória ao criar um novo usuário.',
            })
        return attrs

    def create(self, validated):
        password = validated.pop('password')
        user = User(**validated)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated):
        password = validated.pop('password', None)
        for campo, valor in validated.items():
            setattr(instance, campo, valor)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
