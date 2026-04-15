from django.contrib import admin
from .models import ConfiguracaoSistema, LogColeta


@admin.register(ConfiguracaoSistema)
class ConfiguracaoSistemaAdmin(admin.ModelAdmin):
    list_display = [
        '__str__',
        'dias_sem_comunicacao_pausar',
        'meses_garantia_padrao',
        'dias_aviso_garantia_proxima',
        'dias_aviso_garantia_urgente',
        'atualizado_em',
    ]
    readonly_fields = ['atualizado_em']

    def has_add_permission(self, request):
        # Singleton — não permite criar mais de uma linha
        return not ConfiguracaoSistema.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LogColeta)
class LogColetaAdmin(admin.ModelAdmin):
    list_display = ['credencial', 'status', 'usinas_coletadas', 'inversores_coletados',
                    'alertas_sincronizados', 'duracao_ms', 'iniciado_em']
    list_filter = ['status', 'credencial__provedor']
    readonly_fields = [f.name for f in LogColeta._meta.fields]
    date_hierarchy = 'iniciado_em'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
