import pytest


@pytest.mark.django_db
class TestGarantiaUpsert:
    """Testes para PUT /api/usinas/{id}/garantia/ — GAR-02."""

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 2')
    def test_criar_garantia(self, client, tokens, usina):
        """GAR-02: PUT cria garantia quando nao existe."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 2')
    def test_substituir_garantia(self, client, tokens, usina, garantia_ativa):
        """GAR-02: PUT substitui garantia existente."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 2')
    def test_resposta_inclui_data_fim(self, client, tokens, usina):
        """GAR-02/GAR-04: resposta do PUT inclui data_fim e dias_restantes."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 2')
    def test_upsert_requer_autenticacao(self, client, usina):
        """GAR-02: sem token retorna 401."""
        pass


@pytest.mark.django_db
class TestGarantiaFiltros:
    """Testes para GET /api/garantias/?filtro= — GAR-03."""

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 2')
    def test_lista_todas_garantias(self, client, tokens, garantia_ativa, garantia_vencida):
        """GAR-03: sem filtro retorna todas."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 2')
    def test_filtro_ativas(self, client, tokens, garantia_ativa, garantia_vencida):
        """GAR-03: ?filtro=ativas retorna apenas ativas."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 2')
    def test_filtro_vencidas(self, client, tokens, garantia_ativa, garantia_vencida):
        """GAR-03: ?filtro=vencidas retorna apenas vencidas."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 2')
    def test_filtro_vencendo(self, client, tokens):
        """GAR-03: ?filtro=vencendo retorna garantias com data_fim nos proximos 30 dias."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 2')
    def test_dias_restantes_correto(self, client, tokens, garantia_ativa):
        """GAR-04: campo dias_restantes calculado corretamente."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 2')
    def test_lista_requer_autenticacao(self, client):
        """GAR-03: sem token retorna 401."""
        pass


@pytest.mark.django_db
class TestGarantiaVisibilidade:
    """Testes para GAR-05 e GAR-06 — visibilidade por status de garantia."""

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 2')
    def test_usina_sem_garantia_nao_aparece_com_filtro_ativas(self, client, tokens, usina):
        """GAR-05: usina sem garantia nao aparece ao filtrar garantias ativas."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 2')
    def test_usina_com_garantia_ativa_aparece_com_filtro_ativas(self, client, tokens, usina, garantia_ativa):
        """GAR-06: usina com garantia ativa aparece ao filtrar garantias ativas."""
        pass
