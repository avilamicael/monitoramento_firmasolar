"""
Supressão inteligente de alertas por análise contextual de dados históricos.

Diferente da supressão por CatalogoAlarme (global) ou RegraSupressao (configurada),
estas funções analisam snapshots coletados para decidir se um alerta representa
de fato um problema ou é um comportamento operacional esperado.

Uso em sincronizar_alertas():
    from alertas.supressao_inteligente import e_desligamento_gradual, esta_gerando_agora
    if catalogo.tipo == 'sistema_desligado':
        if esta_gerando_agora(usina):
            continue  # payload do provedor incoerente — a usina está gerando
        if e_desligamento_gradual(usina):
            continue  # pôr do sol — não criar alerta
"""
import logging
from datetime import timedelta

from django.utils import timezone

from usinas.models import Usina, SnapshotUsina, SnapshotInversor

logger = logging.getLogger(__name__)

# Limiar: se a última potência registrada antes do desligamento estiver
# abaixo desse percentual da capacidade instalada, considera-se gradual.
_LIMIAR_PCT_CAPACIDADE = 0.05   # 5% da capacidade instalada (kWp)
_LIMIAR_ABS_KW = 1.0            # mínimo absoluto em kW (para usinas sem capacidade cadastrada)
_JANELA_HORAS = 24              # janela de busca de snapshots (horas)

# Janela para cruzar SnapshotUsina com SnapshotInversor da mesma coleta — idêntica
# à definida em alertas/analise.py. Compartilhar a constante não vale a dependência
# inversa (analise consome supressao_inteligente em outros caminhos).
_JANELA_CICLO = timedelta(minutes=5)


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


def esta_gerando_agora(usina: Usina) -> bool:
    """
    Retorna True se a usina está, neste instante, gerando energia — seja no nível
    da usina (último SnapshotUsina com potencia_kw > 0) ou no nível de inversor
    (algum SnapshotInversor da mesma coleta com pac_kw > 0).

    Motivação: alguns provedores entregam payloads internamente inconsistentes —
    a flag `sistema_desligado` é verdadeira enquanto o próprio payload devolve
    potência de usina ou de inversor acima de zero. Caso real (2026-04-23):
    Hoymiles / usina "Cleber E Bruna" veio com `s_uoff=true`, `real_power=0` e,
    ao mesmo tempo, inversores com pac_kw somando ~3.77 kW.

    Conservador por construção: se não houver snapshot recente, retorna False
    (i.e., deixa o alerta passar). Só suprime quando há evidência concreta de
    geração.
    """
    snap = (
        SnapshotUsina.objects
        .filter(usina=usina)
        .order_by('-coletado_em')
        .values('coletado_em', 'potencia_kw')
        .first()
    )
    if snap is None:
        return False

    if (snap['potencia_kw'] or 0) > 0:
        logger.debug(
            'supressao_inteligente: [%s] %s — usina gera %.3f kW agora, ignora sistema_desligado',
            usina.provedor, usina.nome, snap['potencia_kw'],
        )
        return True

    ts = snap['coletado_em']
    soma_pac = SnapshotInversor.objects.filter(
        inversor__usina=usina,
        coletado_em__gte=ts - _JANELA_CICLO,
        coletado_em__lte=ts + _JANELA_CICLO,
        pac_kw__gt=0,
    ).count()
    if soma_pac > 0:
        logger.debug(
            'supressao_inteligente: [%s] %s — %d inversor(es) com pac_kw>0 no ciclo atual, '
            'ignora sistema_desligado',
            usina.provedor, usina.nome, soma_pac,
        )
        return True

    return False
