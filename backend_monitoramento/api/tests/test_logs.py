import pytest


@pytest.mark.django_db
class TestLogColetaList:
    """Testes para GET /api/coleta/logs/ — LOG-01."""

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 4')
    def test_lista_requer_autenticacao(self, client):
        """LOG-01: sem token retorna 401."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 4')
    def test_lista_autenticado(self, client, tokens, log_coleta):
        """LOG-01: com token retorna lista paginada com status e timestamp."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 4')
    def test_lista_ordenada_por_data(self, client, tokens, log_coleta):
        """LOG-01: resultados ordenados por -iniciado_em."""
        pass
