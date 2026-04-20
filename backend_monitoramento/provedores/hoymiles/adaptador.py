"""
Adaptador Hoymiles — une autenticação + consultas e normaliza para os dataclasses do sistema.
"""
import logging
import zoneinfo
from datetime import datetime, timedelta, timezone

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

# Limite acima do qual consideramos que `s_uoff` é falso positivo: a usina
# não está reportando dados há tanto tempo que a causa provável é Wi-Fi /
# datalogger offline, não desligamento real. Nesse caso o alerta interno
# `sem_comunicacao` (em alertas/analise.py) assume — evita dois alertas
# conflitantes sobre o mesmo problema.
_HORAS_LIMITE_SUOFF = 24


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


def _parsear_data_medicao(realtime: dict, tz_nome: str) -> datetime | None:
    """
    Converte `last_data_time` (ou `data_time`) do payload Hoymiles em datetime UTC.

    O timestamp vem como string naive ("YYYY-MM-DD HH:MM:SS") no fuso da usina.
    Retorna None se ausente ou inválido — o chamador decide o fallback.
    """
    bruto = realtime.get('last_data_time') or realtime.get('data_time')
    if not bruto:
        return None
    try:
        naive = datetime.strptime(str(bruto), '%Y-%m-%d %H:%M:%S')
    except ValueError:
        logger.warning('Hoymiles: data_medicao em formato inesperado — %r', bruto)
        return None
    try:
        tz = zoneinfo.ZoneInfo(tz_nome or 'America/Sao_Paulo')
    except zoneinfo.ZoneInfoNotFoundError:
        tz = zoneinfo.ZoneInfo('America/Sao_Paulo')
    return naive.replace(tzinfo=tz).astimezone(timezone.utc)


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
        # Cache populado em buscar_usinas() e consultado em buscar_alertas()
        # para distinguir `s_uoff` real de Wi-Fi offline no mesmo ciclo de coleta.
        self._ultima_comunicacao_por_usina: dict[str, datetime] = {}

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
        # Reseta o cache a cada coleta — só dados do ciclo atual são relevantes.
        self._ultima_comunicacao_por_usina = {}
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
        id_usina = str(r.get('id', ''))
        tz_nome = r.get('tz_name') or 'America/Sao_Paulo'
        data_medicao = _parsear_data_medicao(rt, tz_nome) or datetime.now(timezone.utc)
        self._ultima_comunicacao_por_usina[id_usina] = data_medicao
        return DadosUsina(
            id_usina_provedor=id_usina,
            nome=r.get('name') or '(sem nome)',
            capacidade_kwp=_para_float(r.get('capacitor') or r.get('capacity')),
            potencia_atual_kw=potencia_w / 1000 if potencia_w else 0.0,
            # Hoymiles retorna energia em Wh — converter para kWh
            energia_hoje_kwh=_para_float(rt.get('today_eq')) / 1000,
            energia_mes_kwh=_para_float(rt.get('month_eq')) / 1000,
            energia_total_kwh=_para_float(rt.get('total_eq')) / 1000,
            status=_normalizar_status(r.get('status')),
            data_medicao=data_medicao,
            fuso_horario=tz_nome,
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
        agora = datetime.now(timezone.utc)
        limite_suoff = timedelta(hours=_HORAS_LIMITE_SUOFF)
        resultado = []
        for r in registros:
            id_usina = str(r.get('id', ''))
            warn_data = r.get('warn_data') or {}
            for flag, (mensagem, nivel) in _FLAGS_ALERTA.items():
                if not warn_data.get(flag):
                    continue
                if flag == 's_uoff' and self._deve_suprimir_suoff(id_usina, agora, limite_suoff):
                    continue
                resultado.append(DadosAlerta(
                    id_alerta_provedor=f'{id_usina}_{flag}',
                    id_tipo_alarme_provedor=flag,
                    id_usina_provedor=id_usina,
                    mensagem=mensagem,
                    nivel=nivel,
                    inicio=agora,
                    equipamento_sn='',
                    estado='ativo',
                    sugestao='',
                    payload_bruto=r,
                ))
        return resultado

    def _deve_suprimir_suoff(self, id_usina: str, agora: datetime, limite: timedelta) -> bool:
        """
        `s_uoff` é suprimido quando a usina não comunica há mais que o limite:
        nesses casos a causa provável é Wi-Fi/datalogger offline, não desligamento
        real — o alerta interno `sem_comunicacao` (alertas/analise.py) trata o caso.
        """
        ultima = self._ultima_comunicacao_por_usina.get(id_usina)
        if ultima is None:
            return False
        if agora - ultima <= limite:
            return False
        logger.info(
            'Hoymiles: suprimindo s_uoff de %s — sem comunicar há %s (cobertura em sem_comunicacao)',
            id_usina, agora - ultima,
        )
        return True
