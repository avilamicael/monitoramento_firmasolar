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

from usinas.models import Usina, SnapshotUsina
from provedores.models import CredencialProvedor
from alertas.supressao_inteligente import e_desligamento_gradual


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
