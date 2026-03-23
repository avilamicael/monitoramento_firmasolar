from django.contrib import admin
from .models import ConfiguracaoNotificacao


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
