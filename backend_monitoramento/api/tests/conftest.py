import pytest
import datetime
from django.utils import timezone
from provedores.models import CredencialProvedor
from usinas.models import Usina, Inversor, SnapshotUsina, SnapshotInversor, GarantiaUsina
from alertas.models import Alerta, CatalogoAlarme
from coleta.models import LogColeta


@pytest.fixture
def credencial(db):
    """CredencialProvedor minima para testes."""
    return CredencialProvedor.objects.create(
        provedor='solis',
        credenciais_enc='placeholder-nao-usado-em-testes',
        ativo=True,
    )


@pytest.fixture
def usina(db, credencial):
    """Usina basica sem garantia."""
    return Usina.objects.create(
        id_usina_provedor='test-001',
        provedor='solis',
        credencial=credencial,
        nome='Usina Teste',
        capacidade_kwp=10.0,
        ativo=True,
    )


@pytest.fixture
def usina_hoymiles(db):
    """Segunda usina de outro provedor para testar filtros."""
    cred = CredencialProvedor.objects.create(
        provedor='hoymiles',
        credenciais_enc='placeholder',
        ativo=True,
    )
    return Usina.objects.create(
        id_usina_provedor='test-002',
        provedor='hoymiles',
        credencial=cred,
        nome='Usina Hoymiles',
        capacidade_kwp=5.0,
        ativo=True,
    )


@pytest.fixture
def garantia_ativa(db, usina):
    """GarantiaUsina com 24 meses iniciada ha 30 dias (ativa)."""
    return GarantiaUsina.objects.create(
        usina=usina,
        data_inicio=datetime.date.today() - datetime.timedelta(days=30),
        meses=24,
    )


@pytest.fixture
def garantia_vencida(db, usina_hoymiles):
    """GarantiaUsina vencida (iniciada ha 2 anos, duracao 12 meses)."""
    return GarantiaUsina.objects.create(
        usina=usina_hoymiles,
        data_inicio=datetime.date.today() - datetime.timedelta(days=730),
        meses=12,
    )


@pytest.fixture
def snapshot_usina(db, usina):
    """SnapshotUsina recente vinculado a usina."""
    snap = SnapshotUsina.objects.create(
        usina=usina,
        coletado_em=timezone.now(),
        potencia_kw=5.5,
        energia_hoje_kwh=12.3,
        energia_mes_kwh=300.0,
        energia_total_kwh=10000.0,
        status='normal',
        qtd_inversores=2,
        qtd_inversores_online=2,
        qtd_alertas=0,
    )
    usina.ultimo_snapshot = snap
    usina.save(update_fields=['ultimo_snapshot'])
    return snap


@pytest.fixture
def inversor(db, usina):
    """Inversor basico vinculado a usina."""
    return Inversor.objects.create(
        usina=usina,
        id_inversor_provedor='inv-001',
        numero_serie='SN12345',
        modelo='Solis 5K',
    )


@pytest.fixture
def snapshot_inversor(db, inversor):
    """SnapshotInversor recente vinculado ao inversor."""
    snap = SnapshotInversor.objects.create(
        inversor=inversor,
        coletado_em=timezone.now(),
        estado='normal',
        pac_kw=4.8,
        energia_hoje_kwh=10.0,
        energia_total_kwh=5000.0,
        tensao_ac_v=220.5,
        corrente_ac_a=21.8,
        tensao_dc_v=380.0,
        corrente_dc_a=12.6,
        frequencia_hz=60.01,
        temperatura_c=45.2,
    )
    inversor.ultimo_snapshot = snap
    inversor.save(update_fields=['ultimo_snapshot'])
    return snap


@pytest.fixture
def catalogo_alarme(db):
    """CatalogoAlarme para criacao de alertas."""
    return CatalogoAlarme.objects.create(
        provedor='solis',
        id_alarme_provedor='ALM-001',
        nome_pt='Falha de comunicacao',
        tipo='comunicacao',
        nivel_padrao='aviso',
    )


@pytest.fixture
def alerta(db, usina, catalogo_alarme):
    """Alerta ativo vinculado a usina."""
    return Alerta.objects.create(
        usina=usina,
        catalogo_alarme=catalogo_alarme,
        id_alerta_provedor='alert-001',
        mensagem='Falha de comunicacao com inversor',
        nivel='aviso',
        inicio=timezone.now() - datetime.timedelta(hours=2),
        estado='ativo',
    )


@pytest.fixture
def log_coleta(db, credencial):
    """LogColeta de sucesso."""
    return LogColeta.objects.create(
        credencial=credencial,
        status='sucesso',
        usinas_coletadas=5,
        inversores_coletados=20,
        alertas_sincronizados=3,
        duracao_ms=1200,
    )


@pytest.fixture
def tokens(client, db, django_user_model):
    """Access e refresh tokens para autenticacao."""
    django_user_model.objects.create_user(username='admin', password='senha123')
    response = client.post(
        '/api/auth/token/',
        {'username': 'admin', 'password': 'senha123'},
        content_type='application/json',
    )
    return response.json()


# --- Fixtures de analytics (Phase 03) ---

@pytest.fixture
def snapshot_usina_hoymiles(db, usina_hoymiles):
    """SnapshotUsina para usina_hoymiles — 3.0 kW, status normal."""
    snap = SnapshotUsina.objects.create(
        usina=usina_hoymiles,
        coletado_em=timezone.now(),
        potencia_kw=3.0,
        energia_hoje_kwh=6.0,
        energia_mes_kwh=150.0,
        energia_total_kwh=5000.0,
        status='normal',
        qtd_inversores=1,
        qtd_inversores_online=1,
        qtd_alertas=0,
    )
    usina_hoymiles.ultimo_snapshot = snap
    usina_hoymiles.save(update_fields=['ultimo_snapshot'])
    return snap


@pytest.fixture
def inversor_hoymiles(db, usina_hoymiles):
    """Inversor vinculado a usina_hoymiles."""
    return Inversor.objects.create(
        usina=usina_hoymiles,
        id_inversor_provedor='inv-hoymiles-001',
        numero_serie='HM12345',
        modelo='HM-1500',
    )


@pytest.fixture
def snapshot_inversor_hoymiles(db, inversor_hoymiles):
    """SnapshotInversor para inversor_hoymiles — pac_kw=2.5."""
    snap = SnapshotInversor.objects.create(
        inversor=inversor_hoymiles,
        coletado_em=timezone.now(),
        estado='normal',
        pac_kw=2.5,
        energia_hoje_kwh=5.0,
        energia_total_kwh=2500.0,
    )
    inversor_hoymiles.ultimo_snapshot = snap
    inversor_hoymiles.save(update_fields=['ultimo_snapshot'])
    return snap


@pytest.fixture
def inversor_inativo(db, usina):
    """Inversor sem snapshot (ultimo_snapshot=None) — exclui do ranking ANA-02."""
    return Inversor.objects.create(
        usina=usina,
        id_inversor_provedor='inv-inativo-001',
        numero_serie='SN-INATIVO',
        modelo='Solis 3K',
    )


@pytest.fixture
def inversor_pac_zero(db, usina):
    """Inversor com snapshot mas pac_kw=0 — exclui do ranking ANA-02."""
    inv = Inversor.objects.create(
        usina=usina,
        id_inversor_provedor='inv-pac-zero-001',
        numero_serie='SN-PACZERO',
        modelo='Solis 5K',
    )
    snap = SnapshotInversor.objects.create(
        inversor=inv,
        coletado_em=timezone.now(),
        estado='offline',
        pac_kw=0.0,
        energia_hoje_kwh=0.0,
        energia_total_kwh=1000.0,
    )
    inv.ultimo_snapshot = snap
    inv.save(update_fields=['ultimo_snapshot'])
    return inv
