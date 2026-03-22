from django.contrib import admin
from .models import CredencialProvedor, CacheTokenProvedor
from .cripto import criptografar_credenciais, descriptografar_credenciais
import json


@admin.register(CredencialProvedor)
class CredencialProvedorAdmin(admin.ModelAdmin):
    list_display = ['provedor', 'ativo', 'precisa_atencao', 'atualizado_em']
    list_filter = ['provedor', 'ativo', 'precisa_atencao']
    readonly_fields = ['criado_em', 'atualizado_em', 'credenciais_preview']

    fields = ['provedor', 'ativo', 'precisa_atencao', 'credenciais_json', 'credenciais_preview', 'criado_em', 'atualizado_em']

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Campo temporário para edição do JSON descriptografado
        from django import forms
        form.base_fields['credenciais_json'] = forms.CharField(
            widget=forms.Textarea(attrs={'rows': 6, 'cols': 60}),
            required=False,
            label='Credenciais (JSON)',
            help_text='Cole as credenciais como JSON. Ex: {"api_key": "...", "app_secret": "..."}',
        )
        return form

    def credenciais_preview(self, obj):
        """Mostra as chaves do JSON (sem valores) para confirmação."""
        if not obj.credenciais_enc:
            return '(nenhuma)'
        try:
            dados = descriptografar_credenciais(obj.credenciais_enc)
            chaves = list(dados.keys())
            return f'Chaves presentes: {", ".join(chaves)}'
        except Exception:
            return '(erro ao descriptografar)'
    credenciais_preview.short_description = 'Credenciais salvas'

    def save_model(self, request, obj, form, change):
        json_raw = form.cleaned_data.get('credenciais_json', '').strip()
        if json_raw:
            try:
                dados = json.loads(json_raw)
                obj.credenciais_enc = criptografar_credenciais(dados)
            except json.JSONDecodeError as exc:
                from django.core.exceptions import ValidationError
                raise ValidationError(f'JSON inválido: {exc}')
        super().save_model(request, obj, form, change)


@admin.register(CacheTokenProvedor)
class CacheTokenProvedorAdmin(admin.ModelAdmin):
    list_display = ['credencial', 'expira_em', 'atualizado_em']
    readonly_fields = ['credencial', 'atualizado_em']
