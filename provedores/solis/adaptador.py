"""
Adaptador Solis — une autenticação + consultas e normaliza para os dataclasses do sistema.
"""
from datetime import datetime, timezone

from provedores.base import AdaptadorProvedor, CapacidadesProvedor, DadosUsina, DadosInversor, DadosAlerta
from .consultas import listar_usinas, listar_inversores, listar_alertas

_STATUS_MAP = {0: 'normal', 1: 'aviso', 2: 'offline', 3: 'construcao'}
_NIVEL_ALERTA_MAP = {'1': 'critico', '3': 'aviso'}


def _para_float(valor) -> float:
    try:
        return float(valor) if valor is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _timestamp_ms_para_datetime(ts_ms) -> datetime | None:
    try:
        return datetime.fromtimestamp(int(ts_ms) / 1000, tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def _normalizar_status(estado) -> str:
    try:
        return _STATUS_MAP.get(int(estado), 'offline')
    except (TypeError, ValueError):
        return 'offline'


class SolisAdaptador(AdaptadorProvedor):
    """
    Adaptador para a API Solis Cloud.

    Autenticação: HMAC-SHA1 stateless — sem token, sem refresh.
    Credenciais (no banco, criptografadas): {"api_key": "...", "app_secret": "..."}
    """

    def __init__(self, credenciais: dict):
        self._api_key = credenciais['api_key']
        self._app_secret = credenciais['app_secret']

    @property
    def chave_provedor(self) -> str:
        return 'solis'

    @property
    def capacidades(self) -> CapacidadesProvedor:
        return CapacidadesProvedor(
            suporta_inversores=True,
            suporta_alertas=True,
            alertas_por_conta=True,
            limite_requisicoes=3,
            janela_segundos=5,
        )

    def buscar_usinas(self) -> list[DadosUsina]:
        registros = listar_usinas(self._api_key, self._app_secret)
        return [self._normalizar_usina(r) for r in registros]

    def buscar_inversores(self, id_usina_provedor: str) -> list[DadosInversor]:
        registros = listar_inversores(id_usina_provedor, self._api_key, self._app_secret)
        return [self._normalizar_inversor(r, id_usina_provedor) for r in registros]

    def buscar_alertas(self, id_usina_provedor: str | None = None) -> list[DadosAlerta]:
        registros = listar_alertas(self._api_key, self._app_secret, id_usina_provedor)
        return [self._normalizar_alerta(r) for r in registros]

    def _normalizar_usina(self, r: dict) -> DadosUsina:
        return DadosUsina(
            id_usina_provedor=str(r.get('id', '')),
            nome=r.get('stationName') or r.get('name') or '(sem nome)',
            capacidade_kwp=_para_float(r.get('dip')),
            potencia_atual_kw=_para_float(r.get('power')),
            energia_hoje_kwh=_para_float(r.get('dayEnergy')),
            energia_mes_kwh=_para_float(r.get('monthEnergy')),
            energia_total_kwh=_para_float(r.get('allEnergy')),
            status=_normalizar_status(r.get('state')),
            data_medicao=datetime.now(timezone.utc),
            fuso_horario=r.get('timeZoneStr', 'America/Sao_Paulo'),
            endereco=r.get('addrOrigin') or '',
            qtd_inversores=int(r.get('inverterCount') or 0),
            qtd_inversores_online=int(r.get('inverterOnlineCount') or 0),
            qtd_alertas=int(r.get('alarmCount') or 0),
            payload_bruto=r,
        )

    def _normalizar_inversor(self, r: dict, id_usina: str) -> DadosInversor:
        strings_mppt = {f'string{i}': r[f'pow{i}'] for i in range(1, 33) if r.get(f'pow{i}') is not None}
        return DadosInversor(
            id_inversor_provedor=str(r.get('id') or r.get('sn', '')),
            id_usina_provedor=id_usina,
            numero_serie=r.get('sn') or '',
            modelo=r.get('machine') or '',
            estado=_normalizar_status(r.get('state')),
            pac_kw=_para_float(r.get('pac')),
            energia_hoje_kwh=_para_float(r.get('etoday')),
            energia_total_kwh=_para_float(r.get('etotal')),
            soc_bateria=_para_float(r.get('batteryCapacitySoc')) or None,
            strings_mppt=strings_mppt,
            data_medicao=_timestamp_ms_para_datetime(r.get('dataTimestamp')) or datetime.now(timezone.utc),
            payload_bruto=r,
        )

    def _normalizar_alerta(self, r: dict) -> DadosAlerta:
        nivel_raw = str(r.get('alarmLevel') or '3')
        estado_raw = str(r.get('state') or '0')
        return DadosAlerta(
            id_alerta_provedor=str(r.get('id') or r.get('alarmCode') or ''),
            id_usina_provedor=str(r.get('stationId') or ''),
            mensagem=r.get('alarmMsg') or r.get('alarmCode') or '',
            nivel=_NIVEL_ALERTA_MAP.get(nivel_raw, 'aviso'),
            inicio=_timestamp_ms_para_datetime(r.get('alarmBeginTime')) or datetime.now(timezone.utc),
            equipamento_sn=r.get('alarmDeviceSn') or r.get('sn') or '',
            estado='ativo' if estado_raw == '0' else 'resolvido',
            sugestao=r.get('advice') or '',
            payload_bruto=r,
        )
