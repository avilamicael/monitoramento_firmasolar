import json
import time

from django import forms
from django.contrib import admin, messages
from django.utils.html import format_html

from .cripto import criptografar_credenciais, descriptografar_credenciais
from .models import CacheTokenProvedor, CredencialProvedor

# Mapeamento: provedor → campos necessários com labels amigáveis
CAMPOS_POR_PROVEDOR = {
    'solis':       [('api_key', 'API Key'), ('app_secret', 'App Secret')],
    'hoymiles':    [('username', 'Usuário / Email'), ('password', 'Senha')],
    'fusionsolar': [('username', 'Usuário'), ('system_code', 'System Code')],
    'solarman':    [('email', 'Email'), ('password', 'Senha')],
    'auxsol':      [('account', 'Usuário / Email'), ('password', 'Senha')],
}

# Provedores que usam token JWT manual (exibir campo extra + instruções)
PROVEDORES_TOKEN_MANUAL = {'solarman'}

# Intervalo mínimo global (em minutos)
INTERVALO_MINIMO_GLOBAL = 30

INSTRUCOES_TOKEN_SOLARMAN = (
    '<div style="background:#e8f4fd;border:1px solid #b3d8fd;border-radius:4px;'
    'padding:12px 16px;margin-top:8px;font-size:12px;line-height:1.6;">'
    '<b>Como obter o Token JWT do Solarman:</b><br>'
    '1. Acesse <a href="https://globalpro.solarmanpv.com" target="_blank">'
    'globalpro.solarmanpv.com</a> e faça login normalmente<br>'
    '2. Após o login, pressione <b>F12</b> para abrir o DevTools do navegador<br>'
    '3. Vá na aba <b>Application</b> (ou Aplicativo)<br>'
    '4. No menu lateral, clique em <b>Cookies</b> → <b>globalpro.solarmanpv.com</b><br>'
    '5. Procure o cookie chamado <b>tokenKey</b><br>'
    '6. Clique duas vezes no <b>valor</b> do cookie (começa com <code>eyJ...</code>), '
    'copie o texto inteiro<br>'
    '7. Cole aqui no campo "Token JWT" e salve<br><br>'
    '<b>O token é válido por ~60 dias.</b> O sistema avisará quando estiver '
    'próximo de expirar.</div>'
)


class CredencialProvedorForm(forms.ModelForm):
    """
    Form com campos individuais por provedor ao invés de JSON manual.
    Os campos são exibidos/ocultados via JavaScript conforme o provedor selecionado.
    """
    # Campos genéricos que cobrem todos os provedores
    campo_1 = forms.CharField(required=False, label='Campo 1', widget=forms.TextInput(attrs={'size': 60}))
    campo_2 = forms.CharField(required=False, label='Campo 2', widget=forms.TextInput(attrs={'size': 60, 'type': 'password', 'autocomplete': 'off'}))
    campo_3 = forms.CharField(required=False, label='Campo 3', widget=forms.TextInput(attrs={'size': 60}))
    campo_4 = forms.CharField(required=False, label='Campo 4', widget=forms.TextInput(attrs={'size': 60, 'type': 'password', 'autocomplete': 'off'}))

    # Token JWT manual (para provedores como Solarman)
    token_jwt = forms.CharField(
        required=False,
        label='Token JWT',
        widget=forms.Textarea(attrs={'rows': 3, 'cols': 80, 'placeholder': 'eyJhbGciOiJSUzI1NiIs...'}),
    )

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

        # Se editando, preencher campos com valores salvos
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

        resultado = {}
        for i, (chave, _label) in enumerate(campos):
            valor = self.cleaned_data.get(f'campo_{i + 1}', '').strip()
            if valor:
                resultado[chave] = valor

        if resultado and len(resultado) == len(campos):
            return resultado

        json_raw = self.cleaned_data.get('credenciais_json', '').strip()
        if json_raw:
            return json.loads(json_raw)

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

    def clean_token_jwt(self):
        token = self.cleaned_data.get('token_jwt', '').strip()
        if token and not token.startswith('eyJ'):
            raise forms.ValidationError(
                'Token inválido. O token JWT deve começar com "eyJ". '
                'Verifique se copiou o valor completo do cookie "tokenKey".'
            )
        return token

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

        # Salvar token JWT no cache (para provedores com token manual)
        token = self.cleaned_data.get('token_jwt', '').strip()
        if token and instance.pk:
            self._salvar_token_cache(instance, token)

        return instance

    def _salvar_token_cache(self, credencial, token: str):
        """Salva o JWT no CacheTokenProvedor."""
        from datetime import datetime, timezone as tz
        from .solarman.autenticacao import decodificar_jwt_payload

        payload = decodificar_jwt_payload(token)
        exp = payload.get('exp')
        expira_em = datetime.fromtimestamp(exp, tz=tz.utc) if exp else None

        cache, _ = CacheTokenProvedor.objects.update_or_create(
            credencial=credencial,
            defaults={
                'dados_token_enc': criptografar_credenciais({'token': token}),
                'expira_em': expira_em,
            },
        )
        # Limpar flag de atenção ao salvar novo token
        if credencial.precisa_atencao:
            credencial.precisa_atencao = False
            credencial.save(update_fields=['precisa_atencao'])


@admin.register(CredencialProvedor)
class CredencialProvedorAdmin(admin.ModelAdmin):
    form = CredencialProvedorForm
    list_display = ['provedor', 'ativo', 'precisa_atencao', 'intervalo_coleta_minutos', 'atualizado_em']
    list_filter = ['provedor', 'ativo', 'precisa_atencao']
    readonly_fields = ['criado_em', 'atualizado_em', 'credenciais_preview', 'token_status']
    actions = ['forcar_coleta']
    fieldsets = [
        (None, {
            'fields': ['provedor', 'ativo', 'precisa_atencao', 'intervalo_coleta_minutos'],
        }),
        ('Credenciais', {
            'fields': ['campo_1', 'campo_2', 'campo_3', 'campo_4', 'credenciais_preview'],
            'description': 'Preencha os campos conforme o provedor selecionado.',
        }),
        ('Token de Acesso', {
            'fields': ['token_jwt', 'token_status'],
            'description': 'Necessário apenas para provedores que exigem token manual (ex: Solarman).',
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

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        token = form.cleaned_data.get('token_jwt', '').strip()
        if token:
            messages.success(request, 'Token JWT salvo com sucesso.')

    def credenciais_preview(self, obj):
        """Mostra as chaves do JSON (sem valores) para confirmação."""
        if not obj.credenciais_enc:
            return '(nenhuma credencial salva)'
        try:
            dados = descriptografar_credenciais(obj.credenciais_enc)
            items = []
            for chave, valor in dados.items():
                if len(str(valor)) > 6:
                    mascarado = f'{str(valor)[:3]}...{str(valor)[-3:]}'
                else:
                    mascarado = '***'
                items.append(f'<b>{chave}</b>: {mascarado}')
            return format_html('<br>'.join(items))
        except Exception:
            return '(erro ao descriptografar)'
    credenciais_preview.short_description = 'Credenciais salvas'

    def token_status(self, obj):
        """Mostra o status do token JWT com validade e instruções."""
        if not obj.pk:
            return '(salve primeiro para ver o status)'

        # Verificar se este provedor usa token manual
        if obj.provedor not in PROVEDORES_TOKEN_MANUAL:
            return format_html(
                '<span style="color:#888;">Este provedor não requer token manual.</span>'
            )

        try:
            cache = obj.cache_token
            dados = descriptografar_credenciais(cache.dados_token_enc)
            token = dados.get('token', '')
        except CacheTokenProvedor.DoesNotExist:
            return format_html(
                '<span style="color:#e74c3c;font-weight:bold;">'
                '&#10060; Nenhum token configurado</span><br>'
                + INSTRUCOES_TOKEN_SOLARMAN
            )

        if not token:
            return format_html(
                '<span style="color:#e74c3c;font-weight:bold;">'
                '&#10060; Token vazio</span><br>'
                + INSTRUCOES_TOKEN_SOLARMAN
            )

        # Decodificar JWT para mostrar validade
        from .solarman.autenticacao import decodificar_jwt_payload, token_expirado
        payload = decodificar_jwt_payload(token)
        exp = payload.get('exp', 0)

        if not exp:
            return format_html(
                '<span style="color:#f39c12;">&#9888; Token presente mas sem data de expiração</span>'
            )

        from datetime import datetime, timezone as tz
        expira_em = datetime.fromtimestamp(exp, tz=tz.utc)
        agora = datetime.now(tz.utc)
        dias_restantes = (expira_em - agora).days

        if token_expirado(token, margem_horas=0):
            cor = '#e74c3c'
            icone = '&#10060;'
            texto = 'EXPIRADO'
        elif dias_restantes <= 7:
            cor = '#e74c3c'
            icone = '&#9888;'
            texto = f'Expira em {dias_restantes} dia(s) — RENOVAR AGORA'
        elif dias_restantes <= 14:
            cor = '#f39c12'
            icone = '&#9888;'
            texto = f'Expira em {dias_restantes} dias'
        else:
            cor = '#27ae60'
            icone = '&#9989;'
            texto = f'Válido por mais {dias_restantes} dias'

        return format_html(
            '<span style="color:{cor};font-weight:bold;">{icone} {texto}</span>'
            '<br><small>Expira em: {expira}</small><br>{instrucoes}',
            cor=cor, icone=format_html(icone), texto=texto,
            expira=expira_em.strftime('%d/%m/%Y %H:%M UTC'),
            instrucoes=format_html(INSTRUCOES_TOKEN_SOLARMAN),
        )
    token_status.short_description = 'Status do Token'

    class Media:
        js = ('provedores/js/credencial_form.js',)


@admin.register(CacheTokenProvedor)
class CacheTokenProvedorAdmin(admin.ModelAdmin):
    list_display = ['credencial', 'expira_em', 'atualizado_em']
    readonly_fields = ['credencial', 'atualizado_em']
