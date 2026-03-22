from django.contrib import admin
from .models import LogColeta


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
