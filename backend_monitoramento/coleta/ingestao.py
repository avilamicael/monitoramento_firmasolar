"""
ServicoIngestao — traduz os dados dos adaptadores para operações no banco.

Responsabilidades:
- Criar/atualizar usinas e inversores (upsert)
- Salvar snapshots de forma idempotente (get_or_create por janela de 10min)
- Sincronizar alertas: criar novos, atualizar existentes, resolver desaparecidos
- Disparar notificações para alertas novos e escalados

Todas as operações são chamadas dentro de uma transação atômica pela task de coleta.
"""
import logging
from datetime import datetime, timezone

from django.db import models, transaction
from django.utils import timezone as dj_timezone

from provedores.base import DadosUsina, DadosInversor, DadosAlerta
from usinas.models import Usina, SnapshotUsina, Inversor, SnapshotInversor, GarantiaUsina
from alertas.models import Alerta, CatalogoAlarme, RegraSupressao
from coleta.models import ConfiguracaoSistema
from alertas.categorizacao import inferir_categoria
from alertas.supressao_inteligente import e_desligamento_gradual, esta_gerando_agora

logger = logging.getLogger(__name__)


def _arredondar_coletado_em(dt: datetime, minutos: int = 10) -> datetime:
    """
    Arredonda para o múltiplo de N minutos mais próximo.
    Garante idempotência: duas coletas na mesma janela de 10min geram apenas 1 snapshot.
    """
    total_segundos = int(dt.timestamp())
    janela = minutos * 60
    arredondado = (total_segundos // janela) * janela
    return datetime.fromtimestamp(arredondado, tz=timezone.utc)


class ServicoIngestao:
    """
    Serviço de ingestão de dados.
    Instanciar uma vez por ciclo de coleta — armazena o coletado_em da rodada.
    """

    def __init__(self, credencial):
        self.credencial = credencial
        self.coletado_em = _arredondar_coletado_em(dj_timezone.now())

    def upsert_usina(self, dados: DadosUsina) -> Usina:
        """Cria ou recupera a usina. Atualiza nome/endereço se mudaram.
        Na primeira inserção, também cria a garantia padrão (meses configuráveis)."""
        usina, criada = Usina.objects.get_or_create(
            id_usina_provedor=dados.id_usina_provedor,
            provedor=self.credencial.provedor,
            defaults={
                'credencial': self.credencial,
                'nome': dados.nome,
                'capacidade_kwp': dados.capacidade_kwp,
                'fuso_horario': dados.fuso_horario,
                'endereco': dados.endereco,
            },
        )
        if criada:
            config = ConfiguracaoSistema.obter()
            GarantiaUsina.objects.get_or_create(
                usina=usina,
                defaults={
                    'data_inicio': dj_timezone.localdate(),
                    'meses': config.meses_garantia_padrao,
                    'observacoes': 'Garantia padrão criada automaticamente no primeiro registro da usina.',
                },
            )
        campos_alterados = []
        if usina.nome != dados.nome:
            usina.nome = dados.nome
            campos_alterados.append('nome')
        if dados.endereco and usina.endereco != dados.endereco:
            usina.endereco = dados.endereco
            campos_alterados.append('endereco')
        if campos_alterados:
            usina.save(update_fields=campos_alterados + ['atualizado_em'])
        return usina

    def criar_snapshot_usina(self, usina: Usina, dados: DadosUsina) -> SnapshotUsina:
        """Cria um snapshot de usina se ainda não existir para esta janela de tempo."""
        snapshot, criado = SnapshotUsina.objects.get_or_create(
            usina=usina,
            coletado_em=self.coletado_em,
            defaults={
                'data_medicao': dados.data_medicao,
                'potencia_kw': dados.potencia_atual_kw,
                'energia_hoje_kwh': dados.energia_hoje_kwh,
                'energia_mes_kwh': dados.energia_mes_kwh,
                'energia_total_kwh': dados.energia_total_kwh,
                'status': dados.status,
                'qtd_inversores': dados.qtd_inversores,
                'qtd_inversores_online': dados.qtd_inversores_online,
                'qtd_alertas': dados.qtd_alertas,
                'payload_bruto': dados.payload_bruto,
            },
        )
        if criado:
            Usina.objects.filter(pk=usina.pk).update(ultimo_snapshot=snapshot)
        return snapshot

    def upsert_inversor(self, usina: Usina, dados: DadosInversor) -> Inversor:
        """Cria ou recupera o inversor."""
        inversor, _ = Inversor.objects.get_or_create(
            usina=usina,
            id_inversor_provedor=dados.id_inversor_provedor,
            defaults={
                'numero_serie': dados.numero_serie,
                'modelo': dados.modelo,
            },
        )
        return inversor

    def criar_snapshot_inversor(self, inversor: Inversor, dados: DadosInversor) -> SnapshotInversor:
        """Cria um snapshot de inversor se ainda não existir para esta janela de tempo."""
        snapshot, criado = SnapshotInversor.objects.get_or_create(
            inversor=inversor,
            coletado_em=self.coletado_em,
            defaults={
                'data_medicao': dados.data_medicao,
                'estado': dados.estado,
                'pac_kw': dados.pac_kw,
                'energia_hoje_kwh': dados.energia_hoje_kwh,
                'energia_total_kwh': dados.energia_total_kwh,
                'soc_bateria': dados.soc_bateria,
                'strings_mppt': dados.strings_mppt,
                'tensao_ac_v': dados.tensao_ac_v,
                'corrente_ac_a': dados.corrente_ac_a,
                'tensao_dc_v': dados.tensao_dc_v,
                'corrente_dc_a': dados.corrente_dc_a,
                'frequencia_hz': dados.frequencia_hz,
                'temperatura_c': dados.temperatura_c,
                'payload_bruto': dados.payload_bruto,
            },
        )
        if criado:
            Inversor.objects.filter(pk=inversor.pk).update(ultimo_snapshot=snapshot)
        return snapshot

    def sincronizar_alertas(self, alertas: list[DadosAlerta], usinas_por_id_provedor: dict) -> None:
        """
        Sincroniza os alertas do provedor com o banco de dados.

        Invariante: existe no máximo UM alerta ativo por (usina, catalogo_alarme,
        origem='provedor'). Quando um alerta é resolvido e o mesmo tipo volta a
        aparecer, é criado um NOVO alerta (nunca reabre o antigo) — assim cada
        ocorrência fica preservada para contagem histórica de eventos.

        - Consulta o CatalogoAlarme para obter nível efetivo e verificar supressão
        - Alarmes suprimidos (globalmente ou via RegraSupressao) são ignorados
        - Se não há alerta ativo do tipo → cria novo com sufixo de timestamp
          e agenda notificação após commit
        - Se há alerta ativo do tipo → atualiza mensagem/nível/atualizado_em
          e notifica apenas se o nível escalou
        - Alertas ativos cujo tipo não apareceu neste ciclo → marca como resolvido

        Args:
            alertas: lista de alertas retornados pelo provedor neste ciclo
            usinas_por_id_provedor: dicionário {id_provedor: Usina} com as usinas deste ciclo
        """
        from notificacoes.tasks import enviar_notificacao_alerta
        from alertas.analise import sufixo_timestamp_id

        if not usinas_por_id_provedor:
            return

        # Identifica o provedor a partir da primeira usina (todas são do mesmo ciclo)
        provedor = next(iter(usinas_por_id_provedor.values())).provedor

        agora = dj_timezone.now()
        # PKs dos alertas tocados (criados ou atualizados) neste ciclo —
        # usado no final para resolver os que não apareceram.
        pks_tocados: set = set()

        for dados in alertas:
            usina = usinas_por_id_provedor.get(dados.id_usina_provedor)
            if usina is None:
                continue
            if not dados.id_alerta_provedor:
                continue

            # Alertas que o provedor já marcou como resolvidos não devem criar nem
            # manter registros ativos. Ignora aqui — o bloco de auto-resolução no
            # final do ciclo cuidará de fechar caso já existam no banco.
            if dados.estado == 'resolvido':
                continue

            # Só gera/reabre alertas do provedor para usinas com garantia ativa.
            # Usinas sem garantia continuam sendo coletadas (dados viram métrica)
            # mas não produzem alertas — mesmo comportamento de alertas internos
            # (alertas/analise.py::_tem_garantia_ativa).
            garantia = getattr(usina, 'garantia', None)
            if garantia is None or not garantia.ativa:
                continue

            # Lookup ou auto-criação no catálogo (apenas se o provedor envia um ID de tipo)
            catalogo = None
            nivel_efetivo = dados.nivel
            if dados.id_tipo_alarme_provedor:
                catalogo, criado_catalogo = CatalogoAlarme.objects.get_or_create(
                    provedor=provedor,
                    id_alarme_provedor=dados.id_tipo_alarme_provedor,
                    defaults={
                        'nome_pt': dados.mensagem[:200],
                        'nome_original': dados.mensagem[:200],
                        'nivel_padrao': dados.nivel,
                        'tipo': inferir_categoria(
                            dados.mensagem, provedor, dados.id_tipo_alarme_provedor
                        ),
                        'criado_auto': True,
                    },
                )
                if criado_catalogo:
                    logger.info(
                        '%s: novo tipo de alarme auto-cadastrado no catálogo: %s — "%s" [categoria: %s]',
                        provedor, dados.id_tipo_alarme_provedor, dados.mensagem[:80],
                        catalogo.tipo,
                    )

                # Supressão global no catálogo
                if catalogo.suprimido:
                    continue

                # Supressão por regra ativa (escopo usina ou todas)
                if RegraSupressao.objects.filter(
                    catalogo=catalogo,
                    escopo='todas',
                ).filter(
                    models.Q(ativo_ate__isnull=True) | models.Q(ativo_ate__gt=dj_timezone.now())
                ).exists():
                    continue

                if RegraSupressao.objects.filter(
                    catalogo=catalogo,
                    escopo='usina',
                    usina=usina,
                ).filter(
                    models.Q(ativo_ate__isnull=True) | models.Q(ativo_ate__gt=dj_timezone.now())
                ).exists():
                    continue

                # Nível efetivo: usa o do catálogo se foi sobrescrito pelo operador
                if catalogo.nivel_sobrescrito:
                    nivel_efetivo = catalogo.nivel_padrao

                # Supressões inteligentes para sistema_desligado:
                #   1) esta_gerando_agora: payload incoerente — a flag diz "desligado"
                #      mas o próprio snapshot (usina ou inversor) mostra geração.
                #      Aplica inclusive para resolver alertas já abertos por ciclos
                #      anteriores com a mesma incoerência (o bloco de auto-resolução
                #      no final de sincronizar_alertas cuida disso: basta não tocar
                #      o alerta neste ciclo).
                #   2) e_desligamento_gradual: pôr do sol normal — só aplica quando
                #      ainda não há alerta aberto (não queremos suprimir retroativamente
                #      um shutdown real que começou antes do entardecer).
                if catalogo.tipo == 'sistema_desligado':
                    if esta_gerando_agora(usina):
                        logger.info(
                            '%s: %s — flag sistema_desligado ignorada (usina gerando agora)',
                            provedor, usina.nome,
                        )
                        continue
                    ja_aberto = Alerta.objects.filter(
                        usina=usina,
                        catalogo_alarme=catalogo,
                        origem='provedor',
                        estado='ativo',
                    ).exists()
                    if not ja_aberto and e_desligamento_gradual(usina):
                        logger.debug(
                            '%s: %s — suprimido (desligamento gradual)',
                            provedor, usina.nome,
                        )
                        continue

            # Lookup do alerta ATIVO do mesmo tipo (catalogo) para essa usina.
            # Invariante: no máximo um ativo por (usina, catalogo, origem='provedor').
            alerta_ativo = None
            if catalogo is not None:
                alerta_ativo = (
                    Alerta.objects
                    .filter(
                        usina=usina,
                        catalogo_alarme=catalogo,
                        origem='provedor',
                        estado='ativo',
                    )
                    .order_by('-inicio')
                    .first()
                )

            if alerta_ativo is None:
                # Sem ativo existente — cria um novo. Sufixo de timestamp garante
                # unicidade do id_alerta_provedor mesmo se existir um resolvido
                # anterior com o mesmo prefixo (antes era `{plant}_{flag}`; agora
                # vira `{plant}_{flag}_{timestamp}`).
                id_unico = f'{dados.id_alerta_provedor}_{sufixo_timestamp_id(agora)}'
                alerta = Alerta.objects.create(
                    usina=usina,
                    origem='provedor',
                    catalogo_alarme=catalogo,
                    id_alerta_provedor=id_unico,
                    equipamento_sn=dados.equipamento_sn,
                    mensagem=dados.mensagem,
                    nivel=nivel_efetivo,
                    inicio=dados.inicio,
                    estado='ativo',
                    sugestao=dados.sugestao or (catalogo.sugestao if catalogo else ''),
                    payload_bruto=dados.payload_bruto,
                )
                pks_tocados.add(alerta.pk)
                alerta_id = str(alerta.id)
                transaction.on_commit(
                    lambda aid=alerta_id: enviar_notificacao_alerta.delay(aid, 'novo')
                )
                Alerta.objects.filter(pk=alerta.pk).update(
                    notificacao_enviada=True,
                    atualizado_em=agora,
                )
                continue

            # Há alerta ativo do mesmo tipo — atualiza in-place.
            pks_tocados.add(alerta_ativo.pk)
            if alerta_ativo.nivel_escalou_para(nivel_efetivo):
                alerta_id = str(alerta_ativo.id)
                transaction.on_commit(
                    lambda aid=alerta_id: enviar_notificacao_alerta.delay(aid, 'escalado')
                )

            campos_update = {
                'nivel': nivel_efetivo,
                'mensagem': dados.mensagem,
                'sugestao': dados.sugestao or (catalogo.sugestao if catalogo else ''),
                'payload_bruto': dados.payload_bruto,
                'atualizado_em': agora,
            }
            if catalogo and alerta_ativo.catalogo_alarme_id is None:
                campos_update['catalogo_alarme'] = catalogo
            Alerta.objects.filter(pk=alerta_ativo.pk).update(**campos_update)

        # Resolver alertas do provedor cujo tipo não apareceu neste ciclo
        # (exclui os que foram tocados — criados ou atualizados — acima).
        ids_usinas = [u.id for u in usinas_por_id_provedor.values()]
        resolvidos = Alerta.objects.filter(
            usina__in=ids_usinas,
            estado='ativo',
            origem='provedor',
        ).exclude(pk__in=pks_tocados)
        qtd_resolvidos = resolvidos.update(
            estado='resolvido',
            fim=agora,
            atualizado_em=agora,
        )
        if qtd_resolvidos:
            logger.info('Alertas resolvidos automaticamente: %d', qtd_resolvidos)
