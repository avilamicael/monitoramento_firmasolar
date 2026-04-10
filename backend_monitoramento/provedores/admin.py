import json

from django import forms
from django.contrib import admin, messages
from django.utils.html import format_html
from django.http import HttpResponseRedirect
from django.urls import reverse

from .cripto import criptografar_credenciais, descriptografar_credenciais
from .models import CacheTokenProvedor, CredencialProvedor

# Mapeamento: provedor → campos necessários com labels amigáveis
CAMPOS_POR_PROVEDOR = {
    'solis':       [('api_key', 'API Key'), ('app_secret', 'App Secret')],
    'hoymiles':    [('username', 'Usuário / Email'), ('password', 'Senha')],
    'fusionsolar': [('username', 'Usuário'), ('system_code', 'System Code')],
    'solarman':    [('app_id', 'App ID'), ('app_secret', 'App Secret'), ('email', 'Email'), ('password', 'Senha')],
    'auxsol':      [('account', 'Usuário / Email'), ('password', 'Senha')],
}

# Intervalo mínimo global (em minutos)
INTERVALO_MINIMO_GLOBAL = 30


class CredencialProvedorForm(forms.ModelForm):
    """
    Form com campos individuais por provedor ao invés de JSON manual.
    Os campos são exibidos/ocultados via JavaScript conforme o provedor selecionado.
    """
    # Campos genéricos que cobrem todos os provedores
    campo_1 = forms.CharField(required=False, label='Campo 1', widget=forms.TextInput(attrs={'size': 60}))
    campo_2 = forms.CharField(required=False, label='Campo 2', widget=forms.PasswordInput(attrs={'size': 60, 'render_value': True}))
    campo_3 = forms.CharField(required=False, label='Campo 3', widget=forms.TextInput(attrs={'size': 60}))
    campo_4 = forms.CharField(required=False, label='Campo 4', widget=forms.PasswordInput(attrs={'size': 60, 'render_value': True}))

    # Fallback: campo JSON para casos especiais
    credenciais_json = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'cols': 60}),
        required=False,
        label='Credenciais (JSON avançado)',
        help_text='Apenas se precisar inserir credenciais manualmente em formato JSON.',
    )

    class Meta:
        model = CredencialProvedor
        exclude = ['credenciais_enc']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['intervalo_coleta_minutos'].help_text = (
            f'Intervalo entre coletas em minutos. Mínimo: {INTERVALO_MINIMO_GLOBAL} minutos.'
        )
        self.fields['intervalo_coleta_minutos'].widget.attrs['min'] = INTERVALO_MINIMO_GLOBAL
        # Se editando um registro existente, preencher os campos com valores salvos
        if self.instance and self.instance.pk and self.instance.credenciais_enc:
            try:
                dados = descriptografar_credenciais(self.instance.credenciais_enc)
                provedor = self.instance.provedor
                campos = CAMPOS_POR_PROVEDOR.get(provedor, [])
                for i, (chave, _label) in enumerate(campos):
                    campo_name = f'campo_{i + 1}'
                    if campo_name in self.fields:
                        self.fields[campo_name].initial = dados.get(chave, '')
            except Exception:
                pass

    def _montar_credenciais(self) -> dict | None:
        """Monta o dict de credenciais a partir dos campos individuais."""
        provedor = self.cleaned_data.get('provedor', '')
        campos = CAMPOS_POR_PROVEDOR.get(provedor, [])

        # Primeiro tenta os campos individuais
        resultado = {}
        for i, (chave, _label) in enumerate(campos):
            valor = self.cleaned_data.get(f'campo_{i + 1}', '').strip()
            if valor:
                resultado[chave] = valor

        if resultado and len(resultado) == len(campos):
            return resultado

        # Fallback: JSON manual
        json_raw = self.cleaned_data.get('credenciais_json', '').strip()
        if json_raw:
            return json.loads(json_raw)

        # Se editando e nem campos nem JSON preenchidos, manter credenciais atuais
        if self.instance and self.instance.pk and self.instance.credenciais_enc:
            return None

        return resultado if resultado else None

    def clean_credenciais_json(self):
        valor = self.cleaned_data.get('credenciais_json', '').strip()
        if valor:
            try:
                json.loads(valor)
            except json.JSONDecodeError as exc:
                raise forms.ValidationError(f'JSON inválido: {exc}')
        return valor

    def clean_intervalo_coleta_minutos(self):
        intervalo = self.cleaned_data.get('intervalo_coleta_minutos') or INTERVALO_MINIMO_GLOBAL
        if intervalo < INTERVALO_MINIMO_GLOBAL:
            raise forms.ValidationError(
                f'O intervalo mínimo permitido é {INTERVALO_MINIMO_GLOBAL} minutos.'
            )
        return intervalo

    def clean(self):
        cleaned = super().clean()
        provedor = cleaned.get('provedor', '')
        campos = CAMPOS_POR_PROVEDOR.get(provedor, [])
        json_raw = cleaned.get('credenciais_json', '').strip()

        # Verificar se os campos obrigatórios estão preenchidos (novo registro)
        if not self.instance.pk or not self.instance.credenciais_enc:
            campos_preenchidos = all(
                cleaned.get(f'campo_{i + 1}', '').strip()
                for i in range(len(campos))
            )
            if not campos_preenchidos and not json_raw:
                labels = [label for _, label in campos]
                raise forms.ValidationError(
                    f'Preencha os campos: {", ".join(labels)} — ou use o campo JSON avançado.'
                )

        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        credenciais = self._montar_credenciais()
        if credenciais:
            instance.credenciais_enc = criptografar_credenciais(credenciais)
        if commit:
            instance.save()
        return instance


@admin.register(CredencialProvedor)
class CredencialProvedorAdmin(admin.ModelAdmin):
    form = CredencialProvedorForm
    list_display = ['provedor', 'ativo', 'precisa_atencao', 'intervalo_coleta_minutos', 'atualizado_em']
    list_filter = ['provedor', 'ativo', 'precisa_atencao']
    readonly_fields = ['criado_em', 'atualizado_em', 'credenciais_preview']
    actions = ['forcar_coleta']
    fieldsets = [
        (None, {
            'fields': ['provedor', 'ativo', 'precisa_atencao', 'intervalo_coleta_minutos'],
        }),
        ('Credenciais', {
            'fields': ['campo_1', 'campo_2', 'campo_3', 'campo_4', 'credenciais_preview'],
            'description': 'Preencha os campos conforme o provedor selecionado.',
        }),
        ('Avançado', {
            'classes': ['collapse'],
            'fields': ['credenciais_json'],
            'description': 'Use apenas se precisar inserir credenciais em formato JSON bruto.',
        }),
        ('Informações', {
            'fields': ['criado_em', 'atualizado_em'],
        }),
    ]

    @admin.action(description='Forçar coleta agora')
    def forcar_coleta(self, request, queryset):
        from coleta.tasks import coletar_dados_provedor
        total = 0
        for cred in queryset.filter(ativo=True):
            coletar_dados_provedor.delay(str(cred.id))
            total += 1
        if total:
            messages.success(request, f'Coleta forçada disparada para {total} provedor(es).')
        else:
            messages.warning(request, 'Nenhum provedor ativo selecionado.')

    def credenciais_preview(self, obj):
        """Mostra as chaves do JSON (sem valores) para confirmação."""
        if not obj.credenciais_enc:
            return '(nenhuma credencial salva)'
        try:
            dados = descriptografar_credenciais(obj.credenciais_enc)
            items = []
            for chave, valor in dados.items():
                # Mostra apenas primeiros e últimos caracteres do valor
                if len(str(valor)) > 6:
                    mascarado = f'{str(valor)[:3]}...{str(valor)[-3:]}'
                else:
                    mascarado = '***'
                items.append(f'<b>{chave}</b>: {mascarado}')
            return format_html('<br>'.join(items))
        except Exception:
            return '(erro ao descriptografar)'
    credenciais_preview.short_description = 'Credenciais salvas'

    class Media:
        js = ('provedores/js/credencial_form.js',)


@admin.register(CacheTokenProvedor)
class CacheTokenProvedorAdmin(admin.ModelAdmin):
    list_display = ['credencial', 'expira_em', 'atualizado_em']
    readonly_fields = ['credencial', 'atualizado_em']
