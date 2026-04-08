import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestCORS:
    """Testes de CORS — cobre API-05."""

    def test_cors_bloqueia_origem_invalida(self, client, settings):
        """API-05: Origem nao listada nao recebe header CORS."""
        settings.CORS_ALLOWED_ORIGINS = ['http://painel.firmasolar.com.br']
        response = client.options(
            reverse('token_obtain_pair'),
            HTTP_ORIGIN='http://atacante.com',
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST',
        )
        assert 'Access-Control-Allow-Origin' not in response

    def test_cors_permite_origem_valida(self, client, settings):
        """API-05: Origem configurada recebe header CORS correto."""
        settings.CORS_ALLOWED_ORIGINS = ['http://localhost:5173']
        response = client.options(
            reverse('token_obtain_pair'),
            HTTP_ORIGIN='http://localhost:5173',
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST',
        )
        assert response['Access-Control-Allow-Origin'] == 'http://localhost:5173'
