"""
Supressão inteligente de alertas por análise contextual de dados históricos.

Diferente da supressão por CatalogoAlarme (global) ou RegraSupressao (configurada),
estas funções analisam snapshots coletados para decidir se um alerta representa
de fato um problema ou é um comportamento operacional esperado.

Uso em sincronizar_alertas():
    from alertas.supressao_inteligente import e_desligamento_gradual
    if catalogo.tipo == 'sistema_desligado' and e_desligamento_gradual(usina):
        continue  # pôr do sol — não criar alerta
"""
import logging
from datetime import timedelta

from django.utils import timezone

from usinas.models import Usina, SnapshotUsina

logger = logging.getLogger(__name__)

# Limiar: se a última potência registrada antes do desligamento estiver
# abaixo desse percentual da capacidade instalada, considera-se gradual.
_LIMIAR_PCT_CAPACIDADE = 0.15   # 15% da capacidade instalada (kWp)
_LIMIAR_ABS_KW = 1.0            # mínimo absoluto em kW (para usinas sem capacidade cadastrada)
_JANELA_HORAS = 24              # janela de busca de snapshots (horas)


def e_desligamento_gradual(usina: Usina) -> bool:
    """
    Retorna True se o desligamento da usina parece gradual (pôr do sol normal).
    Retorna False se parece abrupto (problema real) ou sem evidência suficiente.

    Critério: o último snapshot com potência > 0 nas últimas 24h deve estar
    abaixo do limiar (15% da capacidade instalada ou 1 kW, o que for maior).

    Cenários:
        Usina 7 kWp, último pot = 0.03 kW → limiar 1.05 kW → True  (gradual, suprimir)
        Usina 7 kWp, último pot = 5.00 kW → limiar 1.05 kW → False (abrupto, alertar)
        Sem snapshots com pot nas últimas 24h                → False (conservador, alertar)

    Args:
        usina: instância de Usina com campo capacidade_kwp disponível.

    Returns:
        True se o desligamento é gradual e o alerta deve ser suprimido.
    """
    limiar_kw = max(_LIMIAR_ABS_KW, (usina.capacidade_kwp or 0) * _LIMIAR_PCT_CAPACIDADE)

    ultimo = (
        SnapshotUsina.objects
        .filter(
            usina=usina,
            coletado_em__gte=timezone.now() - timedelta(hours=_JANELA_HORAS),
            potencia_kw__gt=0,
        )
        .order_by('-coletado_em')
        .values('potencia_kw')
        .first()
    )

    if ultimo is None:
        logger.debug(
            'supressao_inteligente: [%s] %s — sem pot nas últimas %dh, não suprime',
            usina.provedor, usina.nome, _JANELA_HORAS,
        )
        return False

    gradual = ultimo['potencia_kw'] <= limiar_kw
    logger.debug(
        'supressao_inteligente: [%s] %s — último pot=%.2f kW, limiar=%.2f kW → %s',
        usina.provedor, usina.nome,
        ultimo['potencia_kw'], limiar_kw,
        'gradual (suprime)' if gradual else 'abrupto (não suprime)',
    )
    return gradual
