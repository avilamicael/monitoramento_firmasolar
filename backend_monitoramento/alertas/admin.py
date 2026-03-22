from django.contrib import admin
from .models import Alerta


@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ['usina', 'nivel', 'mensagem_resumida', 'estado', 'inicio', 'notificacao_enviada']
    list_filter = ['nivel', 'estado', 'usina__provedor']
    search_fields = ['mensagem', 'usina__nome', 'equipamento_sn']
    readonly_fields = ['id', 'criado_em', 'atualizado_em', 'notificacao_enviada', 'payload_bruto']
    date_hierarchy = 'inicio'
    fields = [
        'usina', 'nivel', 'estado', 'mensagem', 'equipamento_sn',
        'inicio', 'fim', 'sugestao', 'anotacoes',
        'notificacao_enviada', 'id_alerta_provedor', 'criado_em', 'atualizado_em',
    ]

    def mensagem_resumida(self, obj):
        return obj.mensagem[:80]
    mensagem_resumida.short_description = 'Problema'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('usina')
