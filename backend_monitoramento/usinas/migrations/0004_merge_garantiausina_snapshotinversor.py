# Merge migration: une as branches 0002_garantiausina e 0003_snapshotinversor_frequencia_temperatura
# Gerado manualmente para resolver conflito de migracao detectado durante execucao de testes.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('usinas', '0002_garantiausina'),
        ('usinas', '0003_snapshotinversor_frequencia_temperatura'),
    ]

    operations = [
    ]
