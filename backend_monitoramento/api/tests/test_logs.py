import pytest
from coleta.models import LogColeta


@pytest.mark.django_db
class TestLogColetaList:

    def test_lista_logs_autenticado(self, client, tokens, credencial):
        """LOG-01: lista logs com status e timestamp"""
        LogColeta.objects.create(
            credencial=credencial,
            status='sucesso',
            usinas_coletadas=3,
            inversores_coletados=9,
            alertas_sincronizados=0,
            duracao_ms=1500,
        )
        LogColeta.objects.create(
            credencial=credencial,
            status='erro',
            usinas_coletadas=0,
            inversores_coletados=0,
            alertas_sincronizados=0,
            duracao_ms=200,
            detalhe_erro='Timeout na API do provedor',
        )

        response = client.get(
            '/api/coleta/logs/',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )

        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 2
        results = data['results']
        # Ordenacao: mais recente primeiro (Meta.ordering = ['-iniciado_em'])
        assert results[0]['status'] == 'erro'
        assert results[0]['iniciado_em'] is not None
        assert results[1]['status'] == 'sucesso'
        assert 'provedor_nome' in results[0]

    def test_lista_logs_sem_token_retorna_401(self, client):
        """Todos os endpoints retornam 401 sem token — sem excecoes"""
        response = client.get('/api/coleta/logs/')
        assert response.status_code in [401, 403]

    def test_lista_logs_vazia(self, client, tokens):
        """Caso de borda: sem logs ainda"""
        response = client.get(
            '/api/coleta/logs/',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        assert response.json()['count'] == 0

    def test_detalhe_erro_presente_quando_preenchido(self, client, tokens, credencial):
        """Campo detalhe_erro aparece quando ha erro"""
        LogColeta.objects.create(
            credencial=credencial,
            status='erro',
            detalhe_erro='Connection refused',
        )
        response = client.get(
            '/api/coleta/logs/',
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert response.status_code == 200
        resultado = response.json()['results'][0]
        assert resultado['detalhe_erro'] == 'Connection refused'
