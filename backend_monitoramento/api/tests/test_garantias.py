import datetime
import pytest
from django.utils import timezone
from usinas.models import GarantiaUsina


@pytest.mark.django_db
class TestGarantiaUpsert:
    """Testes para PUT /api/usinas/{id}/garantia/ — GAR-02."""

    def test_criar_garantia(self, client, tokens, usina):
        """GAR-02: PUT cria garantia quando nao existe."""
        payload = {'data_inicio': '2025-01-01', 'meses': 24}
        response = client.put(
            f'/api/usinas/{usina.id}/garantia/',
            payload,
            content_type='application/json',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        data = response.json()
        assert data['meses'] == 24
        assert data['data_inicio'] == '2025-01-01'
        assert GarantiaUsina.objects.filter(usina=usina).exists()

    def test_substituir_garantia(self, client, tokens, usina, garantia_ativa):
        """GAR-02: PUT substitui garantia existente."""
        assert garantia_ativa.meses == 24
        payload = {'data_inicio': '2024-06-01', 'meses': 36}
        response = client.put(
            f'/api/usinas/{usina.id}/garantia/',
            payload,
            content_type='application/json',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        data = response.json()
        assert data['meses'] == 36
        # Garante que e o mesmo objeto (OneToOne)
        assert GarantiaUsina.objects.filter(usina=usina).count() == 1

    def test_resposta_inclui_data_fim(self, client, tokens, usina):
        """GAR-02/GAR-04: resposta do PUT inclui data_fim e dias_restantes."""
        payload = {'data_inicio': '2025-01-01', 'meses': 24}
        response = client.put(
            f'/api/usinas/{usina.id}/garantia/',
            payload,
            content_type='application/json',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        data = response.json()
        assert 'data_fim' in data
        assert 'dias_restantes' in data
        assert 'ativa' in data
        # data_fim deve ser 2027-01-01 (24 meses apos 2025-01-01)
        assert data['data_fim'] == '2027-01-01'
        assert isinstance(data['dias_restantes'], int)
        assert data['dias_restantes'] >= 0

    def test_upsert_requer_autenticacao(self, client, usina):
        """GAR-02: sem token retorna 401."""
        payload = {'data_inicio': '2025-01-01', 'meses': 24}
        response = client.put(
            f'/api/usinas/{usina.id}/garantia/',
            payload,
            content_type='application/json',
        )
        assert response.status_code == 401


@pytest.mark.django_db
class TestGarantiaFiltros:
    """Testes para GET /api/garantias/?filtro= — GAR-03."""

    def test_lista_todas_garantias(self, client, tokens, garantia_ativa, garantia_vencida):
        """GAR-03: sem filtro retorna todas."""
        response = client.get(
            '/api/garantias/',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        data = response.json()
        # Deve retornar pelo menos as 2 garantias criadas pelas fixtures
        assert data['count'] >= 2

    def test_filtro_ativas(self, client, tokens, garantia_ativa, garantia_vencida):
        """GAR-03: ?filtro=ativas retorna apenas ativas."""
        response = client.get(
            '/api/garantias/?filtro=ativas',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        data = response.json()
        resultados = data['results']
        assert len(resultados) >= 1
        # Todas as retornadas devem estar ativas
        assert all(g['ativa'] is True for g in resultados)
        # A garantia vencida nao deve estar
        ids = [g['usina_id'] for g in resultados]
        assert str(garantia_vencida.usina.id) not in ids

    def test_filtro_vencidas(self, client, tokens, garantia_ativa, garantia_vencida):
        """GAR-03: ?filtro=vencidas retorna apenas vencidas."""
        response = client.get(
            '/api/garantias/?filtro=vencidas',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        data = response.json()
        resultados = data['results']
        assert len(resultados) >= 1
        # Todas as retornadas devem estar vencidas
        assert all(g['ativa'] is False for g in resultados)
        # A garantia ativa nao deve estar
        ids = [g['usina_id'] for g in resultados]
        assert str(garantia_ativa.usina.id) not in ids

    def test_filtro_vencendo(self, client, tokens, usina):
        """GAR-03: ?filtro=vencendo retorna garantias com data_fim nos proximos 30 dias."""
        # Cria garantia que vence em 15 dias
        data_inicio = datetime.date.today() - datetime.timedelta(days=350)
        garantia_vencendo = GarantiaUsina.objects.create(
            usina=usina,
            data_inicio=data_inicio,
            meses=12,  # aprox. 365 dias — vence daqui a ~15 dias
        )
        # Verifica que a propriedade bate com o esperado (entre hoje e +30 dias)
        hoje = timezone.now().date()
        limite = hoje + datetime.timedelta(days=30)
        assert hoje <= garantia_vencendo.data_fim <= limite, (
            f"data_fim={garantia_vencendo.data_fim} nao esta no intervalo [{hoje}, {limite}]"
        )

        response = client.get(
            '/api/garantias/?filtro=vencendo',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        data = response.json()
        ids = [g['usina_id'] for g in data['results']]
        assert str(usina.id) in ids

    def test_dias_restantes_correto(self, client, tokens, garantia_ativa):
        """GAR-04: campo dias_restantes calculado corretamente."""
        response = client.get(
            '/api/garantias/?filtro=ativas',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        data = response.json()
        garantia_data = next(
            g for g in data['results']
            if g['usina_id'] == str(garantia_ativa.usina.id)
        )
        dias = garantia_data['dias_restantes']
        assert isinstance(dias, int)
        assert dias >= 0
        # Com 24 meses a partir de 30 dias atras, restam ~700 dias
        assert dias > 600

    def test_lista_requer_autenticacao(self, client):
        """GAR-03: sem token retorna 401."""
        response = client.get('/api/garantias/')
        assert response.status_code == 401


@pytest.mark.django_db
class TestGarantiaVisibilidade:
    """Testes para GAR-05 e GAR-06 — visibilidade por status de garantia."""

    def test_usina_sem_garantia_nao_aparece_com_filtro_ativas(self, client, tokens, usina):
        """GAR-05: usina sem garantia nao aparece ao filtrar garantias ativas."""
        response = client.get(
            '/api/garantias/?filtro=ativas',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        data = response.json()
        ids = [g['usina_id'] for g in data['results']]
        assert str(usina.id) not in ids

    def test_usina_com_garantia_ativa_aparece_com_filtro_ativas(self, client, tokens, usina, garantia_ativa):
        """GAR-06: usina com garantia ativa aparece ao filtrar garantias ativas."""
        response = client.get(
            '/api/garantias/?filtro=ativas',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        data = response.json()
        ids = [g['usina_id'] for g in data['results']]
        assert str(usina.id) in ids
