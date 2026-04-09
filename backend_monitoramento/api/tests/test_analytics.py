"""
Testes para os endpoints de analytics (Phase 03).

ANA-01: GET /api/analytics/potencia/
ANA-02: GET /api/analytics/ranking-fabricantes/
ANA-03: GET /api/analytics/mapa/

Todos os testes falham com 404 enquanto os endpoints nao existem (Plan 02 os implementa).
"""
import pytest
from django.utils import timezone
from provedores.models import CredencialProvedor
from usinas.models import Usina, SnapshotUsina, Inversor, SnapshotInversor

URL_POTENCIA = '/api/analytics/potencia/'
URL_RANKING = '/api/analytics/ranking-fabricantes/'
URL_MAPA = '/api/analytics/mapa/'


@pytest.mark.django_db
class TestPotenciaMedia:
    """ANA-01: potencia media geral e por provedor."""

    def test_requer_auth(self, client):
        """Sem token, retorna 401."""
        resp = client.get(URL_POTENCIA)
        assert resp.status_code == 401

    def test_media_geral(self, client, tokens, usina, snapshot_usina,
                         usina_hoymiles, snapshot_usina_hoymiles):
        """Com 2 usinas (solis 5.5kW, hoymiles 3.0kW), media_geral_kw = 4.25."""
        resp = client.get(URL_POTENCIA, HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        assert resp.status_code == 200
        data = resp.json()
        assert data['media_geral_kw'] == pytest.approx(4.25, abs=0.01)

    def test_por_provedor(self, client, tokens, usina, snapshot_usina,
                          usina_hoymiles, snapshot_usina_hoymiles):
        """por_provedor contem 2 entradas com provedores corretos e medias individuais."""
        resp = client.get(URL_POTENCIA, HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        assert resp.status_code == 200
        data = resp.json()
        por_provedor = data['por_provedor']
        assert len(por_provedor) == 2
        provedores = {item['provedor'] for item in por_provedor}
        assert 'solis' in provedores
        assert 'hoymiles' in provedores
        solis = next(item for item in por_provedor if item['provedor'] == 'solis')
        hoymiles = next(item for item in por_provedor if item['provedor'] == 'hoymiles')
        assert solis['media_kw'] == pytest.approx(5.5, abs=0.01)
        assert hoymiles['media_kw'] == pytest.approx(3.0, abs=0.01)

    def test_sem_snapshots(self, client, tokens, usina):
        """Nenhuma usina com snapshot: media_geral_kw = null, por_provedor = []."""
        resp = client.get(URL_POTENCIA, HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        assert resp.status_code == 200
        data = resp.json()
        assert data['media_geral_kw'] is None
        assert data['por_provedor'] == []

    def test_usina_sem_snapshot_excluida(self, client, tokens, usina, snapshot_usina,
                                          usina_hoymiles):
        """1 usina com snapshot + 1 sem: media so conta a com snapshot."""
        # usina_hoymiles sem snapshot — nao deve entrar no calculo
        resp = client.get(URL_POTENCIA, HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        assert resp.status_code == 200
        data = resp.json()
        # Apenas usina solis (5.5 kW) entra
        assert data['media_geral_kw'] == pytest.approx(5.5, abs=0.01)
        assert len(data['por_provedor']) == 1
        assert data['por_provedor'][0]['provedor'] == 'solis'


@pytest.mark.django_db
class TestRankingFabricantes:
    """ANA-02: top 5 fabricantes por inversores ativos."""

    def test_requer_auth(self, client):
        """Sem token, retorna 401."""
        resp = client.get(URL_RANKING)
        assert resp.status_code == 401

    def test_ranking_ordenado(self, client, tokens, inversor, snapshot_inversor,
                               inversor_hoymiles, snapshot_inversor_hoymiles):
        """Com inversores ativos de 2 provedores, retorna ordenado desc por inversores_ativos."""
        resp = client.get(URL_RANKING, HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        assert resp.status_code == 200
        data = resp.json()
        ranking = data['ranking']
        assert len(ranking) >= 2
        # Verificar que esta ordenado desc
        contagens = [item['inversores_ativos'] for item in ranking]
        assert contagens == sorted(contagens, reverse=True)

    def test_top_5_limite(self, client, tokens, db):
        """Com mais de 5 provedores, retorna exatamente 5."""
        provedores = ['solis', 'hoymiles', 'fusionsolar', 'growatt', 'deye', 'goodwe']
        for i, prov in enumerate(provedores):
            cred = CredencialProvedor.objects.create(
                provedor=prov,
                credenciais_enc=f'placeholder-{prov}',
                ativo=True,
            )
            usina = Usina.objects.create(
                id_usina_provedor=f'top5-{i:03d}',
                provedor=prov,
                credencial=cred,
                nome=f'Usina {prov}',
                capacidade_kwp=10.0,
                ativo=True,
            )
            inv = Inversor.objects.create(
                usina=usina,
                id_inversor_provedor=f'inv-top5-{i:03d}',
                numero_serie=f'SN-TOP5-{i}',
                modelo='Modelo X',
            )
            snap_inv = SnapshotInversor.objects.create(
                inversor=inv,
                coletado_em=timezone.now(),
                estado='normal',
                pac_kw=float(i + 1),
                energia_hoje_kwh=10.0,
                energia_total_kwh=1000.0,
            )
            inv.ultimo_snapshot = snap_inv
            inv.save(update_fields=['ultimo_snapshot'])

        resp = client.get(URL_RANKING, HTTP_AUTHORIZATION=None)
        # Sem token — 401 (confirma que auth e necessaria mesmo com dados)
        assert resp.status_code == 401

    def test_top_5_limite_autenticado(self, client, tokens, db):
        """Com mais de 5 provedores ativos, retorna exatamente 5."""
        provedores = ['solis', 'hoymiles', 'fusionsolar', 'growatt', 'deye', 'goodwe']
        for i, prov in enumerate(provedores):
            cred = CredencialProvedor.objects.create(
                provedor=prov,
                credenciais_enc=f'placeholder-{prov}',
                ativo=True,
            )
            usina = Usina.objects.create(
                id_usina_provedor=f'lim-{i:03d}',
                provedor=prov,
                credencial=cred,
                nome=f'Usina Limite {prov}',
                capacidade_kwp=10.0,
                ativo=True,
            )
            inv = Inversor.objects.create(
                usina=usina,
                id_inversor_provedor=f'inv-lim-{i:03d}',
                numero_serie=f'SN-LIM-{i}',
                modelo='Modelo Y',
            )
            snap_inv = SnapshotInversor.objects.create(
                inversor=inv,
                coletado_em=timezone.now(),
                estado='normal',
                pac_kw=float(i + 1),
                energia_hoje_kwh=10.0,
                energia_total_kwh=1000.0,
            )
            inv.ultimo_snapshot = snap_inv
            inv.save(update_fields=['ultimo_snapshot'])

        resp = client.get(URL_RANKING, HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        assert resp.status_code == 200
        data = resp.json()
        assert len(data['ranking']) == 5

    def test_exclui_sem_snapshot(self, client, tokens, inversor_inativo):
        """Inversor sem ultimo_snapshot nao conta como ativo."""
        resp = client.get(URL_RANKING, HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        assert resp.status_code == 200
        data = resp.json()
        # inversor_inativo nao deve contribuir para nenhuma contagem
        for item in data['ranking']:
            # Solis tem um inversor inativo — inversores_ativos deve ser 0
            if item['provedor'] == 'solis':
                assert item['inversores_ativos'] == 0

    def test_exclui_pac_zero(self, client, tokens, inversor_pac_zero):
        """Inversor com pac_kw=0 nao conta como ativo."""
        resp = client.get(URL_RANKING, HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        assert resp.status_code == 200
        data = resp.json()
        # inversor_pac_zero nao deve contribuir para contagem de ativos
        for item in data['ranking']:
            if item['provedor'] == 'solis':
                assert item['inversores_ativos'] == 0

    def test_sem_inversores(self, client, tokens):
        """Nenhum inversor: ranking = []."""
        resp = client.get(URL_RANKING, HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        assert resp.status_code == 200
        data = resp.json()
        assert data['ranking'] == []


@pytest.mark.django_db
class TestMapaUsinas:
    """ANA-03: todas as usinas com lat/lng, provedor e status para o mapa."""

    def test_requer_auth(self, client):
        """Sem token, retorna 401."""
        resp = client.get(URL_MAPA)
        assert resp.status_code == 401

    def test_retorna_todas_usinas(self, client, tokens, usina, usina_hoymiles):
        """Com 2 usinas, retorna lista com 2 itens."""
        resp = client.get(URL_MAPA, HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_sem_coords_retorna_null(self, client, tokens, usina):
        """Usina sem lat/lng retorna latitude=null, longitude=null (nao omitida)."""
        # usina criada sem coordenadas
        resp = client.get(URL_MAPA, HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        item = data[0]
        assert 'latitude' in item
        assert 'longitude' in item
        assert item['latitude'] is None
        assert item['longitude'] is None

    def test_com_coords(self, client, tokens, usina):
        """Usina com lat/lng retorna valores corretos."""
        usina.latitude = -23.5505
        usina.longitude = -46.6333
        usina.save(update_fields=['latitude', 'longitude'])

        resp = client.get(URL_MAPA, HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        item = data[0]
        assert item['latitude'] == pytest.approx(-23.5505, abs=0.0001)
        assert item['longitude'] == pytest.approx(-46.6333, abs=0.0001)

    def test_sem_paginacao(self, client, tokens, db):
        """Resposta e array direto (sem keys count/next/previous)."""
        cred = CredencialProvedor.objects.create(
            provedor='solis',
            credenciais_enc='placeholder',
            ativo=True,
        )
        # Criar 15 usinas para garantir que paginacao nao seria acionada se existisse
        for i in range(15):
            Usina.objects.create(
                id_usina_provedor=f'pag-{i:03d}',
                provedor='solis',
                credencial=cred,
                nome=f'Usina Paginacao {i}',
                capacidade_kwp=10.0,
                ativo=True,
            )

        resp = client.get(URL_MAPA, HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        assert resp.status_code == 200
        data = resp.json()
        # Deve ser lista direta, nao objeto paginado
        assert isinstance(data, list)
        assert len(data) == 15
        # Garantir que nao e resposta paginada
        assert not isinstance(data, dict)

    def test_inclui_status(self, client, tokens, usina, snapshot_usina):
        """Cada usina tem campo status (valor de ultimo_snapshot.status ou 'sem_dados')."""
        resp = client.get(URL_MAPA, HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        item = data[0]
        assert 'status' in item
        # usina tem snapshot com status='normal'
        assert item['status'] == 'normal'

    def test_status_sem_dados_quando_sem_snapshot(self, client, tokens, usina):
        """Usina sem snapshot retorna status='sem_dados'."""
        resp = client.get(URL_MAPA, HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        item = data[0]
        assert item['status'] == 'sem_dados'

    def test_campos_obrigatorios(self, client, tokens, usina):
        """Cada item da lista contem os campos esperados: id, nome, provedor, lat, lng, ativo, status."""
        resp = client.get(URL_MAPA, HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        item = data[0]
        for campo in ['id', 'nome', 'provedor', 'latitude', 'longitude', 'ativo', 'status']:
            assert campo in item, f"Campo '{campo}' ausente na resposta"
