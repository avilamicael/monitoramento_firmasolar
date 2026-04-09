import pytest


@pytest.mark.django_db
class TestInversorList:
    """Testes para GET /api/inversores/ — INV-01."""

    def test_lista_requer_autenticacao(self, client):
        """INV-01: sem token retorna 401."""
        response = client.get('/api/inversores/')
        assert response.status_code == 401

    def test_lista_autenticado(self, client, tokens, inversor):
        """INV-01: com token retorna lista paginada."""
        response = client.get(
            '/api/inversores/',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        data = response.json()
        assert 'results' in data
        assert len(data['results']) >= 1
        primeiro = data['results'][0]
        assert 'usina_nome' in primeiro
        assert 'numero_serie' in primeiro
        assert 'modelo' in primeiro
        assert 'payload_bruto' not in primeiro

    def test_filtro_por_usina(self, client, tokens, inversor, usina_hoymiles):
        """INV-01: ?usina={id} retorna apenas inversores daquela usina."""
        response = client.get(
            f'/api/inversores/?usina={inversor.usina.id}',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        data = response.json()
        ids_usina = [r['usina'] for r in data['results']]
        assert all(str(inversor.usina.id) == uid for uid in ids_usina)

    def test_filtro_por_modelo(self, client, tokens, inversor):
        """INV-01: ?modelo=Solis retorna apenas inversores daquele modelo."""
        response = client.get(
            '/api/inversores/?modelo=Solis',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data['results']) >= 1
        for r in data['results']:
            assert 'Solis' in r['modelo']


@pytest.mark.django_db
class TestInversorDetalhe:
    """Testes para GET /api/inversores/{id}/ — INV-02."""

    def test_detalhe_requer_autenticacao(self, client, inversor):
        """INV-02: sem token retorna 401."""
        response = client.get(f'/api/inversores/{inversor.id}/')
        assert response.status_code == 401

    def test_detalhe_retorna_ultimo_snapshot(self, client, tokens, inversor, snapshot_inversor):
        """INV-02: detalhe inclui dados completos do ultimo snapshot."""
        response = client.get(
            f'/api/inversores/{inversor.id}/',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        data = response.json()
        snap = data['ultimo_snapshot']
        assert snap is not None
        assert 'pac_kw' in snap
        assert 'tensao_ac_v' in snap
        assert 'corrente_ac_a' in snap
        assert 'tensao_dc_v' in snap
        assert 'corrente_dc_a' in snap
        assert 'frequencia_hz' in snap
        assert 'temperatura_c' in snap
        assert 'payload_bruto' not in snap

    def test_detalhe_sem_snapshot(self, client, tokens, inversor):
        """INV-02: inversor sem snapshot retorna ultimo_snapshot=null."""
        response = client.get(
            f'/api/inversores/{inversor.id}/',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        data = response.json()
        assert data['ultimo_snapshot'] is None


@pytest.mark.django_db
class TestInversorSnapshots:
    """Testes para GET /api/inversores/{id}/snapshots/ — INV-03."""

    def test_snapshots_requer_autenticacao(self, client, inversor):
        """INV-03: sem token retorna 401."""
        response = client.get(f'/api/inversores/{inversor.id}/snapshots/')
        assert response.status_code == 401

    def test_snapshots_retorna_historico_paginado(self, client, tokens, inversor, snapshot_inversor):
        """INV-03: retorna lista paginada de snapshots."""
        response = client.get(
            f'/api/inversores/{inversor.id}/snapshots/',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        data = response.json()
        assert 'results' in data
        assert len(data['results']) >= 1
        snap = data['results'][0]
        assert 'pac_kw' in snap
        assert 'payload_bruto' not in snap

    def test_post_nao_permitido(self, client, tokens):
        """INV: POST retorna 405 — inversores sao criados pela coleta."""
        response = client.post(
            '/api/inversores/',
            {},
            content_type='application/json',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 405

    def test_delete_nao_permitido(self, client, tokens, inversor):
        """INV: DELETE retorna 405."""
        response = client.delete(
            f'/api/inversores/{inversor.id}/',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 405
