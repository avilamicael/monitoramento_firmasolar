"""
Testes para alertas/supressao_inteligente.py

Cobre os três cenários principais de e_desligamento_gradual():
  - Desligamento gradual: último pot abaixo do limiar → True (suprimir)
  - Desligamento abrupto: último pot acima do limiar → False (alertar)
  - Sem snapshots nas 24h: conservador → False (alertar)
"""
import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

from usinas.models import Usina, SnapshotUsina, Inversor, SnapshotInversor
from provedores.models import CredencialProvedor
from alertas.supressao_inteligente import e_desligamento_gradual, esta_gerando_agora


@pytest.fixture
def credencial(db):
    return CredencialProvedor.objects.create(
        provedor='hoymiles',
        credenciais_enc='placeholder',
        ativo=True,
    )


@pytest.fixture
def usina(db, credencial):
    return Usina.objects.create(
        id_usina_provedor='test-001',
        provedor='hoymiles',
        credencial=credencial,
        nome='Usina de Teste',
        capacidade_kwp=7.38,
        fuso_horario='America/Sao_Paulo',
    )


def _cria_snapshot(usina, horas_atras, potencia_kw):
    """Cria um SnapshotUsina com coletado_em relativo ao momento atual."""
    coletado_em = timezone.now() - timedelta(hours=horas_atras)
    return SnapshotUsina.objects.create(
        usina=usina,
        coletado_em=coletado_em,
        data_medicao=coletado_em,
        potencia_kw=potencia_kw,
        energia_hoje_kwh=10.0,
        energia_mes_kwh=100.0,
        energia_total_kwh=1000.0,
        status='normal' if potencia_kw > 0 else 'offline',
        qtd_inversores=1,
        qtd_inversores_online=1 if potencia_kw > 0 else 0,
        qtd_alertas=0,
    )


@pytest.mark.django_db
class TestEDesligamentoGradual:

    def test_gradual_retorna_true(self, usina):
        """Último snapshot com pot abaixo do limiar → desligamento gradual."""
        # Limiar para 7.38 kWp = max(1.0, 7.38 * 0.05) = 1.0 kW (mínimo absoluto)
        _cria_snapshot(usina, horas_atras=2.5, potencia_kw=0.18)
        _cria_snapshot(usina, horas_atras=2.0, potencia_kw=0.10)
        _cria_snapshot(usina, horas_atras=1.5, potencia_kw=0.03)  # último com pot
        _cria_snapshot(usina, horas_atras=1.0, potencia_kw=0.00)
        _cria_snapshot(usina, horas_atras=0.5, potencia_kw=0.00)

        assert e_desligamento_gradual(usina) is True

    def test_abrupto_retorna_false(self, usina):
        """Último snapshot com pot acima do limiar → desligamento abrupto."""
        # Limiar para 7.38 kWp = max(1.0, 7.38 * 0.05) = 1.0 kW
        _cria_snapshot(usina, horas_atras=2.0, potencia_kw=4.50)
        _cria_snapshot(usina, horas_atras=1.5, potencia_kw=5.20)
        _cria_snapshot(usina, horas_atras=1.0, potencia_kw=5.10)  # último com pot
        _cria_snapshot(usina, horas_atras=0.5, potencia_kw=0.00)
        _cria_snapshot(usina, horas_atras=0.1, potencia_kw=0.00)

        assert e_desligamento_gradual(usina) is False

    def test_sem_snapshots_retorna_false(self, usina):
        """Sem nenhum snapshot com pot nas últimas 24h → conservador, não suprimir."""
        _cria_snapshot(usina, horas_atras=0.5, potencia_kw=0.00)
        _cria_snapshot(usina, horas_atras=0.2, potencia_kw=0.00)

        assert e_desligamento_gradual(usina) is False

    def test_snapshots_fora_da_janela_ignorados(self, usina):
        """Snapshot com pot de 25h atrás não conta — fora da janela de 24h."""
        _cria_snapshot(usina, horas_atras=25, potencia_kw=0.05)  # fora da janela
        _cria_snapshot(usina, horas_atras=1.0, potencia_kw=0.00)

        assert e_desligamento_gradual(usina) is False

    def test_exatamente_no_limiar_considera_gradual(self, usina):
        """Pot exatamente igual ao limiar deve ser considerado gradual (<=)."""
        # Limiar para 7.38 kWp = max(1.0, 7.38 * 0.05) = 1.0 kW (mínimo absoluto domina)
        _cria_snapshot(usina, horas_atras=1.0, potencia_kw=1.0)
        _cria_snapshot(usina, horas_atras=0.5, potencia_kw=0.00)

        assert e_desligamento_gradual(usina) is True

    def test_limiar_usa_minimo_absoluto_sem_capacidade(self, credencial):
        """Usina sem capacidade cadastrada usa limiar absoluto de 1.0 kW."""
        usina_sem_cap = Usina.objects.create(
            id_usina_provedor='test-002',
            provedor='hoymiles',
            credencial=credencial,
            nome='Sem Capacidade',
            capacidade_kwp=0,
            fuso_horario='America/Sao_Paulo',
        )
        # 0.8 kW < limiar absoluto 1.0 kW → gradual
        _cria_snapshot(usina_sem_cap, horas_atras=1.0, potencia_kw=0.80)
        _cria_snapshot(usina_sem_cap, horas_atras=0.5, potencia_kw=0.00)

        assert e_desligamento_gradual(usina_sem_cap) is True


@pytest.mark.django_db
class TestEstaGerandoAgora:
    """
    Cobre os três cenários de decisão para a flag sistema_desligado:
      - usina gera no snapshot mais recente → True (suprime)
      - usina zero no snapshot mas inversores com pac_kw>0 → True (suprime)
      - nada no último ciclo → False (deixa o alerta passar)
    """

    def test_suprime_quando_snapshot_usina_gera(self, usina):
        _cria_snapshot(usina, horas_atras=0.1, potencia_kw=0.5)
        assert esta_gerando_agora(usina) is True

    def test_suprime_quando_inversores_geram_mesmo_com_potencia_usina_zero(
        self, usina
    ):
        """Cenário real Cleber E Bruna: payload da usina diz 0, inversores dizem > 0."""
        snap_usina = SnapshotUsina.objects.create(
            usina=usina,
            coletado_em=timezone.now(),
            potencia_kw=0.0,
            energia_hoje_kwh=10.0,
            energia_mes_kwh=100.0,
            energia_total_kwh=1000.0,
            status='normal',
            qtd_inversores=1,
            qtd_inversores_online=1,
            qtd_alertas=0,
        )
        inv = Inversor.objects.create(
            usina=usina,
            id_inversor_provedor='inv-cleber',
            numero_serie='SN-CLEBER-01',
            modelo='MI-1500',
        )
        SnapshotInversor.objects.create(
            inversor=inv,
            coletado_em=snap_usina.coletado_em,
            estado='normal',
            pac_kw=0.85,
            energia_hoje_kwh=5.0,
            energia_total_kwh=500.0,
            tensao_ac_v=228.0,
        )

        assert esta_gerando_agora(usina) is True

    def test_nao_suprime_sem_snapshot(self, usina):
        assert esta_gerando_agora(usina) is False

    def test_nao_suprime_quando_usina_e_inversores_zerados(self, usina):
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
        inv = Inversor.objects.create(
            usina=usina,
            id_inversor_provedor='inv-x',
            numero_serie='SN-X',
            modelo='MI-1500',
        )
        SnapshotInversor.objects.create(
            inversor=inv,
            coletado_em=snap_usina.coletado_em,
            estado='offline',
            pac_kw=0.0,
            energia_hoje_kwh=0.0,
            energia_total_kwh=0.0,
            tensao_ac_v=0.0,
        )

        assert esta_gerando_agora(usina) is False

    def test_nao_cruza_com_inversor_de_coleta_diferente(self, usina):
        """
        Snapshots de inversor fora da janela de 5min do ciclo atual não devem
        mascarar um desligamento real (ex: inversor gerou ontem mas agora está
        offline).
        """
        # Último snapshot da usina: zerado
        SnapshotUsina.objects.create(
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
        inv = Inversor.objects.create(
            usina=usina,
            id_inversor_provedor='inv-old',
            numero_serie='SN-OLD',
            modelo='MI',
        )
        # Snapshot do inversor de 6 horas atrás (gerando) — NÃO deve ser usado
        SnapshotInversor.objects.create(
            inversor=inv,
            coletado_em=timezone.now() - timedelta(hours=6),
            estado='normal',
            pac_kw=2.5,
            energia_hoje_kwh=5.0,
            energia_total_kwh=500.0,
            tensao_ac_v=230.0,
        )

        assert esta_gerando_agora(usina) is False
