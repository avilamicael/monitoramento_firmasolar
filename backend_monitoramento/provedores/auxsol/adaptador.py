"""
Adaptador AuxSol — une autenticacao + consultas e normaliza para os dataclasses do sistema.
"""
import logging
from datetime import datetime, timezone

import requests

from provedores.base import AdaptadorProvedor, CapacidadesProvedor, DadosUsina, DadosInversor, DadosAlerta
from .autenticacao import fazer_login, token_expirado, _HEADERS_BASE
from .consultas import listar_usinas, listar_inversores, buscar_inversor_realtime, listar_alertas

logger = logging.getLogger(__name__)

# Mapeamento de status AuxSol → status interno
# 01=normal (gerando), 02=standby (noite/sem sol), 03=falha
_STATUS_MAP = {'01': 'normal', '02': 'offline', '03': 'offline'}

# Mapeamento de nivel de alarme AuxSol → nivel interno
_NIVEL_ALERTA_MAP = {'01': 'critico', '02': 'importante', '03': 'aviso', '04': 'info'}


def _para_float(valor) -> float:
    try:
        return float(valor) if valor is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _parse_datetime(dt_str: str, tz_offset: str = '-03:00') -> datetime:
    """Converte string de data AuxSol para datetime UTC."""
    if not dt_str:
        return datetime.now(timezone.utc)
    try:
        # Formato: "2026-04-10 16:02:16"
        dt = datetime.strptime(dt_str[:19], '%Y-%m-%d %H:%M:%S')
        # Aplica offset do timezone da planta
        horas = int(tz_offset.split(':')[0])
        from datetime import timedelta
        tz = timezone(timedelta(hours=horas))
        return dt.replace(tzinfo=tz)
    except (ValueError, IndexError):
        return datetime.now(timezone.utc)


class AuxsolAdaptador(AdaptadorProvedor):
    """
    Adaptador para a API AuxSol Cloud (eu.auxsolcloud.com).

    Autenticacao: Bearer token (UUID) com validade de 12 horas.
    O token e salvo no cache de tokens para reutilizacao entre coletas.

    Credenciais (no banco, criptografadas): {"account": "...", "password": "..."}
    Cache de token: {"token": "uuid...", "obtido_em": timestamp}
    """

    def __init__(self, credenciais: dict):
        self._account = credenciais['account']
        self._password = credenciais['password']
        self._token: str | None = credenciais.get('token')
        self._token_obtido_em: int = credenciais.get('obtido_em', 0)
        self._sessao = requests.Session()
        self._sessao.headers.update(_HEADERS_BASE)

    @property
    def chave_provedor(self) -> str:
        return 'auxsol'

    @property
    def capacidades(self) -> CapacidadesProvedor:
        return CapacidadesProvedor(
            suporta_inversores=True,
            suporta_alertas=True,
            alertas_por_conta=True,
            limite_requisicoes=5,
            janela_segundos=10,
        )

    def _garantir_autenticado(self):
        if not self._token or token_expirado({'obtido_em': self._token_obtido_em}):
            self._fazer_login()

    def _fazer_login(self):
        dados = fazer_login(self._account, self._password, self._sessao)
        self._token = dados['token']
        self._token_obtido_em = dados['obtido_em']

    def _executar_com_relogin(self, fn):
        """Executa fn e tenta re-login se receber erro de autenticacao."""
        from provedores.excecoes import ProvedorErroAuth
        try:
            return fn()
        except ProvedorErroAuth:
            logger.info('AuxSol: token rejeitado pelo servidor, fazendo re-login...')
            self._fazer_login()
            return fn()

    def precisa_renovar_token(self) -> bool:
        return not self._token or token_expirado({'obtido_em': self._token_obtido_em})

    def renovar_token(self, dados_token: dict) -> dict:
        self._token = None
        dados = fazer_login(self._account, self._password, self._sessao)
        self._token = dados['token']
        self._token_obtido_em = dados['obtido_em']
        return dados

    def obter_cache_token(self) -> dict | None:
        if self._token:
            return {'token': self._token, 'obtido_em': self._token_obtido_em}
        return None

    def buscar_usinas(self) -> list[DadosUsina]:
        self._garantir_autenticado()
        registros = self._executar_com_relogin(
            lambda: listar_usinas(self._sessao, self._token)
        )
        return [self._normalizar_usina(r) for r in registros]

    def buscar_inversores(self, id_usina_provedor: str) -> list[DadosInversor]:
        self._garantir_autenticado()
        registros = self._executar_com_relogin(
            lambda: listar_inversores(id_usina_provedor, self._sessao, self._token)
        )
        resultado = []
        for inv in registros:
            sn = inv.get('sn') or ''
            if not sn:
                resultado.append(self._normalizar_inversor(inv, id_usina_provedor, {}))
                continue
            try:
                realtime = buscar_inversor_realtime(sn, self._sessao, self._token)
            except Exception:
                logger.warning('AuxSol: falha ao buscar realtime do inversor %s', sn)
                realtime = {}
            resultado.append(self._normalizar_inversor(inv, id_usina_provedor, realtime))
        return resultado

    def buscar_alertas(self, id_usina_provedor: str | None = None) -> list[DadosAlerta]:
        self._garantir_autenticado()
        registros = listar_alertas(self._sessao, self._token, id_usina_provedor)
        return [self._normalizar_alerta(r) for r in registros]

    def _normalizar_usina(self, r: dict) -> DadosUsina:
        tz_str = r.get('timeZone') or '-03:00'
        return DadosUsina(
            id_usina_provedor=str(r.get('plantId', '')),
            nome=r.get('plantName') or '(sem nome)',
            capacidade_kwp=_para_float(r.get('capacity')),
            potencia_atual_kw=_para_float(r.get('currentPower')),
            energia_hoje_kwh=_para_float(r.get('todayYield')),
            energia_mes_kwh=_para_float(r.get('monthlyYield')),
            energia_total_kwh=_para_float(r.get('totalYield')),
            status=_STATUS_MAP.get(r.get('status', ''), 'offline'),
            data_medicao=_parse_datetime(r.get('dt', ''), tz_str),
            fuso_horario='America/Sao_Paulo',
            endereco=r.get('address') or '',
            payload_bruto=r,
        )

    def _normalizar_inversor(self, inv: dict, id_usina: str, realtime: dict) -> DadosInversor:
        sn = inv.get('sn') or ''
        tz_str = inv.get('timeZone') or '-03:00'

        # Dados basicos do inversor (endpoint list)
        pac_kw = _para_float(inv.get('currentPower'))
        energia_hoje = _para_float(inv.get('dayEnergy'))
        energia_total = _para_float(inv.get('totalEnergy'))

        # Dados do realtime (mais ricos quando disponivel)
        energy = realtime.get('energyData') or {}
        grid = realtime.get('gridData') or {}
        other = realtime.get('otherData') or {}
        battery = realtime.get('batteryData') or {}

        # Se realtime disponivel, usar valores mais atuais
        if energy:
            pac_kw = _para_float(energy.get('power')) or pac_kw
            energia_hoje = _para_float(energy.get('y')) or energia_hoje
            energia_total = _para_float(energy.get('yt')) or energia_total

        # Strings MPPT (PV data)
        strings_mppt = {}
        pv_list = energy.get('pvList') or []
        for pv in pv_list:
            idx = pv.get('index', 0)
            strings_mppt[f'string{idx}'] = _para_float(pv.get('p'))

        # Dados AC da rede
        tensao_ac = None
        corrente_ac = None
        frequencia = None
        ac_list = grid.get('acList') or []
        if ac_list:
            ac = ac_list[0]
            tensao_ac = _para_float(ac.get('u')) or None
            corrente_ac = _para_float(ac.get('i')) or None
            frequencia = _para_float(ac.get('f')) or None

        # Tensao/corrente DC do primeiro MPPT
        tensao_dc = None
        corrente_dc = None
        if pv_list:
            tensao_dc = _para_float(pv_list[0].get('u')) or None
            corrente_dc = _para_float(pv_list[0].get('i')) or None

        # Temperatura (heatsink ou interna)
        temperatura = _para_float(other.get('temperature1')) or _para_float(other.get('insideTemperature')) or None

        # SOC bateria
        soc = None
        if battery:
            soc = _para_float(battery.get('soc')) or None

        return DadosInversor(
            id_inversor_provedor=str(inv.get('inverterId') or sn),
            id_usina_provedor=id_usina,
            numero_serie=sn,
            modelo=inv.get('model') or '',
            estado=_STATUS_MAP.get(inv.get('status', ''), 'offline'),
            pac_kw=pac_kw,
            energia_hoje_kwh=energia_hoje,
            energia_total_kwh=energia_total,
            soc_bateria=soc,
            strings_mppt=strings_mppt,
            tensao_ac_v=tensao_ac,
            corrente_ac_a=corrente_ac,
            tensao_dc_v=tensao_dc,
            corrente_dc_a=corrente_dc,
            frequencia_hz=frequencia,
            temperatura_c=temperatura,
            data_medicao=_parse_datetime(inv.get('lastDt', ''), tz_str),
            payload_bruto={**inv, '_realtime': realtime},
        )

    def _normalizar_alerta(self, r: dict) -> DadosAlerta:
        nivel_raw = str(r.get('alarmLevel') or '03')
        status_raw = str(r.get('status') or '01')

        return DadosAlerta(
            id_alerta_provedor=str(r.get('id') or ''),
            id_usina_provedor=str(r.get('plantId') or ''),
            mensagem=r.get('alarmName') or r.get('alarmCode') or '',
            nivel=_NIVEL_ALERTA_MAP.get(nivel_raw, 'aviso'),
            inicio=_parse_datetime(r.get('alarmTime', '')),
            equipamento_sn=r.get('sn') or '',
            estado='ativo' if status_raw == '01' else 'resolvido',
            id_tipo_alarme_provedor=str(r.get('alarmCode') or ''),
            payload_bruto=r,
        )
