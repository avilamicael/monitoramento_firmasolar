"""
Serializers para gestão de credenciais de provedores via API REST.

Regras de segurança:
- O campo `credenciais_enc` nunca sai no wire.
- Em listagem/detalhe, as credenciais são retornadas mascaradas (3 primeiros +
  3 últimos caracteres de cada valor).
- Na escrita, campos em plain text (campo_1..4, token_jwt) são criptografados
  antes de persistir. O serializer nunca expõe esses campos na resposta.
"""
from datetime import datetime, timezone as dt_tz

from rest_framework import serializers

from coleta.models import LogColeta
from provedores.campos import (
    CAMPOS_POR_PROVEDOR,
    INTERVALO_MINIMO_MINUTOS,
    PROVEDORES_TOKEN_MANUAL,
)
from provedores.cripto import criptografar_credenciais, descriptografar_credenciais
from provedores.models import CacheTokenProvedor, CredencialProvedor


def _mascarar(valor: str) -> str:
    valor = str(valor)
    if len(valor) <= 6:
        return '***'
    return f'{valor[:3]}...{valor[-3:]}'


def _credenciais_preview(credencial: CredencialProvedor) -> dict | None:
    """Descriptografa e retorna credenciais mascaradas por chave."""
    if not credencial.credenciais_enc:
        return None
    try:
        dados = descriptografar_credenciais(credencial.credenciais_enc)
    except Exception:
        return None
    return {chave: _mascarar(valor) for chave, valor in dados.items()}


def _token_status(credencial: CredencialProvedor) -> dict | None:
    """Retorna dados do token JWT (expiração, dias restantes) para provedores manuais."""
    if credencial.provedor not in PROVEDORES_TOKEN_MANUAL:
        return None
    try:
        cache = credencial.cache_token
    except CacheTokenProvedor.DoesNotExist:
        return {'configurado': False}

    try:
        dados = descriptografar_credenciais(cache.dados_token_enc)
        token = dados.get('token', '')
    except Exception:
        return {'configurado': False, 'erro': 'Erro ao ler token'}

    if not token:
        return {'configurado': False}

    try:
        from provedores.solarman.autenticacao import decodificar_jwt_payload
        payload = decodificar_jwt_payload(token)
        exp = payload.get('exp', 0)
    except Exception:
        return {'configurado': True, 'expira_em': None, 'dias_restantes': None}

    if not exp:
        return {'configurado': True, 'expira_em': None, 'dias_restantes': None}

    expira_em = datetime.fromtimestamp(exp, tz=dt_tz.utc)
    dias_restantes = (expira_em - datetime.now(dt_tz.utc)).days
    return {
        'configurado': True,
        'expira_em': expira_em.isoformat(),
        'dias_restantes': dias_restantes,
    }


def _ultima_coleta(credencial: CredencialProvedor) -> dict | None:
    log = (
        LogColeta.objects
        .filter(credencial=credencial)
        .order_by('-iniciado_em')
        .first()
    )
    if log is None:
        return None
    return {
        'status': log.status,
        'usinas_coletadas': log.usinas_coletadas,
        'inversores_coletados': log.inversores_coletados,
        'alertas_sincronizados': log.alertas_sincronizados,
        'duracao_ms': log.duracao_ms,
        'iniciado_em': log.iniciado_em.isoformat(),
        'detalhe_erro': log.detalhe_erro,
    }


class CredencialProvedorReadSerializer(serializers.ModelSerializer):
    """Serializer de leitura. Nunca expõe credenciais em texto puro."""

    provedor_display = serializers.CharField(source='get_provedor_display', read_only=True)
    credenciais_preview = serializers.SerializerMethodField()
    token_status = serializers.SerializerMethodField()
    ultima_coleta = serializers.SerializerMethodField()
    usa_token_manual = serializers.SerializerMethodField()

    class Meta:
        model = CredencialProvedor
        fields = [
            'id', 'provedor', 'provedor_display',
            'ativo', 'precisa_atencao', 'intervalo_coleta_minutos',
            'credenciais_preview', 'token_status', 'usa_token_manual',
            'ultima_coleta', 'criado_em', 'atualizado_em',
        ]
        read_only_fields = fields

    def get_credenciais_preview(self, obj) -> dict | None:
        return _credenciais_preview(obj)

    def get_token_status(self, obj) -> dict | None:
        return _token_status(obj)

    def get_ultima_coleta(self, obj) -> dict | None:
        return _ultima_coleta(obj)

    def get_usa_token_manual(self, obj) -> bool:
        return obj.provedor in PROVEDORES_TOKEN_MANUAL


class CredencialProvedorWriteSerializer(serializers.ModelSerializer):
    """
    Serializer de escrita.

    Aceita `credenciais` como dict de chave→valor (ex: {'api_key': 'xxx', 'app_secret': 'yyy'})
    e criptografa antes de persistir. Opcionalmente aceita `token_jwt` (só para
    provedores em PROVEDORES_TOKEN_MANUAL).
    """
    credenciais = serializers.DictField(
        child=serializers.CharField(allow_blank=False, trim_whitespace=True),
        required=False,
        write_only=True,
        help_text='Dicionário chave→valor conforme CAMPOS_POR_PROVEDOR. '
                  'Opcional em PATCH — se omitido, mantém as credenciais atuais.',
    )
    token_jwt = serializers.CharField(
        required=False, write_only=True, allow_blank=True, trim_whitespace=True,
    )

    class Meta:
        model = CredencialProvedor
        fields = [
            'provedor', 'ativo', 'precisa_atencao',
            'intervalo_coleta_minutos', 'credenciais', 'token_jwt',
        ]

    def validate_intervalo_coleta_minutos(self, valor):
        if valor < INTERVALO_MINIMO_MINUTOS:
            raise serializers.ValidationError(
                f'Intervalo mínimo é {INTERVALO_MINIMO_MINUTOS} minutos.'
            )
        return valor

    def validate_provedor(self, valor):
        if valor not in CAMPOS_POR_PROVEDOR:
            raise serializers.ValidationError(
                f'Provedor "{valor}" não reconhecido.'
            )
        return valor

    def validate(self, attrs):
        # Na criação, credenciais são obrigatórias.
        if self.instance is None and not attrs.get('credenciais'):
            raise serializers.ValidationError({
                'credenciais': 'Credenciais são obrigatórias ao criar uma nova integração.',
            })

        credenciais = attrs.get('credenciais')
        if credenciais:
            provedor = attrs.get('provedor') or (self.instance.provedor if self.instance else None)
            esperadas = {chave for chave, _label, _tipo in CAMPOS_POR_PROVEDOR.get(provedor, [])}
            faltando = esperadas - set(credenciais.keys())
            extras = set(credenciais.keys()) - esperadas
            if faltando:
                raise serializers.ValidationError({
                    'credenciais': f'Faltando campos: {", ".join(sorted(faltando))}',
                })
            if extras:
                raise serializers.ValidationError({
                    'credenciais': f'Campos não reconhecidos para {provedor}: {", ".join(sorted(extras))}',
                })

        # Token JWT só faz sentido para provedores manuais.
        token = attrs.get('token_jwt')
        if token:
            provedor = attrs.get('provedor') or (self.instance.provedor if self.instance else None)
            if provedor not in PROVEDORES_TOKEN_MANUAL:
                raise serializers.ValidationError({
                    'token_jwt': f'Este provedor ({provedor}) não usa token manual.',
                })
            if not token.startswith('eyJ'):
                raise serializers.ValidationError({
                    'token_jwt': 'Token inválido — deve começar com "eyJ" (formato JWT).',
                })

        return attrs

    def create(self, validated):
        credenciais = validated.pop('credenciais')
        token = validated.pop('token_jwt', None)
        instance = CredencialProvedor.objects.create(
            credenciais_enc=criptografar_credenciais(credenciais),
            **validated,
        )
        if token:
            self._salvar_token(instance, token)
        return instance

    def update(self, instance, validated):
        credenciais = validated.pop('credenciais', None)
        token = validated.pop('token_jwt', None)

        for campo, valor in validated.items():
            setattr(instance, campo, valor)
        if credenciais:
            instance.credenciais_enc = criptografar_credenciais(credenciais)
        instance.save()

        if token:
            self._salvar_token(instance, token)
        return instance

    def _salvar_token(self, credencial: CredencialProvedor, token: str):
        from provedores.solarman.autenticacao import decodificar_jwt_payload

        expira_em = None
        try:
            payload = decodificar_jwt_payload(token)
            exp = payload.get('exp')
            if exp:
                expira_em = datetime.fromtimestamp(exp, tz=dt_tz.utc)
        except Exception:
            pass

        CacheTokenProvedor.objects.update_or_create(
            credencial=credencial,
            defaults={
                'dados_token_enc': criptografar_credenciais({'token': token}),
                'expira_em': expira_em,
            },
        )
        if credencial.precisa_atencao:
            CredencialProvedor.objects.filter(pk=credencial.pk).update(precisa_atencao=False)
