"""
Tasks Celery do sistema de coleta.

disparar_coleta_geral   — agendada a cada 30min — inicia coleta de todos os provedores ativos
coletar_dados_provedor  — executa a coleta de um provedor específico
renovar_tokens_provedores — agendada a cada 6h — renova tokens de sessão (Hoymiles, FusionSolar)
limpar_snapshots_antigos  — agendada às 3h — remove snapshots com mais de 90 dias
"""
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from celery import shared_task
from django.db import transaction

from provedores.models import CredencialProvedor, CacheTokenProvedor
from provedores.cripto import descriptografar_credenciais, criptografar_credenciais
from provedores.registro import get_adaptador
from provedores.excecoes import ProvedorErroAuth, ProvedorErroRateLimit
from provedores.limitador import LimitadorRequisicoes
from coleta.ingestao import ServicoIngestao
from coleta.models import ConfiguracaoSistema, LogColeta

logger = logging.getLogger(__name__)


@shared_task
def disparar_coleta_geral():
    """
    Verifica provedores ativos e dispara coleta dos que já passaram
    do intervalo configurado (campo intervalo_coleta_minutos no admin).
    Chamada pelo Celery Beat a cada 30 minutos.
    """
    from django.utils import timezone as tz

    credenciais = CredencialProvedor.objects.filter(ativo=True)
    total = 0
    agora = tz.now()

    for cred in credenciais:
        intervalo_min = cred.intervalo_coleta_minutos or 30
        ultima = (
            LogColeta.objects
            .filter(credencial=cred)
            .values_list('iniciado_em', flat=True)
            .first()
        )
        if ultima is not None:
            segundos_desde_ultima = (agora - ultima).total_seconds()
            if segundos_desde_ultima < (intervalo_min * 60):
                continue

        coletar_dados_provedor.delay(str(cred.id))
        total += 1

    if total:
        logger.info('Coleta iniciada para %d provedor(es)', total)
    return total


def _pausar_usinas_inativas(provedor: str) -> int:
    """
    Desativa (ativo=False) usinas cujo último snapshot está mais antigo que
    o configurado em ConfiguracaoSistema.dias_sem_comunicacao_pausar.

    Usinas sem nenhum snapshot ainda registrado são ignoradas (recém-criadas).
    Para retomar uma usina pausada, reativar manualmente no admin.
    """
    from datetime import timedelta
    from django.utils import timezone as tz
    from usinas.models import Usina

    config = ConfiguracaoSistema.obter()
    limite = tz.now() - timedelta(days=config.dias_sem_comunicacao_pausar)

    pausadas = Usina.objects.filter(
        provedor=provedor,
        ativo=True,
        ultimo_snapshot__isnull=False,
        ultimo_snapshot__coletado_em__lt=limite,
    ).update(ativo=False)

    if pausadas:
        logger.info(
            '%s: %d usina(s) pausada(s) por inatividade (>%d dias sem coleta)',
            provedor, pausadas, config.dias_sem_comunicacao_pausar,
        )
    return pausadas


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    time_limit=300,
    soft_time_limit=240,
)
def coletar_dados_provedor(self, credencial_id: str):
    """
    Coleta dados completos de um provedor: usinas, inversores e alertas.

    Fluxo:
        1. Carrega e descriptografa as credenciais
        2. Monta o adaptador com token em cache (se houver)
        3. Busca usinas, inversores (em paralelo) e alertas
        4. Salva tudo em transação atômica
        5. Persiste token novo no cache
        6. Registra o resultado no LogColeta
    """
    inicio = time.time()

    try:
        credencial = CredencialProvedor.objects.get(pk=credencial_id, ativo=True)
    except CredencialProvedor.DoesNotExist:
        logger.warning('Credencial %s não encontrada ou inativa', credencial_id)
        return

    # Auto-pausa de usinas inativas antes de coletar — evita reprocessar usinas
    # que não comunicam há mais tempo que o limite configurado.
    _pausar_usinas_inativas(credencial.provedor)

    credenciais_dict = descriptografar_credenciais(credencial.credenciais_enc)

    # Mesclar token em cache (se existir) nas credenciais para o adaptador
    try:
        cache = credencial.cache_token
        dados_token = descriptografar_credenciais(cache.dados_token_enc)
        credenciais_dict.update(dados_token)
    except CacheTokenProvedor.DoesNotExist:
        pass

    adaptador = get_adaptador(credencial.provedor, credenciais_dict)

    # Verificar intervalo mínimo entre coletas (provedores com rate limit rígido, ex: FusionSolar)
    min_intervalo = adaptador.capacidades.min_intervalo_coleta_segundos
    if min_intervalo > 0:
        from django.utils import timezone
        ultima = (
            LogColeta.objects
            .filter(credencial=credencial, status='sucesso')
            .values_list('iniciado_em', flat=True)
            .first()
        )
        if ultima is not None:
            segundos_desde_ultima = (timezone.now() - ultima).total_seconds()
            if segundos_desde_ultima < min_intervalo:
                logger.info(
                    '%s: coleta ignorada — última bem-sucedida há %.0fs (mínimo %ds)',
                    credencial.provedor, segundos_desde_ultima, min_intervalo,
                )
                return

    try:
        # 1. Buscar usinas
        with LimitadorRequisicoes(credencial.provedor):
            dados_usinas = adaptador.buscar_usinas()

        if not dados_usinas:
            logger.warning('%s: nenhuma usina encontrada', credencial.provedor)
            LogColeta.objects.create(credencial=credencial, status='parcial',
                                     duracao_ms=int((time.time() - inicio) * 1000))
            return

        # 2. Buscar inversores em paralelo (fora da transação — são chamadas HTTP)
        inversores_por_usina: dict[str, list] = {}
        if adaptador.capacidades.suporta_inversores:
            max_workers = adaptador.capacidades.limite_requisicoes
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futuras = {
                    executor.submit(adaptador.buscar_inversores, u.id_usina_provedor): u.id_usina_provedor
                    for u in dados_usinas
                }
                for futura in as_completed(futuras):
                    id_usina = futuras[futura]
                    try:
                        inversores_por_usina[id_usina] = futura.result()
                    except Exception as exc:
                        logger.warning('%s: erro ao buscar inversores de %s: %s',
                                       credencial.provedor, id_usina, exc)
                        inversores_por_usina[id_usina] = []

        # 3. Buscar alertas
        dados_alertas = []
        if adaptador.capacidades.suporta_alertas:
            try:
                with LimitadorRequisicoes(credencial.provedor):
                    if adaptador.capacidades.alertas_por_conta:
                        dados_alertas = adaptador.buscar_alertas()
                    else:
                        for u in dados_usinas:
                            dados_alertas.extend(adaptador.buscar_alertas(u.id_usina_provedor))
            except Exception as exc:
                logger.warning('%s: erro ao buscar alertas: %s', credencial.provedor, exc)

        # 4. Persistir tudo em transação atômica + análise de alertas internos
        from alertas.analise import analisar_usina
        from usinas.models import Usina

        # IDs de usinas pausadas para este provedor — não processar snapshot nem alertas
        ids_pausadas = set(
            Usina.objects
            .filter(provedor=credencial.provedor, ativo=False)
            .values_list('id_usina_provedor', flat=True)
        )

        ingestao = ServicoIngestao(credencial)
        usinas_por_id_provedor = {}
        total_inversores = 0

        with transaction.atomic():
            for dados_usina in dados_usinas:
                if dados_usina.id_usina_provedor in ids_pausadas:
                    continue
                usina = ingestao.upsert_usina(dados_usina)
                snapshot_usina = ingestao.criar_snapshot_usina(usina, dados_usina)
                usinas_por_id_provedor[dados_usina.id_usina_provedor] = usina

                inversores_snapshots = []
                for dados_inv in inversores_por_usina.get(dados_usina.id_usina_provedor, []):
                    inversor = ingestao.upsert_inversor(usina, dados_inv)
                    snap_inv = ingestao.criar_snapshot_inversor(inversor, dados_inv)
                    inversores_snapshots.append((inversor, snap_inv))
                    total_inversores += 1

                # Análise de alertas internos (após snapshot salvo)
                try:
                    analisar_usina(usina, snapshot_usina, inversores_snapshots)
                except Exception as exc:
                    logger.warning('%s: erro na análise interna de %s: %s',
                                   credencial.provedor, usina.nome, exc)

            ingestao.sincronizar_alertas(dados_alertas, usinas_por_id_provedor)

        # 5. Salvar token novo no cache
        token_novo = adaptador.obter_cache_token()
        if token_novo:
            CacheTokenProvedor.objects.update_or_create(
                credencial=credencial,
                defaults={'dados_token_enc': criptografar_credenciais(token_novo)},
            )

        # 6. Limpar flag de atenção se estava marcado
        if credencial.precisa_atencao:
            CredencialProvedor.objects.filter(pk=credencial.pk).update(precisa_atencao=False)

        duracao_ms = int((time.time() - inicio) * 1000)
        LogColeta.objects.create(
            credencial=credencial,
            status='sucesso',
            usinas_coletadas=len(dados_usinas),
            inversores_coletados=total_inversores,
            alertas_sincronizados=len(dados_alertas),
            duracao_ms=duracao_ms,
        )
        logger.info('%s: coleta concluída — %d usinas, %d inversores, %d alertas em %dms',
                    credencial.provedor, len(dados_usinas), total_inversores, len(dados_alertas), duracao_ms)

    except ProvedorErroAuth as exc:
        # Erro de autenticação — não tentar novamente, marcar para atenção manual
        logger.error('%s: erro de autenticação — %s', credencial.provedor, exc)
        CredencialProvedor.objects.filter(pk=credencial.pk).update(precisa_atencao=True)
        LogColeta.objects.create(
            credencial=credencial,
            status='auth_erro',
            detalhe_erro=str(exc),
            duracao_ms=int((time.time() - inicio) * 1000),
        )

    except ProvedorErroRateLimit as exc:
        logger.warning('%s: rate limit atingido — aguardando próximo ciclo do Beat',
                       credencial.provedor)
        # Persistir token atualizado mesmo em falha por rate limit.
        # O adaptador pode ter feito re-login durante a tentativa (para lidar com 305).
        # Se o token novo não for salvo, o próximo ciclo carrega o token expirado do banco
        # e repete o ciclo: 305 → re-login → 407, multiplicando os logins desnecessários.
        try:
            token_novo = adaptador.obter_cache_token()
            if token_novo:
                CacheTokenProvedor.objects.update_or_create(
                    credencial=credencial,
                    defaults={'dados_token_enc': criptografar_credenciais(token_novo)},
                )
        except Exception:
            pass  # falha ao salvar token não deve bloquear o próximo ciclo
        # Não retentar: provedores com min_intervalo (ex: FusionSolar) têm rate limit estrutural.
        # Retries rápidos só queimam quota e ativam backoffs desnecessários.
        # O próximo ciclo do Beat verificará o min_intervalo e tentará no momento correto.
        LogColeta.objects.create(
            credencial=credencial,
            status='erro',
            detalhe_erro=str(exc),
            duracao_ms=int((time.time() - inicio) * 1000),
        )

    except Exception as exc:
        logger.error('%s: erro inesperado — %s', credencial.provedor, exc, exc_info=True)
        LogColeta.objects.create(
            credencial=credencial,
            status='erro',
            detalhe_erro=str(exc),
            duracao_ms=int((time.time() - inicio) * 1000),
        )
        raise self.retry(exc=exc)


@shared_task
def renovar_tokens_provedores():
    """
    Renova tokens de sessão dos provedores que suportam refresh (Hoymiles, FusionSolar).
    Chamada pelo Celery Beat a cada 6 horas.
    """
    caches = CacheTokenProvedor.objects.select_related('credencial').filter(
        credencial__ativo=True,
    )
    renovados = 0
    for cache in caches:
        cred = cache.credencial
        try:
            credenciais_dict = descriptografar_credenciais(cred.credenciais_enc)
            dados_token = descriptografar_credenciais(cache.dados_token_enc)
            credenciais_dict.update(dados_token)

            adaptador = get_adaptador(cred.provedor, credenciais_dict)
            novo_token = adaptador.renovar_token(dados_token)

            cache.dados_token_enc = criptografar_credenciais(novo_token)
            cache.save(update_fields=['dados_token_enc', 'atualizado_em'])
            renovados += 1
        except Exception as exc:
            logger.error('%s: falha ao renovar token — %s', cred.provedor, exc)
            CredencialProvedor.objects.filter(pk=cred.pk).update(precisa_atencao=True)

    logger.info('Tokens renovados: %d', renovados)
    return renovados


@shared_task
def limpar_snapshots_antigos():
    """
    Remove snapshots com mais de 90 dias para controlar o crescimento do banco.
    Chamada pelo Celery Beat diariamente às 3h da manhã.
    """
    from django.utils import timezone
    from datetime import timedelta
    from usinas.models import SnapshotUsina, SnapshotInversor

    corte = timezone.now() - timedelta(days=90)

    qtd_usinas = SnapshotUsina.objects.filter(coletado_em__lt=corte).delete()[0]
    qtd_inversores = SnapshotInversor.objects.filter(coletado_em__lt=corte).delete()[0]

    logger.info('Limpeza: %d snapshots de usinas e %d de inversores removidos', qtd_usinas, qtd_inversores)
    return {'snapshots_usinas': qtd_usinas, 'snapshots_inversores': qtd_inversores}
