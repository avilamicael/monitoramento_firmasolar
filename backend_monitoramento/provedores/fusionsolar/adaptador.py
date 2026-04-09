"""
Adaptador FusionSolar — une autenticação + consultas e normaliza para os dataclasses do sistema.
"""
import logging
from datetime import datetime, timezone

import requests

from provedores.base import AdaptadorProvedor, CapacidadesProvedor, DadosUsina, DadosInversor, DadosAlerta
from .autenticacao import fazer_login
from .consultas import listar_usinas, listar_todos_inversores, listar_alertas

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

        # Cache de inversores preenchido em buscar_usinas() para evitar N chamadas à API
        self._cache_inversores: dict[str, list] | None = None

    @property
    def chave_provedor(self) -> str:
        return 'fusionsolar'

    @property
    def capacidades(self) -> CapacidadesProvedor:
        return CapacidadesProvedor(
            suporta_inversores=True,
            suporta_alertas=True,
            alertas_por_conta=True,
            # FusionSolar tem limite rígido de frequência — 1 req a cada 5s por usina
            limite_requisicoes=1,
            janela_segundos=5,
            # Intervalo mínimo entre coletas: 30 min (1800s) definido empiricamente.
            # A API rejeita com failCode=407 chamadas com menos de ~30 min de intervalo.
            # Tentar com 15 min (900s) acionava retries + backoff de 1800s → ciclo de 60 min.
            # Com 1800s direto, a coleta ocorre a cada 30 min sem backoff (48 coletas/dia).
            min_intervalo_coleta_segundos=1800,
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
        usinas = [self._normalizar_usina(r) for r in registros]

        # Pré-carrega todos os inversores em lote logo após buscar as usinas.
        # Isso evita 50 chamadas individuais a /getDevList (uma por usina),
        # que causaria rate limit 407 da FusionSolar com carteiras grandes.
        codigos = [r.get('stationCode', '') for r in registros if r.get('stationCode')]
        self._cache_inversores = listar_todos_inversores(
            codigos, self._sessao, self._usuario, self._system_code
        )
        return usinas

    def buscar_inversores(self, id_usina_provedor: str) -> list[DadosInversor]:
        """Retorna inversores do cache preenchido em buscar_usinas()."""
        if self._cache_inversores is None:
            # Fallback: cache não preenchido (situação inesperada)
            logger.warning('FusionSolar: cache de inversores vazio ao buscar %s', id_usina_provedor)
            return []
        registros = self._cache_inversores.get(id_usina_provedor, [])
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
            endereco=r.get('stationAddr') or r.get('address') or '',
            qtd_inversores=0,
            qtd_inversores_online=0,
            qtd_alertas=0,
            payload_bruto=r,
        )

    def _normalizar_inversor(self, r: dict, id_usina: str) -> DadosInversor:
        kpi = r.get('_kpi') or {}
        dev_id = str(r.get('id', ''))

        # Strings MPPT: campos mppt_N_cap (energia acumulada por string)
        strings_mppt = {
            k: float(v)
            for k, v in kpi.items()
            if k.startswith('mppt_') and k.endswith('_cap') and v
        }

        # run_state=1 = ligado; qualquer outro = offline
        run_state = kpi.get('run_state')
        if run_state is not None:
            estado = 'normal' if int(run_state) == 1 else 'offline'
        else:
            estado = 'normal' if r.get('devStatus') == 1 else 'offline'

        # FusionSolar retorna tensão AC por fase (a_u = fase A) e corrente (a_i = fase A).
        # Para DC: pv1_u (tensão string 1) e pv1_i (corrente string 1).
        # Inversores trifásicos também têm b_u/c_u, mas usamos fase A como referência.
        tensao_ac = _para_float(kpi.get('a_u') or kpi.get('ab_u')) or None
        corrente_ac = _para_float(kpi.get('a_i')) or None
        tensao_dc = _para_float(kpi.get('pv1_u')) or None
        corrente_dc = _para_float(kpi.get('pv1_i')) or None
        frequencia = _para_float(kpi.get('elec_freq')) or None
        temperatura = _para_float(kpi.get('temperature')) or None
        return DadosInversor(
            id_inversor_provedor=dev_id,
            id_usina_provedor=id_usina,
            numero_serie=r.get('esnCode') or r.get('devSn') or dev_id,
            modelo=r.get('invType') or r.get('devName') or '',
            estado=estado,
            pac_kw=_para_float(kpi.get('active_power')),
            energia_hoje_kwh=_para_float(kpi.get('day_cap')),
            # total_cap = energia total acumulada (campo correto para devTypeId=38)
            # mppt_total_cap não existe neste tipo de dispositivo
            energia_total_kwh=_para_float(kpi.get('total_cap') or kpi.get('mppt_total_cap')),
            soc_bateria=None,
            strings_mppt=strings_mppt,
            tensao_ac_v=tensao_ac,
            corrente_ac_a=corrente_ac,
            tensao_dc_v=tensao_dc,
            corrente_dc_a=corrente_dc,
            frequencia_hz=frequencia,
            temperatura_c=temperatura,
            data_medicao=datetime.now(timezone.utc),
            payload_bruto=r,
        )

    def _normalizar_alerta(self, r: dict) -> DadosAlerta:
        alarm_id = str(r.get('alarmId') or '')
        dev_sn = r.get('devSn') or ''

        # Chave de deduplicação: tipo de alarme + serial do dispositivo.
        # Usar só devSn causaria conflito se um inversor tiver 2 alarmes diferentes ativos.
        id_alerta = f'{alarm_id}_{dev_sn}' if alarm_id and dev_sn else (alarm_id or dev_sn or '')

        # FusionSolar alarmLevel: 1=crítico, 2=importante, 3=aviso, 4=info
        _NIVEL_MAP = {1: 'critico', 2: 'importante', 3: 'aviso', 4: 'info'}
        nivel = _NIVEL_MAP.get(r.get('alarmLevel'), 'aviso')

        return DadosAlerta(
            id_alerta_provedor=id_alerta,
            id_usina_provedor=r.get('stationCode') or '',
            mensagem=r.get('alarmName') or alarm_id or '',
            nivel=nivel,
            inicio=datetime.now(timezone.utc),
            equipamento_sn=dev_sn,
            estado='ativo',
            sugestao=r.get('repairSuggestion') or '',
            id_tipo_alarme_provedor=alarm_id,
            payload_bruto=r,
        )
