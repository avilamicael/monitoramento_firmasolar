import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

app = Celery('monitoramento')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# ── Agendamentos ───────────────────────────────────────────────────────────────
app.conf.beat_schedule = {
    # Coleta dados de todos os provedores ativos a cada 10 minutos
    'coletar-todos-provedores': {
        'task': 'coleta.tasks.disparar_coleta_geral',
        'schedule': crontab(minute='*/10'),
    },
    # Renova tokens de provedores com sessão (Hoymiles, FusionSolar) a cada 6h
    'renovar-tokens': {
        'task': 'coleta.tasks.renovar_tokens_provedores',
        'schedule': crontab(minute=0, hour='*/6'),
    },
    # Remove snapshots antigos diariamente às 3h da manhã
    'limpar-snapshots-antigos': {
        'task': 'coleta.tasks.limpar_snapshots_antigos',
        'schedule': crontab(minute=0, hour=3),
    },
}
