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
from usinas.models import Usina, SnapshotUsina, Inversor, SnapshotInversor
from alertas.models import Alerta, CatalogoAlarme, RegraSupressao

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
        """Cria ou recupera a usina. Atualiza nome/endereço se mudaram."""
        usina, _ = Usina.objects.get_or_create(
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
                'payload_bruto': dados.payload_bruto,
            },
        )
        if criado:
            Inversor.objects.filter(pk=inversor.pk).update(ultimo_snapshot=snapshot)
        return snapshot

    def sincronizar_alertas(self, alertas: list[DadosAlerta], usinas_por_id_provedor: dict) -> None:
        """
        Sincroniza os alertas do provedor com o banco de dados:

        - Consulta o CatalogoAlarme para obter nível efetivo e verificar supressão
        - Alarmes suprimidos (globalmente ou via RegraSupressao) são ignorados
        - Novos alertas → cria + dispara notificação
        - Alertas existentes → detecta escalonamento; atualiza nível/sugestão
        - Alertas que sumiram do provedor → marca como 'resolvido'
        - Alertas 'em_atendimento' não têm o estado sobrescrito automaticamente

        Args:
            alertas: lista de alertas retornados pelo provedor neste ciclo
            usinas_por_id_provedor: dicionário {id_provedor: Usina} com as usinas deste ciclo
        """
        from notificacoes.servico import ServicoNotificacao
        servico_notificacao = ServicoNotificacao()

        if not usinas_por_id_provedor:
            return

        # Identifica o provedor a partir da primeira usina (todas são do mesmo ciclo)
        provedor = next(iter(usinas_por_id_provedor.values())).provedor

        ids_ativos_provedor: set[str] = set()

        for dados in alertas:
            usina = usinas_por_id_provedor.get(dados.id_usina_provedor)
            if usina is None:
                continue
            if not dados.id_alerta_provedor:
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
                        'criado_auto': True,
                    },
                )
                if criado_catalogo:
                    logger.info(
                        '%s: novo tipo de alarme auto-cadastrado no catálogo: %s — "%s"',
                        provedor, dados.id_tipo_alarme_provedor, dados.mensagem[:80],
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

            ids_ativos_provedor.add(dados.id_alerta_provedor)

            alerta, criado = Alerta.objects.get_or_create(
                usina=usina,
                id_alerta_provedor=dados.id_alerta_provedor,
                defaults={
                    'catalogo_alarme': catalogo,
                    'equipamento_sn': dados.equipamento_sn,
                    'mensagem': dados.mensagem,
                    'nivel': nivel_efetivo,
                    'inicio': dados.inicio,
                    'estado': 'ativo',
                    'sugestao': dados.sugestao or (catalogo.sugestao if catalogo else ''),
                    'payload_bruto': dados.payload_bruto,
                },
            )

            if criado:
                servico_notificacao.notificar_novo_alerta(alerta)
                Alerta.objects.filter(pk=alerta.pk).update(notificacao_enviada=True)
            else:
                # Detectar escalonamento (qualquer subida de nível, não só aviso→crítico)
                if alerta.nivel_escalou_para(nivel_efetivo):
                    servico_notificacao.notificar_alerta_escalado(alerta)

                campos_update = {
                    'nivel': nivel_efetivo,
                    'sugestao': dados.sugestao or (catalogo.sugestao if catalogo else ''),
                    'payload_bruto': dados.payload_bruto,
                }
                if catalogo and alerta.catalogo_alarme_id is None:
                    campos_update['catalogo_alarme'] = catalogo
                # Reabrir se tinha sido resolvido e voltou
                if alerta.estado == 'resolvido':
                    campos_update['estado'] = 'ativo'
                # Não sobrescreve 'em_atendimento' — equipe está ciente

                Alerta.objects.filter(pk=alerta.pk).update(**campos_update)

        # Resolver alertas que sumiram do provedor neste ciclo
        ids_usinas = [u.id for u in usinas_por_id_provedor.values()]
        resolvidos = Alerta.objects.filter(
            usina__in=ids_usinas,
            estado='ativo',
        ).exclude(
            id_alerta_provedor__in=ids_ativos_provedor,
        )
        qtd_resolvidos = resolvidos.update(
            estado='resolvido',
            fim=dj_timezone.now(),
        )
        if qtd_resolvidos:
            logger.info('Alertas resolvidos automaticamente: %d', qtd_resolvidos)
