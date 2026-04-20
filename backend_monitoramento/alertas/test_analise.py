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
