import pytest


@pytest.mark.django_db
class TestAlertaList:
    """Testes para GET /api/alertas/ — ALT-01, ALT-04."""

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 3')
    def test_lista_requer_autenticacao(self, client):
        """ALT-01: sem token retorna 401."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 3')
    def test_lista_autenticado(self, client, tokens, alerta):
        """ALT-01: com token retorna lista paginada."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 3')
    def test_filtro_por_estado(self, client, tokens, alerta):
        """ALT-01: ?estado=ativo retorna apenas alertas ativos."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 3')
    def test_filtro_por_nivel(self, client, tokens, alerta):
        """ALT-01: ?nivel=aviso retorna apenas alertas de nivel aviso."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 3')
    def test_filtro_por_usina(self, client, tokens, alerta):
        """ALT-01: ?usina={id} retorna apenas alertas daquela usina."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 3')
    def test_campo_com_garantia_true(self, client, tokens, alerta, garantia_ativa):
        """ALT-04: alerta de usina com garantia ativa tem com_garantia=true."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 3')
    def test_campo_com_garantia_false(self, client, tokens, alerta):
        """ALT-04: alerta de usina sem garantia tem com_garantia=false."""
        pass


@pytest.mark.django_db
class TestAlertaDetalhe:
    """Testes para GET /api/alertas/{id}/ — ALT-02."""

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 3')
    def test_detalhe_requer_autenticacao(self, client, alerta):
        """ALT-02: sem token retorna 401."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 3')
    def test_detalhe_retorna_dados_completos(self, client, tokens, alerta):
        """ALT-02: detalhe inclui todos os campos do alerta."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 3')
    def test_detalhe_inclui_com_garantia(self, client, tokens, alerta):
        """ALT-02/ALT-04: detalhe inclui campo com_garantia."""
        pass


@pytest.mark.django_db
class TestAlertaPatch:
    """Testes para PATCH /api/alertas/{id}/ — ALT-03."""

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 3')
    def test_patch_requer_autenticacao(self, client, alerta):
        """ALT-03: sem token retorna 401."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 3')
    def test_patch_atualiza_estado(self, client, tokens, alerta):
        """ALT-03: PATCH com estado='em_atendimento' atualiza o campo."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 3')
    def test_patch_atualiza_anotacoes(self, client, tokens, alerta):
        """ALT-03: PATCH com anotacoes atualiza o campo."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 3')
    def test_post_nao_permitido(self, client, tokens):
        """ALT-03: POST retorna 405 — alertas sao criados pela coleta."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 3')
    def test_delete_nao_permitido(self, client, tokens, alerta):
        """ALT-03: DELETE retorna 405."""
        pass
