from django.contrib import admin
from .models import ConfiguracaoNotificacao, Notificacao, NotificacaoLeitura


@admin.register(Notificacao)
class NotificacaoAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'tipo', 'nivel', 'apenas_staff', 'criado_em']
    list_filter = ['tipo', 'nivel', 'apenas_staff']
    search_fields = ['titulo', 'mensagem']
    readonly_fields = ['id', 'criado_em']
    date_hierarchy = 'criado_em'


@admin.register(NotificacaoLeitura)
class NotificacaoLeituraAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'notificacao', 'lida_em']
    readonly_fields = ['usuario', 'notificacao', 'lida_em']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ConfiguracaoNotificacao)
class ConfiguracaoNotificacaoAdmin(admin.ModelAdmin):
    list_display = ['canal', 'ativo', 'notificar_critico', 'notificar_importante', 'notificar_aviso', 'notificar_info', 'atualizado_em']
    fields = [
        'canal', 'ativo',
        'notificar_critico', 'notificar_importante', 'notificar_aviso', 'notificar_info',
        'destinatarios',
        'atualizado_em',
    ]
    readonly_fields = ['atualizado_em']

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['destinatarios'].widget.attrs.update({
            'rows': 8,
            'placeholder': 'Um por linha:\nnoreply@firma.com\ngestor@firma.com',
        })
        return form
