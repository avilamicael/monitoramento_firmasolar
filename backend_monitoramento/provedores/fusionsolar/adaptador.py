"""
Adaptador FusionSolar — une autenticação + consultas e normaliza para os dataclasses do sistema.
"""
import logging
from datetime import datetime, timezone

import requests

from provedores.base import AdaptadorProvedor, CapacidadesProvedor, DadosUsina, DadosInversor, DadosAlerta
from .autenticacao import fazer_login
from .consultas import listar_usinas, listar_inversores, listar_alertas

logger = logging.getLogger(__name__)


def _para_float(valor) -> float:
    try:
        return float(valor) if valor is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


class FusionSolarAdaptador(AdaptadorProvedor):
    """
    Adaptador para a API Huawei FusionSolar (thirdData).

    Autenticação: sessão com XSRF-TOKEN (cookie após login).
    A sessão expira após algumas horas — re-login automático em consultas.py.

    Credenciais (no banco, criptografadas): {"username": "...", "system_code": "..."}
    Cache de token: {"xsrf_token": "..."}
    """

    def __init__(self, credenciais: dict):
        self._usuario = credenciais['username']
        self._system_code = credenciais['system_code']
        self._sessao = requests.Session()
        self._sessao.headers.update({'Content-Type': 'application/json'})

        # Carrega token em cache se disponível
        xsrf = credenciais.get('xsrf_token')
        if xsrf:
            self._sessao.headers.update({'XSRF-TOKEN': xsrf})
            self._autenticado = True
        else:
            self._autenticado = False

    @property
    def chave_provedor(self) -> str:
        return 'fusionsolar'

    @property
    def capacidades(self) -> CapacidadesProvedor:
        return CapacidadesProvedor(
            suporta_inversores=False,   # conta sem permissão p/ dados de inversores (erro 407)
            suporta_alertas=True,
            alertas_por_conta=True,
            limite_requisicoes=1,
            janela_segundos=5,
        )

    def _garantir_autenticado(self):
        if not self._autenticado:
            fazer_login(self._usuario, self._system_code, self._sessao)
            self._autenticado = True

    def precisa_renovar_token(self) -> bool:
        return not self._autenticado

    def renovar_token(self, dados_token: dict) -> dict:
        self._autenticado = False
        token = fazer_login(self._usuario, self._system_code, self._sessao)
        self._autenticado = True
        return {'xsrf_token': token}

    def obter_cache_token(self) -> dict | None:
        xsrf = self._sessao.headers.get('XSRF-TOKEN', '')
        return {'xsrf_token': xsrf} if xsrf else None

    def buscar_usinas(self) -> list[DadosUsina]:
        self._garantir_autenticado()
        registros = listar_usinas(self._sessao, self._usuario, self._system_code)
        return [self._normalizar_usina(r) for r in registros]

    def buscar_inversores(self, id_usina_provedor: str) -> list[DadosInversor]:
        self._garantir_autenticado()
        registros = listar_inversores(id_usina_provedor, self._sessao, self._usuario, self._system_code)
        return [self._normalizar_inversor(r, id_usina_provedor) for r in registros]

    def buscar_alertas(self, id_usina_provedor: str | None = None) -> list[DadosAlerta]:
        self._garantir_autenticado()
        registros = listar_alertas(self._sessao, self._usuario, self._system_code)
        return [self._normalizar_alerta(r) for r in registros]

    def _normalizar_usina(self, r: dict) -> DadosUsina:
        kpi = r.get('_kpi') or {}
        # FusionSolar retorna capacidade em MW — converter para kWp
        capacidade_mw = _para_float(r.get('capacity'))
        capacidade_kwp = capacidade_mw * 1000 if capacidade_mw < 100 else capacidade_mw
        return DadosUsina(
            id_usina_provedor=r.get('stationCode') or '',
            nome=r.get('stationName') or r.get('stationCode') or '(sem nome)',
            capacidade_kwp=capacidade_kwp,
            potencia_atual_kw=_para_float(kpi.get('total_current_power')),
            energia_hoje_kwh=_para_float(kpi.get('day_power')),
            energia_mes_kwh=_para_float(kpi.get('month_power')),
            energia_total_kwh=_para_float(kpi.get('total_power')),
            status='normal',   # FusionSolar não expõe status simples no list
            data_medicao=datetime.now(timezone.utc),
            fuso_horario=r.get('timeZone') or 'America/Sao_Paulo',
            endereco=r.get('address') or '',
            qtd_inversores=0,
            qtd_inversores_online=0,
            qtd_alertas=0,
            payload_bruto=r,
        )

    def _normalizar_inversor(self, r: dict, id_usina: str) -> DadosInversor:
        kpi = r.get('_kpi') or {}
        dev_id = str(r.get('id', ''))
        return DadosInversor(
            id_inversor_provedor=dev_id,
            id_usina_provedor=id_usina,
            numero_serie=r.get('esnCode') or r.get('devSn') or dev_id,
            modelo=r.get('invType') or '',
            estado='normal' if r.get('devStatus') == 1 else 'offline',
            pac_kw=_para_float(kpi.get('active_power')),
            energia_hoje_kwh=_para_float(kpi.get('day_cap')),
            energia_total_kwh=_para_float(kpi.get('mppt_total_cap')),
            soc_bateria=None,
            strings_mppt={},
            data_medicao=datetime.now(timezone.utc),
            payload_bruto=r,
        )

    def _normalizar_alerta(self, r: dict) -> DadosAlerta:
        return DadosAlerta(
            id_alerta_provedor=str(r.get('sn') or r.get('devSn') or ''),
            id_usina_provedor=r.get('stationCode') or '',
            mensagem=r.get('alarmName') or r.get('alarmId') or '',
            nivel='critico' if r.get('alarmLevel') == 1 else 'aviso',
            inicio=datetime.now(timezone.utc),
            equipamento_sn=r.get('devSn') or '',
            estado='ativo',
            sugestao=r.get('repairSuggestion') or '',
            payload_bruto=r,
        )
