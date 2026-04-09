import pytest


@pytest.mark.django_db
class TestUsinaList:
    """Testes para GET /api/usinas/ — USN-01, USN-04."""

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 2')
    def test_lista_requer_autenticacao(self, client):
        """USN-01: sem token retorna 401."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 2')
    def test_lista_autenticado_retorna_usinas(self, client, tokens, usina):
        """USN-01: com token retorna lista paginada."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 2')
    def test_filtro_por_provedor(self, client, tokens, usina, usina_hoymiles):
        """USN-01: ?provedor=solis retorna apenas usinas solis."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 2')
    def test_filtro_por_ativo(self, client, tokens, usina):
        """USN-01: ?ativo=true retorna apenas usinas ativas."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 2')
    def test_filtro_por_status_garantia_ativa(self, client, tokens, usina, garantia_ativa):
        """USN-01: ?status_garantia=ativa retorna usinas com garantia ativa."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 2')
    def test_filtro_por_status_garantia_sem_garantia(self, client, tokens, usina):
        """USN-01: ?status_garantia=sem_garantia retorna usinas sem garantia."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 2')
    def test_campo_status_garantia_sem_garantia(self, client, tokens, usina):
        """USN-04: usina sem GarantiaUsina retorna status_garantia='sem_garantia'."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 2')
    def test_campo_status_garantia_ativa(self, client, tokens, usina, garantia_ativa):
        """USN-04: usina com garantia ativa retorna status_garantia='ativa'."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 2')
    def test_campo_status_garantia_vencida(self, client, tokens, usina_hoymiles, garantia_vencida):
        """USN-04: usina com garantia vencida retorna status_garantia='vencida'."""
        pass


@pytest.mark.django_db
class TestUsinaDetalhe:
    """Testes para GET /api/usinas/{id}/ — USN-02."""

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 2')
    def test_detalhe_requer_autenticacao(self, client, usina):
        """USN-02: sem token retorna 401."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 2')
    def test_detalhe_retorna_inversores(self, client, tokens, usina, inversor):
        """USN-02: detalhe inclui lista de inversores."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 2')
    def test_detalhe_retorna_ultimo_snapshot(self, client, tokens, usina, snapshot_usina):
        """USN-02: detalhe inclui dados do ultimo snapshot."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 2')
    def test_detalhe_usina_sem_snapshot(self, client, tokens, usina):
        """USN-02: usina sem snapshot retorna ultimo_snapshot=null."""
        pass


@pytest.mark.django_db
class TestUsinaPatch:
    """Testes para PATCH /api/usinas/{id}/ — USN-03."""

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 2')
    def test_patch_requer_autenticacao(self, client, usina):
        """USN-03: sem token retorna 401."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 2')
    def test_patch_atualiza_nome(self, client, tokens, usina):
        """USN-03: PATCH com nome atualiza o campo."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 2')
    def test_patch_atualiza_capacidade(self, client, tokens, usina):
        """USN-03: PATCH com capacidade_kwp atualiza o campo."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 2')
    def test_post_nao_permitido(self, client, tokens):
        """USN-03: POST retorna 405 — usinas sao criadas apenas pela coleta."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 2')
    def test_delete_nao_permitido(self, client, tokens, usina):
        """USN-03: DELETE retorna 405."""
        pass


@pytest.mark.django_db
class TestUsinaSnapshots:
    """Testes para GET /api/usinas/{id}/snapshots/ — USN-05."""

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 2')
    def test_snapshots_requer_autenticacao(self, client, usina):
        """USN-05: sem token retorna 401."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 2')
    def test_snapshots_retorna_historico_paginado(self, client, tokens, usina, snapshot_usina):
        """USN-05: retorna lista paginada de snapshots ordenados por -coletado_em."""
        pass

    @pytest.mark.skip(reason='Aguardando implementacao — Wave 2')
    def test_snapshots_paginacao_100(self, client, tokens, usina):
        """USN-05: page_size padrao e 100 (PaginacaoSnapshots)."""
        pass
