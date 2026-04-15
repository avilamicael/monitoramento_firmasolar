"""
Serializer da ConfiguracaoNotificacao exposto via API (staff only).
"""
import re
from urllib.parse import urlparse

from rest_framework import serializers

from notificacoes.models import ConfiguracaoNotificacao


_EMAIL_RE = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
_TEL_BR_RE = re.compile(r'^\+?[0-9]{10,15}$')


def _split_destinatarios(raw: str) -> list[str]:
    if not raw:
        return []
    itens = re.split(r'[,\n]', raw)
    return [i.strip() for i in itens if i.strip()]


class ConfiguracaoNotificacaoSerializer(serializers.ModelSerializer):
    destinatarios_lista = serializers.SerializerMethodField()

    class Meta:
        model = ConfiguracaoNotificacao
        fields = [
            'id', 'canal', 'ativo',
            'destinatarios', 'destinatarios_lista',
            'notificar_critico', 'notificar_importante',
            'notificar_aviso', 'notificar_info',
            'atualizado_em',
        ]
        read_only_fields = ['id', 'atualizado_em', 'destinatarios_lista']

    def get_destinatarios_lista(self, obj) -> list[str]:
        return obj.lista_destinatarios()

    def validate(self, attrs):
        canal = attrs.get('canal') or (self.instance.canal if self.instance else None)
        destinatarios_raw = attrs.get('destinatarios', '')
        if destinatarios_raw is None:
            destinatarios_raw = ''

        itens = _split_destinatarios(destinatarios_raw)

        if canal == 'email':
            invalidos = [i for i in itens if not _EMAIL_RE.match(i)]
            if invalidos:
                raise serializers.ValidationError({
                    'destinatarios': f'E-mails inválidos: {", ".join(invalidos)}',
                })
        elif canal == 'whatsapp':
            invalidos = [i for i in itens if not _TEL_BR_RE.match(i.replace(' ', '').replace('-', ''))]
            if invalidos:
                raise serializers.ValidationError({
                    'destinatarios': f'Números inválidos (use formato +5548999999999): {", ".join(invalidos)}',
                })
        elif canal == 'webhook':
            for url in itens:
                parsed = urlparse(url)
                if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
                    raise serializers.ValidationError({
                        'destinatarios': f'URL inválida: {url}',
                    })

        if attrs.get('ativo') and not itens:
            raise serializers.ValidationError({
                'destinatarios': 'Informe pelo menos um destinatário quando o canal está ativo.',
            })

        return attrs
