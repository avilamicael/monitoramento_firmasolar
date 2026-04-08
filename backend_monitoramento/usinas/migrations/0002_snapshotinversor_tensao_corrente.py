from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usinas', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='snapshotinversor',
            name='tensao_ac_v',
            field=models.FloatField(blank=True, null=True, verbose_name='Tensão AC (V)'),
        ),
        migrations.AddField(
            model_name='snapshotinversor',
            name='corrente_ac_a',
            field=models.FloatField(blank=True, null=True, verbose_name='Corrente AC (A)'),
        ),
        migrations.AddField(
            model_name='snapshotinversor',
            name='tensao_dc_v',
            field=models.FloatField(blank=True, null=True, verbose_name='Tensão DC (V)'),
        ),
        migrations.AddField(
            model_name='snapshotinversor',
            name='corrente_dc_a',
            field=models.FloatField(blank=True, null=True, verbose_name='Corrente DC (A)'),
        ),
    ]
