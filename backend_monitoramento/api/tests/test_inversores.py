import pytest


@pytest.mark.django_db
class TestInversorList:
    """Testes para GET /api/inversores/ — INV-01."""

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 3')
    def test_lista_requer_autenticacao(self, client):
        """INV-01: sem token retorna 401."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 3')
    def test_lista_autenticado(self, client, tokens, inversor):
        """INV-01: com token retorna lista paginada."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 3')
    def test_filtro_por_usina(self, client, tokens, inversor):
        """INV-01: ?usina={id} retorna apenas inversores daquela usina."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 3')
    def test_filtro_por_modelo(self, client, tokens, inversor):
        """INV-01: ?modelo=Solis retorna apenas inversores daquele modelo."""
        pass


@pytest.mark.django_db
class TestInversorDetalhe:
    """Testes para GET /api/inversores/{id}/ — INV-02."""

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 3')
    def test_detalhe_requer_autenticacao(self, client, inversor):
        """INV-02: sem token retorna 401."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 3')
    def test_detalhe_retorna_ultimo_snapshot(self, client, tokens, inversor, snapshot_inversor):
        """INV-02: detalhe inclui dados completos do ultimo snapshot."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 3')
    def test_detalhe_sem_snapshot(self, client, tokens, inversor):
        """INV-02: inversor sem snapshot retorna ultimo_snapshot=null."""
        pass


@pytest.mark.django_db
class TestInversorSnapshots:
    """Testes para GET /api/inversores/{id}/snapshots/ — INV-03."""

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 3')
    def test_snapshots_requer_autenticacao(self, client, inversor):
        """INV-03: sem token retorna 401."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 3')
    def test_snapshots_retorna_historico_paginado(self, client, tokens, inversor, snapshot_inversor):
        """INV-03: retorna lista paginada de snapshots."""
        pass
