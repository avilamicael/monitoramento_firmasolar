"""
Contrato base para todos os adaptadores de provedores de energia solar.

Cada provedor (Solis, Hoymiles, FusionSolar) implementa esta interface,
garantindo que o sistema de coleta trate todos da mesma forma.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


# ── Estruturas de dados ────────────────────────────────────────────────────────

@dataclass
class DadosUsina:
    """Dados normalizados de uma usina solar, independente do provedor."""
    id_usina_provedor: str
    nome: str
    capacidade_kwp: float
    potencia_atual_kw: float
    energia_hoje_kwh: float
    energia_mes_kwh: float
    energia_total_kwh: float
    # Status: 'normal', 'aviso', 'offline', 'construcao'
    status: str
    data_medicao: datetime
    fuso_horario: str = 'America/Sao_Paulo'
    endereco: str = ''
    qtd_inversores: int = 0
    qtd_inversores_online: int = 0
    qtd_alertas: int = 0
    payload_bruto: dict = field(default_factory=dict)


@dataclass
class DadosInversor:
    """Dados normalizados de um inversor solar."""
    id_inversor_provedor: str
    id_usina_provedor: str
    numero_serie: str
    modelo: str
    # Estado: 'normal', 'aviso', 'offline'
    estado: str
    pac_kw: float            # potência AC atual
    energia_hoje_kwh: float
    energia_total_kwh: float
    data_medicao: datetime
    soc_bateria: float | None = None   # % carga da bateria (quando há armazenamento)
    strings_mppt: dict = field(default_factory=dict)  # ex: {'string1': 120.5, 'string2': 118.2}
    payload_bruto: dict = field(default_factory=dict)


@dataclass
class DadosAlerta:
    """Dados normalizados de um alerta/problema reportado pelo provedor."""
    id_alerta_provedor: str
    id_usina_provedor: str
    mensagem: str
    # Nível: 'info', 'aviso', 'importante', 'critico'
    nivel: str
    inicio: datetime
    equipamento_sn: str = ''
    estado: str = 'ativo'    # 'ativo' ou 'resolvido'
    sugestao: str = ''
    # ID do *tipo* de alarme no provedor — chave de lookup no CatalogoAlarme
    # Ex FusionSolar: "2032" (alarmId); ex Hoymiles: código próprio
    id_tipo_alarme_provedor: str = ''
    payload_bruto: dict = field(default_factory=dict)


@dataclass
class CapacidadesProvedor:
    """
    Declara o que cada provedor suporta e seus limites de requisição.
    Usado pelo sistema de coleta para decidir como chamar o adaptador.
    """
    suporta_inversores: bool = True
    suporta_alertas: bool = True
    # True = buscar alertas uma vez p/ toda a conta; False = buscar por usina
    alertas_por_conta: bool = True
    # Rate limit: máximo de requisições por janela de segundos
    limite_requisicoes: int = 5
    janela_segundos: int = 10
    # Intervalo mínimo entre coletas bem-sucedidas (0 = sem restrição).
    # Usado para evitar cascade de rate limit em provedores com janelas rígidas (ex: FusionSolar).
    min_intervalo_coleta_segundos: int = 0


# ── Contrato ABC ───────────────────────────────────────────────────────────────

class AdaptadorProvedor(ABC):
    """
    Interface que todo adaptador de provedor deve implementar.

    Cada adaptador recebe as credenciais descriptografadas no construtor
    e opcionalmente um token em cache (para provedores com sessão).
    """

    @property
    @abstractmethod
    def chave_provedor(self) -> str:
        """Identificador único do provedor: 'solis', 'hoymiles', 'fusionsolar'."""

    @property
    @abstractmethod
    def capacidades(self) -> CapacidadesProvedor:
        """Declara o que este provedor suporta e seus limites."""

    @abstractmethod
    def buscar_usinas(self) -> list[DadosUsina]:
        """Retorna todas as usinas da conta."""

    @abstractmethod
    def buscar_inversores(self, id_usina_provedor: str) -> list[DadosInversor]:
        """Retorna todos os inversores de uma usina."""

    @abstractmethod
    def buscar_alertas(self, id_usina_provedor: str | None = None) -> list[DadosAlerta]:
        """
        Retorna alertas ativos.
        Se id_usina_provedor for None e alertas_por_conta=True, busca de uma vez.
        """

    def precisa_renovar_token(self) -> bool:
        """Retorna True se o token de sessão precisa ser renovado. Override nos provedores com sessão."""
        return False

    def renovar_token(self, dados_token: dict) -> dict:
        """Renova o token de sessão. Override nos provedores com sessão."""
        return dados_token

    def obter_cache_token(self) -> dict | None:
        """
        Retorna o token atual para ser salvo no banco após a coleta.
        Override nos provedores com sessão (Hoymiles, FusionSolar).
        """
        return None
