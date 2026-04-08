import pytest
from datetime import date
from usinas.models import GarantiaUsina, Usina


@pytest.fixture
def usina(db):
    """Cria uma usina minima para testes de garantia."""
    from provedores.models import CredencialProvedor
    cred = CredencialProvedor.objects.create(
        provedor='solis',
        credenciais_enc='enc_placeholder',
    )
    return Usina.objects.create(
        id_usina_provedor='test-001',
        provedor='solis',
        credencial=cred,
        nome='Usina Teste',
        capacidade_kwp=10.0,
    )


class TestGarantiaUsina:
    """Testes do model GarantiaUsina — cobre GAR-01."""

    def test_garantia_data_fim_calculada(self, usina):
        """GAR-01: data_fim = data_inicio + meses."""
        garantia = GarantiaUsina(
            usina=usina,
            data_inicio=date(2024, 1, 15),
            meses=12,
        )
        assert garantia.data_fim == date(2025, 1, 15)

    def test_garantia_data_fim_fim_de_mes(self, usina):
        """GAR-01: data_fim lida corretamente com fim de mes (bissexto)."""
        garantia = GarantiaUsina(
            usina=usina,
            data_inicio=date(2024, 1, 31),
            meses=1,
        )
        # relativedelta(months=1) de 31/jan/2024 = 29/fev/2024 (bissexto)
        assert garantia.data_fim == date(2024, 2, 29)

    def test_garantia_ativa_quando_dentro_do_prazo(self, usina):
        """GAR-01: ativa retorna True quando data_fim esta no futuro."""
        garantia = GarantiaUsina(
            usina=usina,
            data_inicio=date(2025, 1, 1),
            meses=120,  # 10 anos a partir de 2025 — vence em 2035
        )
        assert garantia.ativa is True

    def test_garantia_inativa_quando_vencida(self, usina):
        """GAR-01: ativa retorna False quando data_fim esta no passado."""
        garantia = GarantiaUsina(
            usina=usina,
            data_inicio=date(2020, 1, 1),
            meses=12,  # venceu em jan/2021
        )
        assert garantia.ativa is False

    def test_garantia_dias_restantes_positivo(self, usina):
        """GAR-01: dias_restantes > 0 quando garantia ativa."""
        garantia = GarantiaUsina(
            usina=usina,
            data_inicio=date(2025, 1, 1),
            meses=120,
        )
        assert garantia.dias_restantes > 0

    def test_garantia_dias_restantes_zero_quando_vencida(self, usina):
        """GAR-01: dias_restantes == 0 quando garantia vencida."""
        garantia = GarantiaUsina(
            usina=usina,
            data_inicio=date(2020, 1, 1),
            meses=12,
        )
        assert garantia.dias_restantes == 0

    def test_garantia_str(self, usina):
        """GAR-01: __str__ contem nome da usina e meses."""
        garantia = GarantiaUsina(
            usina=usina,
            data_inicio=date(2024, 1, 1),
            meses=24,
        )
        resultado = str(garantia)
        assert 'Usina Teste' in resultado
        assert '24' in resultado

    @pytest.mark.django_db
    def test_garantia_persistencia(self, usina):
        """GAR-01: GarantiaUsina persiste e recupera do banco."""
        GarantiaUsina.objects.create(
            usina=usina,
            data_inicio=date(2024, 6, 1),
            meses=36,
            observacoes='Garantia de teste',
        )
        garantia = GarantiaUsina.objects.get(usina=usina)
        assert garantia.meses == 36
        assert garantia.data_fim == date(2027, 6, 1)
        assert garantia.observacoes == 'Garantia de teste'
