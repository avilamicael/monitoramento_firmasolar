"""
Management command para atualizar e testar credenciais FusionSolar.

Uso:
    # Atualizar credenciais
    python manage.py fusionsolar_credenciais --usuario api_firmasolar --system-code "mH*2020@"

    # Testar sem alterar
    python manage.py fusionsolar_credenciais --testar

    # Atualizar e testar em seguida
    python manage.py fusionsolar_credenciais --usuario api_firmasolar --system-code "mH*2020@" --testar
"""
import json

from django.core.management.base import BaseCommand, CommandError

from provedores.cripto import criptografar_credenciais, descriptografar_credenciais
from provedores.models import CredencialProvedor, CacheTokenProvedor


class Command(BaseCommand):
    help = 'Atualiza e/ou testa credenciais FusionSolar no banco'

    def add_arguments(self, parser):
        parser.add_argument('--usuario', help='Nome de usuário FusionSolar (NorthBound)')
        parser.add_argument('--system-code', dest='system_code', help='System code (senha NorthBound)')
        parser.add_argument(
            '--testar',
            action='store_true',
            help='Testa a conexão com as credenciais salvas (ou as novas, se fornecidas)',
        )
        parser.add_argument(
            '--mostrar',
            action='store_true',
            help='Mostra as credenciais atuais descriptografadas (sem segredos completos)',
        )

    def handle(self, *args, **options):
        usuario = options.get('usuario')
        system_code = options.get('system_code')
        testar = options.get('testar')
        mostrar = options.get('mostrar')

        try:
            credencial = CredencialProvedor.objects.get(provedor='fusionsolar')
        except CredencialProvedor.DoesNotExist:
            credencial = None

        # ── Mostrar credenciais atuais ──────────────────────────────────────────
        if mostrar:
            if not credencial:
                self.stdout.write(self.style.WARNING('Nenhuma credencial FusionSolar cadastrada.'))
            else:
                dados = descriptografar_credenciais(credencial.credenciais_enc)
                u = dados.get('username', '(vazio)')
                sc = dados.get('system_code', '(vazio)')
                # Mascara os últimos 4 chars do system_code
                sc_masked = sc[:-4] + '****' if len(sc) > 4 else '****'
                self.stdout.write(f'  username    : {u}')
                self.stdout.write(f'  system_code : {sc_masked}')
                self.stdout.write(f'  ativo       : {credencial.ativo}')
                self.stdout.write(f'  precisa_atencao: {credencial.precisa_atencao}')
            return

        # ── Atualizar credenciais ───────────────────────────────────────────────
        if usuario or system_code:
            if not (usuario and system_code):
                raise CommandError('Forneça --usuario e --system-code juntos.')

            novas = {'username': usuario, 'system_code': system_code}
            enc = criptografar_credenciais(novas)

            if credencial:
                credencial.credenciais_enc = enc
                credencial.precisa_atencao = False
                credencial.ativo = True
                credencial.save(update_fields=['credenciais_enc', 'precisa_atencao', 'ativo', 'atualizado_em'])
                self.stdout.write(self.style.SUCCESS(f'Credenciais atualizadas para usuário: {usuario}'))

                # Invalida cache de token para forçar novo login com as novas credenciais
                deleted, _ = CacheTokenProvedor.objects.filter(credencial=credencial).delete()
                if deleted:
                    self.stdout.write('Cache de token anterior removido — próxima coleta fará novo login.')
            else:
                credencial = CredencialProvedor.objects.create(
                    provedor='fusionsolar',
                    credenciais_enc=enc,
                )
                self.stdout.write(self.style.SUCCESS(f'Credencial FusionSolar criada para usuário: {usuario}'))

        # ── Testar conexão ──────────────────────────────────────────────────────
        if testar:
            if not credencial:
                raise CommandError('Nenhuma credencial FusionSolar para testar.')

            self.stdout.write('Testando conexão com a API FusionSolar...')
            dados = descriptografar_credenciais(credencial.credenciais_enc)

            import requests
            from provedores.fusionsolar.autenticacao import fazer_login, BASE_URL

            sessao = requests.Session()
            sessao.headers.update({'Content-Type': 'application/json'})

            try:
                token = fazer_login(dados['username'], dados['system_code'], sessao)
                self.stdout.write(self.style.SUCCESS('Login bem-sucedido!'))
                self.stdout.write(f'  XSRF-TOKEN: {token[:20]}...' if token else '  (sem token)')
            except Exception as exc:
                raise CommandError(f'Login falhou: {exc}')

            # Busca lista de usinas
            self.stdout.write('Buscando lista de usinas...')
            try:
                resp = sessao.post(f'{BASE_URL}/getStationList', json={}, timeout=20)
                dados_resp = resp.json()
                if dados_resp.get('success'):
                    usinas = dados_resp.get('data') or []
                    self.stdout.write(self.style.SUCCESS(f'  {len(usinas)} usina(s) encontrada(s):'))
                    for u in usinas[:5]:
                        self.stdout.write(f'    - {u.get("stationName")} ({u.get("stationCode")})')
                    if len(usinas) > 5:
                        self.stdout.write(f'    ... e mais {len(usinas) - 5}')
                else:
                    fail = dados_resp.get('failCode')
                    msg = dados_resp.get('message') or str(dados_resp)
                    self.stdout.write(self.style.ERROR(f'  API retornou erro: failCode={fail} — {msg}'))
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f'  Erro ao buscar usinas: {exc}'))
