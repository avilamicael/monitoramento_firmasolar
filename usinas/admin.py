from django.contrib import admin
from .models import Usina, SnapshotUsina, Inversor, SnapshotInversor


@admin.register(Usina)
class UsinaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'provedor', 'capacidade_kwp', 'ativo', 'atualizado_em']
    list_filter = ['provedor', 'ativo']
    search_fields = ['nome', 'endereco']
    readonly_fields = ['id', 'criado_em', 'atualizado_em', 'ultimo_snapshot']


@admin.register(SnapshotUsina)
class SnapshotUsinaAdmin(admin.ModelAdmin):
    list_display = ['usina', 'coletado_em', 'potencia_kw', 'energia_hoje_kwh', 'status']
    list_filter = ['status', 'usina__provedor']
    readonly_fields = ['id', 'coletado_em']
    date_hierarchy = 'coletado_em'


@admin.register(Inversor)
class InversorAdmin(admin.ModelAdmin):
    list_display = ['numero_serie', 'modelo', 'usina', 'criado_em']
    search_fields = ['numero_serie', 'modelo']
    list_filter = ['usina__provedor']


@admin.register(SnapshotInversor)
class SnapshotInversorAdmin(admin.ModelAdmin):
    list_display = ['inversor', 'coletado_em', 'pac_kw', 'estado']
    list_filter = ['estado']
    date_hierarchy = 'coletado_em'
