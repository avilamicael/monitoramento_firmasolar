import pytest
import json
import base64
from django.urls import reverse


@pytest.mark.django_db
class TestAutenticacaoJWT:
    """Testes de autenticacao JWT — cobre API-02, API-03, API-04, API-06."""

    @pytest.fixture
    def usuario(self, django_user_model):
        return django_user_model.objects.create_user(
            username='admin', password='senha123'
        )

    @pytest.fixture
    def tokens(self, client, usuario):
        response = client.post(
            reverse('token_obtain_pair'),
            {'username': 'admin', 'password': 'senha123'},
            content_type='application/json',
        )
        return response.json()

    def test_login_retorna_tokens(self, client, usuario):
        """API-02: Login com credenciais validas retorna access e refresh."""
        response = client.post(
            reverse('token_obtain_pair'),
            {'username': 'admin', 'password': 'senha123'},
            content_type='application/json',
        )
        assert response.status_code == 200
        data = response.json()
        assert 'access' in data
        assert 'refresh' in data

    def test_login_credenciais_invalidas(self, client, usuario):
        """API-02: Login com credenciais invalidas retorna 401."""
        response = client.post(
            reverse('token_obtain_pair'),
            {'username': 'admin', 'password': 'errada'},
            content_type='application/json',
        )
        assert response.status_code == 401

    def test_refresh_emite_novo_access(self, client, tokens):
        """API-03: Refresh valido emite novo access token."""
        response = client.post(
            reverse('token_refresh'),
            {'refresh': tokens['refresh']},
            content_type='application/json',
        )
        assert response.status_code == 200
        assert 'access' in response.json()

    def test_refresh_token_rotacionado_invalido(self, client, tokens):
        """API-03/API-06: Token original nao e reutilizavel apos rotacao."""
        # Primeiro uso — deve funcionar
        response1 = client.post(
            reverse('token_refresh'),
            {'refresh': tokens['refresh']},
            content_type='application/json',
        )
        assert response1.status_code == 200

        # Segundo uso do MESMO refresh — deve falhar (blacklist)
        response2 = client.post(
            reverse('token_refresh'),
            {'refresh': tokens['refresh']},
            content_type='application/json',
        )
        assert response2.status_code == 401

    def test_endpoint_protegido_sem_token(self, client):
        """API-04: Endpoint protegido rejeita requisicao sem token."""
        response = client.get(reverse('api_ping'))
        assert response.status_code == 401

    def test_endpoint_protegido_com_token(self, client, tokens):
        """API-04: Endpoint protegido aceita requisicao com token valido."""
        response = client.get(
            reverse('api_ping'),
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        assert response.json() == {'status': 'ok'}

    def test_token_lifetimes(self, tokens):
        """API-06: Access token expira em 15 min; refresh em 7 dias."""
        def decode_payload(token):
            payload = token.split('.')[1]
            # Adiciona padding para base64
            payload += '=' * (4 - len(payload) % 4)
            return json.loads(base64.urlsafe_b64decode(payload))

        access_payload = decode_payload(tokens['access'])
        assert access_payload['exp'] - access_payload['iat'] == 900  # 15 min

        refresh_payload = decode_payload(tokens['refresh'])
        assert refresh_payload['exp'] - refresh_payload['iat'] == 604800  # 7 dias
