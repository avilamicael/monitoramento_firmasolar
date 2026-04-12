"""
Analise interna de dados coletados para gerar alertas inteligentes.

Chamado ao final de cada ciclo de coleta, apos salvar snapshots.
Analisa dados de usinas e inversores para:
  1. Enriquecer alertas existentes do provedor com diagnostico
  2. Criar alertas novos para problemas nao reportados pelo provedor

Regra: alertas de inversor sao AGRUPADOS por usina+categoria.
Uma usina com 5 inversores em sobretensao gera 1 alerta, nao 5.

Tipos de alerta:
  Instantaneos:
    - tensao_zero: tensao AC = 0 em qualquer momento
    - sobretensao: tensao AC >= 240V
    - sem_geracao_diurna: usina com pac=0 entre 8h-18h
    - sem_comunicacao: inversor sem comunicar ha 24h+

  Progressivos:
    - corrente_baixa: corrente AC/DC <= 0.1A por 2+ horas entre 9h-17h
"""
import logging
from datetime import timedelta

from django.utils import timezone as dj_timezone

from usinas.models import Usina, SnapshotUsina, Inversor, SnapshotInversor
from alertas.models import Alerta, SupressaoInterna

logger = logging.getLogger(__name__)

# Horario comercial (fixo — todas as usinas em SC)
HORA_INICIO_COMERCIAL = 8
HORA_FIM_COMERCIAL = 18
HORA_INICIO_CORRENTE = 9
HORA_FIM_CORRENTE = 17

# Thresholds
TENSAO_SOBRETENSAO_V = 240.0
CORRENTE_MINIMA_A = 0.1
CORRENTE_BAIXA_HORAS = 2


def analisar_usina(usina: Usina, snapshot: SnapshotUsina, inversores_snapshots: list[tuple[Inversor, SnapshotInversor | None]]) -> None:
    """Analisa dados de uma usina e seus inversores. Alertas agrupados por usina+categoria."""
    agora = dj_timezone.now()

    try:
        import zoneinfo
        tz = zoneinfo.ZoneInfo(usina.fuso_horario or 'America/Sao_Paulo')
        hora_local = agora.astimezone(tz).hour
    except Exception:
        hora_local = agora.hour - 3

    horario_comercial = HORA_INICIO_COMERCIAL <= hora_local < HORA_FIM_COMERCIAL
    horario_corrente = HORA_INICIO_CORRENTE <= hora_local < HORA_FIM_CORRENTE

    # === Alertas de usina (nivel planta) ===
    if horario_comercial:
        _verificar_sem_geracao_diurna(usina, snapshot, agora)

    _verificar_sem_comunicacao(usina, snapshot, agora)

    # === Alertas de inversor (agrupados por usina+categoria) ===
    inversores_tensao_zero = []
    inversores_sobretensao = []
    inversores_corrente_baixa = []

    for inversor, snap_inv in inversores_snapshots:
        if snap_inv is None:
            continue

        # Tensao zero
        if snap_inv.tensao_ac_v is not None and snap_inv.tensao_ac_v == 0:
            inversores_tensao_zero.append((inversor, snap_inv))

        # Sobretensao
        if snap_inv.tensao_ac_v is not None and snap_inv.tensao_ac_v >= TENSAO_SOBRETENSAO_V:
            inversores_sobretensao.append((inversor, snap_inv))

        # Corrente baixa (progressivo — verifica historico)
        if horario_corrente:
            if _inversor_corrente_baixa_prolongada(inversor, snap_inv, agora):
                inversores_corrente_baixa.append((inversor, snap_inv))

    # Gerar alertas agrupados
    _alerta_agrupado_tensao_zero(usina, inversores_tensao_zero, inversores_snapshots)
    _alerta_agrupado_sobretensao(usina, inversores_sobretensao, inversores_snapshots)
    _alerta_agrupado_corrente_baixa(usina, inversores_corrente_baixa, inversores_snapshots)


# === Funcoes de alerta agrupado ===

def _alerta_agrupado_tensao_zero(usina, afetados, todos):
    chave = str(usina.id_usina_provedor)
    if afetados:
        sns = [inv.numero_serie for inv, _ in afetados]
        _enriquecer_ou_criar(
            usina=usina,
            categoria='tensao_zero',
            chave=chave,
            nivel='critico',
            mensagem=f'Tensao AC zero em {len(afetados)} inversor(es): {", ".join(sns)}',
            sugestao='Inversor(es) desligado(s). Verificar disjuntor, rede eletrica ou defeito interno.',
        )
    else:
        _resolver_alerta_interno(usina, 'tensao_zero', chave)


def _alerta_agrupado_sobretensao(usina, afetados, todos):
    chave = str(usina.id_usina_provedor)
    if afetados:
        detalhes = [f'{inv.numero_serie}: {snap.tensao_ac_v:.1f}V' for inv, snap in afetados]
        _enriquecer_ou_criar(
            usina=usina,
            categoria='sobretensao',
            chave=chave,
            nivel='aviso',
            mensagem=f'Sobretensao em {len(afetados)} inversor(es) — {", ".join(detalhes)} (limite: {TENSAO_SOBRETENSAO_V}V)',
            sugestao='Tensao acima do normal. Monitorar — risco de desligamento por protecao do inversor.',
        )
    else:
        _resolver_alerta_interno(usina, 'sobretensao', chave)


def _alerta_agrupado_corrente_baixa(usina, afetados, todos):
    chave = str(usina.id_usina_provedor)
    if afetados:
        sns = [inv.numero_serie for inv, _ in afetados]
        _enriquecer_ou_criar(
            usina=usina,
            categoria='corrente_baixa',
            chave=chave,
            nivel='critico',
            mensagem=f'Corrente baixa prolongada em {len(afetados)} inversor(es): {", ".join(sns)} (abaixo de {CORRENTE_MINIMA_A}A ha mais de {CORRENTE_BAIXA_HORAS}h)',
            sugestao='Inversor(es) com problema de geracao. Verificar paineis, cabos e conexoes.',
        )
    else:
        _resolver_alerta_interno(usina, 'corrente_baixa', chave)


def _inversor_corrente_baixa_prolongada(inversor, snap, agora) -> bool:
    """Retorna True se a corrente esta baixa ha mais de CORRENTE_BAIXA_HORAS."""
    corrente_ac = snap.corrente_ac_a or 0
    corrente_dc = snap.corrente_dc_a or 0

    if corrente_ac > CORRENTE_MINIMA_A or corrente_dc > CORRENTE_MINIMA_A:
        return False

    limite = agora - timedelta(hours=CORRENTE_BAIXA_HORAS)
    snapshots_recentes = (
        SnapshotInversor.objects
        .filter(inversor=inversor, coletado_em__gte=limite)
        .order_by('coletado_em')
    )

    if snapshots_recentes.count() < 2:
        return False

    todos_baixos = all(
        (s.corrente_ac_a or 0) <= CORRENTE_MINIMA_A and (s.corrente_dc_a or 0) <= CORRENTE_MINIMA_A
        for s in snapshots_recentes
    )
    if not todos_baixos:
        return False

    primeiro = snapshots_recentes.first()
    ultimo = snapshots_recentes.last()
    return (ultimo.coletado_em - primeiro.coletado_em) >= timedelta(hours=CORRENTE_BAIXA_HORAS)


# === Alertas de usina (nivel planta) ===

def _verificar_sem_geracao_diurna(usina, snapshot, agora):
    chave = str(usina.id_usina_provedor)
    if snapshot.potencia_kw <= 0:
        _enriquecer_ou_criar(
            usina=usina,
            categoria='sem_geracao_diurna',
            chave=chave,
            nivel='importante',
            mensagem=f'Usina sem geracao em horario comercial — potencia: {snapshot.potencia_kw} kW',
            sugestao='Verificar se ha problema no inversor, disjuntor ou falta de energia na rede.',
        )
    else:
        _resolver_alerta_interno(usina, 'sem_geracao_diurna', chave)


def _verificar_sem_comunicacao(usina, snapshot, agora):
    chave = str(usina.id_usina_provedor)
    ultima_comunicacao = snapshot.data_medicao or snapshot.coletado_em
    diff = agora - ultima_comunicacao
    horas = diff.total_seconds() / 3600
    dias = diff.days

    if horas >= 24:
        if dias >= 7:
            nivel = 'importante'
            tempo = f'{dias} dias'
        else:
            nivel = 'aviso'
            tempo = f'{dias} dia(s)' if dias >= 1 else f'{int(horas)} horas'

        _enriquecer_ou_criar(
            usina=usina,
            categoria='sem_comunicacao',
            chave=chave,
            nivel=nivel,
            mensagem=f'Inversor sem comunicacao ha {tempo} — ultima comunicacao: {ultima_comunicacao.strftime("%d/%m/%Y %H:%M")}',
            sugestao='Possivel falha de Wi-Fi ou datalogger desconectado. Verificar conexao de internet do local.',
        )
    else:
        _resolver_alerta_interno(usina, 'sem_comunicacao', chave)


# === Funcoes auxiliares ===

def _buscar_alerta_provedor_relacionado(usina, categoria, equipamento_sn=''):
    filtro = {'usina': usina, 'origem': 'provedor', 'estado': 'ativo'}
    if equipamento_sn:
        filtro['equipamento_sn'] = equipamento_sn
    return Alerta.objects.filter(**filtro).order_by('-inicio').first()


def _enriquecer_ou_criar(usina, categoria, chave, nivel, mensagem, sugestao='', equipamento_sn=''):
    agora = dj_timezone.now()

    if SupressaoInterna.objects.filter(usina=usina, categoria=categoria).exists():
        return

    alerta_provedor = _buscar_alerta_provedor_relacionado(usina, categoria, equipamento_sn)
    if alerta_provedor:
        campos = {}
        if not alerta_provedor.categoria:
            campos['categoria'] = categoria
        if not alerta_provedor.sugestao and sugestao:
            campos['sugestao'] = sugestao
        if alerta_provedor.nivel_escalou_para(nivel):
            campos['nivel'] = nivel
        if campos:
            Alerta.objects.filter(pk=alerta_provedor.pk).update(**campos)
        return

    id_alerta = f'interno_{categoria}_{chave}'
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
        campos = {'mensagem': mensagem}
        if alerta.estado == 'resolvido':
            campos['estado'] = 'ativo'
            campos['fim'] = None
        if alerta.nivel_escalou_para(nivel):
            campos['nivel'] = nivel
        Alerta.objects.filter(pk=alerta.pk).update(**campos)


def _resolver_alerta_interno(usina, categoria, chave):
    """Resolve alertas internos E alertas do provedor enriquecidos com esta categoria."""
    agora = dj_timezone.now()
    # Resolver alerta interno pelo ID
    id_alerta = f'interno_{categoria}_{chave}'
    Alerta.objects.filter(
        usina=usina,
        id_alerta_provedor=id_alerta,
        estado='ativo',
    ).update(estado='resolvido', fim=agora)

    # Resolver alertas do provedor que foram enriquecidos com esta categoria
    Alerta.objects.filter(
        usina=usina,
        categoria=categoria,
        estado='ativo',
    ).update(estado='resolvido', fim=agora)
