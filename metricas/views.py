"""
Endpoint /metricas/ — expõe dados no formato Prometheus para scraping.

Autenticação: token fixo configurado em METRICAS_TOKEN no .env
Header aceito: Authorization: Bearer <token>

As métricas são geradas sob demanda a cada scrape (sem cache).
"""
import logging
from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden

from prometheus_client import Gauge, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST

logger = logging.getLogger(__name__)


def _verificar_token(request) -> bool:
    """Verifica o token de autenticação da requisição."""
    token_esperado = getattr(settings, 'METRICAS_TOKEN', '')
    if not token_esperado:
        logger.warning('METRICAS_TOKEN não configurado — acesso negado por segurança')
        return False

    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:] == token_esperado

    token_header = request.META.get('HTTP_X_METRICS_TOKEN', '')
    return token_header == token_esperado


def metricas_view(request):
    if not _verificar_token(request):
        return HttpResponseForbidden('Token inválido ou ausente')

    try:
        return HttpResponse(
            _gerar_metricas(),
            content_type=CONTENT_TYPE_LATEST,
        )
    except Exception as exc:
        logger.error('Erro ao gerar métricas: %s', exc, exc_info=True)
        return HttpResponse('# Erro ao gerar métricas\n', content_type=CONTENT_TYPE_LATEST, status=500)


def _gerar_metricas() -> bytes:
    """Gera todas as métricas Prometheus a partir do banco de dados atual."""
    from usinas.models import Usina
    from alertas.models import Alerta
    from coleta.models import LogColeta

    registry = CollectorRegistry()

    # ── Métricas por usina ───────────────────────────────────────────────────
    labels_usina = ['provedor', 'id_usina', 'nome_usina']

    g_potencia = Gauge('solar_usina_potencia_kw', 'Potência atual da usina (kW)', labels_usina, registry=registry)
    g_energia_hoje = Gauge('solar_usina_energia_hoje_kwh', 'Energia gerada hoje (kWh)', labels_usina, registry=registry)
    g_energia_total = Gauge('solar_usina_energia_total_kwh', 'Energia total gerada (kWh)', labels_usina, registry=registry)
    g_status = Gauge('solar_usina_status', 'Status da usina (0=normal, 1=aviso, 2=offline, 3=construção)', labels_usina, registry=registry)
    g_qtd_alertas = Gauge('solar_usina_qtd_alertas', 'Quantidade de alertas ativos reportados pelo provedor', labels_usina, registry=registry)

    # ── Métricas por inversor ────────────────────────────────────────────────
    g_pac = Gauge('solar_inversor_pac_kw', 'Potência AC atual do inversor (kW)',
                  labels_usina + ['serial', 'modelo'], registry=registry)

    # ── Métricas de frota ────────────────────────────────────────────────────
    g_frota = Gauge('solar_frota_potencia_kw', 'Potência total da frota (kW)', ['provedor'], registry=registry)

    # ── Métricas de alertas ativos ───────────────────────────────────────────
    g_alerta = Gauge('solar_usina_alerta_ativo',
                     'Alerta ativo (1 por alerta). Use para tabela de problemas.',
                     labels_usina + ['mensagem', 'nivel'],
                     registry=registry)

    # ── Última coleta bem-sucedida ───────────────────────────────────────────
    g_ultima_coleta = Gauge('solar_ultima_coleta_timestamp',
                            'Unix timestamp da última coleta bem-sucedida',
                            ['provedor'], registry=registry)

    # ── Preencher dados ──────────────────────────────────────────────────────
    _STATUS_VALOR = {'normal': 0, 'aviso': 1, 'offline': 2, 'construcao': 3}

    totais_por_provedor: dict[str, float] = {}
    usinas = Usina.objects.filter(ativo=True).select_related('ultimo_snapshot')

    for usina in usinas:
        snap = usina.ultimo_snapshot
        if not snap:
            continue

        lbl = [usina.provedor, str(usina.id), usina.nome]
        g_potencia.labels(*lbl).set(snap.potencia_kw or 0)
        g_energia_hoje.labels(*lbl).set(snap.energia_hoje_kwh or 0)
        g_energia_total.labels(*lbl).set(snap.energia_total_kwh or 0)
        g_status.labels(*lbl).set(_STATUS_VALOR.get(snap.status, 2))
        g_qtd_alertas.labels(*lbl).set(snap.qtd_alertas or 0)

        # Acumular frota por provedor
        totais_por_provedor[usina.provedor] = (
            totais_por_provedor.get(usina.provedor, 0) + (snap.potencia_kw or 0)
        )

        # Inversores
        for inv in usina.inversores.select_related('ultimo_snapshot').all():
            inv_snap = inv.ultimo_snapshot
            if inv_snap:
                g_pac.labels(*lbl, inv.numero_serie or str(inv.id), inv.modelo or '').set(inv_snap.pac_kw or 0)

    for provedor, total in totais_por_provedor.items():
        g_frota.labels(provedor).set(total)

    # Alertas ativos
    alertas = Alerta.objects.filter(estado='ativo').select_related('usina')
    for alerta in alertas:
        usina = alerta.usina
        lbl = [usina.provedor, str(usina.id), usina.nome]
        g_alerta.labels(*lbl, alerta.mensagem[:100], alerta.nivel).set(1)

    # Última coleta bem-sucedida por provedor
    from django.db.models import Max
    logs = (LogColeta.objects
            .filter(status='sucesso')
            .values('credencial__provedor')
            .annotate(ultima=Max('iniciado_em')))
    for log in logs:
        provedor = log['credencial__provedor']
        ultima = log['ultima']
        if ultima:
            g_ultima_coleta.labels(provedor).set(ultima.timestamp())

    return generate_latest(registry)
