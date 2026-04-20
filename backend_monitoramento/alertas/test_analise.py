"""
Testes de persistência + histerese para alertas internos de sobretensão.

A regra implementada:
  - Abre alerta apenas após N coletas consecutivas com tensão > limite
  - Fecha alerta apenas após N coletas consecutivas com tensão <= limite
  - Oscilação intermediária (ex: alto, baixo, alto) mantém o estado atual
"""
import datetime
from unittest.mock import patch

import pytest
from django.utils import timezone

from alertas.analise import (
    SOBRETENSAO_N_COLETAS,
    _alerta_agrupado_sobretensao,
    _contar_coletas_com_sobretensao,
    _enriquecer_ou_criar,
    _resolver_alerta_interno,
    sufixo_timestamp_id,
)
from alertas.models import Alerta
from provedores.models import CredencialProvedor
from usinas.models import (
    GarantiaUsina,
    Inversor,
    SnapshotInversor,
    SnapshotUsina,
    Usina,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def usina(db):
    cred = CredencialProvedor.objects.create(
        provedor='solis', credenciais_enc='x', ativo=True
    )
    u = Usina.objects.create(
        id_usina_provedor='plant-sobretensao',
        provedor='solis',
        credencial=cred,
        nome='Usina Sobretensão Teste',
        capacidade_kwp=10.0,
        tensao_sobretensao_v=240.0,
        ativo=True,
    )
    GarantiaUsina.objects.create(
        usina=u,
        data_inicio=datetime.date.today() - datetime.timedelta(days=30),
        meses=12,
    )
    return u


@pytest.fixture
def inversor(usina):
    return Inversor.objects.create(
        usina=usina,
        id_inversor_provedor='inv-sobretensao',
        numero_serie='SN-SOBRE-01',
        modelo='Solis 5K',
    )


def _criar_historico(usina: Usina, inversor: Inversor, tensoes: list[float]):
    """
    Cria SnapshotUsina + SnapshotInversor para cada tensão informada.
    Ordem cronológica: `tensoes[0]` é o mais antigo, `tensoes[-1]` o mais recente.
    Intervalos de 10 min entre coletas.
    """
    agora = timezone.now()
    n = len(tensoes)
    for i, tensao in enumerate(tensoes):
        ts = agora - datetime.timedelta(minutes=10 * (n - 1 - i))
        SnapshotUsina.objects.create(
            usina=usina,
            coletado_em=ts,
            potencia_kw=1.0,
            energia_hoje_kwh=5.0,
            energia_mes_kwh=100.0,
            energia_total_kwh=1000.0,
            status='normal',
            qtd_inversores=1,
            qtd_inversores_online=1,
            qtd_alertas=0,
        )
        SnapshotInversor.objects.create(
            inversor=inversor,
            coletado_em=ts,
            estado='normal',
            pac_kw=1.0,
            energia_hoje_kwh=5.0,
            energia_total_kwh=1000.0,
            tensao_ac_v=tensao,
        )


# ── _contar_coletas_com_sobretensao ──────────────────────────────────────────

class TestContarColetasComSobretensao:
    def test_retorna_zero_quando_historico_insuficiente(self, db, usina, inversor):
        _criar_historico(usina, inversor, [245.0, 245.0])  # 2 coletas, N=3
        assert _contar_coletas_com_sobretensao(usina, 240.0, 3) == 0

    def test_conta_n_coletas_todas_acima(self, db, usina, inversor):
        _criar_historico(usina, inversor, [245.0, 245.0, 245.0])
        assert _contar_coletas_com_sobretensao(usina, 240.0, 3) == 3

    def test_conta_zero_quando_todas_no_limite(self, db, usina, inversor):
        _criar_historico(usina, inversor, [240.0, 240.0, 240.0])  # igual ao limite = normal
        assert _contar_coletas_com_sobretensao(usina, 240.0, 3) == 0

    def test_conta_zero_quando_todas_abaixo(self, db, usina, inversor):
        _criar_historico(usina, inversor, [230.0, 235.0, 238.0])
        assert _contar_coletas_com_sobretensao(usina, 240.0, 3) == 0

    def test_conta_mistura(self, db, usina, inversor):
        _criar_historico(usina, inversor, [245.0, 238.0, 245.0])  # alto-normal-alto
        assert _contar_coletas_com_sobretensao(usina, 240.0, 3) == 2

    def test_considera_apenas_ultimas_n(self, db, usina, inversor):
        # 5 coletas: normais antigas + 3 recentes acima. Resultado considera só as 3 recentes.
        _criar_historico(usina, inversor, [230.0, 230.0, 245.0, 245.0, 245.0])
        assert _contar_coletas_com_sobretensao(usina, 240.0, 3) == 3


# ── _alerta_agrupado_sobretensao (histerese + persistência) ─────────────────

class TestAlertaAgrupadoSobretensao:
    def _ha_alerta_ativo_sobretensao(self, usina):
        return Alerta.objects.filter(
            usina=usina, origem='interno', categoria='sobretensao', estado='ativo'
        ).exists()

    def test_nao_abre_com_menos_de_n_coletas_acima(self, db, usina, inversor):
        _criar_historico(usina, inversor, [245.0, 245.0])  # só 2 coletas
        snap = SnapshotInversor.objects.filter(inversor=inversor).latest('coletado_em')
        _alerta_agrupado_sobretensao(usina, [(inversor, snap)], [(inversor, snap)], 240.0)
        assert not self._ha_alerta_ativo_sobretensao(usina)

    def test_abre_apos_n_coletas_acima_do_limite(self, db, usina, inversor):
        _criar_historico(usina, inversor, [245.0, 245.0, 245.0])
        snap = SnapshotInversor.objects.filter(inversor=inversor).latest('coletado_em')
        _alerta_agrupado_sobretensao(usina, [(inversor, snap)], [(inversor, snap)], 240.0)
        assert self._ha_alerta_ativo_sobretensao(usina)

    def test_nao_abre_no_limite_exato(self, db, usina, inversor):
        """240V = 240V não passa do limite → não abre."""
        _criar_historico(usina, inversor, [240.0, 240.0, 240.0])
        snap = SnapshotInversor.objects.filter(inversor=inversor).latest('coletado_em')
        _alerta_agrupado_sobretensao(usina, [], [(inversor, snap)], 240.0)
        assert not self._ha_alerta_ativo_sobretensao(usina)

    def test_mantem_aberto_com_oscilacao(self, db, usina, inversor):
        """Alerta já aberto; histórico oscilando não fecha nem abre de novo."""
        Alerta.objects.create(
            usina=usina,
            origem='interno',
            categoria='sobretensao',
            id_alerta_provedor='interno_sobretensao_plant-sobretensao',
            mensagem='Sobretensao pre-existente',
            nivel='aviso',
            inicio=timezone.now() - datetime.timedelta(hours=1),
            estado='ativo',
        )
        _criar_historico(usina, inversor, [245.0, 235.0, 245.0])  # oscila — 2 de 3 acima
        snap = SnapshotInversor.objects.filter(inversor=inversor).latest('coletado_em')
        _alerta_agrupado_sobretensao(usina, [(inversor, snap)], [(inversor, snap)], 240.0)
        assert self._ha_alerta_ativo_sobretensao(usina)  # continua ativo

    def test_fecha_apos_n_coletas_abaixo_ou_igual(self, db, usina, inversor):
        """Alerta aberto é resolvido apenas após N coletas todas <= limite."""
        Alerta.objects.create(
            usina=usina,
            origem='interno',
            categoria='sobretensao',
            id_alerta_provedor='interno_sobretensao_plant-sobretensao',
            mensagem='Sobretensao pre-existente',
            nivel='aviso',
            inicio=timezone.now() - datetime.timedelta(hours=1),
            estado='ativo',
        )
        _criar_historico(usina, inversor, [230.0, 235.0, 238.0])  # todas <= 240
        snap = SnapshotInversor.objects.filter(inversor=inversor).latest('coletado_em')
        _alerta_agrupado_sobretensao(usina, [], [(inversor, snap)], 240.0)
        assert not self._ha_alerta_ativo_sobretensao(usina)

    def test_nao_fecha_com_apenas_uma_coleta_baixa(self, db, usina, inversor):
        """Um único pico para baixo não resolve — precisa de N consecutivas."""
        Alerta.objects.create(
            usina=usina,
            origem='interno',
            categoria='sobretensao',
            id_alerta_provedor='interno_sobretensao_plant-sobretensao',
            mensagem='Sobretensao pre-existente',
            nivel='aviso',
            inicio=timezone.now() - datetime.timedelta(hours=1),
            estado='ativo',
        )
        _criar_historico(usina, inversor, [245.0, 245.0, 235.0])  # só última abaixo
        snap = SnapshotInversor.objects.filter(inversor=inversor).latest('coletado_em')
        _alerta_agrupado_sobretensao(usina, [], [(inversor, snap)], 240.0)
        assert self._ha_alerta_ativo_sobretensao(usina)  # continua ativo

    def test_constante_de_coletas_e_3(self):
        """Contrato fixado para evitar regressão silenciosa."""
        assert SOBRETENSAO_N_COLETAS == 3


# ── Evento por incidente: nunca reabre alerta resolvido ─────────────────────

class TestEventoPorIncidente:
    """
    Quando uma condição some e reaparece, o sistema cria um NOVO alerta
    em vez de reabrir o antigo resolvido. Assim relatórios podem contar
    o número de eventos (ex: 3 picos de sobretensão em abril).
    """

    def test_cria_alerta_novo_quando_nao_ha_ativo(self, db, usina):
        _enriquecer_ou_criar(
            usina=usina, categoria='sobretensao', chave='k',
            nivel='aviso', mensagem='primeiro evento',
        )
        assert Alerta.objects.filter(
            usina=usina, categoria='sobretensao', estado='ativo'
        ).count() == 1

    def test_atualiza_alerta_ativo_existente_em_vez_de_criar_outro(self, db, usina):
        _enriquecer_ou_criar(
            usina=usina, categoria='sobretensao', chave='k',
            nivel='aviso', mensagem='mensagem inicial',
        )
        _enriquecer_ou_criar(
            usina=usina, categoria='sobretensao', chave='k',
            nivel='aviso', mensagem='mensagem atualizada',
        )
        ativos = Alerta.objects.filter(
            usina=usina, categoria='sobretensao', estado='ativo'
        )
        assert ativos.count() == 1
        assert ativos.first().mensagem == 'mensagem atualizada'

    def test_cria_alerta_novo_apos_resolvido_anterior(self, db, usina):
        """
        Fluxo: abre → resolve → condição volta → deve criar NOVO alerta
        (nunca reabrir o resolvido).
        """
        _enriquecer_ou_criar(
            usina=usina, categoria='sobretensao', chave='k',
            nivel='aviso', mensagem='primeiro evento',
        )
        _resolver_alerta_interno(usina, 'sobretensao')
        _enriquecer_ou_criar(
            usina=usina, categoria='sobretensao', chave='k',
            nivel='aviso', mensagem='segundo evento',
        )
        total = Alerta.objects.filter(usina=usina, categoria='sobretensao').count()
        resolvidos = Alerta.objects.filter(
            usina=usina, categoria='sobretensao', estado='resolvido'
        ).count()
        ativos = Alerta.objects.filter(
            usina=usina, categoria='sobretensao', estado='ativo'
        ).count()
        assert total == 2
        assert resolvidos == 1
        assert ativos == 1

    def test_id_alerta_provedor_unico_para_cada_evento(self, db, usina):
        """Cada novo alerta ganha sufixo de timestamp — unicidade preservada."""
        _enriquecer_ou_criar(
            usina=usina, categoria='sobretensao', chave='k',
            nivel='aviso', mensagem='evento 1',
        )
        _resolver_alerta_interno(usina, 'sobretensao')
        _enriquecer_ou_criar(
            usina=usina, categoria='sobretensao', chave='k',
            nivel='aviso', mensagem='evento 2',
        )
        ids = list(Alerta.objects
                   .filter(usina=usina, categoria='sobretensao')
                   .values_list('id_alerta_provedor', flat=True))
        assert len(ids) == 2
        assert len(set(ids)) == 2, f'IDs devem ser únicos: {ids}'

    def test_resolver_usa_categoria_em_vez_de_id_alerta_provedor(self, db, usina):
        """`chave` parâmetro é ignorado — categoria + origem já identificam."""
        _enriquecer_ou_criar(
            usina=usina, categoria='sobretensao', chave='qualquer',
            nivel='aviso', mensagem='evento',
        )
        # Resolve sem passar `chave`
        _resolver_alerta_interno(usina, 'sobretensao')
        assert not Alerta.objects.filter(
            usina=usina, categoria='sobretensao', estado='ativo'
        ).exists()

    def test_resolver_atualiza_fim_e_atualizado_em(self, db, usina):
        _enriquecer_ou_criar(
            usina=usina, categoria='sobretensao', chave='k',
            nivel='aviso', mensagem='evento',
        )
        antes = timezone.now()
        _resolver_alerta_interno(usina, 'sobretensao')
        alerta = Alerta.objects.get(usina=usina, categoria='sobretensao')
        assert alerta.estado == 'resolvido'
        assert alerta.fim is not None
        assert alerta.fim >= antes
        assert alerta.atualizado_em >= antes

    def test_atualizado_em_muda_ao_reconfirmar_alerta_ativo(self, db, usina):
        """Phase 3: toda reconfirmação atualiza `atualizado_em`."""
        _enriquecer_ou_criar(
            usina=usina, categoria='sobretensao', chave='k',
            nivel='aviso', mensagem='inicial',
        )
        original = Alerta.objects.get(usina=usina, categoria='sobretensao').atualizado_em
        # Força passagem de tempo
        import time
        time.sleep(0.01)
        _enriquecer_ou_criar(
            usina=usina, categoria='sobretensao', chave='k',
            nivel='aviso', mensagem='reconfirmada',
        )
        atualizado = Alerta.objects.get(usina=usina, categoria='sobretensao').atualizado_em
        assert atualizado > original

    def test_sufixo_timestamp_id_tem_formato_compacto(self):
        """Formato YYYYMMDDTHHMMSSffffffZ — compacto, ordenável, único."""
        dt = timezone.now()
        sufixo = sufixo_timestamp_id(dt)
        assert len(sufixo) == 22  # ex: "20260420T195118481228Z"
        assert sufixo.endswith('Z')
        assert 'T' in sufixo


# ── sem_geracao_diurna e sem_comunicacao não disputam a mesma categoria ─────

class TestNaoCriarSemComunicacaoEmVerificarSemGeracao:
    """
    Antes, `_verificar_sem_geracao_diurna` criava um alerta de `sem_comunicacao`
    quando todos os inversores estavam offline, mas `_verificar_sem_comunicacao`
    (que roda logo depois, no mesmo ciclo) resolvia o alerta caso `data_medicao`
    fosse recente. Resultado: cada coleta criava + resolvia o mesmo alerta,
    gerando registros "fantasma" de 4ms de duração.

    O fix: `_verificar_sem_geracao_diurna` nunca mais gera `sem_comunicacao` —
    essa categoria é decidida exclusivamente por `_verificar_sem_comunicacao`,
    baseado em `data_medicao >= 24h`.
    """

    def test_todos_inversores_offline_gera_sem_geracao_nao_sem_comunicacao(
        self, db, usina, inversor
    ):
        from alertas.analise import _verificar_sem_geracao_diurna

        # Snapshot atual: potencia 0, inversor offline
        snap_usina = SnapshotUsina.objects.create(
            usina=usina,
            coletado_em=timezone.now(),
            potencia_kw=0.0,
            energia_hoje_kwh=0.0,
            energia_mes_kwh=0.0,
            energia_total_kwh=0.0,
            status='offline',
            qtd_inversores=1,
            qtd_inversores_online=0,
            qtd_alertas=0,
        )
        snap_inv = SnapshotInversor.objects.create(
            inversor=inversor,
            coletado_em=timezone.now(),
            estado='offline',
            pac_kw=0.0,
            energia_hoje_kwh=0.0,
            energia_total_kwh=1000.0,
            tensao_ac_v=0.0,
        )

        _verificar_sem_geracao_diurna(
            usina, snap_usina, [(inversor, snap_inv)], timezone.now()
        )

        # Deve criar sem_geracao_diurna, NÃO sem_comunicacao
        assert Alerta.objects.filter(
            usina=usina, categoria='sem_geracao_diurna', estado='ativo'
        ).exists()
        assert not Alerta.objects.filter(
            usina=usina, categoria='sem_comunicacao'
        ).exists()

    def test_mensagem_diferencia_todos_offline_de_inversor_online_sem_gerar(
        self, db, usina, inversor
    ):
        from alertas.analise import _verificar_sem_geracao_diurna

        snap_usina = SnapshotUsina.objects.create(
            usina=usina,
            coletado_em=timezone.now(),
            potencia_kw=0.0,
            energia_hoje_kwh=0.0,
            energia_mes_kwh=0.0,
            energia_total_kwh=0.0,
            status='offline',
            qtd_inversores=1,
            qtd_inversores_online=0,
            qtd_alertas=0,
        )
        snap_inv = SnapshotInversor.objects.create(
            inversor=inversor,
            coletado_em=timezone.now(),
            estado='offline',
            pac_kw=0.0,
            energia_hoje_kwh=0.0,
            energia_total_kwh=1000.0,
            tensao_ac_v=0.0,
        )

        _verificar_sem_geracao_diurna(
            usina, snap_usina, [(inversor, snap_inv)], timezone.now()
        )

        mensagem = Alerta.objects.get(
            usina=usina, categoria='sem_geracao_diurna'
        ).mensagem
        # Indica claramente que são TODOS os inversores offline (diagnóstico)
        assert 'offline' in mensagem.lower()
        assert '1' in mensagem  # total_inv = 1
