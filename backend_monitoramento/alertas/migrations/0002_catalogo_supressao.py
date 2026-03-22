import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('alertas', '0001_initial'),
        ('usinas', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CatalogoAlarme',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('provedor', models.CharField(db_index=True, max_length=50)),
                ('id_alarme_provedor', models.CharField(max_length=100, verbose_name='ID do alarme no provedor')),
                ('nome_pt', models.CharField(max_length=200, verbose_name='Nome em português')),
                ('nome_original', models.CharField(blank=True, max_length=200, verbose_name='Nome original (do provedor)')),
                ('tipo', models.CharField(blank=True, max_length=100, verbose_name='Categoria/tipo')),
                ('nivel_padrao', models.CharField(
                    choices=[('info', 'Info'), ('aviso', 'Aviso'), ('importante', 'Importante'), ('critico', 'Crítico')],
                    default='aviso',
                    max_length=10,
                    verbose_name='Nível padrão',
                )),
                ('nivel_sobrescrito', models.BooleanField(
                    default=False,
                    verbose_name='Nível sobrescrito pelo operador',
                    help_text='Quando True, o nivel_padrao foi definido manualmente e não será alterado por atualizações automáticas da coleta.',
                )),
                ('suprimido', models.BooleanField(
                    default=False,
                    verbose_name='Suprimido globalmente',
                    help_text='Quando True, este tipo de alarme não gera registros nem notificações em nenhuma usina.',
                )),
                ('sugestao', models.TextField(blank=True, verbose_name='Sugestão de resolução')),
                ('criado_auto', models.BooleanField(
                    default=False,
                    verbose_name='Criado automaticamente',
                    help_text='True quando a entrada foi criada durante a coleta (alarme não documentado).',
                )),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Catálogo de Alarme',
                'verbose_name_plural': 'Catálogo de Alarmes',
                'ordering': ['provedor', 'id_alarme_provedor'],
                'unique_together': {('provedor', 'id_alarme_provedor')},
            },
        ),
        migrations.CreateModel(
            name='RegraSupressao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('escopo', models.CharField(
                    choices=[('usina', 'Somente esta usina'), ('todas', 'Todas as usinas')],
                    max_length=10,
                )),
                ('motivo', models.TextField(blank=True, verbose_name='Motivo da supressão')),
                ('ativo_ate', models.DateTimeField(
                    blank=True,
                    null=True,
                    verbose_name='Ativo até',
                    help_text='Deixe em branco para supressão permanente.',
                )),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('catalogo', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='regras_supressao',
                    to='alertas.catalogoalarme',
                )),
                ('usina', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='regras_supressao',
                    to='usinas.usina',
                    help_text='Obrigatório quando escopo=usina. Ignorado quando escopo=todas.',
                )),
            ],
            options={
                'verbose_name': 'Regra de Supressão',
                'verbose_name_plural': 'Regras de Supressão',
                'ordering': ['-criado_em'],
            },
        ),
        migrations.AddField(
            model_name='alerta',
            name='catalogo_alarme',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='alertas',
                to='alertas.catalogoalarme',
                verbose_name='Tipo de alarme (catálogo)',
            ),
        ),
        migrations.AlterField(
            model_name='alerta',
            name='nivel',
            field=models.CharField(
                choices=[('info', 'Info'), ('aviso', 'Aviso'), ('importante', 'Importante'), ('critico', 'Crítico')],
                db_index=True,
                default='aviso',
                max_length=10,
            ),
        ),
    ]
