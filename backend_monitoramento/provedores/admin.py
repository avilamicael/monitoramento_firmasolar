import json

from django import forms
from django.contrib import admin

from .cripto import criptografar_credenciais, descriptografar_credenciais
from .models import CacheTokenProvedor, CredencialProvedor


class CredencialProvedorForm(forms.ModelForm):
    """
    Form customizado que expõe um campo de texto legível para edição das credenciais.
    O campo credenciais_json é convertido para/de credenciais_enc (Fernet) no save().
    """
    credenciais_json = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 6, 'cols': 60}),
        required=False,
        label='Credenciais (JSON)',
        help_text='Cole as credenciais como JSON. Ex: {"api_key": "...", "app_secret": "..."}',
    )

    class Meta:
        model = CredencialProvedor
        exclude = ['credenciais_enc']

    def clean_credenciais_json(self):
        valor = self.cleaned_data.get('credenciais_json', '').strip()
        if valor:
            try:
                json.loads(valor)
            except json.JSONDecodeError as exc:
                raise forms.ValidationError(f'JSON inválido: {exc}')
        return valor

    def save(self, commit=True):
        instance = super().save(commit=False)
        json_raw = self.cleaned_data.get('credenciais_json', '').strip()
        if json_raw:
            instance.credenciais_enc = criptografar_credenciais(json.loads(json_raw))
        if commit:
            instance.save()
        return instance


@admin.register(CredencialProvedor)
class CredencialProvedorAdmin(admin.ModelAdmin):
    form = CredencialProvedorForm
    list_display = ['provedor', 'ativo', 'precisa_atencao', 'atualizado_em']
    list_filter = ['provedor', 'ativo', 'precisa_atencao']
    readonly_fields = ['criado_em', 'atualizado_em', 'credenciais_preview']
    fields = ['provedor', 'ativo', 'precisa_atencao', 'credenciais_json', 'credenciais_preview', 'criado_em', 'atualizado_em']

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


@admin.register(CacheTokenProvedor)
class CacheTokenProvedorAdmin(admin.ModelAdmin):
    list_display = ['credencial', 'expira_em', 'atualizado_em']
    readonly_fields = ['credencial', 'atualizado_em']
