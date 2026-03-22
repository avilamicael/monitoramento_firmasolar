"""
Contrato base para backends de notificação.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class DadosNotificacao:
    """Dados de um alerta formatados para envio por qualquer canal."""
    id_alerta: str
    nome_usina: str
    provedor: str
    mensagem: str
    nivel: str          # 'critico' ou 'aviso'
    sugestao: str
    equipamento_sn: str
    inicio: datetime
    # True = novo alerta; False = alerta escalado (aviso → crítico)
    novo: bool


class BackendNotificacao(ABC):
    """
    Interface que todos os backends de notificação devem implementar.

    Cada backend é responsável por:
    - Verificar se está configurado (is_disponivel)
    - Enviar a notificação (enviar)
    """

    @abstractmethod
    def is_disponivel(self) -> bool:
        """Retorna True se o backend tem as credenciais necessárias para funcionar."""

    @abstractmethod
    def enviar(self, dados: DadosNotificacao, destinatarios: list[str]) -> None:
        """
        Envia a notificação para os destinatários.
        Erros devem ser logados mas não relançados — falha em um canal não impede os demais.
        """
