from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usinas', '0002_snapshotinversor_tensao_corrente'),
    ]

    operations = [
        migrations.AddField(
            model_name='snapshotinversor',
            name='frequencia_hz',
            field=models.FloatField(blank=True, null=True, verbose_name='Frequência (Hz)'),
        ),
        migrations.AddField(
            model_name='snapshotinversor',
            name='temperatura_c',
            field=models.FloatField(blank=True, null=True, verbose_name='Temperatura (°C)'),
        ),
    ]
