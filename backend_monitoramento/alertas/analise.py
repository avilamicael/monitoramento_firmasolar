"""
Analise interna de dados coletados para gerar alertas inteligentes.

Chamado ao final de cada ciclo de coleta, apos sincronizar alertas do provedor.
Analisa snapshots de usinas e inversores para detectar problemas que os
provedores nao reportam ou reportam de forma insuficiente.

Tipos de alerta:
  Instantaneos (detectados numa unica coleta):
    - tensao_zero: tensao AC = 0 em qualquer momento
    - sobretensao: tensao AC >= 240V
    - sem_geracao_diurna: usina com pac=0 entre 8h-18h
    - sem_comunicacao: ultima coleta muito antiga

  Progressivos (acumulam evidencia ao longo de varias coletas):
    - corrente_baixa: corrente AC/DC <= 0.1A por 2+ horas entre 9h-17h
"""
import logging
from datetime import timedelta

from django.utils import timezone as dj_timezone

from usinas.models import Usina, SnapshotUsina, Inversor, SnapshotInversor
from alertas.models import Alerta

logger = logging.getLogger(__name__)

# Horario comercial (fixo por enquanto — todas as usinas em SC)
HORA_INICIO_COMERCIAL = 8
HORA_FIM_COMERCIAL = 18

# Horario para analise de corrente
HORA_INICIO_CORRENTE = 9
HORA_FIM_CORRENTE = 17

# Thresholds
TENSAO_SOBRETENSAO_V = 240.0
CORRENTE_MINIMA_A = 0.1
CORRENTE_BAIXA_HORAS = 2
SEM_COMUNICACAO_MINUTOS = 90


def analisar_usina(usina: Usina, snapshot: SnapshotUsina, inversores_snapshots: list[tuple[Inversor, SnapshotInversor | None]]) -> None:
    """
    Analisa os dados de uma usina e seus inversores apos a coleta.
    Cria ou resolve alertas internos conforme as regras definidas.

    Args:
        usina: instancia da usina
        snapshot: snapshot da usina recem-coletado
        inversores_snapshots: lista de tuplas (inversor, snapshot_inversor) da coleta atual
    """
    agora = dj_timezone.now()

    # Determinar hora local da usina
    try:
        import zoneinfo
        tz = zoneinfo.ZoneInfo(usina.fuso_horario or 'America/Sao_Paulo')
        hora_local = agora.astimezone(tz).hour
    except Exception:
        hora_local = agora.hour - 3  # fallback SC

    horario_comercial = HORA_INICIO_COMERCIAL <= hora_local < HORA_FIM_COMERCIAL
    horario_corrente = HORA_INICIO_CORRENTE <= hora_local < HORA_FIM_CORRENTE

    # === Alertas de usina (nivel planta) ===

    # Sem geracao em horario comercial
    if horario_comercial:
        _verificar_sem_geracao_diurna(usina, snapshot, agora)

    # Sem comunicacao
    _verificar_sem_comunicacao(usina, snapshot, agora)

    # === Alertas de inversor (nivel equipamento) ===
    for inversor, snap_inv in inversores_snapshots:
        if snap_inv is None:
            continue

        _verificar_tensao_zero(usina, inversor, snap_inv, agora)
        _verificar_sobretensao(usina, inversor, snap_inv, agora)

        if horario_corrente:
            _verificar_corrente_baixa(usina, inversor, snap_inv, agora)


def _criar_ou_manter_alerta(
    usina: Usina,
    categoria: str,
    chave: str,
    nivel: str,
    mensagem: str,
    sugestao: str = '',
    equipamento_sn: str = '',
) -> None:
    """Cria um alerta interno ou mantem ativo se ja existe."""
    id_alerta = f'interno_{categoria}_{chave}'
    agora = dj_timezone.now()

    alerta, criado = Alerta.objects.get_or_create(
        usina=usina,
        id_alerta_provedor=id_alerta,
        defaults={
            'origem': 'interno',
            'categoria': categoria,
            'mensagem': mensagem,
            'nivel': nivel,
            'inicio': agora,
            'estado': 'ativo',
            'sugestao': sugestao,
            'equipamento_sn': equipamento_sn,
        },
    )

    if not criado:
        campos = {}
        # Reabrir se estava resolvido
        if alerta.estado == 'resolvido':
            campos['estado'] = 'ativo'
            campos['fim'] = None
        # Atualizar nivel se escalou
        if alerta.nivel_escalou_para(nivel):
            campos['nivel'] = nivel
        # Atualizar mensagem (pode ter dados atualizados)
        campos['mensagem'] = mensagem
        if campos:
            Alerta.objects.filter(pk=alerta.pk).update(**campos)


def _resolver_alerta(usina: Usina, categoria: str, chave: str) -> None:
    """Resolve um alerta interno se existir e estiver ativo."""
    id_alerta = f'interno_{categoria}_{chave}'
    Alerta.objects.filter(
        usina=usina,
        id_alerta_provedor=id_alerta,
        estado='ativo',
    ).update(estado='resolvido', fim=dj_timezone.now())


# === Regras de deteccao ===

def _verificar_sem_geracao_diurna(usina: Usina, snapshot: SnapshotUsina, agora) -> None:
    """Usina com potencia zero em horario comercial."""
    chave = str(usina.id_usina_provedor)

    if snapshot.potencia_kw <= 0:
        _criar_ou_manter_alerta(
            usina=usina,
            categoria='sem_geracao_diurna',
            chave=chave,
            nivel='importante',
            mensagem=f'Usina sem geracao em horario comercial — potencia: {snapshot.potencia_kw} kW',
            sugestao='Verificar se ha problema no inversor, disjuntor ou falta de energia na rede.',
        )
    else:
        _resolver_alerta(usina, 'sem_geracao_diurna', chave)


def _verificar_sem_comunicacao(usina: Usina, snapshot: SnapshotUsina, agora) -> None:
    """Ultima coleta muito antiga — possivel falha de Wi-Fi."""
    chave = str(usina.id_usina_provedor)
    diff = agora - snapshot.coletado_em

    if diff > timedelta(minutes=SEM_COMUNICACAO_MINUTOS):
        minutos = int(diff.total_seconds() / 60)
        _criar_ou_manter_alerta(
            usina=usina,
            categoria='sem_comunicacao',
            chave=chave,
            nivel='aviso',
            mensagem=f'Sem comunicacao ha {minutos} minutos — ultima coleta: {snapshot.coletado_em.strftime("%H:%M")}',
            sugestao='Possivel falha de Wi-Fi ou problema no datalogger. Verificar conexao de internet do local.',
        )
    else:
        _resolver_alerta(usina, 'sem_comunicacao', chave)


def _verificar_tensao_zero(usina: Usina, inversor: Inversor, snap: SnapshotInversor, agora) -> None:
    """Tensao AC zero — inversor desligou."""
    chave = inversor.numero_serie

    if snap.tensao_ac_v is not None and snap.tensao_ac_v == 0:
        _criar_ou_manter_alerta(
            usina=usina,
            categoria='tensao_zero',
            chave=chave,
            nivel='critico',
            mensagem=f'Tensao AC zero no inversor {inversor.numero_serie} — inversor desligado',
            sugestao='Inversor pode ter desligado por falha na rede, disjuntor desarmado ou defeito interno.',
            equipamento_sn=chave,
        )
    else:
        _resolver_alerta(usina, 'tensao_zero', chave)


def _verificar_sobretensao(usina: Usina, inversor: Inversor, snap: SnapshotInversor, agora) -> None:
    """Sobretensao AC >= 240V — risco de desligamento."""
    chave = inversor.numero_serie

    if snap.tensao_ac_v is not None and snap.tensao_ac_v >= TENSAO_SOBRETENSAO_V:
        _criar_ou_manter_alerta(
            usina=usina,
            categoria='sobretensao',
            chave=chave,
            nivel='aviso',
            mensagem=f'Sobretensao detectada no inversor {inversor.numero_serie} — tensao AC: {snap.tensao_ac_v:.1f}V (limite: {TENSAO_SOBRETENSAO_V}V)',
            sugestao='Tensao acima do normal. Monitorar — risco de desligamento por protecao do inversor.',
            equipamento_sn=chave,
        )
    else:
        _resolver_alerta(usina, 'sobretensao', chave)


def _verificar_corrente_baixa(usina: Usina, inversor: Inversor, snap: SnapshotInversor, agora) -> None:
    """
    Corrente AC/DC muito baixa por periodo prolongado (2+ horas entre 9h-17h).
    Consulta snapshots anteriores para verificar persistencia.
    """
    chave = inversor.numero_serie

    # Verificar corrente atual
    corrente_ac = snap.corrente_ac_a or 0
    corrente_dc = snap.corrente_dc_a or 0

    if corrente_ac > CORRENTE_MINIMA_A or corrente_dc > CORRENTE_MINIMA_A:
        # Corrente ok — resolver alerta se existia
        _resolver_alerta(usina, 'corrente_baixa', chave)
        return

    # Corrente baixa agora — verificar ha quanto tempo
    limite = agora - timedelta(hours=CORRENTE_BAIXA_HORAS)

    # Buscar snapshots das ultimas 2 horas deste inversor
    snapshots_recentes = (
        SnapshotInversor.objects
        .filter(
            inversor=inversor,
            coletado_em__gte=limite,
        )
        .order_by('coletado_em')
    )

    if not snapshots_recentes.exists():
        return

    # Verificar se TODOS os snapshots das ultimas 2h tem corrente baixa
    todos_baixos = all(
        (s.corrente_ac_a or 0) <= CORRENTE_MINIMA_A and (s.corrente_dc_a or 0) <= CORRENTE_MINIMA_A
        for s in snapshots_recentes
    )

    if not todos_baixos:
        return

    # Verificar que temos pelo menos 2 snapshots (evitar falso positivo com 1 ponto)
    qtd = snapshots_recentes.count()
    if qtd < 2:
        return

    # Confirmar duracao real (diferenca entre primeiro e ultimo snapshot)
    primeiro = snapshots_recentes.first()
    ultimo = snapshots_recentes.last()
    duracao = ultimo.coletado_em - primeiro.coletado_em

    if duracao < timedelta(hours=CORRENTE_BAIXA_HORAS):
        return

    horas = duracao.total_seconds() / 3600
    _criar_ou_manter_alerta(
        usina=usina,
        categoria='corrente_baixa',
        chave=chave,
        nivel='critico',
        mensagem=(
            f'Corrente baixa prolongada no inversor {inversor.numero_serie} — '
            f'AC: {corrente_ac:.2f}A, DC: {corrente_dc:.2f}A '
            f'(abaixo de {CORRENTE_MINIMA_A}A ha {horas:.1f} horas)'
        ),
        sugestao='Inversor pode estar com problema de geracao. Verificar paineis, cabos e conexoes.',
        equipamento_sn=chave,
    )
