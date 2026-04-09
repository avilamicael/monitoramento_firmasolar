import pytest


@pytest.mark.django_db
class TestAlertaList:
    """Testes para GET /api/alertas/ — ALT-01, ALT-04."""

    def test_lista_requer_autenticacao(self, client):
        """ALT-01: sem token retorna 401."""
        response = client.get('/api/alertas/')
        assert response.status_code == 401

    def test_lista_autenticado(self, client, tokens, alerta):
        """ALT-01: com token retorna lista paginada."""
        response = client.get(
            '/api/alertas/',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        data = response.json()
        assert 'results' in data
        assert len(data['results']) >= 1
        primeiro = data['results'][0]
        assert 'com_garantia' in primeiro
        assert 'usina_nome' in primeiro
        assert 'payload_bruto' not in primeiro

    def test_filtro_por_estado(self, client, tokens, alerta):
        """ALT-01: ?estado=ativo retorna apenas alertas ativos."""
        response = client.get(
            '/api/alertas/?estado=ativo',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data['results']) >= 1
        for r in data['results']:
            assert r['estado'] == 'ativo'

    def test_filtro_por_nivel(self, client, tokens, alerta):
        """ALT-01: ?nivel=aviso retorna apenas alertas de nivel aviso."""
        response = client.get(
            '/api/alertas/?nivel=aviso',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data['results']) >= 1
        for r in data['results']:
            assert r['nivel'] == 'aviso'

    def test_filtro_por_usina(self, client, tokens, alerta):
        """ALT-01: ?usina={id} retorna apenas alertas daquela usina."""
        response = client.get(
            f'/api/alertas/?usina={alerta.usina.id}',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data['results']) >= 1
        for r in data['results']:
            assert str(alerta.usina.id) == r['usina']

    def test_campo_com_garantia_true(self, client, tokens, alerta, garantia_ativa):
        """ALT-04: alerta de usina com garantia ativa tem com_garantia=true."""
        response = client.get(
            '/api/alertas/',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        data = response.json()
        alertas_usina = [r for r in data['results'] if str(alerta.usina.id) == r['usina']]
        assert len(alertas_usina) >= 1
        assert alertas_usina[0]['com_garantia'] is True

    def test_campo_com_garantia_false(self, client, tokens, alerta):
        """ALT-04: alerta de usina sem garantia tem com_garantia=false."""
        response = client.get(
            '/api/alertas/',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        data = response.json()
        alertas_usina = [r for r in data['results'] if str(alerta.usina.id) == r['usina']]
        assert len(alertas_usina) >= 1
        assert alertas_usina[0]['com_garantia'] is False


@pytest.mark.django_db
class TestAlertaDetalhe:
    """Testes para GET /api/alertas/{id}/ — ALT-02."""

    def test_detalhe_requer_autenticacao(self, client, alerta):
        """ALT-02: sem token retorna 401."""
        response = client.get(f'/api/alertas/{alerta.id}/')
        assert response.status_code == 401

    def test_detalhe_retorna_dados_completos(self, client, tokens, alerta):
        """ALT-02: detalhe inclui todos os campos do alerta."""
        response = client.get(
            f'/api/alertas/{alerta.id}/',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        data = response.json()
        assert 'mensagem' in data
        assert 'nivel' in data
        assert 'estado' in data
        assert 'sugestao' in data
        assert 'anotacoes' in data
        assert 'com_garantia' in data
        assert 'payload_bruto' not in data

    def test_detalhe_inclui_com_garantia(self, client, tokens, alerta):
        """ALT-02/ALT-04: detalhe inclui campo com_garantia."""
        response = client.get(
            f'/api/alertas/{alerta.id}/',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        data = response.json()
        assert 'com_garantia' in data
        assert isinstance(data['com_garantia'], bool)


@pytest.mark.django_db
class TestAlertaPatch:
    """Testes para PATCH /api/alertas/{id}/ — ALT-03."""

    def test_patch_requer_autenticacao(self, client, alerta):
        """ALT-03: sem token retorna 401."""
        response = client.patch(
            f'/api/alertas/{alerta.id}/',
            {'estado': 'em_atendimento'},
            content_type='application/json',
        )
        assert response.status_code == 401

    def test_patch_atualiza_estado(self, client, tokens, alerta):
        """ALT-03: PATCH com estado='em_atendimento' atualiza o campo."""
        response = client.patch(
            f'/api/alertas/{alerta.id}/',
            {'estado': 'em_atendimento'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        alerta.refresh_from_db()
        assert alerta.estado == 'em_atendimento'

    def test_patch_atualiza_anotacoes(self, client, tokens, alerta):
        """ALT-03: PATCH com anotacoes atualiza o campo."""
        response = client.patch(
            f'/api/alertas/{alerta.id}/',
            {'anotacoes': 'Verificado e em acompanhamento.'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        alerta.refresh_from_db()
        assert alerta.anotacoes == 'Verificado e em acompanhamento.'

    def test_post_nao_permitido(self, client, tokens):
        """ALT-03: POST retorna 405 — alertas sao criados pela coleta."""
        response = client.post(
            '/api/alertas/',
            {},
            content_type='application/json',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 405

    def test_delete_nao_permitido(self, client, tokens, alerta):
        """ALT-03: DELETE retorna 405."""
        response = client.delete(
            f'/api/alertas/{alerta.id}/',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 405
