from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notificacoes', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuracaonotificacao',
            name='notificar_importante',
            field=models.BooleanField(default=True, verbose_name='Notificar alertas importantes'),
        ),
        migrations.AddField(
            model_name='configuracaonotificacao',
            name='notificar_info',
            field=models.BooleanField(default=False, verbose_name='Notificar alertas informativos'),
        ),
    ]
