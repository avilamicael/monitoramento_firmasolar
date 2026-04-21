from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('provedores', '0004_update_intervalo_default_30'),
    ]

    operations = [
        migrations.AlterField(
            model_name='credencialprovedor',
            name='provedor',
            field=models.CharField(
                choices=[
                    ('solis', 'Solis Cloud'),
                    ('hoymiles', 'Hoymiles S-Cloud'),
                    ('fusionsolar', 'Huawei FusionSolar'),
                    ('solarman', 'Solarman Pro'),
                    ('auxsol', 'AuxSol Cloud'),
                    ('foxess', 'FoxESS Cloud'),
                ],
                max_length=30,
                unique=True,
            ),
        ),
    ]
