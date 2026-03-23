from django.contrib import admin
from django.utils import timezone

from .models import Alerta, CatalogoAlarme, RegraSupressao


@admin.register(CatalogoAlarme)
class CatalogoAlarmeAdmin(admin.ModelAdmin):
    list_display = [
        'provedor', 'id_alarme_provedor', 'nome_pt', 'tipo',
        'nivel_padrao', 'nivel_sobrescrito', 'suprimido', 'criado_auto',
    ]
    list_filter = ['provedor', 'tipo', 'nivel_padrao', 'suprimido', 'nivel_sobrescrito', 'criado_auto']
    search_fields = ['id_alarme_provedor', 'nome_pt', 'nome_original']
    readonly_fields = ['criado_em', 'atualizado_em', 'criado_auto']
    fieldsets = [
        (None, {
            'fields': ['provedor', 'id_alarme_provedor', 'nome_pt', 'nome_original'],
        }),
        ('Categoria', {
            'fields': ['tipo'],
            'description': (
                'Preenchida automaticamente na primeira detecção do alarme. '
                'Corrija manualmente se a inferência automática errou. '
                'Valores: equipamento · comunicacao · rede_eletrica · sistema_desligado · preventivo'
            ),
        }),
        ('Nível de severidade', {
            'fields': ['nivel_padrao', 'nivel_sobrescrito'],
            'description': (
                'Marque "Nível sobrescrito pelo operador" para fixar o nível e impedir '
                'que a coleta automática o sobrescreva.'
            ),
        }),
        ('Supressão global', {
            'fields': ['suprimido'],
            'description': (
                'Suprimir globalmente impede que qualquer ocorrência deste tipo gere alertas '
                'em qualquer usina. Para supressão por usina, use Regras de Supressão.'
            ),
        }),
        ('Texto de apoio', {
            'fields': ['sugestao'],
        }),
        ('Auditoria', {
            'fields': ['criado_auto', 'criado_em', 'atualizado_em'],
            'classes': ['collapse'],
        }),
    ]


@admin.register(RegraSupressao)
class RegraSupressaoAdmin(admin.ModelAdmin):
    list_display = ['catalogo', 'escopo', 'usina', 'motivo_resumido', 'ativo_ate', 'esta_ativa_display', 'criado_em']
    list_filter = ['escopo', 'catalogo__provedor']
    search_fields = ['catalogo__nome_pt', 'catalogo__id_alarme_provedor', 'usina__nome', 'motivo']
    readonly_fields = ['criado_em']
    raw_id_fields = ['usina']
    fields = ['catalogo', 'escopo', 'usina', 'motivo', 'ativo_ate', 'criado_em']

    def motivo_resumido(self, obj):
        return obj.motivo[:60] if obj.motivo else '—'
    motivo_resumido.short_description = 'Motivo'

    def esta_ativa_display(self, obj):
        return obj.esta_ativa()
    esta_ativa_display.boolean = True
    esta_ativa_display.short_description = 'Ativa'


@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = [
        'usina', 'nivel', 'mensagem_resumida', 'estado',
        'catalogo_alarme', 'inicio', 'notificacao_enviada',
    ]
    list_filter = ['nivel', 'estado', 'usina__provedor', 'catalogo_alarme__tipo']
    search_fields = ['mensagem', 'usina__nome', 'equipamento_sn', 'id_alerta_provedor']
    readonly_fields = ['id', 'criado_em', 'atualizado_em', 'notificacao_enviada', 'payload_bruto']
    raw_id_fields = ['catalogo_alarme']
    date_hierarchy = 'inicio'
    fields = [
        'usina', 'catalogo_alarme', 'nivel', 'estado', 'mensagem', 'equipamento_sn',
        'inicio', 'fim', 'sugestao', 'anotacoes',
        'notificacao_enviada', 'id_alerta_provedor', 'criado_em', 'atualizado_em',
    ]

    def mensagem_resumida(self, obj):
        return obj.mensagem[:80]
    mensagem_resumida.short_description = 'Problema'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('usina', 'catalogo_alarme')
