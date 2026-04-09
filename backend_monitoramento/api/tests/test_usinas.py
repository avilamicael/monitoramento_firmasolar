import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestUsinaList:
    """Testes para GET /api/usinas/ — USN-01, USN-04."""

    def test_lista_requer_autenticacao(self, client):
        """USN-01: sem token retorna 401."""
        response = client.get('/api/usinas/')
        assert response.status_code == 401

    def test_lista_autenticado_retorna_usinas(self, client, tokens, usina):
        """USN-01: com token retorna lista paginada."""
        response = client.get(
            '/api/usinas/',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        data = response.json()
        assert 'results' in data
        assert data['count'] >= 1

    def test_filtro_por_provedor(self, client, tokens, usina, usina_hoymiles):
        """USN-01: ?provedor=solis retorna apenas usinas solis."""
        response = client.get(
            '/api/usinas/?provedor=solis',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        data = response.json()
        assert all(u['provedor'] == 'solis' for u in data['results'])
        # Garante que a usina solis aparece
        ids = [u['id'] for u in data['results']]
        assert str(usina.id) in ids

    def test_filtro_por_ativo(self, client, tokens, usina):
        """USN-01: ?ativo=true retorna apenas usinas ativas."""
        response = client.get(
            '/api/usinas/?ativo=true',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        data = response.json()
        assert all(u['ativo'] is True for u in data['results'])

    def test_filtro_por_status_garantia_ativa(self, client, tokens, usina, garantia_ativa):
        """USN-01: ?status_garantia=ativa retorna usinas com garantia ativa."""
        response = client.get(
            '/api/usinas/?status_garantia=ativa',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        data = response.json()
        ids = [u['id'] for u in data['results']]
        assert str(usina.id) in ids
        # Todas as usinas retornadas devem ter status_garantia='ativa'
        assert all(u['status_garantia'] == 'ativa' for u in data['results'])

    def test_filtro_por_status_garantia_sem_garantia(self, client, tokens, usina):
        """USN-01: ?status_garantia=sem_garantia retorna usinas sem garantia."""
        response = client.get(
            '/api/usinas/?status_garantia=sem_garantia',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        data = response.json()
        ids = [u['id'] for u in data['results']]
        assert str(usina.id) in ids
        assert all(u['status_garantia'] == 'sem_garantia' for u in data['results'])

    def test_campo_status_garantia_sem_garantia(self, client, tokens, usina):
        """USN-04: usina sem GarantiaUsina retorna status_garantia='sem_garantia'."""
        response = client.get(
            '/api/usinas/',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        data = response.json()
        usina_data = next(u for u in data['results'] if u['id'] == str(usina.id))
        assert usina_data['status_garantia'] == 'sem_garantia'

    def test_campo_status_garantia_ativa(self, client, tokens, usina, garantia_ativa):
        """USN-04: usina com garantia ativa retorna status_garantia='ativa'."""
        response = client.get(
            '/api/usinas/',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        data = response.json()
        usina_data = next(u for u in data['results'] if u['id'] == str(usina.id))
        assert usina_data['status_garantia'] == 'ativa'

    def test_campo_status_garantia_vencida(self, client, tokens, usina_hoymiles, garantia_vencida):
        """USN-04: usina com garantia vencida retorna status_garantia='vencida'."""
        response = client.get(
            '/api/usinas/',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        data = response.json()
        usina_data = next(u for u in data['results'] if u['id'] == str(usina_hoymiles.id))
        assert usina_data['status_garantia'] == 'vencida'


@pytest.mark.django_db
class TestUsinaDetalhe:
    """Testes para GET /api/usinas/{id}/ — USN-02."""

    def test_detalhe_requer_autenticacao(self, client, usina):
        """USN-02: sem token retorna 401."""
        response = client.get(f'/api/usinas/{usina.id}/')
        assert response.status_code == 401

    def test_detalhe_retorna_inversores(self, client, tokens, usina, inversor):
        """USN-02: detalhe inclui lista de inversores."""
        response = client.get(
            f'/api/usinas/{usina.id}/',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        data = response.json()
        assert 'inversores' in data
        assert len(data['inversores']) == 1
        assert data['inversores'][0]['id'] == str(inversor.id)

    def test_detalhe_retorna_ultimo_snapshot(self, client, tokens, usina, snapshot_usina):
        """USN-02: detalhe inclui dados do ultimo snapshot."""
        response = client.get(
            f'/api/usinas/{usina.id}/',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        data = response.json()
        assert data['ultimo_snapshot'] is not None
        assert data['ultimo_snapshot']['id'] == str(snapshot_usina.id)
        # payload_bruto NUNCA deve aparecer em respostas de snapshot
        assert 'payload_bruto' not in data['ultimo_snapshot']

    def test_detalhe_usina_sem_snapshot(self, client, tokens, usina):
        """USN-02: usina sem snapshot retorna ultimo_snapshot=null."""
        response = client.get(
            f'/api/usinas/{usina.id}/',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        data = response.json()
        assert data['ultimo_snapshot'] is None


@pytest.mark.django_db
class TestUsinaPatch:
    """Testes para PATCH /api/usinas/{id}/ — USN-03."""

    def test_patch_requer_autenticacao(self, client, usina):
        """USN-03: sem token retorna 401."""
        response = client.patch(
            f'/api/usinas/{usina.id}/',
            {'nome': 'Novo Nome'},
            content_type='application/json',
        )
        assert response.status_code == 401

    def test_patch_atualiza_nome(self, client, tokens, usina):
        """USN-03: PATCH com nome atualiza o campo."""
        response = client.patch(
            f'/api/usinas/{usina.id}/',
            {'nome': 'Nome Atualizado'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        usina.refresh_from_db()
        assert usina.nome == 'Nome Atualizado'

    def test_patch_atualiza_capacidade(self, client, tokens, usina):
        """USN-03: PATCH com capacidade_kwp atualiza o campo."""
        response = client.patch(
            f'/api/usinas/{usina.id}/',
            {'capacidade_kwp': 15.0},
            content_type='application/json',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        usina.refresh_from_db()
        assert usina.capacidade_kwp == 15.0

    def test_post_nao_permitido(self, client, tokens):
        """USN-03: POST retorna 405 — usinas sao criadas apenas pela coleta."""
        response = client.post(
            '/api/usinas/',
            {'nome': 'Nova'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 405

    def test_delete_nao_permitido(self, client, tokens, usina):
        """USN-03: DELETE retorna 405."""
        response = client.delete(
            f'/api/usinas/{usina.id}/',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 405


@pytest.mark.django_db
class TestUsinaSnapshots:
    """Testes para GET /api/usinas/{id}/snapshots/ — USN-05."""

    def test_snapshots_requer_autenticacao(self, client, usina):
        """USN-05: sem token retorna 401."""
        response = client.get(f'/api/usinas/{usina.id}/snapshots/')
        assert response.status_code == 401

    def test_snapshots_retorna_historico_paginado(self, client, tokens, usina, snapshot_usina):
        """USN-05: retorna lista paginada de snapshots ordenados por -coletado_em."""
        response = client.get(
            f'/api/usinas/{usina.id}/snapshots/',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        data = response.json()
        assert 'results' in data
        assert data['count'] >= 1
        # payload_bruto NUNCA deve aparecer
        for snap in data['results']:
            assert 'payload_bruto' not in snap

    def test_snapshots_paginacao_100(self, client, tokens, usina):
        """USN-05: page_size padrao e 100 (PaginacaoSnapshots)."""
        response = client.get(
            f'/api/usinas/{usina.id}/snapshots/',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        data = response.json()
        # Com 0 snapshots, count deve ser 0 e results vazio
        assert 'count' in data
        assert 'results' in data
