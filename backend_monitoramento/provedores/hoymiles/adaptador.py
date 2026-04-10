"""
Adaptador Hoymiles — une autenticação + consultas e normaliza para os dataclasses do sistema.
"""
import logging
from datetime import datetime, timezone

import requests

from provedores.base import AdaptadorProvedor, CapacidadesProvedor, DadosUsina, DadosInversor, DadosAlerta
from provedores.excecoes import ProvedorErro
from .autenticacao import fazer_login, _HEADERS_BASE
from .consultas import listar_usinas, listar_inversores, listar_alertas, baixar_dados_dia

logger = logging.getLogger(__name__)

_STATUS_MAP = {
    0:  'offline',
    1:  'offline',
    2:  'aviso',
    3:  'normal',
    40: 'normal',
}

# Mapeamento de flags warn_data para mensagens legíveis
_FLAGS_ALERTA = {
    'g_warn':    ('Aviso de rede elétrica (grid)', 'aviso'),
    'l3_warn':   ('Aviso de isolamento L3', 'aviso'),
    's_ustable': ('Tensão instável', 'aviso'),
    's_uoff':    ('Sistema desligado', 'critico'),
    'dl':        ('Desconexão de link/comunicação', 'critico'),
    's_uid':     ('Falha de identificação do dispositivo', 'aviso'),
}


def _para_float(valor) -> float:
    try:
        return float(valor) if valor is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _normalizar_status(codigo) -> str:
    try:
        return _STATUS_MAP.get(int(codigo), 'offline')
    except (TypeError, ValueError):
        return 'offline'


class HoymilesAdaptador(AdaptadorProvedor):
    """
    Adaptador para a API Hoymiles S-Cloud.

    Autenticação: nonce-hash (login com hash da senha) → token "3.xxx"
    O token é salvo no banco (CacheTokenProvedor) e reutilizado entre coletas.

    Credenciais (no banco, criptografadas): {"username": "...", "password": "..."}
    Cache de token: {"token": "3.xxx..."}
    """

    def __init__(self, credenciais: dict):
        self._usuario = credenciais['username']
        self._senha = credenciais['password']
        self._token: str | None = credenciais.get('token')
        self._sessao = requests.Session()
        self._sessao.headers.update(_HEADERS_BASE)

    @property
    def chave_provedor(self) -> str:
        return 'hoymiles'

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
            self._token = fazer_login(self._usuario, self._senha, self._sessao)

    def precisa_renovar_token(self) -> bool:
        return not bool(self._token)

    def renovar_token(self, dados_token: dict) -> dict:
        self._token = None
        self._token = fazer_login(self._usuario, self._senha, self._sessao)
        return {'token': self._token}

    def obter_cache_token(self) -> dict | None:
        return {'token': self._token} if self._token else None

    def buscar_usinas(self) -> list[DadosUsina]:
        self._garantir_autenticado()
        registros = listar_usinas(self._sessao, self._token)
        return [self._normalizar_usina(r) for r in registros]

    def buscar_inversores(self, id_usina_provedor: str) -> list[DadosInversor]:
        self._garantir_autenticado()
        registros = listar_inversores(id_usina_provedor, self._sessao, self._token)
        dados_dia = baixar_dados_dia(id_usina_provedor, self._sessao, self._token)
        return [self._normalizar_inversor(r, id_usina_provedor, dados_dia) for r in registros]

    def buscar_alertas(self, id_usina_provedor: str | None = None) -> list[DadosAlerta]:
        self._garantir_autenticado()
        try:
            registros = listar_alertas(self._sessao, self._token)
        except ProvedorErro:
            return []
        return self._extrair_alertas(registros)

    def _normalizar_usina(self, r: dict) -> DadosUsina:
        rt = r.get('_realtime') or {}
        potencia_w = _para_float(rt.get('real_power', 0))
        return DadosUsina(
            id_usina_provedor=str(r.get('id', '')),
            nome=r.get('name') or '(sem nome)',
            capacidade_kwp=_para_float(r.get('capacitor') or r.get('capacity')),
            potencia_atual_kw=potencia_w / 1000 if potencia_w else 0.0,
            # Hoymiles retorna energia em Wh — converter para kWh
            energia_hoje_kwh=_para_float(rt.get('today_eq')) / 1000,
            energia_mes_kwh=_para_float(rt.get('month_eq')) / 1000,
            energia_total_kwh=_para_float(rt.get('total_eq')) / 1000,
            status=_normalizar_status(r.get('status')),
            data_medicao=datetime.now(timezone.utc),
            fuso_horario=r.get('tz_name') or 'America/Sao_Paulo',
            endereco=r.get('address') or '',
            qtd_inversores=0,
            qtd_inversores_online=0,
            qtd_alertas=0,
            payload_bruto=r,
        )

    def _normalizar_inversor(self, r: dict, id_usina: str, dados_dia: dict | None = None) -> DadosInversor:
        sn = r.get('sn') or r.get('dtu_sn') or str(r.get('id', ''))
        conectado = (r.get('warn_data') or {}).get('connect', False)
        micro_id = r.get('id')
        eletrico = (dados_dia or {}).get(micro_id, {})
        return DadosInversor(
            id_inversor_provedor=str(micro_id or sn),
            id_usina_provedor=id_usina,
            numero_serie=sn,
            modelo=r.get('model') or r.get('model_no') or f"tipo-{r.get('type', '?')}",
            estado='normal' if conectado else 'offline',
            pac_kw=eletrico.get('pac_kw') or 0.0,
            energia_hoje_kwh=eletrico.get('energia_hoje_kwh') or 0.0,
            energia_total_kwh=0.0,
            soc_bateria=None,
            strings_mppt=eletrico.get('strings_mppt', {}),
            tensao_dc_v=eletrico.get('tensao_dc_v'),
            corrente_dc_a=eletrico.get('corrente_dc_a'),
            tensao_ac_v=eletrico.get('tensao_ca_v'),
            frequencia_hz=eletrico.get('frequencia_hz'),
            temperatura_c=eletrico.get('temperatura_c'),
            data_medicao=datetime.now(timezone.utc),
            payload_bruto=r,
        )

    def _extrair_alertas(self, registros: list[dict]) -> list[DadosAlerta]:
        resultado = []
        for r in registros:
            id_usina = str(r.get('id', ''))
            warn_data = r.get('warn_data') or {}
            for flag, (mensagem, nivel) in _FLAGS_ALERTA.items():
                if warn_data.get(flag):
                    resultado.append(DadosAlerta(
                        id_alerta_provedor=f'{id_usina}_{flag}',
                        id_tipo_alarme_provedor=flag,
                        id_usina_provedor=id_usina,
                        mensagem=mensagem,
                        nivel=nivel,
                        inicio=datetime.now(timezone.utc),
                        equipamento_sn='',
                        estado='ativo',
                        sugestao='',
                        payload_bruto=r,
                    ))
        return resultado
