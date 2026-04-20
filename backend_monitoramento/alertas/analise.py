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
    - sobretensao: tensao AC > limite da usina, persistida por SOBRETENSAO_N_COLETAS
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
TENSAO_SOBRETENSAO_V_PADRAO = 240.0  # fallback — cada usina tem seu próprio threshold
CORRENTE_MINIMA_A = 0.1
CORRENTE_BAIXA_HORAS = 2

# Persistência para sobretensão: precisa N coletas consecutivas acima do limite para abrir
# e N coletas consecutivas iguais ou abaixo para fechar. Evita oscilar ao redor do limite.
# Regra do limite: > usina.tensao_sobretensao_v abre; <= fecha (borda é estado "normal").
SOBRETENSAO_N_COLETAS = 3

# Janela de tolerância ao cruzar timestamps de SnapshotUsina com SnapshotInversor.
# Em uma mesma coleta, os timestamps não são idênticos (snapshots são criados em
# momentos ligeiramente diferentes). Uma janela pequena garante que correlacionamos
# snapshots da mesma coleta sem pegar snapshots de coletas adjacentes.
_JANELA_CICLO = timedelta(minutes=5)


def _tem_garantia_ativa(usina: Usina) -> bool:
    """Retorna True se a usina tem garantia registrada e ainda ativa."""
    garantia = getattr(usina, 'garantia', None)
    return garantia is not None and garantia.ativa


def _verificar_garantia_expirando(usina: Usina) -> None:
    """Cria/resolve alerta quando a garantia está perto do fim.

    Limites em ConfiguracaoSistema: dias_aviso_garantia_proxima e _urgente.
    """
    from coleta.models import ConfiguracaoSistema

    garantia = getattr(usina, 'garantia', None)
    chave = str(usina.id_usina_provedor)
    if garantia is None or not garantia.ativa:
        _resolver_alerta_interno(usina, 'garantia_expirando', chave)
        return

    config = ConfiguracaoSistema.obter()
    dias = garantia.dias_restantes
    if dias > config.dias_aviso_garantia_proxima:
        _resolver_alerta_interno(usina, 'garantia_expirando', chave)
        return

    nivel = 'importante' if dias <= config.dias_aviso_garantia_urgente else 'aviso'
    _enriquecer_ou_criar(
        usina=usina,
        categoria='garantia_expirando',
        chave=chave,
        nivel=nivel,
        mensagem=f'Garantia da usina termina em {dias} dia(s) — data fim: {garantia.data_fim.strftime("%d/%m/%Y")}',
        sugestao='Entrar em contato com o cliente para renovação antes do fim da garantia.',
    )


def analisar_usina(usina: Usina, snapshot: SnapshotUsina, inversores_snapshots: list[tuple[Inversor, SnapshotInversor | None]]) -> None:
    """Analisa dados de uma usina e seus inversores. Alertas agrupados por usina+categoria.

    Só gera alertas para usinas com garantia ativa. Usinas sem garantia (ou garantia expirada)
    continuam sendo coletadas — os dados viram métricas de dashboard — mas não produzem alertas.
    """
    if not _tem_garantia_ativa(usina):
        return

    _verificar_garantia_expirando(usina)

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
        _verificar_sem_geracao_diurna(usina, snapshot, inversores_snapshots, agora)

    _verificar_sem_comunicacao(usina, snapshot, agora)

    # === Alertas de inversor (agrupados por usina+categoria) ===
    inversores_tensao_zero = []
    inversores_sobretensao = []
    inversores_corrente_baixa = []

    limite_sobretensao = usina.tensao_sobretensao_v or TENSAO_SOBRETENSAO_V_PADRAO

    for inversor, snap_inv in inversores_snapshots:
        if snap_inv is None:
            continue

        # Tensao zero
        if snap_inv.tensao_ac_v is not None and snap_inv.tensao_ac_v == 0:
            inversores_tensao_zero.append((inversor, snap_inv))

        # Sobretensao — só passa do limite (> limite); igual/abaixo é considerado normal.
        # A persistência (abrir apenas após N coletas consecutivas) é aplicada depois,
        # em _alerta_agrupado_sobretensao, consultando o histórico dos últimos snapshots.
        if snap_inv.tensao_ac_v is not None and snap_inv.tensao_ac_v > limite_sobretensao:
            inversores_sobretensao.append((inversor, snap_inv))

        # Corrente baixa (progressivo — verifica historico)
        if horario_corrente:
            if _inversor_corrente_baixa_prolongada(inversor, snap_inv, agora):
                inversores_corrente_baixa.append((inversor, snap_inv))

    # Gerar alertas agrupados
    _alerta_agrupado_tensao_zero(usina, inversores_tensao_zero, inversores_snapshots)
    _alerta_agrupado_sobretensao(usina, inversores_sobretensao, inversores_snapshots, limite_sobretensao)
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


def _alerta_agrupado_sobretensao(usina, afetados, todos, limite):
    """
    Persistência:
      - Abre o alerta apenas se as últimas SOBRETENSAO_N_COLETAS coletas tiveram
        pelo menos um inversor acima do limite.
      - Fecha o alerta apenas se as últimas SOBRETENSAO_N_COLETAS coletas tiveram
        todos os inversores iguais ou abaixo do limite.
      - Caso intermediário (oscilação), mantém o estado atual — não abre nem fecha.
    """
    chave = str(usina.id_usina_provedor)
    n_acima = _contar_coletas_com_sobretensao(usina, limite, SOBRETENSAO_N_COLETAS)

    if n_acima >= SOBRETENSAO_N_COLETAS:
        detalhes = [f'{inv.numero_serie}: {snap.tensao_ac_v:.1f}V' for inv, snap in afetados]
        if not detalhes:
            # O histórico aponta sobretensão sustentada mas a coleta atual já normalizou:
            # ainda conta como anormal até termos N coletas consecutivas abaixo do limite.
            detalhes = [f'(coleta atual sem leitura acima de {limite}V)']
        _enriquecer_ou_criar(
            usina=usina,
            categoria='sobretensao',
            chave=chave,
            nivel='aviso',
            mensagem=f'Sobretensao em {len(afetados) or "1"} inversor(es) — {", ".join(detalhes)} (limite: {limite}V, persistencia: {SOBRETENSAO_N_COLETAS} coletas)',
            sugestao='Tensao acima do normal. Monitorar — risco de desligamento por protecao do inversor.',
        )
    elif n_acima == 0:
        _resolver_alerta_interno(usina, 'sobretensao', chave)
    # else: entre 1 e N-1 coletas afetadas → mantém estado atual (sem ação)


def _contar_coletas_com_sobretensao(usina, limite, n) -> int:
    """
    Retorna quantas das últimas `n` coletas da usina tiveram pelo menos um
    inversor com `tensao_ac_v > limite`. Retorna 0 se não há histórico suficiente
    (menos de `n` coletas) — assim o sistema aguarda dados estáveis antes de abrir
    ou fechar alertas.
    """
    timestamps = list(
        SnapshotUsina.objects
        .filter(usina=usina)
        .order_by('-coletado_em')
        .values_list('coletado_em', flat=True)[:n]
    )
    if len(timestamps) < n:
        return 0

    contagem = 0
    for t in timestamps:
        existe_acima = SnapshotInversor.objects.filter(
            inversor__usina=usina,
            coletado_em__gte=t - _JANELA_CICLO,
            coletado_em__lte=t + _JANELA_CICLO,
            tensao_ac_v__gt=limite,
        ).exists()
        if existe_acima:
            contagem += 1
    return contagem


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

def _verificar_sem_geracao_diurna(usina, snapshot, inversores_snapshots, agora):
    """
    Verifica se a usina esta sem gerar em horario comercial.
    Distingue entre 'sem comunicacao' (inversores offline) e 'sem geracao' (inversores online mas sem gerar).
    """
    chave = str(usina.id_usina_provedor)

    if snapshot.potencia_kw <= 0:
        # Verificar se o problema e comunicacao (todos os inversores offline)
        total_inv = len(inversores_snapshots)
        offline = sum(
            1 for _, snap_inv in inversores_snapshots
            if snap_inv is None or snap_inv.estado == 'offline'
        )

        if total_inv > 0 and offline == total_inv:
            # Todos offline — problema de comunicacao, nao de geracao
            _resolver_alerta_interno(usina, 'sem_geracao_diurna', chave)
            _enriquecer_ou_criar(
                usina=usina,
                categoria='sem_comunicacao',
                chave=chave,
                nivel='importante',
                mensagem=f'Todos os {total_inv} inversor(es) offline — possivel falha de comunicacao',
                sugestao='Nenhum inversor esta comunicando. Verificar Wi-Fi, datalogger e alimentacao eletrica do local.',
            )
        else:
            # Inversores online mas sem gerar — problema de geracao
            _enriquecer_ou_criar(
                usina=usina,
                categoria='sem_geracao_diurna',
                chave=chave,
                nivel='importante',
                mensagem=f'Usina sem geracao em horario comercial — potencia: {snapshot.potencia_kw} kW ({offline}/{total_inv} inversores offline)',
                sugestao='Verificar se ha problema no inversor, disjuntor ou falta de energia na rede.',
            )
    else:
        _resolver_alerta_interno(usina, 'sem_geracao_diurna', chave)
        _resolver_alerta_interno(usina, 'sem_comunicacao', chave)


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

def _enriquecer_ou_criar(usina, categoria, chave, nivel, mensagem, sugestao='', equipamento_sn=''):
    """
    Cria ou atualiza um alerta interno. Nao enriquece alertas do provedor
    para evitar categorias erradas (ex: L3 warning categorizado como sem_geracao).
    """
    agora = dj_timezone.now()

    if SupressaoInterna.objects.filter(usina=usina, categoria=categoria).exists():
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
    """Resolve alerta interno pelo ID."""
    id_alerta = f'interno_{categoria}_{chave}'
    Alerta.objects.filter(
        usina=usina,
        id_alerta_provedor=id_alerta,
        estado='ativo',
    ).update(estado='resolvido', fim=dj_timezone.now())
