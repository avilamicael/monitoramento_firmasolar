"""
Adaptador Solarman — une autenticacao + consultas e normaliza para os dataclasses do sistema.
"""
import logging
from datetime import datetime, timezone

import requests

from provedores.base import AdaptadorProvedor, CapacidadesProvedor, DadosUsina, DadosInversor, DadosAlerta
from provedores.excecoes import ProvedorErroAuth
from .autenticacao import validar_token, token_expirado, _HEADERS_BASE
from .consultas import listar_usinas, listar_inversores, buscar_dados_inversor, listar_alertas

logger = logging.getLogger(__name__)

_STATUS_MAP = {'NORMAL': 'normal', 'OFFLINE': 'offline', 'ALARM': 'aviso'}


def _para_float(valor) -> float:
    try:
        return float(valor) if valor is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


class SolarmanAdaptador(AdaptadorProvedor):
    """
    Adaptador para a API Solarman Business (globalpro.solarmanpv.com).

    Autenticacao: JWT token com validade de ~60 dias.
    O login web exige Cloudflare Turnstile, entao o token e obtido manualmente.

    Credenciais (no banco, criptografadas): {"email": "...", "password": "..."}
    Cache de token: {"token": "eyJ..."} — JWT copiado do browser
    """

    def __init__(self, credenciais: dict):
        self._email = credenciais.get('email', '')
        self._password = credenciais.get('password', '')
        self._token: str | None = credenciais.get('token')
        self._sessao = requests.Session()
        self._sessao.headers.update(_HEADERS_BASE)
        # IDs das usinas para busca de alertas em lote
        self._station_ids: list[int] = []

    @property
    def chave_provedor(self) -> str:
        return 'solarman'

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
        if not self._token:
            raise ProvedorErroAuth(
                'Solarman: token JWT ausente — copie o cookie "tokenKey" do browser '
                'e salve no cache de token via admin.'
            )
        validar_token(self._token)

    def precisa_renovar_token(self) -> bool:
        if not self._token:
            return True
        return token_expirado(self._token, margem_horas=72)

    def renovar_token(self, dados_token: dict) -> dict:
        # Renovacao automatica nao e possivel (Cloudflare Turnstile).
        # Se o token atual ainda for valido, reutiliza.
        token = dados_token.get('token') or self._token
        if token and not token_expirado(token, margem_horas=0):
            self._token = token
            return {'token': token}
        raise ProvedorErroAuth(
            'Solarman: token JWT expirado — faca login manualmente no browser '
            'e copie o novo token (cookie "tokenKey").'
        )

    def obter_cache_token(self) -> dict | None:
        return {'token': self._token} if self._token else None

    def buscar_usinas(self) -> list[DadosUsina]:
        self._garantir_autenticado()
        registros = listar_usinas(self._sessao, self._token)
        usinas = []
        self._station_ids = []
        for r in registros:
            station = r.get('station') or {}
            station_id = station.get('id')
            if station_id:
                self._station_ids.append(station_id)
            usinas.append(self._normalizar_usina(station))
        return usinas

    def buscar_inversores(self, id_usina_provedor: str) -> list[DadosInversor]:
        self._garantir_autenticado()
        registros = listar_inversores(id_usina_provedor, self._sessao, self._token)
        resultado = []
        for inv in registros:
            device_id = inv.get('id')
            dados_eletricos = {}
            if device_id and inv.get('netState') == 1:
                try:
                    dados_eletricos = buscar_dados_inversor(str(device_id), self._sessao, self._token)
                except Exception:
                    logger.warning('Solarman: falha ao buscar dados do inversor %s', device_id)
            resultado.append(self._normalizar_inversor(inv, id_usina_provedor, dados_eletricos))
        return resultado

    def buscar_alertas(self, id_usina_provedor: str | None = None) -> list[DadosAlerta]:
        self._garantir_autenticado()
        if id_usina_provedor:
            ids = [int(id_usina_provedor)]
        elif self._station_ids:
            ids = self._station_ids
        else:
            return []
        registros = listar_alertas(ids, self._sessao, self._token)
        return [self._normalizar_alerta(r) for r in registros if r.get('alertName')]

    def _normalizar_usina(self, s: dict) -> DadosUsina:
        status_raw = s.get('networkStatus', 'OFFLINE')
        last_update = s.get('lastUpdateTime')
        if last_update:
            data_medicao = datetime.fromtimestamp(last_update, tz=timezone.utc)
        else:
            data_medicao = datetime.now(timezone.utc)

        return DadosUsina(
            id_usina_provedor=str(s.get('id', '')),
            nome=s.get('name') or '(sem nome)',
            capacidade_kwp=_para_float(s.get('installedCapacity')),
            potencia_atual_kw=_para_float(s.get('generationPower')) / 1000,
            energia_hoje_kwh=_para_float(s.get('generationValue')),
            energia_mes_kwh=_para_float(s.get('generationMonth')),
            energia_total_kwh=_para_float(s.get('generationTotal')),
            status=_STATUS_MAP.get(status_raw, 'offline'),
            data_medicao=data_medicao,
            fuso_horario=s.get('regionTimezone') or 'America/Sao_Paulo',
            endereco=s.get('locationAddress') or '',
            payload_bruto=s,
        )

    def _normalizar_inversor(self, inv: dict, id_usina: str, dados: dict) -> DadosInversor:
        sn = inv.get('deviceSn') or inv.get('serialNumber') or ''
        online = inv.get('netState') == 1

        collection_time = inv.get('collectionTime')
        if collection_time:
            data_medicao = datetime.fromtimestamp(collection_time, tz=timezone.utc)
        else:
            data_medicao = datetime.now(timezone.utc)

        # Dados eletricos do stats/day (ultimo ponto)
        pac_w = _para_float(dados.get('APo_t1'))
        energia_hoje = _para_float(dados.get('Etdy_ge0'))
        energia_total = _para_float(dados.get('Et_ge0'))

        # Strings MPPT (DC Power por PV)
        strings_mppt = {}
        for i in range(1, 5):
            potencia = dados.get(f'DP{i}')
            if potencia is not None and float(potencia) > 0:
                strings_mppt[f'string{i}'] = _para_float(potencia)

        # Tensao/corrente DC (primeiro PV com dados)
        tensao_dc = _para_float(dados.get('DV1')) or None
        corrente_dc = _para_float(dados.get('DC1')) or None

        # Dados AC
        tensao_ac = _para_float(dados.get('AV1')) or None
        corrente_ac = _para_float(dados.get('AC1')) or None
        frequencia = _para_float(dados.get('AF1')) or None

        # Temperatura
        temperatura = _para_float(dados.get('AC_RDT_T1')) or None

        return DadosInversor(
            id_inversor_provedor=str(inv.get('id') or sn),
            id_usina_provedor=id_usina,
            numero_serie=sn,
            modelo=inv.get('type') or 'MICRO_INVERTER',
            estado='normal' if online else 'offline',
            pac_kw=pac_w / 1000 if pac_w else 0.0,
            energia_hoje_kwh=energia_hoje,
            energia_total_kwh=energia_total,
            soc_bateria=None,
            strings_mppt=strings_mppt,
            tensao_ac_v=tensao_ac,
            corrente_ac_a=corrente_ac,
            tensao_dc_v=tensao_dc,
            corrente_dc_a=corrente_dc,
            frequencia_hz=frequencia,
            temperatura_c=temperatura,
            data_medicao=data_medicao,
            payload_bruto={**inv, '_stats': dados},
        )

    def _normalizar_alerta(self, r: dict) -> DadosAlerta:
        nivel_map = {'serious': 'critico', 'important': 'importante', 'minor': 'aviso'}
        nivel_raw = str(r.get('level') or 'minor').lower()

        inicio_ts = r.get('alertStartTime')
        if inicio_ts:
            inicio = datetime.fromtimestamp(inicio_ts, tz=timezone.utc)
        else:
            inicio = datetime.now(timezone.utc)

        return DadosAlerta(
            id_alerta_provedor=str(r.get('id') or r.get('ruleId') or ''),
            id_usina_provedor=str(r.get('stationId') or ''),
            mensagem=r.get('alertName') or '',
            nivel=nivel_map.get(nivel_raw, 'aviso'),
            inicio=inicio,
            equipamento_sn=r.get('deviceSn') or '',
            estado='ativo' if r.get('status') != 'RESTORED' else 'resolvido',
            id_tipo_alarme_provedor=str(r.get('ruleId') or ''),
            payload_bruto=r,
        )
